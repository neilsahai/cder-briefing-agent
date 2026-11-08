"""The agent run: gate → interpretations → planner tool loop → narrator → render → verifier → tier.

Each stage writes a trace step. The run returns an Answer with the rendered text, claim verdicts,
trust tier, interpretations, warnings, evidence, and the full trace.
"""
from __future__ import annotations

import json
from typing import Any, Callable

from pydantic import BaseModel, Field

from ..llm.provider import get_provider, structured, text_of, tool_uses
from ..llm.routing import planner_escalation
from ..models import Interpretation, RowRef, Warning
from ..tools import REGISTRY, anthropic_tool_specs, call_tool
from ..registry.certified import get_registry
from ..registry.runs import save_run
from .sql_candidates import run_sql_candidates
from . import prompts
from .evidence import EvidenceRegistry, RenderError, citations_in, render
from ..tools.warnings_util import group_warnings_by_code
from .schemas import DECLARE_INTERPRETATIONS_TOOL, FINISH_TOOL, GATE_TOOL, NARRATE_TOOL, VERIFY_TOOL
from .trace import Trace, Tracer, TraceStep

MAX_TOOL_ITERATIONS = 12
MAX_NARRATION_RETRIES = 2
MAX_REVISIONS = 1

TIER_LABELS = {1: "Certified", 2: "Derived", 3: "Qualified", 4: "Not answerable from this data"}


class Claim(BaseModel):
    text: str
    verdict: str
    evidence_ids: list[str] = Field(default_factory=list)
    expected_source_table: str | None = None
    note: str | None = None


class Answer(BaseModel):
    run_id: str
    question: str
    tier: int
    tier_label: str
    tier_reasons: list[str]
    headline: str
    markdown: str
    markdown_template: str
    gate: dict[str, Any]
    interpretations_declared: list[dict[str, Any]]
    interpretations_applied: list[Interpretation]
    divergent_interpretations: list[dict[str, Any]]
    cannot_answer: list[str]
    warnings: list[Warning]
    claims: list[Claim]
    verification: dict[str, Any]
    evidence: list[dict[str, Any]]
    rows: list[RowRef]
    substitutions: list[dict[str, Any]]
    certified_query_match: dict[str, Any] | None = None
    pins: dict[str, str] = Field(default_factory=dict)
    escalation: dict[str, Any]
    trace: Trace
    manual_lookups_replaced: int


def _tool_result_payload(ev_id: str, result) -> str:
    """What the planner sees after a tool call: compact value + warnings + interpretations, keyed by evidence id."""
    v = result.value
    if isinstance(v, dict):
        v = {k: (f"<{len(x)} records; see evidence>" if isinstance(x, list) and len(x) > 15 and k in ("records", "application_records") else x) for k, x in v.items()}
    return json.dumps({
        "evidence_id": ev_id,
        "value": v,
        "rows_cited": len(result.rows),
        "coverage": result.coverage,
        "interpretations": [f"{i.term} → {i.chosen} (alt {i.alternatives}) [{i.decision_ref}]" for i in result.interpretations],
        "warnings": [f"[{w.severity.value}] {w.code}: {w.message}" for w in result.warnings],
    }, default=str)


