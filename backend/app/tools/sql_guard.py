"""Guarded SQL: read-only DuckDB over the three tables + derived views, validated with an AST walk.

Allowed: a single SELECT (CTEs ok) over known tables/views and known columns.
Forbidden: DDL/DML, multiple statements, unknown relations, functions that fabricate values
(random, now/current_date — the as-of date must come from the ontology), and any attempt to
reference files or extensions.

Result rows carry line_no so they become RowRefs like every other tool. [Tier 2 — Derived]
"""
from __future__ import annotations

import re
from typing import Any

import sqlglot
from pydantic import BaseModel, Field
from sqlglot import exp

from ..data.audit import get_audit
from ..data.store import TABLES, get_store
from ..models import Interpretation, RowRef, Severity, ToolResult, Warning
from .base import tool

VIEWS = {"shortages_latest", "inspections_fy", "facilities"}
ALLOWED_RELATIONS = set(TABLES) | VIEWS
FORBIDDEN_FUNCS = {"random", "rand", "now", "current_date", "current_timestamp", "today", "read_csv", "read_csv_auto",
                   "read_parquet", "read_json", "glob", "getenv", "load", "install", "uuid"}
ROW_LIMIT = 500


class SQLGuardError(Exception):
    pass


def validate_sql(sql: str, known_columns: dict[str, set[str]]) -> exp.Expression:
    try:
        stmts = [t for t in sqlglot.parse(sql, read="duckdb") if t is not None]
    except Exception as ex:  # noqa: BLE001
        raise SQLGuardError(f"could not parse SQL: {ex}") from ex
    if len(stmts) != 1:
        raise SQLGuardError("multiple statements are not allowed")
    tree = stmts[0]
    if not isinstance(tree, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        raise SQLGuardError(f"only SELECT statements are allowed (got {type(tree).__name__})")
    for node in tree.walk():
        if isinstance(node, (exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Drop, exp.Alter, exp.Command, exp.Pragma, exp.Copy)):
            raise SQLGuardError(f"forbidden statement type: {type(node).__name__}")
        if isinstance(node, exp.Table):
            name = node.name.lower()
            # CTE names are allowed
            ctes = {c.alias_or_name.lower() for c in tree.find_all(exp.CTE)}
            if name not in ALLOWED_RELATIONS and name not in ctes:
                raise SQLGuardError(f"unknown relation '{node.name}'. Allowed: {sorted(ALLOWED_RELATIONS)}")
        if isinstance(node, exp.Func):
            names = {str(node.key).lower(), str(node.sql_name()).lower(), str(node.name).lower()}
            if isinstance(node, exp.Anonymous):
                names.add(str(node.this).lower())
            hit = names & (FORBIDDEN_FUNCS | {"currentdate", "currenttimestamp", "currenttime", "rand", "randn"})
            if hit:
                fname = sorted(hit)[0]
                raise SQLGuardError(f"function '{fname}' is not allowed (values must come from the data, not the clock or randomness)")
    # column check (best effort: only for unqualified/qualified column refs on known relations)
    all_cols = set().union(*known_columns.values()) | {"fy_end", "fy_class", "last_inspection_end_date", "inspection_count", "oai_count"}
    for col in tree.find_all(exp.Column):
        c = col.name
        if c and c != "*" and c.lower() not in {x.lower() for x in all_cols}:
            aliases = {a.alias_or_name for a in tree.find_all(exp.Alias)} | {c.alias_or_name for c in tree.find_all(exp.CTE)}
            if c not in aliases:
                raise SQLGuardError(f"unknown column '{c}'")
    return tree


class SQLIn(BaseModel):
    sql: str = Field(description="A single read-only SELECT over drug_shortages, applications, inspections, shortages_latest, inspections_fy, facilities. Include line_no columns so rows can be cited.")
    purpose: str = Field(description="One sentence: what question this query answers and which interpretation it applies.")
    interpretation_notes: list[str] = Field(default_factory=list, description="Ambiguous terms and the reading encoded in this SQL.")


@tool(
    "sql_query",
    """LAST RESORT (Tier 2 — Derived). Run a read-only SELECT when no certified tool can answer. The SQL is
    validated (SELECT only, known tables/columns, no clock/random functions), executed against DuckDB, and
    returned with row citations when line_no columns are selected. Prefer the shortages_latest view for
    'current' questions (it applies the latest-revision rule). State the interpretation you encoded. The
    answer will be labeled Derived, not Certified.""",
    decision_refs=("D12", "D13"),
    certified=False,
)
def sql_query(p: SQLIn) -> ToolResult:
    store = get_store()
    audit = get_audit()
    known = {t: set(store.frames[t].columns) for t in TABLES}
    try:
        validate_sql(p.sql, known)
    except SQLGuardError as ex:
        return ToolResult(tool="sql_query", value={"error": str(ex), "sql": p.sql}, source_tables=[],
                          warnings=[Warning(code="SQL_REJECTED", severity=Severity.high, message=f"SQL rejected by guard: {ex}")])
    try:
        df = store.df(p.sql)
    except Exception as ex:  # noqa: BLE001
        return ToolResult(tool="sql_query", value={"error": f"execution error: {ex}", "sql": p.sql}, source_tables=[],
                          warnings=[Warning(code="SQL_ERROR", severity=Severity.high, message=f"SQL execution failed: {ex}")])
    truncated = len(df) > ROW_LIMIT
    df = df.head(ROW_LIMIT)
    # citations: any column named line_no or <table>_line_no
    rows: list[RowRef] = []
    tables_used = sorted({t.name.lower() for t in sqlglot.parse_one(p.sql, read="duckdb").find_all(exp.Table)} & ALLOWED_RELATIONS)
    base_tables = sorted({{"shortages_latest": "drug_shortages", "inspections_fy": "inspections", "facilities": "inspections"}.get(t, t) for t in tables_used})
    line_cols = [c for c in df.columns if c == "line_no" or c.endswith("_line_no")]
    for c in line_cols:
        tbl = base_tables[0] if c == "line_no" and len(base_tables) == 1 else c.replace("_line_no", "")
        if tbl in TABLES:
            for v in df[c].dropna().unique():
                rows.append(RowRef(table=tbl, line=int(v), key=""))
    warnings = [Warning(code="TIER2_DERIVED", severity=Severity.medium,
                        message="This value comes from LLM-authored SQL (validated and executed), not a certified tool. Review before citing in testimony.")]
    if not rows:
        warnings.append(Warning(code="SQL_NO_ROW_CITATIONS", severity=Severity.high,
                                message="The query did not select line_no columns, so its result cannot be traced to rows. Re-run selecting line_no."))
    if truncated:
        warnings.append(Warning(code="SQL_TRUNCATED", severity=Severity.medium, message=f"Result truncated to {ROW_LIMIT} rows."))
    warnings += audit.warnings_for(rows, min_severity=Severity.medium)
    records = df.astype(str).to_dict("records")
    interps = [Interpretation(term=n, chosen="encoded in SQL", alternatives=[], decision_ref="D13") for n in p.interpretation_notes]
    return ToolResult(tool="sql_query", value={"sql": p.sql, "purpose": p.purpose, "row_count": len(df), "columns": list(df.columns), "records": records},
                      rows=rows, source_tables=base_tables, interpretations=interps, warnings=warnings)
