"""Run persistence: every answer + trace saved as JSON for replay, analytics, and promotion."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import STATE_DIR

RUNS_DIR = STATE_DIR / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)


def save_run(answer_json: dict[str, Any]) -> Path:
    p = RUNS_DIR / f"{answer_json['run_id']}.json"
    p.write_text(json.dumps(answer_json, default=str))
    return p


def load_run(run_id: str) -> dict[str, Any] | None:
    p = RUNS_DIR / f"{run_id}.json"
    return json.loads(p.read_text()) if p.exists() else None


def list_runs(limit: int = 200) -> list[dict[str, Any]]:
    out = []
    for p in sorted(RUNS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
        try:
            d = json.loads(p.read_text())
        except Exception:  # noqa: BLE001
            continue
        tot = d.get("trace", {}).get("steps", [])
        llm = [s["llm"] for s in tot if s.get("llm")]
        out.append({
            "run_id": d["run_id"], "question": d["question"], "tier": d["tier"], "tier_label": d["tier_label"],
            "started_at": d.get("trace", {}).get("started_at"), "headline": d.get("headline"),
            "n_claims": len(d.get("claims", [])), "n_flagged": len([c for c in d.get("claims", []) if c["verdict"] in ("unsupported", "misattributed")]),
            "rows_cited": len(d.get("rows", [])), "llm_calls": len(llm),
            "input_tokens": sum(x["input_tokens"] for x in llm), "output_tokens": sum(x["output_tokens"] for x in llm),
            "latency_ms": sum(s.get("duration_ms", 0) for s in tot),
            "cost_usd": (sum(x["cost_usd"] for x in llm) if llm and all(x.get("cost_usd") is not None for x in llm) else None),
            "certified_query_match": (d.get("certified_query_match") or {}).get("name"),
            "used_sql": any(s["kind"] == "sql" for s in tot),
            "models": sorted({x["model"] for x in llm}),
        })
    return out


def analytics() -> dict[str, Any]:
    runs = list_runs(limit=10000)
    by_tier = {1: 0, 2: 0, 3: 0, 4: 0}
    for r in runs:
        by_tier[r["tier"]] = by_tier.get(r["tier"], 0) + 1
    uncertified = [r for r in runs if r["tier"] in (2, 3)]
    # most common uncertified questions = certification backlog
    from collections import Counter
    backlog = Counter(r["question"].strip().lower() for r in uncertified).most_common(10)
    lat = [r["latency_ms"] for r in runs if r["latency_ms"]]
    return {
        "total_runs": len(runs),
        "by_tier": by_tier,
        "certified_rate": round(by_tier[1] / len(runs), 3) if runs else None,
        "avg_latency_ms": int(sum(lat) / len(lat)) if lat else None,
        "avg_rows_cited": round(sum(r["rows_cited"] for r in runs) / len(runs), 1) if runs else None,
        "total_input_tokens": sum(r["input_tokens"] for r in runs),
        "total_output_tokens": sum(r["output_tokens"] for r in runs),
        "verifier_flag_rate": round(sum(1 for r in runs if r["n_flagged"]) / len(runs), 3) if runs else None,
        "certification_backlog": [{"question": q, "count": n} for q, n in backlog],
        "sql_usage_rate": round(sum(1 for r in runs if r["used_sql"]) / len(runs), 3) if runs else None,
    }
