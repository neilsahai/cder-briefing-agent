"""Golden answers for the three required queries under default AND alternate interpretations.
These are the Tier-1 regression evals. If any of these change, DECISIONS.md must change with them."""
import pytest

from app.tools import call_tool


# ----------------------------------------------------------------------------- Q1
def test_q1_default_strict_fy24_25():
    r = call_tool("cq_quality_shortages_oai_sites", {})
    v = r.value
    assert v["as_of"] == "2025-10-23"
    assert v["fiscal_years"] == [2024, 2025]
    assert v["drugs_in_shortage_for_quality"]["count_distinct_drugs"] == 6
    assert v["drugs_in_shortage_for_quality"]["drugs"] == [
        "Ampicillin-Sulbactam", "Cefepime HCl", "Meropenem", "Methotrexate Sodium", "Piperacillin-Tazobactam", "Vancomycin HCl"]
    assert v["site_coverage"] == {"input_records": 6, "linked": 6, "unlinked": 0}
    oai = {s["fei"]: s for s in v["sites_with_oai_in_window"]}
    assert set(oai) == {"3001234567", "3002891456", "3007445123", "3009123789"}
    assert oai["3001234567"]["facility_operator"] == "Baxter Healthcare Corporation"
    assert oai["3009123789"]["oai_inspections"][0]["fy_by_end"] == 2025
    # Hospira = VAI only; Zhejiang Huahai = never inspected — both must be separated, not dropped
    notes = {s["fei"]: s["note"] for s in v["sites_without_oai_in_window"]}
    assert notes == {"3005678901": "no OAI in window", "3007891234": "no inspection record"}
    # every number is backed by rows
    assert len(r.rows) >= 6 + 6 + 4
    assert {i.decision_ref for i in r.interpretations} >= {"D1", "D2", "D3", "D5", "D6", "D7", "D8"}
    assert any(w.code == "COUNTRY_UNKNOWN" for w in r.warnings)


def test_q1_broad_quality_scope_changes_count():
    r = call_tool("cq_quality_shortages_oai_sites", {"quality_scope": "broad"})
    assert r.value["drugs_in_shortage_for_quality"]["count_records"] == 21
    assert r.value["drugs_in_shortage_for_quality"]["count_distinct_drugs"] == 15
    interp = [i for i in r.interpretations if i.term == "quality problems"][0]
    assert interp.chosen == "broad" and interp.alternatives == ["strict"]


def test_q1_include_current_fy_mode_same_oai_set_and_says_so():
    r = call_tool("cq_quality_shortages_oai_sites", {"fy_mode": "include_current"})
    assert r.value["fiscal_years"] == [2025, 2026]
    # FY2026 has no classified OAI yet; FY2024 OAIs drop out
    assert {s["fei"] for s in r.value["sites_with_oai_in_window"]} == {"3001234567", "3009123789"}


def test_q1_classification_date_basis_identical_for_these_sites():
    a = call_tool("cq_quality_shortages_oai_sites", {"fy_basis": "inspection_end_date"})
    b = call_tool("cq_quality_shortages_oai_sites", {"fy_basis": "classification_date"})
    assert {s["fei"] for s in a.value["sites_with_oai_in_window"]} == {s["fei"] for s in b.value["sites_with_oai_in_window"]}


def test_q1_as_of_early_2025_per_pdf_wording():
    r = call_tool("cq_quality_shortages_oai_sites", {"as_of": "2025-03-01"})
    assert r.value["fiscal_years"] == [2023, 2024]
    assert {s["fei"] for s in r.value["sites_with_oai_in_window"]} == {"3002891456", "3007445123"}


