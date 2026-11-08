"""Shortage tools. [D4, D5, D6]"""
from __future__ import annotations

from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field

from .. import ontology
from ..data.audit import get_audit
from ..data.store import get_store
from ..models import Interpretation, Severity, ToolResult, Warning
from .base import tool


def _records(df: pd.DataFrame) -> list[dict]:
    cols = ["shortage_id", "generic_name", "presentation", "ndc", "shortage_status", "initial_posting_date",
            "revision_date", "reason_category", "related_application", "line_no"]
    out = []
    for _, r in df[cols].iterrows():
        d = {c: (str(r[c])[:10] if "date" in c else r[c]) for c in cols if c != "line_no"}
        d["row_id"] = f"drug_shortages#L{int(r['line_no'])}"
        out.append(d)
    return out


class CurrentShortagesIn(BaseModel):
    as_of: str | None = Field(None, description="ISO date; default = latest date in dataset.")
    generic_name: list[str] | None = Field(None, description="Canonical generic names (use resolve_entity first).")
    presentation_like: str | None = Field(None, description="SQL LIKE pattern on presentation, e.g. 'Oral Suspension%'.")
    reason_scope: Literal["strict", "broad", "any"] = Field(
        "any", description="'strict' = Quality: cGMP Issue only; 'broad' = + Manufacturing Delay; 'any' = no reason filter. [D5]"
    )
    reason_categories: list[str] | None = Field(None, description="Explicit reason_category values (overrides reason_scope).")
    statuses: list[Literal["Current", "Resolved", "Discontinued"]] = Field(["Current"], description="Statuses to include. Default Current only.")
    antibiotics_only: bool = Field(False, description="Restrict to the ontology's antibiotic list (hearing topic).")
    pediatric_proxy: bool = Field(False, description="Restrict to oral suspension/solution presentations (pediatric proxy; labeled as such).")


@tool(
    "current_shortages",
    """List shortage records by status as of a date, using ONE row per shortage_id (latest revision) so
    conflicting status records are never double-counted. Returns records with row IDs, counts at three levels
    (distinct drugs, records, presentations), the interpretation applied for 'quality problems', and data
    warnings (status conflicts, stale records). Use for 'how many drugs are in shortage', 'what is currently
    short', 'quality-related shortages', 'is X resolved'.""",
    decision_refs=("D4", "D5", "D6"),
)
def current_shortages(p: CurrentShortagesIn) -> ToolResult:
    store = get_store()
    audit = get_audit(p.as_of)
    as_of = store.resolve_as_of(p.as_of)
    interps: list[Interpretation] = []
    warnings: list[Warning] = []

    # latest revision on or before as_of
    sql = """
      SELECT s.* FROM drug_shortages s
      JOIN (SELECT shortage_id, MAX(revision_date) AS mr FROM drug_shortages WHERE revision_date <= ? GROUP BY shortage_id) m
        ON s.shortage_id = m.shortage_id AND s.revision_date = m.mr
      WHERE 1=1
    """
    params: list = [as_of]
    sql += " AND s.shortage_status IN (" + ",".join("?" * len(p.statuses)) + ")"
    params += p.statuses
    if p.generic_name:
        sql += " AND s.generic_name IN (" + ",".join("?" * len(p.generic_name)) + ")"
        params += p.generic_name
    if p.presentation_like:
        sql += " AND s.presentation LIKE ?"
        params.append(p.presentation_like)
    if p.reason_categories:
        sql += " AND s.reason_category IN (" + ",".join("?" * len(p.reason_categories)) + ")"
        params += p.reason_categories
    elif p.reason_scope != "any":
        cats = ontology.definition("quality_problem")[p.reason_scope]
        sql += " AND s.reason_category IN (" + ",".join("?" * len(cats)) + ")"
        params += cats
        alt = "broad" if p.reason_scope == "strict" else "strict"
        interps.append(Interpretation(term="quality problems", chosen=p.reason_scope, alternatives=[alt], decision_ref="D5",
                                      note=f"{p.reason_scope} = {cats}"))
    if p.antibiotics_only:
        abx = ontology.pediatric_antibiotics()["antibiotic_generic_names"]
        sql += " AND s.generic_name IN (" + ",".join("?" * len(abx)) + ")"
        params += abx
    if p.pediatric_proxy:
        pats = ontology.pediatric_antibiotics()["pediatric_presentation_proxy"]
        sql += " AND (" + " OR ".join("s.presentation LIKE ?" for _ in pats) + ")"
        params += pats
        warnings.append(Warning(code="INTERP_PEDIATRIC_PROXY", severity=Severity.medium,
                                message="Dataset has no pediatric flag; oral suspension/solution presentations used as a proxy for pediatric products."))
    sql += " ORDER BY s.generic_name, s.presentation, s.shortage_id"
    df = store.df(sql, params)

    rows = store.rowrefs("drug_shortages", df)
    # Attach lineage warnings (status conflicts, stale, orphan apps...) for the rows actually used
    warnings += audit.warnings_for(rows, min_severity=Severity.low)

    # Superseded revisions of any shortage_id in the result are cited via the DQ01 lineage warning,
    # whose `rows` include both the used and the superseded record.

    interps.append(Interpretation(term="currently", chosen=f"as_of={as_of}", alternatives=["user-specified date"], decision_ref="D1"))
    interps.append(Interpretation(term="how many drugs", chosen="distinct generic_name", alternatives=["shortage_id (records)", "generic_name+presentation"], decision_ref="D6"))

    value = {
        "as_of": as_of.isoformat(),
        "statuses": p.statuses,
        "counts": {
            "distinct_drugs": int(df["generic_name"].nunique()) if len(df) else 0,
            "records": int(len(df)),
            "presentations": int(df[["generic_name", "presentation"]].drop_duplicates().shape[0]) if len(df) else 0,
        },
        "by_reason": df["reason_category"].value_counts().to_dict() if len(df) else {},
        "by_status": df["shortage_status"].value_counts().to_dict() if len(df) else {},
        "drugs": sorted(df["generic_name"].unique().tolist()) if len(df) else [],
        "records": _records(df),
    }
    return ToolResult(tool="current_shortages", value=value, rows=rows, source_tables=["drug_shortages"],
                      interpretations=interps, warnings=warnings, as_of=as_of)


