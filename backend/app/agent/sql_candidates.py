"""Multi-candidate SQL: when the planner resorts to LLM-authored SQL, two more models independently write SQL
for the same stated purpose. All candidates run through the same guard. Agreement raises confidence;
disagreement is surfaced as an ambiguity signal (Snowflake Cortex Analyst pattern)."""
from __future__ import annotations

import json
from typing import Any

from .. import ontology
from ..data.store import get_store
from ..llm.provider import Provider, structured
from ..models import Interpretation, Severity, ToolResult, Warning
from ..tools import call_tool
from .trace import Tracer

SQL_SYSTEM = """You write ONE read-only DuckDB SELECT to answer a stated purpose over an FDA drug-shortage dataset.
Rules: only these relations — drug_shortages, applications, inspections, shortages_latest (one row per shortage_id,
latest revision; use it for anything 'current'), inspections_fy (inspections + fy_end, fy_class), facilities.
Always select the line_no column(s) of the base rows you rely on (alias as <table>_line_no when joining) so results
can be cited. Never use now()/current_date/random. Encode exactly the interpretation stated. Return only the tool call.

SCHEMA:
{schema}

DEFINITIONS (from the ontology):
{defs}
"""

SQL_TOOL = {
    "name": "candidate_sql",
    "description": "Return the SQL for the purpose.",
    "input_schema": {"type": "object", "properties": {"sql": {"type": "string"}, "reasoning": {"type": "string"}}, "required": ["sql"]},
}


def _data_columns(columns: list[str]) -> list[str]:
    return [c for c in columns if not (c == "line_no" or c.endswith("_line_no"))]


def _project(records: list[dict[str, Any]], cols: list[str]) -> frozenset:
    return frozenset(tuple(str(r.get(c)) for c in cols) for r in records)


def compare_candidates(cands: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare valid candidates on their COMMON data columns. Different shapes with no common columns are
    'incomparable', not 'disagree'."""
    valid = [c for c in cands if c.get("records") is not None]
    if len(valid) < 2:
        return {"n_valid": len(valid), "verdict": "n/a", "row_counts": [c["row_count"] for c in valid]}
    common = set(_data_columns(valid[0]["columns"]))
    for c in valid[1:]:
        common &= set(_data_columns(c["columns"]))
    common_l = sorted(common)
    if not common_l:
        return {"n_valid": len(valid), "verdict": "incomparable", "row_counts": [c["row_count"] for c in valid], "common_columns": []}
    projections = {_project(c["records"], common_l) for c in valid}
    return {"n_valid": len(valid), "verdict": "agree" if len(projections) == 1 else "disagree",
            "row_counts": [c["row_count"] for c in valid], "common_columns": common_l}


def run_sql_candidates(prov: Provider, tracer: Tracer, planner_input: dict[str, Any], primary: ToolResult) -> ToolResult:
    store = get_store()
    defs = json.dumps(ontology.load()["definitions"], indent=0, default=str)[:3000]
    system = SQL_SYSTEM.format(schema=store.schema_text(), defs=defs)
    purpose = planner_input.get("purpose", "")
    notes = planner_input.get("interpretation_notes", [])
    user = f"PURPOSE: {purpose}\nINTERPRETATION NOTES: {notes}\nWrite the SQL."

    candidates = [{"source": "planner", "model": None, "sql": planner_input["sql"], "row_count": primary.value.get("row_count"),
                   "records": primary.value.get("records", []), "columns": primary.value.get("columns", []), "error": None}]
    for role in ("sql_candidate_b", "sql_candidate_c"):
        try:
            out, call, _ = structured(prov, role, system=system, messages=[{"role": "user", "content": user}], tool=SQL_TOOL, max_tokens=1200)
            res = call_tool("sql_query", {"sql": out["sql"], "purpose": purpose, "interpretation_notes": notes})
            err = res.value.get("error")
            cand = {"source": role, "model": call.model, "sql": out["sql"], "row_count": None if err else res.value.get("row_count"),
                    "records": None if err else res.value.get("records", []), "columns": None if err else res.value.get("columns", []), "error": err}
            tracer.step("sql", f"SQL candidate ({call.model}) → {'error' if err else str(cand['row_count']) + ' rows'}", llm=call,
                        input={"sql": out["sql"]}, output={"row_count": cand["row_count"], "error": err}, status="warn" if err else "ok")
        except Exception as ex:  # noqa: BLE001
            cand = {"source": role, "model": None, "sql": None, "row_count": None, "records": None, "columns": None, "error": str(ex)}
            tracer.step("error", f"SQL candidate {role} failed", output=str(ex), status="fail")
        candidates.append(cand)

    cmp = compare_candidates(candidates)
    verdict = cmp["verdict"]
    primary.value["candidates"] = [{k: v for k, v in c.items() if k not in ("records", "columns")} for c in candidates]
    primary.value["candidate_agreement"] = cmp
    if verdict == "disagree":
        primary.warnings.append(Warning(code="SQL_CANDIDATES_DISAGREE", severity=Severity.high,
                                        message=f"Independently written SQL candidates returned different values on shared columns {cmp['common_columns']} "
                                                f"(row counts {cmp['row_counts']}). The question or data admits more than one reading; treat this value as contested until an analyst reviews the SQL."))
        primary.interpretations.append(Interpretation(term=purpose[:60], chosen="planner SQL", alternatives=[c["source"] + " SQL" for c in candidates[1:] if c.get("records") is not None],
                                                      decision_ref="D13", note="candidate result sets differ"))
    elif verdict == "agree":
        primary.warnings.append(Warning(code="SQL_CANDIDATES_AGREE", severity=Severity.info,
                                        message=f"{cmp['n_valid']} independently written SQL candidates returned identical values on shared columns {cmp['common_columns']}."))
    elif verdict == "incomparable":
        primary.warnings.append(Warning(code="SQL_CANDIDATES_INCOMPARABLE", severity=Severity.low,
                                        message="Independently written SQL candidates returned differently shaped results and could not be compared."))
    tracer.step("sql", f"SQL candidates: {verdict} ({cmp['n_valid']} valid)", output=cmp, status="ok" if verdict == "agree" else "warn")
    return primary