# ----------------------------------------------------------------------------- Q2
def test_q2_amoxicillin_oral_suspension_default():
    r = call_tool("cq_supply_picture", {})
    v = r.value
    assert v["applications"] == {"total_applications": 6, "approved_full": 4, "tentative_approval": 2,
                                 "actively_marketed": 3, "approved_but_discontinued": 1, "approved_per_chosen_scope": 4}
    assert v["applications_filterable_by_dosage_form"] is False
    assert v["currently_in_shortage_count"] == 1
    assert v["currently_in_shortage"][0]["shortage_id"] == "DS-2023-0142"
    assert v["shortage_latest_status_by_record"] == {"DS-2023-0142": "Current", "DS-2022-0089": "Discontinued"}
    tl = v["status_timelines"]["DS-2023-0142"]
    assert tl["status_changed"] is True
    assert [t["status"] for t in tl["timeline"]] == ["Resolved", "Current"]
    codes = {w.code for w in r.warnings}
    assert {"DQ01_status_conflict", "DQ12_missing_dosage_form"} <= codes
    # the dosage-form warning must be HIGH because the question literally asked for oral suspension
    assert [w for w in r.warnings if w.code == "DQ12_missing_dosage_form"][0].severity.value == "high"


def test_q2_include_tentative_scope():
    r = call_tool("cq_supply_picture", {"approved_scope": "include_tentative"})
    assert r.value["applications"]["approved_per_chosen_scope"] == 6


def test_q2_as_of_before_relisting_shows_resolved():
    # Between 2023-11-15 and 2024-01-10 the latest revision said Resolved. The system must report that
    # honestly for that as-of date, AND still carry the conflict warning.
    r = call_tool("cq_supply_picture", {"as_of": "2023-12-01"})
    assert r.value["currently_in_shortage_count"] == 0
    assert r.value["shortage_latest_status_by_record"]["DS-2023-0142"] == "Resolved"
    assert any(w.code == "DQ01_status_conflict" for w in r.warnings)


# ----------------------------------------------------------------------------- Q3
def test_q3_default():
    r = call_tool("cq_foreign_sites_not_inspected", {})
    v = r.value
    assert v["current_shortage_records"] == 57
    assert v["site_coverage"] == {"input_records": 57, "linked": 13, "unlinked": 44}
    stale = {s["fei"]: s for s in v["foreign_sites_not_inspected_since"]}
    assert set(stale) == {"3025111222", "3026333444", "3027555666", "4005777888"}
    assert stale["3027555666"]["last_inspection_fy"] == 2017
    assert stale["4005777888"]["country"] == "China"
    never = {s["fei"] for s in v["sites_never_inspected_country_unknown"]}
    assert never == {"3007891234", "4001567890"}
    assert {s["fei"] for s in v["foreign_sites_inspected_more_recently"]} == {"3010234567"}
    assert v["counts"] == {"foreign_stale": 4, "never_inspected": 2, "foreign_recent": 1}
    codes = {w.code for w in r.warnings}
    assert {"COVERAGE", "COUNTRY_UNKNOWN", "FEI_VERIFY"} <= codes


def test_q3_exclusive_reading_changes_nothing_here_but_is_labeled():
    r = call_tool("cq_foreign_sites_not_inspected", {"inclusive": False})
    assert {s["fei"] for s in r.value["foreign_sites_not_inspected_since"]} == {"3025111222", "3026333444", "3027555666", "4005777888"}
    assert [i for i in r.interpretations if i.term == "not inspected since"][0].chosen == "last inspection FY < target"


def test_q3_since_fy2024_moves_aurobindo_hyderabad():
    r = call_tool("cq_foreign_sites_not_inspected", {"since_fy": 2024})
    assert "3010234567" in {s["fei"] for s in r.value["foreign_sites_not_inspected_since"]}


# ----------------------------------------------------------------------------- invariants
@pytest.mark.parametrize("name,args", [
    ("cq_quality_shortages_oai_sites", {}),
    ("cq_supply_picture", {}),
    ("cq_foreign_sites_not_inspected", {}),
    ("current_shortages", {}),
    ("applications_for_ingredient", {"active_ingredient": ["Amoxicillin"]}),
])
def test_every_result_has_rows_tables_and_decision_refs(name, args):
    r = call_tool(name, args)
    assert r.rows, f"{name} returned numbers without row citations"
    assert r.source_tables
    assert all(i.decision_ref.startswith("D") for i in r.interpretations)
    assert all(x.id.split("#L")[0] in ("drug_shortages", "applications", "inspections") for x in r.rows)
