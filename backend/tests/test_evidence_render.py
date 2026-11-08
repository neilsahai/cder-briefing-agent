"""Placeholder rendering: the mechanism that makes model-written numbers impossible. No LLM needed."""
import pytest

from app.agent.evidence import EvidenceRegistry, RenderError, citations_in, render
from app.tools import call_tool


@pytest.fixture
def reg():
    r = EvidenceRegistry()
    r.add("cq_quality_shortages_oai_sites", {}, call_tool("cq_quality_shortages_oai_sites", {}))
    r.add("fiscal_year_window", {"n_years": 2}, call_tool("fiscal_year_window", {"n_years": 2}))
    return r


def test_render_substitutes_values(reg):
    t = "As of {{E1.as_of}}, {{E1.drugs_in_shortage_for_quality.count_distinct_drugs}} drugs are in shortage [E1]."
    out, subs = render(t, reg)
    assert out == "As of 2025-10-23, 6 drugs are in shortage [E1]."
    assert subs[1]["value"] == 6


def test_render_list_formats(reg):
    out, _ = render("Drugs: {{E1.drugs_in_shortage_for_quality.drugs|and}}.", reg)
    assert out.startswith("Drugs: Ampicillin-Sulbactam, Cefepime HCl") and " and Vancomycin HCl." in out
    out, _ = render("{{E1.sites_with_oai_in_window|count}} sites; FY{{E2.fiscal_years[0]}}–FY{{E2.fiscal_years[1]}}.", reg)
    assert out == "4 sites; FY2024–FY2025."


def test_render_rejects_literal_digits(reg):
    with pytest.raises(RenderError, match="literal digit"):
        render("There are 6 drugs in shortage [E1].", reg)
    with pytest.raises(RenderError, match="literal digit"):
        render("FEI 3001234567 received an OAI [E1].", reg)


def test_render_rejects_unknown_evidence_or_path(reg):
    with pytest.raises(RenderError, match="unknown evidence"):
        render("{{E9.as_of}}", reg)
    with pytest.raises(RenderError, match="not found"):
        render("{{E1.made_up_field}}", reg)
    with pytest.raises(RenderError, match="out of range"):
        render("{{E2.fiscal_years[7]}}", reg)


def test_citations_parsed():
    assert citations_in("A [E1]. B [E2, E3]. C [E1].") == ["E1", "E2", "E3"]


def test_registry_prompt_contains_warnings_and_interpretations(reg):
    txt = reg.for_prompt()
    assert "DQ06_fei_no_inspection" in txt or "COUNTRY_UNKNOWN" in txt
    assert "quality problems → strict" in txt
    assert "### E1" in txt and "### E2" in txt
