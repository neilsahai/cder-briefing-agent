"""CLI: python scripts/ask.py "question" [--as-of 2025-03-01] [--json out.json]
Streams trace steps as they happen, then prints the rendered answer, tier, claims and caveats."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from app.agent.runner import run  # noqa: E402
from app.agent.trace import TraceStep  # noqa: E402


def sink(st: TraceStep) -> None:
    mark = {"ok": "·", "warn": "!", "fail": "✗"}[st.status]
    llm = f"  [{st.llm.model} {st.llm.input_tokens}+{st.llm.output_tokens}tok {st.llm.latency_ms}ms" + (f" ${st.llm.cost_usd:.4f}" if st.llm.cost_usd is not None else "") + "]" if st.llm else ""
    print(f"{mark} {st.seq:02d} {st.kind:<10} {st.title}{llm}", file=sys.stderr, flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--as-of", default=None)
    ap.add_argument("--json", default=None, help="write full Answer JSON here")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--pin", action="append", default=[], help="term=reading, e.g. 'approved=full'")
    ap.add_argument("--no-registry", action="store_true")
    a = ap.parse_args()
    pins = dict(x.split("=", 1) for x in a.pin)
    ans = run(a.question, as_of=a.as_of, pins=pins, sink=None if a.quiet else sink, use_registry=not a.no_registry)
    print("\n" + "=" * 100)
    print(f"TIER {ans.tier} — {ans.tier_label}: " + "; ".join(ans.tier_reasons))
    print("=" * 100)
    print(f"\n> {ans.headline}\n")
    print(ans.markdown)
    if ans.claims:
        flagged = [c for c in ans.claims if c.verdict in ("unsupported", "misattributed")]
        print(f"\n--- VERIFIER: {ans.verification.get('overall')} | {len(ans.claims)} claims, {len(flagged)} flagged")
        for c in flagged:
            print(f"  ✗ {c.verdict}: {c.text}  ({c.note})")
    if ans.warnings:
        print("\n--- WARNINGS attached to evidence")
        for w in ans.warnings:
            print(f"  [{w.severity.value}] {w.code}: {w.message[:160]}")
    t = ans.trace.totals()
    print(f"\n--- TRACE: {t['llm_calls']} LLM calls, {t['tool_calls']} tool calls, {t['input_tokens']}+{t['output_tokens']} tokens, "
          f"{t['latency_ms_total']} ms, cost={t['cost_usd']}, rows cited={len(ans.rows)}, models={t['models_used']}")
    if a.json:
        Path(a.json).write_text(ans.model_dump_json(indent=1))
        print(f"wrote {a.json}")


if __name__ == "__main__":
    main()
