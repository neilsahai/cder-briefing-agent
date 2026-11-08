"""Certified queries: the three required questions composed from certified tools.

These are NOT hardcoded answers. Each is a deterministic plan over the same tools the agent uses,
parameterized by the same interpretation switches, producing the same ToolResult evidence shape.
They are seeded into the certified-query registry (Tier 1) with verified_by = 'N. Sahai (seed)'.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ..models import Interpretation, Severity, ToolResult, Warning
from .applications import ApplicationsIn, applications_for_ingredient
from .base import tool
from .fiscal import FYWindowIn, fiscal_year_window
from .inspections import InspectionsIn, NotInspectedIn, inspections_for_sites, sites_not_inspected_since
from .shortages import CurrentShortagesIn, ShortageHistoryIn, current_shortages, shortage_history
from .sites import SitesIn, sites_for_shortages
from .warnings_util import consolidate


def _merge(*results: ToolResult, tool: str, value: dict) -> ToolResult:
    rows, warnings, interps, tables = [], [], [], []
    seen_rows, seen_w = set(), set()
    for r in results:
        for x in r.rows:
            if x.id not in seen_rows:
                seen_rows.add(x.id); rows.append(x)
        for w in r.warnings:
            k = (w.code, w.message)
            if k not in seen_w:
                seen_w.add(k); warnings.append(w)
        interps += r.interpretations
        tables += [t for t in r.source_tables if t not in tables]
    # de-dupe interpretations by (term, chosen)
    seen_i, uniq = set(), []
    for i in interps:
        k = (i.term, i.chosen)
        if k not in seen_i:
            seen_i.add(k); uniq.append(i)
    return ToolResult(tool=tool, value=value, rows=rows, warnings=consolidate(warnings), interpretations=uniq, source_tables=tables,
                      as_of=results[0].as_of if results else None)


# --------------------------------------------------------------------------- Q1
class Q1In(BaseModel):
    as_of: str | None = None
    quality_scope: Literal["strict", "broad"] = "strict"
    fy_mode: Literal["completed", "include_current"] = "completed"
    fy_basis: Literal["inspection_end_date", "classification_date"] = "inspection_end_date"
    project_area: list[Literal["Pre-Approval", "Drug Quality Assurance"]] | None = None


@tool(
    "cq_quality_shortages_oai_sites",
    """CERTIFIED QUERY (Q1): How many drugs are currently in shortage because of quality problems, and which of
    their manufacturing sites received an OAI classification in the last two fiscal years? Composes
    current_shortages → sites_for_shortages → fiscal_year_window → inspections_for_sites. All interpretation
    switches exposed (quality scope, FY mode, FY basis, project area).""",
    decision_refs=("D1", "D2", "D3", "D5", "D6", "D7", "D8"),
)
def cq_quality_shortages_oai_sites(p: Q1In) -> ToolResult:
    cs = current_shortages(CurrentShortagesIn(as_of=p.as_of, reason_scope=p.quality_scope))
    ids = [r["shortage_id"] for r in cs.value["records"]]
    sites = sites_for_shortages(SitesIn(shortage_ids=ids, as_of=p.as_of))
    fyw = fiscal_year_window(FYWindowIn(n_years=2, as_of=p.as_of, mode=p.fy_mode))
    feis = sites.value["distinct_feis"]
    insp = inspections_for_sites(InspectionsIn(feis=feis, classification=["OAI"], fiscal_years=fyw.value["fiscal_years"],
                                               fy_basis=p.fy_basis, project_area=p.project_area))
    oai_feis = sorted({r["fei"] for r in insp.value["rows"]})
    site_index = {s["fei"]: s for s in sites.value["sites"]}
    oai_sites = []
    for fei in oai_feis:
        s = site_index[fei]
        hits = [r for r in insp.value["rows"] if r["fei"] == fei]
        oai_sites.append({"fei": fei, "facility_operator": s["facility_operator"], "country": s["country"],
                          "sponsors": sorted({x["sponsor_name"] for x in sites.value["sites"] if x["fei"] == fei}),
                          "drugs": sorted({x["generic_name"] for x in sites.value["sites"] if x["fei"] == fei}),
                          "oai_inspections": hits})
    no_oai = [{"fei": s["fei"], "facility_operator": s["facility_operator"], "country": s["country"], "generic_name": s["generic_name"],
               "last_inspection_end_date": s["last_inspection_end_date"], "note": "no OAI in window" if s["country_known"] else "no inspection record"}
              for s in sites.value["sites"] if s["fei"] not in oai_feis]
    # ---- deterministic alternates (so the trust tier never depends on whether the planner chose to compute them)
    alt_notes: list[Interpretation] = []
    alt_scope = "broad" if p.quality_scope == "strict" else "strict"
    cs_alt = current_shortages(CurrentShortagesIn(as_of=p.as_of, reason_scope=alt_scope))
    alt_notes.append(Interpretation(term="quality problems", chosen=p.quality_scope, alternatives=[alt_scope], decision_ref="D5",
                                    alternate_result={"distinct_drugs": cs_alt.value["counts"]["distinct_drugs"], "records": cs_alt.value["counts"]["records"]},
                                    differs=cs_alt.value["counts"]["distinct_drugs"] != cs.value["counts"]["distinct_drugs"],
                                    note=f"{p.quality_scope}: {cs.value['counts']['distinct_drugs']} drugs; {alt_scope}: {cs_alt.value['counts']['distinct_drugs']} drugs"))
    alt_mode = "include_current" if p.fy_mode == "completed" else "completed"
    fyw_alt = fiscal_year_window(FYWindowIn(n_years=2, as_of=p.as_of, mode=alt_mode))
    insp_alt = inspections_for_sites(InspectionsIn(feis=feis, classification=["OAI"], fiscal_years=fyw_alt.value["fiscal_years"], fy_basis=p.fy_basis, project_area=p.project_area))
    alt_sites = sorted({r["fei"] for r in insp_alt.value["rows"]})
    alt_notes.append(Interpretation(term="last two fiscal years", chosen=f"{p.fy_mode} → FY{fyw.value['fiscal_years'][0]}–FY{fyw.value['fiscal_years'][-1]}",
                                    alternatives=[f"{alt_mode} → FY{fyw_alt.value['fiscal_years'][0]}–FY{fyw_alt.value['fiscal_years'][-1]}"], decision_ref="D3",
                                    alternate_result={"fiscal_years": fyw_alt.value["fiscal_years"], "sites_with_oai": alt_sites}, differs=alt_sites != oai_feis,
                                    note=f"{len(oai_feis)} OAI sites under {p.fy_mode}; {len(alt_sites)} under {alt_mode}"))
    alt_basis = "classification_date" if p.fy_basis == "inspection_end_date" else "inspection_end_date"
    insp_alt2 = inspections_for_sites(InspectionsIn(feis=feis, classification=["OAI"], fiscal_years=fyw.value["fiscal_years"], fy_basis=alt_basis, project_area=p.project_area))
    alt_sites2 = sorted({r["fei"] for r in insp_alt2.value["rows"]})
    alt_notes.append(Interpretation(term="fiscal year", chosen=p.fy_basis, alternatives=[alt_basis], decision_ref="D2",
                                    alternate_result={"sites_with_oai": alt_sites2}, differs=alt_sites2 != oai_feis,
                                    note=f"same {len(oai_feis)} sites under both bases" if alt_sites2 == oai_feis else f"{len(alt_sites2)} sites under {alt_basis}"))

    value = {
        "question": "Q1",
        "as_of": cs.value["as_of"],
        "alternate_readings": {i.term: {"chosen": i.chosen, "alternate": i.alternatives[0], "alternate_result": i.alternate_result, "differs": i.differs} for i in alt_notes},
        "quality_scope": p.quality_scope,
        "fiscal_years": fyw.value["fiscal_years"],
        "fy_basis": p.fy_basis,
        "drugs_in_shortage_for_quality": {"count_distinct_drugs": cs.value["counts"]["distinct_drugs"],
                                          "count_records": cs.value["counts"]["records"], "drugs": cs.value["drugs"]},
        "shortage_records": cs.value["records"],
        "site_coverage": sites.value["coverage"],
        "sites_with_oai_in_window": oai_sites,
        "sites_without_oai_in_window": no_oai,
        "unlinked_shortages": sites.value["unlinked"],
        "n_sites_with_oai": len(oai_sites),
    }
    out = _merge(cs, sites, fyw, insp, tool="cq_quality_shortages_oai_sites", value=value)
    # replace the generic interpretations for these terms with the computed ones
    keep = [i for i in out.interpretations if i.term not in {"quality problems", "last N fiscal years", "fiscal year", "last two fiscal years"}]
    out.interpretations = keep + alt_notes
    return out


# --------------------------------------------------------------------------- Q2
class Q2In(BaseModel):
    as_of: str | None = None
    generic_name: str = "Amoxicillin"
    presentation_like: str = "Oral Suspension%"
    approved_scope: Literal["full", "include_tentative"] = "full"


@tool(
    "cq_supply_picture",
    """CERTIFIED QUERY (Q2): For a drug + presentation (default amoxicillin oral suspension), the real supply
    picture: approved applications, actively marketed, tentative approvals, and what is currently in shortage —
    with the full status history so Resolved/Discontinued/Current are never conflated, and explicit disclosure
    that applications cannot be filtered by dosage form.""",
    decision_refs=("D1", "D4", "D9"),
)
def cq_supply_picture(p: Q2In) -> ToolResult:
    apps = applications_for_ingredient(ApplicationsIn(active_ingredient=[p.generic_name], approved_scope=p.approved_scope,
                                                      presentation_requested=p.presentation_like.replace("%", "").strip()))
    cur = current_shortages(CurrentShortagesIn(as_of=p.as_of, generic_name=[p.generic_name], presentation_like=p.presentation_like,
                                               statuses=["Current"]))
    allst = current_shortages(CurrentShortagesIn(as_of=p.as_of, generic_name=[p.generic_name], presentation_like=p.presentation_like,
                                                 statuses=["Current", "Resolved", "Discontinued"]))
    hist = shortage_history(ShortageHistoryIn(generic_name=[p.generic_name], presentation_like=p.presentation_like))
    alt_scope = "include_tentative" if p.approved_scope == "full" else "full"
    apps_alt = applications_for_ingredient(ApplicationsIn(active_ingredient=[p.generic_name], approved_scope=alt_scope))
    approved_interp = Interpretation(term="approved", chosen=p.approved_scope, alternatives=[alt_scope], decision_ref="D9",
                                     alternate_result={"approved": apps_alt.value["counts"]["approved_per_chosen_scope"]},
                                     differs=apps_alt.value["counts"]["approved_per_chosen_scope"] != apps.value["counts"]["approved_per_chosen_scope"],
                                     note=f"{p.approved_scope}: {apps.value['counts']['approved_per_chosen_scope']}; {alt_scope}: {apps_alt.value['counts']['approved_per_chosen_scope']}")
    value = {
        "question": "Q2",
        "as_of": cur.value["as_of"],
        "alternate_readings": {"approved": {"chosen": p.approved_scope, "alternate": alt_scope, "alternate_result": approved_interp.alternate_result, "differs": approved_interp.differs}},
        "drug": p.generic_name,
        "presentation_filter": p.presentation_like,
        "applications": apps.value["counts"],
        "application_records": apps.value["records"],
        "applications_filterable_by_dosage_form": False,
        "shortage_latest_status_by_record": {r["shortage_id"]: r["shortage_status"] for r in allst.value["records"]},
        "currently_in_shortage": cur.value["records"],
        "currently_in_shortage_count": cur.value["counts"]["records"],
        "status_timelines": hist.value["timelines"],
        "status_semantics": hist.value["status_semantics"],
    }
    out = _merge(apps, cur, allst, hist, tool="cq_supply_picture", value=value)
    out.interpretations = [i for i in out.interpretations if i.term != "approved applications"] + [approved_interp]
    return out


# --------------------------------------------------------------------------- Q3
class Q3In(BaseModel):
    as_of: str | None = None
    since_fy: int = 2021
    inclusive: bool = True
    fy_basis: Literal["inspection_end_date", "classification_date"] = "inspection_end_date"


@tool(
    "cq_foreign_sites_not_inspected",
    """CERTIFIED QUERY (Q3): Which foreign manufacturing establishments supplying drugs currently in shortage
    have not been inspected since FY2021? Composes current_shortages → sites_for_shortages →
    sites_not_inspected_since(foreign_only). Reports stale foreign sites, never-inspected sites (country
    unknown), and coverage of the shortage→application link.""",
    decision_refs=("D1", "D7", "D10", "D11"),
)
def cq_foreign_sites_not_inspected(p: Q3In) -> ToolResult:
    cs = current_shortages(CurrentShortagesIn(as_of=p.as_of))
    ids = [r["shortage_id"] for r in cs.value["records"]]
    sites = sites_for_shortages(SitesIn(shortage_ids=ids, as_of=p.as_of))
    feis = sites.value["distinct_feis"]
    ni = sites_not_inspected_since(NotInspectedIn(feis=feis, since_fy=p.since_fy, inclusive=p.inclusive, foreign_only=True, fy_basis=p.fy_basis))
    fei_drugs = {}
    for s in sites.value["sites"]:
        fei_drugs.setdefault(s["fei"], {"drugs": set(), "sponsors": set()})
        fei_drugs[s["fei"]]["drugs"].add(s["generic_name"]); fei_drugs[s["fei"]]["sponsors"].add(s["sponsor_name"])
    for grp in ("stale", "never_inspected", "recently_inspected"):
        for rec in ni.value[grp]:
            d = fei_drugs.get(rec["fei"], {"drugs": set(), "sponsors": set()})
            rec["drugs_in_shortage"] = sorted(d["drugs"]); rec["sponsors"] = sorted(d["sponsors"])
    # never-inspected: annotate sponsor-name inference explicitly
    for rec in ni.value["never_inspected"]:
        rec["sponsor_name_suggests_foreign"] = any(k in " ".join(rec["sponsors"]).lower() for k in ("zhejiang", "hainan", "shanxi", "nanjing", "pharma co ltd", "limited", "gmbh", "ag", "sa", "dd"))
        rec["note"] = "Country not in data; inference from sponsor name only."
    ni_alt = sites_not_inspected_since(NotInspectedIn(feis=feis, since_fy=p.since_fy, inclusive=not p.inclusive, foreign_only=True, fy_basis=p.fy_basis))
    alt_stale = sorted(r["fei"] for r in ni_alt.value["stale"])
    cur_stale = sorted(r["fei"] for r in ni.value["stale"])
    since_interp = Interpretation(term="not inspected since", chosen="last inspection FY <= target" if p.inclusive else "last inspection FY < target",
                                  alternatives=["last inspection FY < target" if p.inclusive else "last inspection FY <= target"], decision_ref="D11",
                                  alternate_result={"foreign_stale_feis": alt_stale}, differs=alt_stale != cur_stale,
                                  note="same sites under both readings" if alt_stale == cur_stale else f"{len(cur_stale)} vs {len(alt_stale)} sites")
    value = {
        "question": "Q3",
        "as_of": cs.value["as_of"],
        "alternate_readings": {"not inspected since": {"chosen": since_interp.chosen, "alternate": since_interp.alternatives[0], "alternate_result": since_interp.alternate_result, "differs": since_interp.differs}},
        "since_fy": p.since_fy,
        "current_shortage_records": cs.value["counts"]["records"],
        "current_shortage_drugs": cs.value["drugs"],
        "site_coverage": sites.value["coverage"],
        "foreign_sites_not_inspected_since": ni.value["stale"],
        "sites_never_inspected_country_unknown": ni.value["never_inspected"],
        "foreign_sites_inspected_more_recently": ni.value["recently_inspected"],
        "counts": {"foreign_stale": len(ni.value["stale"]), "never_inspected": len(ni.value["never_inspected"]),
                   "foreign_recent": len(ni.value["recently_inspected"])},
    }
    out = _merge(cs, sites, ni, tool="cq_foreign_sites_not_inspected", value=value)
    out.interpretations = [i for i in out.interpretations if i.term != "not inspected since"] + [since_interp]
    return out
