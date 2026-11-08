"""Entity / literal resolution. Maps user phrasing to canonical dataset values so the planner never
guesses a literal. [Snowflake: incorrect literal generation is a top text-to-SQL failure mode]"""
from __future__ import annotations

from difflib import get_close_matches
from typing import Literal

from pydantic import BaseModel, Field

from .. import ontology
from ..data.store import get_store
from ..models import Interpretation, Severity, ToolResult, Warning
from .base import tool


class ResolveIn(BaseModel):
    text: str = Field(description="The user's phrase, e.g. 'pip-tazo', 'oral suspension', 'failed inspection', 'overseas'.")
    kind: Literal["generic_name", "presentation", "classification", "country", "firm", "application"] = Field(
        description="Which kind of value to resolve to."
    )


@tool(
    "resolve_entity",
    """Resolve a user phrase to canonical value(s) that actually exist in the data. Returns exact matches,
    synonym matches from the ontology, and fuzzy candidates with scores. ALWAYS call this before filtering on a
    drug name, presentation, firm, country, or classification so no literal is invented. If nothing resolves,
    say so rather than guessing.""",
    decision_refs=("D7",),
)
def resolve_entity(p: ResolveIn) -> ToolResult:
    store = get_store()
    q = p.text.strip().lower()
    warnings: list[Warning] = []
    interps: list[Interpretation] = []

    if p.kind == "generic_name":
        universe = sorted(set(store.frames["drug_shortages"]["generic_name"]) | set(store.frames["applications"]["active_ingredient"]))
        syn = ontology.synonyms("generic_name")
    elif p.kind == "presentation":
        universe = sorted(set(store.frames["drug_shortages"]["presentation"]))
        syn = ontology.synonyms("presentation_family")
    elif p.kind == "classification":
        universe = ["NAI", "VAI", "OAI"]
        syn = ontology.synonyms("classification")
    elif p.kind == "country":
        universe = sorted(set(store.frames["inspections"]["country"]))
        syn = ontology.synonyms("country")
    elif p.kind == "firm":
        universe = sorted(set(store.frames["inspections"]["firm_name"]) | set(store.frames["applications"]["sponsor_name"]))
        syn = {}
    else:  # application
        universe = sorted(set(store.frames["applications"]["application_number"]) | set(store.frames["drug_shortages"]["related_application"]))
        syn = {}

    exact = [u for u in universe if u.lower() == q]
    synonym_hit = syn.get(q)
    contains = [u for u in universe if q in u.lower() and u not in exact]
    fuzzy = [u for u in get_close_matches(p.text, universe, n=5, cutoff=0.6) if u not in exact and u not in contains]

    resolved: list[str] = []
    method = None
    if exact:
        resolved, method = exact, "exact"
    elif synonym_hit:
        # synonyms may be a LIKE pattern (e.g. 'Oral Suspension%') or a negation ('!= United States')
        resolved, method = [synonym_hit], "ontology_synonym"
    elif len(contains) == 1:
        resolved, method = contains, "unique_substring"
    elif contains:
        resolved, method = contains, "multiple_substring"
        warnings.append(Warning(code="INTERP_AMBIGUOUS_ENTITY", severity=Severity.medium,
                                message=f"'{p.text}' matches {len(contains)} {p.kind} values: {contains}. Pick explicitly or report all."))
    elif fuzzy:
        # Fuzzy hits are NEVER a resolution — only candidates. The planner must ask or pick explicitly.
        resolved, method = [], "fuzzy_candidates_only"
        warnings.append(Warning(code="INTERP_FUZZY_ENTITY", severity=Severity.high,
                                message=f"'{p.text}' does not match any {p.kind} value. Closest candidates: {fuzzy}. "
                                        f"Do NOT use a candidate without confirming it with the user."))
    else:
        warnings.append(Warning(code="ENTITY_NOT_FOUND", severity=Severity.high,
                                message=f"'{p.text}' does not match any {p.kind} value in the dataset. Do not invent one."))

    if p.kind == "classification" and q in ("failed inspection", "failed"):
        interps.append(Interpretation(term="failed inspection", chosen="OAI", alternatives=["VAI"], decision_ref="D8",
                                      note="'Failed' is colloquial. OAI = Official Action Indicated (unacceptable compliance). VAI is not a failure."))
    if p.kind == "generic_name" and "amoxicillin" in q and "clav" not in q and "augmentin" not in q:
        others = [u for u in universe if "amoxicillin" in u.lower() and u.lower() != "amoxicillin"]
        if others:
            interps.append(Interpretation(term=p.text, chosen="Amoxicillin", alternatives=others, decision_ref="D6",
                                          note="Amoxicillin and Amoxicillin-Clavulanate are different products; not combined unless asked."))

    return ToolResult(
        tool="resolve_entity",
        value={"query": p.text, "kind": p.kind, "resolved": resolved, "method": method,
               "candidates": {"exact": exact, "synonym": synonym_hit, "substring": contains, "fuzzy": fuzzy}},
        source_tables=["drug_shortages", "applications", "inspections"],
        warnings=warnings,
        interpretations=interps,
    )
