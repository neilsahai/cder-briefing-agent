"""Eval runner.

  python evals/run_evals.py --suite regression --trials 1
  python evals/run_evals.py --suite capability --trials 1 --concurrency 3
  python evals/run_evals.py --suite all --trials 3        # pass^3 reliability view

Writes evals/results/<suite>_<timestamp>.json and updates evals/results/latest_<suite>.json + SCORECARD.md.
A case passes a trial when every code check passes AND every listed judge dimension passes.
pass@k = any trial passed; pass^k = all trials passed (the reliability number that matters for testimony).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "evals"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from app.agent.runner import run  # noqa: E402
from graders import code_grade, judge, unverified_numbers  # noqa: E402

RESULTS = ROOT / "evals" / "results"
RESULTS.mkdir(exist_ok=True, parents=True)


def load_cases(suite: str) -> list[dict]:
    files = {"regression": ["regression.yaml"], "capability": ["capability.yaml"], "all": ["regression.yaml", "capability.yaml"]}[suite]
    cases = []
    for f in files:
        d = yaml.safe_load((ROOT / "evals" / "cases" / f).read_text())
        for c in d["cases"]:
            c["suite"] = d["suite"]
            cases.append(c)
    return cases


def run_case(case: dict, trial: int) -> dict:
    t0 = time.perf_counter()
    rec = {"id": case["id"], "suite": case["suite"], "trial": trial, "question": case["question"]}
    try:
        ans = run(case["question"], as_of=case.get("as_of"), pins=case.get("pins"), use_registry=not case.get("no_registry", False), persist=True)
        a = json.loads(ans.model_dump_json())
        checks = code_grade(a, case.get("expect", {}))
        judges = []
        for dim in case.get("judge", []):
            try:
                judges.append(judge(a, dim, case["question"]))
            except Exception as ex:  # noqa: BLE001
                judges.append({"dimension": dim, "pass": False, "score": 0.0, "rationale": f"judge error: {ex}"})
        code_ok = all(c["pass"] for c in checks)
        judge_ok = all(j["pass"] for j in judges)
        tot = ans.trace.totals()
        flagged_pre = None
        for s in ans.trace.steps:
            if s.kind == "verify" and s.title.startswith("Verifier:"):
                try:
                    flagged_pre = int(s.title.split(", ")[1].split(" ")[0])
                except Exception:  # noqa: BLE001
                    pass
                break
        rec.update({
            "run_id": a["run_id"], "tier": a["tier"], "tier_label": a["tier_label"], "gate": a["gate"].get("category"),
            "passed": code_ok and judge_ok, "code_ok": code_ok, "judge_ok": judge_ok, "checks": checks, "judges": judges,
            "claims_total": len(a.get("claims", [])), "claims_flagged_final": len([c for c in a.get("claims", []) if c["verdict"] in ("unsupported", "misattributed")]),
            "claims_flagged_first_pass": flagged_pre, "unverified_numbers": unverified_numbers(a),
            "escalated": a["escalation"]["escalate"], "used_sql": any(s.kind == "sql" for s in ans.trace.steps),
            "certified_match": (a.get("certified_query_match") or {}).get("name"),
            "llm_calls": tot["llm_calls"], "tool_calls": tot["tool_calls"], "input_tokens": tot["input_tokens"], "output_tokens": tot["output_tokens"],
            "cost_usd": tot["cost_usd"], "latency_ms": int((time.perf_counter() - t0) * 1000), "rows_cited": len(a.get("rows", [])),
            "headline": a.get("headline"),
        })
    except Exception as ex:  # noqa: BLE001
        rec.update({"passed": False, "error": f"{type(ex).__name__}: {ex}", "traceback": traceback.format_exc()[-2000:], "latency_ms": int((time.perf_counter() - t0) * 1000)})
    return rec


def summarize(records: list[dict], suite: str) -> dict:
    by_case: dict[str, list[dict]] = {}
    for r in records:
        by_case.setdefault(r["id"], []).append(r)
    cases = []
    for cid, rs in by_case.items():
        passes = [r.get("passed", False) for r in rs]
        cases.append({"id": cid, "suite": rs[0]["suite"], "trials": len(rs), "pass_at_k": any(passes), "pass_pow_k": all(passes),
                      "pass_rate": sum(passes) / len(passes), "tiers": [r.get("tier") for r in rs],
                      "failed_checks": sorted({c["check"] for r in rs for c in r.get("checks", []) if not c["pass"]}),
                      "failed_judges": sorted({j["dimension"] for r in rs for j in r.get("judges", []) if not j["pass"]}),
                      "errors": [r["error"] for r in rs if r.get("error")]})
    ok = [r for r in records if "error" not in r]
    n = len(ok)
    def avg(k):
        vals = [r[k] for r in ok if r.get(k) is not None]
        return round(sum(vals) / len(vals), 1) if vals else None
    summary = {
        "suite": suite, "generated_at": datetime.now(timezone.utc).isoformat(), "n_cases": len(by_case), "n_trials": len(records),
        "case_pass_at_k": round(sum(c["pass_at_k"] for c in cases) / len(cases), 3) if cases else None,
        "case_pass_pow_k": round(sum(c["pass_pow_k"] for c in cases) / len(cases), 3) if cases else None,
        "trial_pass_rate": round(sum(1 for r in records if r.get("passed")) / len(records), 3) if records else None,
        "hallucinated_number_rate": round(sum(1 for r in ok if r.get("unverified_numbers")) / n, 3) if n else None,
        "claims_total": sum(r.get("claims_total", 0) for r in ok),
        "claims_flagged_final": sum(r.get("claims_flagged_final", 0) for r in ok),
        "citation_precision_final": round(1 - sum(r.get("claims_flagged_final", 0) for r in ok) / max(1, sum(r.get("claims_total", 0) for r in ok)), 4),
        "verifier_caught_first_pass_rate": round(sum(1 for r in ok if (r.get("claims_flagged_first_pass") or 0) > 0) / n, 3) if n else None,
        "tier_distribution": {t: sum(1 for r in ok if r.get("tier") == t) for t in (1, 2, 3, 4)},
        "escalation_rate": round(sum(1 for r in ok if r.get("escalated")) / n, 3) if n else None,
        "sql_rate": round(sum(1 for r in ok if r.get("used_sql")) / n, 3) if n else None,
        "avg_latency_ms": avg("latency_ms"), "avg_llm_calls": avg("llm_calls"), "avg_tool_calls": avg("tool_calls"),
        "avg_input_tokens": avg("input_tokens"), "avg_output_tokens": avg("output_tokens"), "avg_rows_cited": avg("rows_cited"),
        "total_cost_usd": round(sum(r["cost_usd"] for r in ok if r.get("cost_usd") is not None), 4) if ok and all(r.get("cost_usd") is not None for r in ok) else None,
        "errors": sum(1 for r in records if r.get("error")),
        "cases": cases,
    }
    return summary


def write_scorecard(summaries: dict[str, dict]) -> None:
    lines = ["# Eval scorecard", "", f"_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}. Numbers are measured by `evals/run_evals.py`; nothing here is estimated._", ""]
    for suite, s in summaries.items():
        lines += [f"## {suite} suite — {s['n_cases']} cases × {s['n_trials'] // max(1, s['n_cases'])} trial(s)", "",
                  "| Metric | Value |", "|---|---|",
                  f"| Case pass@k (any trial) | **{s['case_pass_at_k']:.0%}** |" if s["case_pass_at_k"] is not None else "| Case pass@k | n/a |",
                  f"| Case pass^k (all trials) | **{s['case_pass_pow_k']:.0%}** |" if s["case_pass_pow_k"] is not None else "| Case pass^k | n/a |",
                  f"| Hallucinated-number rate (digits in answer not present in evidence) | **{s['hallucinated_number_rate']:.1%}** |" if s["hallucinated_number_rate"] is not None else "",
                  f"| Claims verified / flagged after revision | {s['claims_total']} / {s['claims_flagged_final']} (precision {s['citation_precision_final']:.1%}) |",
                  f"| Runs where the verifier caught something on first pass | {s['verifier_caught_first_pass_rate']:.0%} |" if s["verifier_caught_first_pass_rate"] is not None else "",
                  f"| Tier distribution (1/2/3/4) | {s['tier_distribution'][1]} / {s['tier_distribution'][2]} / {s['tier_distribution'][3]} / {s['tier_distribution'][4]} |",
                  f"| Planner escalation rate | {s['escalation_rate']:.0%} |" if s["escalation_rate"] is not None else "",
                  f"| LLM-SQL (Tier 2 path) rate | {s['sql_rate']:.0%} |" if s["sql_rate"] is not None else "",
                  f"| Avg latency / LLM calls / tool calls | {s['avg_latency_ms']} ms / {s['avg_llm_calls']} / {s['avg_tool_calls']} |",
                  f"| Avg tokens in / out | {s['avg_input_tokens']} / {s['avg_output_tokens']} |",
                  f"| Avg rows cited per answer | {s['avg_rows_cited']} |",
                  f"| Total cost (USD, from pricing.json) | {s['total_cost_usd'] if s['total_cost_usd'] is not None else 'n/a — pricing table not configured'} |",
                  f"| Errors | {s['errors']} |", "",
                  "| Case | Pass | Tiers | Failed checks | Failed judges |", "|---|---|---|---|---|"]
        for c in s["cases"]:
            mark = "✅" if c["pass_pow_k"] else ("🟡" if c["pass_at_k"] else "❌")
            lines.append(f"| `{c['id']}` | {mark} {c['pass_rate']:.0%} | {c['tiers']} | {', '.join(c['failed_checks'])[:120]} | {', '.join(c['failed_judges'])} |")
        lines.append("")
    (RESULTS / "SCORECARD.md").write_text("\n".join(lines))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", choices=["regression", "capability", "all"], default="regression")
    ap.add_argument("--trials", type=int, default=1)
    ap.add_argument("--concurrency", type=int, default=3)
    ap.add_argument("--only", default=None, help="comma-separated case ids")
    a = ap.parse_args()
    cases = load_cases(a.suite)
    if a.only:
        ids = set(a.only.split(","))
        cases = [c for c in cases if c["id"] in ids]
    jobs = [(c, t) for c in cases for t in range(1, a.trials + 1)]
    print(f"{len(cases)} cases × {a.trials} trial(s) = {len(jobs)} runs, concurrency {a.concurrency}", file=sys.stderr)
    records = []
    with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        futs = {ex.submit(run_case, c, t): (c["id"], t) for c, t in jobs}
        for f in as_completed(futs):
            r = f.result()
            records.append(r)
            mark = "PASS" if r.get("passed") else "FAIL"
            extra = r.get("error") or ("; ".join(c["check"] for c in r.get("checks", []) if not c["pass"]) + " " + "; ".join(j["dimension"] for j in r.get("judges", []) if not j["pass"]))
            print(f"[{mark}] {r['id']} t{r['trial']} tier={r.get('tier')} {r.get('latency_ms')}ms {extra[:160]}", file=sys.stderr, flush=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suites = sorted({r["suite"] for r in records})
    summaries = {}
    for suite in suites:
        recs = [r for r in records if r["suite"] == suite]
        s = summarize(recs, suite)
        summaries[suite] = s
        (RESULTS / f"{suite}_{ts}.json").write_text(json.dumps({"summary": s, "records": recs}, indent=1, default=str))
        (RESULTS / f"latest_{suite}.json").write_text(json.dumps({"summary": s, "records": recs}, indent=1, default=str))
        print(f"\n== {suite}: pass@k {s['case_pass_at_k']}, pass^k {s['case_pass_pow_k']}, hallucinated-number rate {s['hallucinated_number_rate']}, "
              f"claims {s['claims_total']} flagged {s['claims_flagged_final']}, tiers {s['tier_distribution']}", file=sys.stderr)
    # merge with any existing latest for the other suite so the scorecard shows both
    for other in ("regression", "capability"):
        if other not in summaries and (RESULTS / f"latest_{other}.json").exists():
            summaries[other] = json.loads((RESULTS / f"latest_{other}.json").read_text())["summary"]
    write_scorecard(dict(sorted(summaries.items())))
    print(f"scorecard → {RESULTS / 'SCORECARD.md'}", file=sys.stderr)


if __name__ == "__main__":
    main()
