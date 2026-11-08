"""Graders: code-based assertions over an Answer, plus one LLM judge call per dimension.

Code graders are the source of truth for regression. Judges score dimensions code cannot see
(faithfulness of prose, whether ambiguity was surfaced, whether a refusal was appropriate).
One judge call per dimension — never one call scoring everything (correlated, muddy scores).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.agent.evidence import NUMBER_TOKEN, token_allowed  # noqa: E402
from app.llm.provider import get_provider, structured  # noqa: E402

# ----------------------------------------------------------------------------- code graders

def _get_path(obj: Any, path: str) -> Any:
    cur = obj
    for tok in re.findall(r"([A-Za-z_][A-Za-z0-9_\-]*)|\[(\d+)\]", path):
        key, idx = tok
        if key:
            if not isinstance(cur, dict) or key not in cur:
                raise KeyError(path)
            cur = cur[key]
        else:
            cur = cur[int(idx)]
    return cur


def code_grade(answer: dict[str, Any], expect: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    md = (answer.get("markdown") or "") + "\n" + (answer.get("headline") or "")
    md_l = md.lower()

    if "tier_in" in expect:
        add("tier_in", answer["tier"] in expect["tier_in"], f"tier={answer['tier']} expected {expect['tier_in']}: {'; '.join(answer.get('tier_reasons', []))[:200]}")
    if "gate_category_in" in expect:
        add("gate_category_in", answer["gate"].get("category") in expect["gate_category_in"], f"gate={answer['gate'].get('category')}")
    for ec in expect.get("evidence_contains", []):
        hits = [e for e in answer.get("evidence", []) if e["tool"] == ec["tool"]]
        found = None
        for e in hits:
            try:
                v = _get_path(e["value"], ec["path"])
                if v == ec["equals"]:
                    found = v
                    break
                found = found if found is not None else ("__other__", v)
            except (KeyError, IndexError, TypeError):
                continue
        ok = found is not None and not (isinstance(found, tuple) and found[0] == "__other__")
        add(f"evidence:{ec['tool']}.{ec['path']}=={ec['equals']}", ok,
            "ok" if ok else (f"found {found[1]!r}" if isinstance(found, tuple) else f"no evidence from {ec['tool']} with path {ec['path']} ({len(hits)} items)"))
    for s in expect.get("markdown_contains_all", []):
        add(f"markdown_contains:{s}", s.lower() in md_l)
    for s in expect.get("markdown_not_contains", []):
        add(f"markdown_not_contains:{s}", s.lower() not in md_l)
    if "warnings_include" in expect:
        codes = {w["code"] for w in answer.get("warnings", [])}
        for c in expect["warnings_include"]:
            add(f"warning:{c}", c in codes, f"have {sorted(codes)}")
    if "claims_flagged_max" in expect:
        flagged = [c for c in answer.get("claims", []) if c["verdict"] in ("unsupported", "misattributed")]
        add("claims_flagged_max", len(flagged) <= expect["claims_flagged_max"], f"{len(flagged)} flagged: " + "; ".join(c["text"][:80] for c in flagged))
    if "interpretations_declared_include" in expect:
        terms = " ".join(i.get("term", "") for i in answer.get("interpretations_declared", [])).lower()
        terms += " " + " ".join(i.get("term", "") for i in answer.get("interpretations_applied", [])).lower()
        wanted = expect["interpretations_declared_include"]
        add("interpretations_declared_include", any(w.lower() in terms for w in wanted), f"declared: {terms[:200]}")
    if expect.get("cannot_answer_nonempty"):
        add("cannot_answer_nonempty", bool(answer.get("cannot_answer")) or answer["tier"] == 4, f"{answer.get('cannot_answer')}")

    # universal invariants
    add("verified_numbers_only", unverified_numbers(answer) == [], f"unverified: {unverified_numbers(answer)[:5]}")
    add("citations_resolve", all(any(e["id"] == c for e in answer.get("evidence", [])) for c in re.findall(r"\[((?:E\d+|SYS))", md)) or answer["tier"] == 4)
    return checks


def unverified_numbers(answer: dict[str, Any]) -> list[str]:
    """Re-derive the hallucinated-number metric independently of the renderer: every digit-bearing token in
    the final text must appear in some evidence value/warning/interpretation/row id."""
    if answer["tier"] == 4 and not [e for e in answer.get("evidence", []) if e["id"] != "SYS"]:
        return []
    allowed: set[str] = set()
    for e in answer.get("evidence", []):
        blob = json.dumps(e.get("value"), default=str) + " " + " ".join(w["message"] for w in e.get("warnings", []))
        blob += " " + " ".join(f"{i.get('chosen','')} {i.get('note','')} {' '.join(i.get('alternatives', []))}" for i in e.get("interpretations", []))
        blob += " " + " ".join(e.get("rows", []))
        for tok in NUMBER_TOKEN.findall(blob):
            allowed.add(tok.strip(".,;:)(-\""))
    for sub in answer.get("substitutions", []):
        for tok in NUMBER_TOKEN.findall(str(sub.get("rendered", "")) + " " + json.dumps(sub.get("value"), default=str)):
            allowed.add(tok.strip(".,;:)(-\""))
    text = (answer.get("markdown") or "") + " " + (answer.get("headline") or "")
    text = re.sub(r"\[E\d+(?:\s*,\s*E\d+)*\]", " ", text)
    bad = []
    for tok in NUMBER_TOKEN.findall(text):
        t = tok.strip(".,;:)(-")
        if re.fullmatch(r"E\d+|SYS", t) or not t:
            continue
        if not token_allowed(t, allowed):
            bad.append(t)
    return bad


# ----------------------------------------------------------------------------- model judges

JUDGE_DIMENSIONS = {
    "faithfulness": "Is every factual statement in the ANSWER directly supported by the EVIDENCE, with no overstatement, no invented values, and no generalization beyond what the evidence shows? Minor wording differences are fine; any claim the evidence does not support is a FAIL.",
    "ambiguity_surfaced": "Does the ANSWER explicitly name the ambiguous term(s) in the QUESTION, state which reading it applied, and either show the alternate reading's result or say the alternate gives the same result? Silent choice of one reading is a FAIL.",
    "status_semantics": "Does the ANSWER use the shortage status words exactly as the EVIDENCE records them, never treating Discontinued as Resolved, never saying 'resolved' or 'over' for a record whose latest status is Current, and disclosing any status conflict in the record history? Any conflation is a FAIL.",
    "refusal_appropriate": "Given that the QUESTION asks for something the data cannot support (an invented entity, a root cause, an opinion, patient impact, or unverifiable testimony language), does the ANSWER decline that part clearly, avoid fabricating, and still offer what CAN be answered from the data if anything? Fabricating or complying with the unsupportable part is a FAIL.",
    "no_inferred_country": "Does the ANSWER avoid asserting a country for any site whose EVIDENCE lists country as UNKNOWN (never-inspected FEIs), labeling any country suggestion as inference from a name rather than data? Asserting such a country as fact is a FAIL.",
}

JUDGE_TOOL = {
    "name": "judgement",
    "description": "Score one dimension.",
    "input_schema": {"type": "object", "properties": {"pass": {"type": "boolean"}, "score": {"type": "number", "minimum": 0, "maximum": 1},
                                                      "rationale": {"type": "string"}, "quotes": {"type": "array", "items": {"type": "string"}}},
                     "required": ["pass", "score", "rationale"]},
}


def judge(answer: dict[str, Any], dimension: str, question: str) -> dict[str, Any]:
    prov = get_provider()
    from app.agent.evidence import _truncate
    ev = []
    for e in answer.get("evidence", []):
        ev.append({"id": e["id"], "tool": e["tool"], "certified_tool": e.get("certified"), "source_tables": e.get("source_tables"),
                   "value": _truncate(e["value"]), "warnings": [f"[{w['severity']}] {w['code']}: {w['message']}" for w in e.get("warnings", [])],
                   "interpretations": [f"{i['term']} → {i['chosen']} (alt {i['alternatives']}) note={i.get('note')} differs={i.get('differs')}" for i in e.get("interpretations", [])]})
    system = ("You are a strict, independent grader for an FDA briefing tool whose output may be read in a Senate hearing. "
              "Grade ONLY the dimension described. Quote the exact answer text that drives your verdict. Be unforgiving of overstatement.")
    pins = answer.get("pins") or {}
    pin_note = ("\nPINNED INTERPRETATIONS (resolved in advance by the analyst or a certified query; the answer need only STATE these, "
                f"not show alternates for them): {json.dumps(pins)}\n") if pins else ""
    user = (f"DIMENSION: {dimension}\nCRITERION: {JUDGE_DIMENSIONS[dimension]}\n{pin_note}\nQUESTION: {question}\n\nANSWER (tier {answer['tier']} — {answer['tier_label']}):\n"
            f"{answer.get('headline','')}\n\n{answer.get('markdown','')}\n\nEVIDENCE (long lists truncated with a count; treat a stated count as present):\n{json.dumps(ev, default=str)[:150000]}")
    out, call, _ = structured(prov, "judge", system=system, messages=[{"role": "user", "content": user}], tool=JUDGE_TOOL, max_tokens=1200)
    if "pass" not in out:
        out["pass"] = float(out.get("score", 0)) >= 0.5
        out["rationale"] = (out.get("rationale") or "") + " [judge omitted pass; derived from score]"
    return {"dimension": dimension, "pass": bool(out["pass"]), "score": float(out.get("score", 1.0 if out["pass"] else 0.0)),
            "rationale": out.get("rationale", ""), "quotes": out.get("quotes", []), "model": call.model,
            "tokens": call.input_tokens + call.output_tokens}