class ShortageHistoryIn(BaseModel):
    generic_name: list[str] | None = Field(None, description="Canonical generic names.")
    presentation_like: str | None = None
    shortage_id: list[str] | None = None


@tool(
    "shortage_history",
    """Return EVERY revision row (all statuses, all dates) for a drug/presentation/shortage_id, in chronological
    order, with the status timeline per shortage_id and an explicit flag where a record changed status. Use this
    to answer 'is X resolved?', 'what happened with X?', or whenever a status word will appear in the answer —
    it is the only tool that shows superseded records.""",
    decision_refs=("D4",),
)
def shortage_history(p: ShortageHistoryIn) -> ToolResult:
    store = get_store()
    audit = get_audit()
    sql = "SELECT * FROM drug_shortages WHERE 1=1"
    params: list = []
    if p.generic_name:
        sql += " AND generic_name IN (" + ",".join("?" * len(p.generic_name)) + ")"; params += p.generic_name
    if p.presentation_like:
        sql += " AND presentation LIKE ?"; params.append(p.presentation_like)
    if p.shortage_id:
        sql += " AND shortage_id IN (" + ",".join("?" * len(p.shortage_id)) + ")"; params += p.shortage_id
    sql += " ORDER BY shortage_id, revision_date"
    df = store.df(sql, params)
    rows = store.rowrefs("drug_shortages", df)
    warnings = audit.warnings_for(rows, min_severity=Severity.low)

    timelines = {}
    for sid, g in df.groupby("shortage_id"):
        g = g.sort_values("revision_date")
        timelines[sid] = {
            "generic_name": g.iloc[0].generic_name,
            "presentation": g.iloc[0].presentation,
            "timeline": [{"status": r.shortage_status, "revision_date": str(r.revision_date)[:10], "row_id": f"drug_shortages#L{int(r.line_no)}"} for r in g.itertuples()],
            "latest_status": g.iloc[-1].shortage_status,
            "status_changed": g["shortage_status"].nunique() > 1,
        }
    sem = ontology.status_semantics()
    value = {"timelines": timelines, "records": _records(df), "status_semantics": {k: v["meaning"] for k, v in sem.items()}}
    interps = [Interpretation(term="resolved", chosen="Resolved per FDA: market covered", alternatives=["Discontinued ≠ Resolved"], decision_ref="D4",
                              note="Never equate Discontinued with Resolved.")]
    return ToolResult(tool="shortage_history", value=value, rows=rows, source_tables=["drug_shortages"], interpretations=interps, warnings=warnings)
