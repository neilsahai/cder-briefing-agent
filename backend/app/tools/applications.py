"""Application tools. [D9]"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .. import ontology
from ..data.audit import get_audit
from ..data.store import get_store
from ..models import Interpretation, Severity, ToolResult, Warning
from .base import tool


class ApplicationsIn(BaseModel):
    active_ingredient: list[str] = Field(description="Canonical active ingredient(s) (use resolve_entity).")
    approved_scope: Literal["full", "include_tentative"] = Field("full", description="'full' excludes Tentative Approval (default). [D9]")
    presentation_requested: str | None = Field(None, description="If the user asked about a dosage form (e.g. 'oral suspension'), pass it so the limitation is disclosed.")


@tool(
    "applications_for_ingredient",
    """Count and list drug applications for an active ingredient: approved (full), tentative approvals,
    actively marketed (Prescription), discontinued; with sponsor, FEI, and row IDs. Discloses that
    applications.csv has NO dosage-form column, so counts cannot be restricted to a presentation. Use for
    'how many approved applications', 'how many are actively marketed', 'who holds ANDAs for X'.""",
    decision_refs=("D9",),
)
def applications_for_ingredient(p: ApplicationsIn) -> ToolResult:
    store = get_store()
    audit = get_audit()
    df = store.df("SELECT * FROM applications WHERE active_ingredient IN (" + ",".join("?" * len(p.active_ingredient)) + ") ORDER BY approval_date",
                  p.active_ingredient)
    rows = store.rowrefs("applications", df)
    warnings = audit.warnings_for(rows, min_severity=Severity.medium)
    full = ontology.definition("approved_application")["full"]
    approved_full = df[df["marketing_status"].isin(full)]
    tentative = df[df["marketing_status"] == "Tentative Approval"]
    marketed = df[df["marketing_status"] == "Prescription"]
    discontinued = df[df["marketing_status"] == "Discontinued"]
    chosen_approved = len(df) if p.approved_scope == "include_tentative" else len(approved_full)
    if p.presentation_requested:
        warnings.insert(0, Warning(code="DQ12_missing_dosage_form", severity=Severity.high,
                                   message=f"The question asks about '{p.presentation_requested}' but applications.csv has no dosage-form column. "
                                           f"These application counts cover ALL {', '.join(p.active_ingredient)} products (any dosage form) and may overstate "
                                           f"the number of {p.presentation_requested} applications."))
    recs = [{"application_number": r.application_number, "app_type": r.app_type, "sponsor_name": r.sponsor_name,
             "active_ingredient": r.active_ingredient, "approval_date": str(r.approval_date)[:10], "marketing_status": r.marketing_status,
             "manufacturing_fei": r.manufacturing_fei, "row_id": f"applications#L{int(r.line_no)}"} for r in df.itertuples()]
    value = {
        "active_ingredient": p.active_ingredient,
        "counts": {
            "total_applications": len(df),
            "approved_full": len(approved_full),
            "tentative_approval": len(tentative),
            "actively_marketed": len(marketed),
            "approved_but_discontinued": len(discontinued),
            "approved_per_chosen_scope": chosen_approved,
        },
        "dosage_form_available": False,
        "records": recs,
    }
    interps = [
        Interpretation(term="approved applications", chosen=p.approved_scope,
                       alternatives=["include_tentative" if p.approved_scope == "full" else "full"], decision_ref="D9",
                       note=f"full={len(approved_full)} (Prescription+Discontinued); include_tentative={len(df)}"),
        Interpretation(term="actively marketed", chosen="marketing_status = Prescription", alternatives=[], decision_ref="D9"),
    ]
    return ToolResult(tool="applications_for_ingredient", value=value, rows=rows, source_tables=["applications"],
                      interpretations=interps, warnings=warnings)


class DataHealthIn(BaseModel):
    as_of: str | None = None


@tool(
    "data_health",
    """Summarize the data-quality audit: every rule that fired, severity, and affected row counts. Use when
    asked how reliable the data is, what caveats apply overall, or before drafting a briefing.""",
    decision_refs=("D4", "D7", "D9"),
)
def data_health(p: DataHealthIn) -> ToolResult:
    audit = get_audit(p.as_of)
    s = audit.summary()
    details = [{"rule_id": f.rule_id, "severity": f.severity, "message": f.message, "row_ids": [r.id for r in f.rows][:20]}
               for f in audit.findings if f.severity in ("high", "medium")]
    return ToolResult(tool="data_health", value={"summary": s, "high_and_medium_findings": details},
                      source_tables=["drug_shortages", "applications", "inspections"])


class GlossaryIn(BaseModel):
    terms: list[str] | None = Field(None, description="Terms to define (e.g. 'Resolved', 'OAI', 'fiscal year', 'quality problems'). None = all.")


@tool(
    "glossary",
    """Return the ontology's definitions: FDA status semantics (Current/Resolved/Discontinued), inspection
    classifications (NAI/VAI/OAI), fiscal-year rule, and the default reading + alternates for every ambiguous
    term with its DECISIONS.md reference. Use for definitional questions and whenever a status or
    classification word needs to be explained. Certified: content comes from ontology.yaml, not the model.""",
    decision_refs=("D2", "D4", "D5", "D8", "D9", "D10", "D11"),
)
def glossary(p: GlossaryIn) -> ToolResult:
    o = ontology.load()
    classifications = {
        "NAI": "No Action Indicated — facility in an acceptable state of compliance.",
        "VAI": "Voluntary Action Indicated — objectionable conditions found; voluntary correction; not a regulatory action.",
        "OAI": "Official Action Indicated — facility in an unacceptable state of compliance; regulatory action may follow. Classification is per project area.",
    }
    full = {
        "status_semantics": {k: {"fda_label": v["fda_label"], "meaning": v["meaning"], "note": v.get("note")} for k, v in o["status_semantics"].items()},
        "inspection_classifications": classifications,
        "fiscal_year": o["definitions"]["fiscal_year"],
        "ambiguous_terms": {t: {"definition": m["definition"], "interpretations": m.get("interpretations", []), "note": m.get("note")} for t, m in o["ambiguous_terms"].items()},
        "definitions": o["definitions"],
        "defaults": o["defaults"],
    }
    if p.terms:
        wanted = [t.lower() for t in p.terms]
        def keep(d: dict) -> dict:
            return {k: v for k, v in d.items() if any(w in k.lower() or k.lower() in w for w in wanted)}
        full = {"status_semantics": keep(full["status_semantics"]), "inspection_classifications": keep(full["inspection_classifications"]),
                "fiscal_year": full["fiscal_year"] if any("fiscal" in w or "fy" in w for w in wanted) else None,
                "ambiguous_terms": keep(full["ambiguous_terms"]), "definitions": keep(full["definitions"]), "defaults": full["defaults"]}
    return ToolResult(tool="glossary", value=full, source_tables=["ontology.yaml"],
                      interpretations=[Interpretation(term="definitions", chosen="ontology.yaml v" + str(o["version"]), alternatives=[], decision_ref="D4")])
