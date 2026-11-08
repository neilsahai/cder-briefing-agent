"""Inspection tools. [D2, D8, D11]"""
from __future__ import annotations

from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field

from ..data.audit import get_audit
from ..data.store import fiscal_year, get_store
from ..models import Interpretation, Severity, ToolResult, Warning
from .base import tool


class InspectionsIn(BaseModel):
    feis: list[str] = Field(description="FEI numbers to look up (from sites_for_shortages).")
    classification: list[Literal["NAI", "VAI", "OAI"]] | None = Field(None, description="Filter classifications; None = all.")
    fiscal_years: list[int] | None = Field(None, description="Restrict to these FDA fiscal years (from fiscal_year_window).")
    fy_basis: Literal["inspection_end_date", "classification_date"] = Field("inspection_end_date", description="Which date assigns FY. [D2]")
    project_area: list[Literal["Pre-Approval", "Drug Quality Assurance"]] | None = Field(None, description="Optional project-area filter.")


@tool(
    "inspections_for_sites",
    """Return inspection rows for given FEIs, optionally filtered by classification (e.g. OAI), fiscal-year
    window, and project area. Computes the FY under BOTH date bases and flags any row whose FY differs by basis.
    Also returns per-FEI summary: last inspection, OAI count in window. Use for 'which sites received an OAI',
    'inspection history of X'.""",
    decision_refs=("D2", "D8"),
)
def inspections_for_sites(p: InspectionsIn) -> ToolResult:
    store = get_store()
    audit = get_audit()
    if not p.feis:
        return ToolResult(tool="inspections_for_sites", value={"rows": [], "per_fei": {}}, source_tables=["inspections"])
    df = store.df("SELECT * FROM inspections_fy WHERE fei_number IN (" + ",".join("?" * len(p.feis)) + ")", p.feis)
    fy_col = "fy_end" if p.fy_basis == "inspection_end_date" else "fy_class"
    alt_col = "fy_class" if fy_col == "fy_end" else "fy_end"
    full = df.copy()
    if p.classification:
        df = df[df["classification"].isin(p.classification)]
    if p.project_area:
        df = df[df["project_area"].isin(p.project_area)]
    basis_sensitive = []
    if p.fiscal_years:
        in_chosen = df[fy_col].isin(p.fiscal_years)
        in_alt = df[alt_col].isin(p.fiscal_years)
        basis_sensitive = df[in_chosen != in_alt]
        df = df[in_chosen]
    df = df.sort_values(["fei_number", "inspection_end_date"])
    rows = store.rowrefs("inspections", df)
    warnings = audit.warnings_for(rows, min_severity=Severity.low)
    if len(basis_sensitive):
        warnings.append(Warning(code="INTERP_FY_BASIS", severity=Severity.medium, rows=store.rowrefs("inspections", basis_sensitive),
                                message=f"{len(basis_sensitive)} inspection(s) fall inside the FY window under one date basis but not the other: "
                                        + "; ".join(f"FEI {r.fei_number} {r.firm_name} ended {str(r.inspection_end_date)[:10]} (FY{r.fy_end}) classified {str(r.classification_date)[:10]} (FY{r.fy_class})"
                                                    for r in basis_sensitive.itertuples())))
    recs = []
    for r in df.itertuples():
        recs.append({"fei": r.fei_number, "firm_name": r.firm_name, "city": r.city, "country": r.country,
                     "inspection_end_date": str(r.inspection_end_date)[:10], "classification_date": str(r.classification_date)[:10],
                     "classification": r.classification, "project_area": r.project_area, "product_type": r.product_type,
                     "fy_by_end": int(r.fy_end), "fy_by_classification": int(r.fy_class), "row_id": f"inspections#L{int(r.line_no)}"})
    per_fei = {}
    for fei in p.feis:
        f_all = full[full["fei_number"] == fei]
        f_hit = df[df["fei_number"] == fei]
        per_fei[fei] = {
            "has_inspection_record": bool(len(f_all)),
            "firm_name": f_all.iloc[0].firm_name if len(f_all) else None,
            "country": f_all.iloc[0].country if len(f_all) else "UNKNOWN",
            "last_inspection_end_date": str(f_all["inspection_end_date"].max())[:10] if len(f_all) else None,
            "last_inspection_fy": int(f_all[fy_col].max()) if len(f_all) else None,
            "matching_rows": len(f_hit),
            "matching_project_areas": sorted(f_hit["project_area"].unique().tolist()),
        }
    interps = [Interpretation(term="fiscal year", chosen=p.fy_basis, alternatives=["classification_date" if p.fy_basis == "inspection_end_date" else "inspection_end_date"],
                              decision_ref="D2", note="FDA Data Dashboard reports by inspection end date.")]
    if p.classification == ["OAI"]:
        interps.append(Interpretation(term="received an OAI classification", chosen="any project_area (disclosed per row)",
                                      alternatives=["Drug Quality Assurance only"], decision_ref="D8"))
    return ToolResult(tool="inspections_for_sites", value={"rows": recs, "per_fei": per_fei, "fy_basis": p.fy_basis, "fiscal_years": p.fiscal_years},
                      rows=rows, source_tables=["inspections"], interpretations=interps, warnings=warnings)


