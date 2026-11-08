"""Manufacturing-site resolution: Shortage → Application → Facility. [D7, D10]"""
from __future__ import annotations

import re

import pandas as pd
from pydantic import BaseModel, Field

from ..data.audit import FEI_VALID, get_audit
from ..data.store import fiscal_year, get_store
from ..models import Interpretation, RowRef, Severity, ToolResult, Warning
from .base import tool


class SitesIn(BaseModel):
    shortage_ids: list[str] | None = Field(None, description="Shortage IDs to resolve sites for (from current_shortages).")
    application_numbers: list[str] | None = Field(None, description="Or resolve sites directly for application numbers.")
    as_of: str | None = None


@tool(
    "sites_for_shortages",
    """Resolve manufacturing sites (FEI) for shortage records via their linked application. For each FEI
    returns: sponsor (application holder), facility operator (from inspections), country (UNKNOWN if the FEI
    has never been inspected), last inspection date, FEI format validity, and the row IDs of every hop in the
    join. ALWAYS reports coverage: how many of the input shortages could be linked at all. Use for 'which
    manufacturers/sites/facilities' questions.""",
    decision_refs=("D7", "D10"),
)
def sites_for_shortages(p: SitesIn) -> ToolResult:
    store = get_store()
    audit = get_audit(p.as_of)
    s = store.frames["drug_shortages"]
    a = store.frames["applications"]
    fac = store.df("SELECT * FROM facilities")

    if p.shortage_ids:
        latest = store.df("SELECT * FROM shortages_latest WHERE shortage_id IN (" + ",".join("?" * len(p.shortage_ids)) + ")", p.shortage_ids)
        apps_wanted = latest[["shortage_id", "generic_name", "related_application", "line_no"]].rename(columns={"line_no": "_sline"})
    elif p.application_numbers:
        apps_wanted = pd.DataFrame({"shortage_id": [None] * len(p.application_numbers), "generic_name": [None] * len(p.application_numbers),
                                    "related_application": p.application_numbers, "_sline": [None] * len(p.application_numbers)})
    else:
        raise ValueError("Provide shortage_ids or application_numbers")

    j = apps_wanted.merge(a, left_on="related_application", right_on="application_number", how="left")
    j = j.merge(fac, left_on="manufacturing_fei", right_on="fei_number", how="left")

    rows: list[RowRef] = []
    sites: list[dict] = []
    unlinked: list[dict] = []
    for _, r in j.iterrows():
        if r.get("_sline") is not None and not pd.isna(r.get("_sline")):
            rows.append(RowRef(table="drug_shortages", line=int(r["_sline"]), key=f"{r.shortage_id}"))
        if pd.isna(r.get("application_number")):
            unlinked.append({"shortage_id": r.shortage_id, "generic_name": r.generic_name, "related_application": r.related_application,
                             "row_id": f"drug_shortages#L{int(r['_sline'])}" if not pd.isna(r.get("_sline")) else None,
                             "reason": "application number not in applications.csv"})
            continue
        rows.append(RowRef(table="applications", line=int(r["line_no"]), key=r.application_number))
        fei = r.manufacturing_fei
        has_insp = not pd.isna(r.get("fei_number"))
        if has_insp:
            insp_rows = store.frames["inspections"][store.frames["inspections"]["fei_number"] == fei]
            rows += store.rowrefs("inspections", insp_rows)
        fmt_ok = bool(re.fullmatch(FEI_VALID, str(fei)))
        sites.append({
            "shortage_id": r.shortage_id,
            "generic_name": r.generic_name,
            "application_number": r.application_number,
            "application_row_id": f"applications#L{int(r['line_no'])}",
            "sponsor_name": r.sponsor_name,
            "marketing_status": r.marketing_status,
            "fei": fei,
            "fei_format_valid": fmt_ok,
            "fei_prefix_anomaly": fmt_ok and not str(fei).startswith("3"),
            "facility_operator": r.firm_name if has_insp else None,
            "city": r.city if has_insp else None,
            "country": r.country if has_insp else "UNKNOWN",
            "country_known": has_insp,
            "sponsor_is_operator": (has_insp and str(r.sponsor_name).lower() == str(r.firm_name).lower()),
            "last_inspection_end_date": str(r.last_inspection_end_date)[:10] if has_insp else None,
            "last_inspection_fy": fiscal_year(r.last_inspection_end_date) if has_insp else None,
            "inspection_count": int(r.inspection_count) if has_insp else 0,
            "oai_count_all_time": int(r.oai_count) if has_insp else 0,
        })

    n_in = len(apps_wanted)
    n_linked = len(sites)
    warnings = audit.warnings_for(rows, min_severity=Severity.low)
    if unlinked:
        warnings.insert(0, Warning(code="COVERAGE", severity=Severity.high,
                                   message=f"Manufacturing site is knowable for {n_linked} of {n_in} input shortage records; "
                                           f"{len(unlinked)} reference an application not present in applications.csv.",
                                   rows=[RowRef(table="drug_shortages", line=int(u["row_id"].split("#L")[1]), key=u["shortage_id"] or "")
                                         for u in unlinked if u["row_id"]]))
    unknown_country = [x for x in sites if not x["country_known"]]
    if unknown_country:
        warnings.append(Warning(code="COUNTRY_UNKNOWN", severity=Severity.medium,
                                message=f"{len(unknown_country)} site(s) have no inspection record, so country is UNKNOWN: "
                                        + ", ".join(f"{x['fei']} ({x['sponsor_name']})" for x in unknown_country)
                                        + ". Sponsor names may suggest a country but that is inference, not data."))
    bad_fei = [x for x in sites if not x["fei_format_valid"] or x["fei_prefix_anomaly"]]
    if bad_fei:
        warnings.append(Warning(code="FEI_VERIFY", severity=Severity.medium,
                                message="FEI format check: " + "; ".join(
                                    f"{x['fei']} {'INVALID' if not x['fei_format_valid'] else 'prefix anomaly'}" for x in bad_fei)
                                        + ". Verify against FDA's FEI portal before citing."))
    interps = [
        Interpretation(term="manufacturer", chosen="facility operator (inspections.firm_name) AND sponsor (applications.sponsor_name), both shown",
                       alternatives=["sponsor only", "operator only"], decision_ref="D7"),
        Interpretation(term="foreign", chosen="inspections.country != 'United States'; UNKNOWN if never inspected",
                       alternatives=["infer from sponsor name (not used)"], decision_ref="D10"),
    ]
    value = {
        "coverage": {"input_records": n_in, "linked": n_linked, "unlinked": len(unlinked)},
        "sites": sites,
        "unlinked": unlinked,
        "distinct_feis": sorted({x["fei"] for x in sites}),
    }
    return ToolResult(tool="sites_for_shortages", value=value, rows=rows,
                      source_tables=["drug_shortages", "applications", "inspections"], interpretations=interps,
                      warnings=warnings, coverage=f"sites known for {n_linked} of {n_in} records")