def run(question: str, *, as_of: str | None = None, pins: dict[str, str] | None = None,
        sink: Callable[[TraceStep], None] | None = None, use_registry: bool = True, persist: bool = True) -> Answer:
    tracer = Tracer(question, sink)
    prov = get_provider()
    registry = EvidenceRegistry()
    pins = dict(pins or {})

    # ------------------------------------------------------------------ 0. certified registry match
    cq_match = None
    if use_registry:
        cand = get_registry().match(question)
        if cand and cand["match_kind"] == "borderline":
            # confirm with a small model: is this the same question (same facts asked, same scope)?
            conf, ccall, _ = structured(prov, "entity", system="You compare two analyst questions over the same FDA dataset.",
                                        messages=[{"role": "user", "content": f"Q_NEW: {question}\nQ_CERTIFIED: {cand['question']}\nDo they ask for the same facts with the same scope, such that the certified answer plan would correctly answer Q_NEW?"}],
                                        tool={"name": "same_question", "description": "Decide if the two questions are equivalent.",
                                              "input_schema": {"type": "object", "properties": {"equivalent": {"type": "boolean"}, "reason": {"type": "string"}}, "required": ["equivalent", "reason"]}},
                                        max_tokens=300)
            tracer.step("info", f"Borderline certified match (score {cand['score']}) → {'confirmed' if conf['equivalent'] else 'rejected'}", llm=ccall, output=conf)
            cand = cand if conf["equivalent"] else None
        if cand:
            cq_match = {"name": cand["name"], "tool": cand["tool"], "args": cand["args"], "pins": cand["pins"], "verified_by": cand["verified_by"],
                        "verified_at": cand["verified_at"], "version": cand["version"], "score": cand["score"]}
            for k, v in cand["pins"].items():
                pins.setdefault(k, v)
            tracer.step("info", f"Certified query match: {cand['name']} (score {cand['score']})", output=cq_match)
    if pins:
        tracer.step("info", f"Interpretations pinned: {len(pins)}", output=pins)

    # ------------------------------------------------------------------ 1. gate
    gate, call, _ = structured(prov, "gate", system=prompts.gate_system(), messages=[{"role": "user", "content": question}], tool=GATE_TOOL, max_tokens=800)
    valid = {"answerable", "in_scope_not_in_data", "out_of_scope", "unsafe_or_policy"}
    if gate.get("category") not in valid:
        raw = gate.get("category")
        # models sometimes invent 'partially_answerable'; a partially answerable question IS answerable with disclosure
        gate["category"] = "answerable" if gate.get("answerable_part") else "in_scope_not_in_data"
        gate["category_raw"] = raw
    tracer.step("gate", f"Answerability: {gate['category']}", llm=call, input=question, output=gate,
                status="ok" if gate["category"] == "answerable" else "warn")

    if gate["category"] in ("out_of_scope", "unsafe_or_policy"):
        md = (f"**Not answerable from this data.** {gate['reason']}\n\n"
              + (f"What this tool can answer: {gate.get('answerable_part')}" if gate.get("answerable_part") else
                 "This tool answers questions about drug shortage records, drug applications, and establishment inspections in the provided FDA snapshot."))
        tracer.step("tier", "Tier 4", output={"tier": 4})
        a4 = Answer(run_id=tracer.trace.run_id, question=question, tier=4, tier_label=TIER_LABELS[4],
                    tier_reasons=[gate["reason"]], headline="Not answerable from this data.", markdown=md, markdown_template=md,
                    gate=gate, interpretations_declared=[], interpretations_applied=[], divergent_interpretations=[],
                    cannot_answer=[gate.get("unanswerable_part") or gate["reason"]], warnings=[], claims=[], verification={},
                    evidence=[], rows=[], substitutions=[], pins=pins, escalation={"escalate": False, "reasons": []}, trace=tracer.trace,
                    manual_lookups_replaced=0)
        if persist:
            save_run(json.loads(a4.model_dump_json()))
        return a4

    # ------------------------------------------------------------------ 2. planner (declare interpretations first)
    tools = anthropic_tool_specs() + [DECLARE_INTERPRETATIONS_TOOL, FINISH_TOOL]
    user_msg = question if not as_of else f"{question}\n\n(as_of date to use: {as_of})"
    if cq_match:
        user_msg += (f"\n\nCERTIFIED PLAN AVAILABLE: tool `{cq_match['tool']}` with args {json.dumps(cq_match.get('args', {}))} was verified by "
                     f"{cq_match['verified_by']} for this question. Call it with exactly these args as your primary evidence. "
                     f"If the question actually differs from the certified one (a different year, drug, or scope), adapt the args — "
                     f"the answer will then not carry certified status, which is correct.")
    if pins:
        user_msg += ("\n\nINTERPRETATIONS PINNED BY THE ANALYST (treat as resolved; do not present alternates as open): "
                     + "; ".join(f"'{k}' = {v}" for k, v in pins.items()))
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_msg}]

    # first turn: force declare_interpretations
    declared, call, decl_use = structured(prov, "planner", system=prompts.planner_system(), messages=messages,
                                          tool=DECLARE_INTERPRETATIONS_TOOL, extra_tools=anthropic_tool_specs() + [FINISH_TOOL], max_tokens=1500)
    tracer.step("plan", "Interpretations declared", llm=call, output=declared)
    messages.append({"role": "assistant", "content": call.response.content})
    messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": decl_use.id,
                                                  "content": "Recorded. Proceed with tool calls; call finish when done."}]})

    # escalation decision (deterministic)
    n_div = sum(1 for i in declared.get("interpretations", []) if i.get("will_compute_alternate"))
    needs_sql = any("sql_query" in s for s in declared.get("plan", []))
    esc = planner_escalation(n_div, needs_sql, gate["category"])
    tracer.step("escalation", f"Planner model: {'Opus (escalated)' if esc.escalate else 'Sonnet'}",
                output={"escalate": esc.escalate, "reasons": esc.reasons}, status="warn" if esc.escalate else "ok")

    finish: dict[str, Any] | None = None
    used_sql = False

    def process_uses(uses, call) -> list[dict[str, Any]]:
        nonlocal finish, used_sql
        results_content = []
        first_llm_attached = False
        for u in uses:
            if u.name == "finish":
                finish = u.input
                tracer.step("plan", "Planner finished", llm=None if first_llm_attached else call, output=finish)
                first_llm_attached = True
                results_content.append({"type": "tool_result", "tool_use_id": u.id, "content": "ok"})
                continue
            if u.name == "declare_interpretations":
                results_content.append({"type": "tool_result", "tool_use_id": u.id, "content": "Recorded. Proceed with tool calls; call finish when done."})
                continue
            t = tracer.timer()
            try:
                res = call_tool(u.name, u.input)
                if u.name == "sql_query" and not res.value.get("error"):
                    used_sql = True
                    res = run_sql_candidates(prov, tracer, u.input, res)
                ev = registry.add(u.name, u.input, res, certified=REGISTRY[u.name].certified)
                payload = _tool_result_payload(ev.id, res)
                tracer.step("sql" if u.name == "sql_query" else "tool_call", f"{u.name} → {ev.id}", llm=None if first_llm_attached else call,
                            input=u.input, output={"evidence_id": ev.id, "rows_cited": len(res.rows), "warnings": [w.code for w in res.warnings],
                                                   "value_preview": json.loads(payload)["value"]}, duration_ms=t.ms(),
                            status="warn" if any(w.severity.value == "high" for w in res.warnings) else "ok")
                first_llm_attached = True
                results_content.append({"type": "tool_result", "tool_use_id": u.id, "content": payload})
            except Exception as ex:  # noqa: BLE001
                tracer.step("error", f"{u.name} failed", input=u.input, output=str(ex), duration_ms=t.ms(), status="fail")
                results_content.append({"type": "tool_result", "tool_use_id": u.id, "content": f"TOOL ERROR: {ex}", "is_error": True})
        return results_content

    # the first (declaration) turn may also contain data tool calls — honor all of them
    messages.pop()  # remove the single-result message added above; rebuild with results for every tool_use
    messages.append({"role": "user", "content": process_uses(tool_uses(call.response), None)})

    for _ in range(MAX_TOOL_ITERATIONS):
        if finish is not None:
            break
        call = prov.messages(esc.role, system=prompts.planner_system(), messages=messages, tools=tools, max_tokens=2500)
        uses = tool_uses(call.response)
        messages.append({"role": "assistant", "content": call.response.content})
        if not uses:
            messages.append({"role": "user", "content": "Call `finish` with the evidence ids to use. Do not answer in prose."})
            tracer.step("info", "Planner nudged to call finish", llm=call, output=text_of(call.response)[:500], status="warn")
            continue
        messages.append({"role": "user", "content": process_uses(uses, call)})

    if finish is None:
        finish = {"evidence_used": [e.id for e in registry.items], "divergent_interpretations": [], "used_sql": used_sql,
                  "cannot_answer": ["Planner did not finish within the step budget."], "analyst_notes": ""}
        tracer.step("error", "Planner step budget exhausted", status="fail")

    # ------------------------------------------------------------------ 3. narrator + render (retry on render failure)
    narr_user = (f"QUESTION: {question}\n\nGATE: {json.dumps(gate)}\n\nINTERPRETATIONS DECLARED: {json.dumps(declared)}\n\n"
                 f"PLANNER FINISH: {json.dumps(finish)}\n\n# EVIDENCE\n{registry.for_prompt()}")
    template, headline_t, rendered, headline, subs = "", "", "", "", []
    last_err = None
    for attempt in range(MAX_NARRATION_RETRIES + 1):
        msgs = [{"role": "user", "content": narr_user if attempt == 0 else narr_user + f"\n\nYOUR PREVIOUS DRAFT FAILED RENDERING: {last_err}\nFix it. Remember: no digits anywhere except inside placeholders."}]
        out, call, _ = structured(prov, "narrator", system=prompts.NARRATOR_SYSTEM, messages=msgs, tool=NARRATE_TOOL, max_tokens=4000)
        if "markdown" not in out or "headline" not in out:
            last_err = f"narrator returned keys {list(out)} (stop_reason={call.stop_reason}); expected markdown+headline"
            tracer.step("narrate", "Narration malformed", llm=call, output={"raw": str(out)[:2000], "stop_reason": call.stop_reason}, status="fail")
            continue
        template, headline_t = out["markdown"], out["headline"]
        tracer.step("narrate", f"Narration draft {attempt + 1}", llm=call, output={"markdown_template": template, "headline_template": headline_t})
        try:
            rendered, subs = render(template, registry)
            headline, hsubs = render(headline_t, registry)
            subs += hsubs
            tracer.step("render", f"Rendered {len(subs)} placeholders; no literal digits", output={"substitutions": subs})
            last_err = None
            break
        except RenderError as ex:
            last_err = str(ex)
            tracer.step("render", "Render failed", output=last_err, status="fail")
    if last_err:
        rendered = ("**Answer withheld.** The narration could not be rendered without an unverifiable value "
                    f"({last_err}). Evidence is available below; no numbers were generated by the model.")
        headline = "Answer withheld: unverifiable value in narration."

    # ------------------------------------------------------------------ 4. verifier (independent model) + one revision loop
    verification: dict[str, Any] = {}
    claims: list[Claim] = []
    revisions = 0

    def _verify(text: str) -> tuple[dict[str, Any], list[Claim]]:
        ver_user = f"RENDERED ANSWER:\n{text}\n\n# EVIDENCE REGISTRY\n{registry.for_prompt()}"
        v, vcall, _ = structured(prov, "verifier", system=prompts.VERIFIER_SYSTEM, messages=[{"role": "user", "content": ver_user}], tool=VERIFY_TOOL, max_tokens=8000)
        cl = [Claim(**c) for c in v.get("claims", [])]
        bad = [c for c in cl if c.verdict in ("unsupported", "misattributed")]
        tracer.step("verify", f"Verifier: {v.get('overall')} — {len(cl)} claims, {len(bad)} flagged", llm=vcall, output=v,
                    status="ok" if v.get("overall") == "pass" and not bad else ("warn" if v.get("overall") == "pass_with_notes" else "fail"))
        missing = [c for c in citations_in(text) if registry.get(c) is None]
        if missing:
            tracer.step("verify", "Dangling citations", output=missing, status="fail")
            cl.append(Claim(text=f"Citations {missing} do not exist in evidence", verdict="unsupported"))
        return v, cl

    if not last_err:
        verification, claims = _verify(rendered)
        flagged = [c for c in claims if c.verdict in ("unsupported", "misattributed")]
        checklist = [k for k in ("interpretations_disclosed", "high_warnings_surfaced", "status_semantics_respected", "no_country_asserted_for_unknown") if verification.get(k) is False]
        if (flagged or verification.get("overall") == "fail") and revisions < MAX_REVISIONS:
            revisions += 1
            issues = [f"- [{c.verdict}] \"{c.text}\" — {c.note or ''}" for c in flagged]
            issues += [f"- [checklist] {k} = false" for k in checklist]
            issues.append(f"- [verifier summary] {verification.get('summary', '')}")
            fix_msg = (narr_user + "\n\nYOUR PREVIOUS DRAFT WAS CHECKED BY AN INDEPENDENT VERIFIER. Fix every item below — reword or remove flagged claims so each is exactly what the evidence supports; add any missing interpretation disclosure or high-severity caveat:\n"
                       + "\n".join(issues)
                       + "\n\nPREVIOUS DRAFT (template):\n" + template + "\n\nReturn the full corrected answer. No digits outside placeholders.")
            out, call, _ = structured(prov, "narrator", system=prompts.NARRATOR_SYSTEM, messages=[{"role": "user", "content": fix_msg}], tool=NARRATE_TOOL, max_tokens=4000)
            if "markdown" in out and "headline" in out:
                try:
                    r2, s2 = render(out["markdown"], registry)
                    h2, hs2 = render(out["headline"], registry)
                    template, headline_t, rendered, headline, subs = out["markdown"], out["headline"], r2, h2, s2 + hs2
                    tracer.step("narrate", f"Narration revised after verifier ({len(flagged)} claim(s), {len(checklist)} checklist item(s))", llm=call, output={"fixed": [c.text for c in flagged] + checklist})
                    verification, claims = _verify(rendered)
                except RenderError as ex:
                    tracer.step("render", "Revision failed to render; keeping verified-with-notes draft", llm=call, output=str(ex), status="warn")
            else:
                tracer.step("narrate", "Revision malformed; keeping original draft", llm=call, status="warn")

    # ------------------------------------------------------------------ 5. trust tier
    warnings = group_warnings_by_code(registry.all_warnings())
    interps = registry.all_interpretations()
    reasons: list[str] = []
    def _pinned(term: str) -> bool:
        t = term.lower()
        return any(k.lower() in t or t in k.lower() for k in pins)
    divergent_all = [d for d in finish.get("divergent_interpretations", []) if d.get("differs_materially")]
    # deterministic: tool-reported divergence (certified queries compute their alternates)
    seen_terms = {d.get("term", "").lower() for d in divergent_all}
    for i in interps:
        if i.differs and i.term.lower() not in seen_terms:
            divergent_all.append({"term": i.term, "differs_materially": True, "how": i.note or "", "source": "tool"})
            seen_terms.add(i.term.lower())
    divergent = [d for d in divergent_all if not _pinned(d.get("term", ""))]
    pinned_resolved = [d for d in divergent_all if _pinned(d.get("term", ""))]
    if pinned_resolved:
        reasons.append(f"{len(pinned_resolved)} ambiguous term(s) resolved by analyst pins: " + ", ".join(d['term'] for d in pinned_resolved))
    tier = 1
    flagged_final = [c for c in claims if c.verdict in ("unsupported", "misattributed")]
    checklist_fail = [k for k in ("interpretations_disclosed", "high_warnings_surfaced", "status_semantics_respected", "no_country_asserted_for_unknown") if verification and verification.get(k) is False]
    if last_err:
        tier = 3
        reasons.append("narration could not be rendered safely")
    elif flagged_final:
        tier = 3
        reasons.append(f"verifier flagged {len(flagged_final)} claim(s) after revision: " + "; ".join(c.text[:60] for c in flagged_final[:2]))
    elif verification and verification.get("overall") == "fail":
        tier = 3
        reasons.append("verifier checklist failed: " + (", ".join(checklist_fail) if checklist_fail else verification.get("summary", "")[:120]))
    if used_sql or finish.get("used_sql"):
        tier = max(tier, 2)
        reasons.append("answer depends on LLM-authored SQL (validated, executed, not certified)")
    if divergent:
        tier = max(tier, 3)
        reasons.append(f"{len(divergent)} interpretation(s) give materially different answers; shown side by side")
    if gate["category"] == "in_scope_not_in_data" or finish.get("cannot_answer"):
        reasons.append("part of the question cannot be answered from this data (disclosed)")
        if gate["category"] == "in_scope_not_in_data" and not registry.items:
            tier = 4
    if tier == 1 and any(not e.certified for e in registry.items):
        tier = 2
        reasons.append("some evidence came from a non-certified tool")
    if tier == 1:
        reasons.append("all evidence from certified tools; interpretations disclosed; verifier passed")
    cq_applied = bool(cq_match) and any(e.tool == cq_match["tool"] and all(e.args.get(k) == v for k, v in cq_match.get("args", {}).items()) for e in registry.items)
    if cq_match and not cq_applied:
        reasons.append(f"certified query '{cq_match['name']}' was suggested but its exact plan was not used; no certified credit")
        cq_match = {**cq_match, "applied": False}
    elif cq_match:
        cq_match = {**cq_match, "applied": True}
        if tier == 1:
            reasons.append(f"matches certified query '{cq_match['name']}' verified by {cq_match.get('verified_by')}")
    tracer.step("tier", f"Tier {tier} — {TIER_LABELS[tier]}", output={"tier": tier, "reasons": reasons})

    # manual lookups replaced: one per cited row across distinct tables, a conservative proxy
    lookups = len(registry.all_rows())
    tracer.step("final", "Answer assembled", output={"rows_cited": lookups, **tracer.trace.totals()})

    answer = Answer(run_id=tracer.trace.run_id, question=question, tier=tier, tier_label=TIER_LABELS[tier], tier_reasons=reasons,
                  headline=headline, markdown=rendered, markdown_template=template, gate=gate,
                  interpretations_declared=declared.get("interpretations", []), interpretations_applied=interps,
                  divergent_interpretations=finish.get("divergent_interpretations", []), cannot_answer=finish.get("cannot_answer", []),
                  warnings=warnings, claims=claims, verification=verification,
                  evidence=[{"id": e.id, "tool": e.tool, "args": e.args, "certified": e.certified, "rows": [r.id for r in e.result.rows],
                             "source_tables": e.result.source_tables, "value": e.result.value,
                             "warnings": [w.model_dump() for w in e.result.warnings],
                             "interpretations": [i.model_dump() for i in e.result.interpretations]} for e in registry.items],
                  rows=registry.all_rows(), substitutions=subs, certified_query_match=cq_match, pins=pins,
                  escalation={"escalate": esc.escalate, "reasons": esc.reasons}, trace=tracer.trace, manual_lookups_replaced=lookups)
    if persist:
        save_run(json.loads(answer.model_dump_json()))
    return answer