class NotInspectedIn(BaseModel):
    feis: list[str]
    since_fy: int = Field(description="e.g. 2021 → sites whose last inspection was in FY2021 or earlier.")
    inclusive: bool = Field(True, description="True: 'not inspected since FY2021' = last inspection FY <= 2021. False: last inspection FY < 2021.")
    foreign_only: bool = Field(False, description="Only sites with country != United States (UNKNOWN-country sites reported separately).")
    fy_basis: Literal["inspection_end_date", "classification_date"] = "inspection_end_date"


@tool(
    "sites_not_inspected_since",
    """Classify FEIs into: last inspected in/before the target FY (stale), never inspected (no record; country
    unknown), and recently inspected. Optionally restrict to foreign sites. Returns row IDs for each FEI's
    most recent inspection. Use for 'which establishments have not been inspected since FY20xx'.""",
    decision_refs=("D10", "D11"),
)
def sites_not_inspected_since(p: NotInspectedIn) -> ToolResult:
    store = get_store()
    audit = get_audit()
    if not p.feis:
        return ToolResult(tool="sites_not_inspected_since", value={}, source_tables=["inspections"])
    df = store.df("SELECT * FROM inspections_fy WHERE fei_number IN (" + ",".join("?" * len(p.feis)) + ")", p.feis)
    fy_col = "fy_end" if p.fy_basis == "inspection_end_date" else "fy_class"
    stale, recent, never, unknown_country = [], [], [], []
    rows = []
    for fei in p.feis:
        g = df[df["fei_number"] == fei]
        if not len(g):
            never.append({"fei": fei, "country": "UNKNOWN"})
            continue
        last = g.sort_values("inspection_end_date").iloc[-1]
        rows.append(store.rowref("inspections", last))
        is_foreign = last.country != "United States"
        rec = {"fei": fei, "firm_name": last.firm_name, "city": last.city, "country": last.country, "is_foreign": is_foreign,
               "last_inspection_end_date": str(last.inspection_end_date)[:10], "last_inspection_fy": int(last[fy_col]),
               "last_classification": last.classification, "inspection_count": int(len(g)), "row_id": f"inspections#L{int(last.line_no)}"}
        if p.foreign_only and not is_foreign:
            continue
        cond = rec["last_inspection_fy"] <= p.since_fy if p.inclusive else rec["last_inspection_fy"] < p.since_fy
        (stale if cond else recent).append(rec)
    warnings = audit.warnings_for(rows, min_severity=Severity.low)
    if never:
        warnings.append(Warning(code="COUNTRY_UNKNOWN", severity=Severity.medium,
                                message=f"{len(never)} FEI(s) have no inspection record at all: {[n['fei'] for n in never]}. "
                                        f"They cannot be classified as foreign or domestic from this data, and 'not inspected since FY{p.since_fy}' "
                                        f"is trivially true but means something different (never inspected)."))
    interps = [
        Interpretation(term="not inspected since", chosen="last inspection FY <= target" if p.inclusive else "last inspection FY < target",
                       alternatives=["last inspection FY < target" if p.inclusive else "last inspection FY <= target"], decision_ref="D11"),
        Interpretation(term="foreign", chosen="inspections.country != 'United States'", alternatives=["UNKNOWN when never inspected"], decision_ref="D10"),
    ]
    return ToolResult(tool="sites_not_inspected_since",
                      value={"since_fy": p.since_fy, "inclusive": p.inclusive, "foreign_only": p.foreign_only,
                             "stale": stale, "never_inspected": never, "recently_inspected": recent,
                             "counts": {"stale": len(stale), "never_inspected": len(never), "recent": len(recent)}},
                      rows=rows, source_tables=["inspections"], interpretations=interps, warnings=warnings)
