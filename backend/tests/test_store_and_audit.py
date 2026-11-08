"""Data layer + audit regression tests. Each DQ rule is pinned to the exact rows it must find."""
from datetime import date

from app.data.store import fiscal_year, fy_bounds
from app.models import RowRef


def test_tables_loaded_with_line_numbers(store):
    assert store.frames["drug_shortages"].shape[0] == 150
    assert store.frames["applications"].shape[0] == 128
    assert store.frames["inspections"].shape[0] == 80
    # line 2 is the first data row in every file
    assert store.frames["drug_shortages"].iloc[0]["line_no"] == 2
    assert store.frames["drug_shortages"].iloc[0]["shortage_id"] == "DS-2023-0142"


def test_data_max_date_is_disclosed_as_of(store):
    assert store.data_max_date == date(2025, 10, 23)  # D1


def test_fiscal_year_rule():  # D2
    assert fiscal_year(date(2023, 10, 1)) == 2024
    assert fiscal_year(date(2024, 9, 30)) == 2024
    assert fiscal_year(date(2024, 10, 1)) == 2025
    assert fy_bounds(2024) == (date(2023, 10, 1), date(2024, 9, 30))


def test_shortages_latest_dedupes_to_one_row_per_id(store):  # D4
    n = store.df("SELECT COUNT(*) n FROM shortages_latest").iloc[0, 0]
    assert n == 149
    row = store.df("SELECT shortage_status, revision_date FROM shortages_latest WHERE shortage_id='DS-2023-0142'")
    assert row.iloc[0]["shortage_status"] == "Current"
    assert str(row.iloc[0]["revision_date"])[:10] == "2024-01-10"


def test_dq01_status_conflict_is_exactly_the_amoxicillin_record(audit):
    f = [x for x in audit.findings if x.rule_id == "DQ01_status_conflict"]
    assert len(f) == 1
    assert f[0].details["shortage_id"] == "DS-2023-0142"
    assert f[0].details["used"] == "Current"
    assert sorted(r.line for r in f[0].rows) == [2, 3]
    assert "Resolved" in f[0].message and "Current" in f[0].message


def test_dq02_orphan_applications_count(audit):
    f = [x for x in audit.findings if x.rule_id == "DQ02_orphan_application"][0]
    assert f.details == {"count": 129, "total": 150}


def test_dq03_ingredient_mismatch_is_amox_clav_to_anda078201(audit):
    f = [x for x in audit.findings if x.rule_id == "DQ03_ingredient_mismatch"]
    assert len(f) == 1 and f[0].details["application"] == "ANDA078201"
    assert len([r for r in f[0].rows if r.table == "drug_shortages"]) == 7


def test_dq04_no_invalid_fei_but_dq05_prefix_anomalies(audit):
    assert not [x for x in audit.findings if x.rule_id == "DQ04_fei_invalid_format"]
    f = {x.message.split()[1]: x for x in audit.findings if x.rule_id == "DQ05_fei_prefix_anomaly"}
    assert len(f["applications"].rows) == 19
    assert len(f["inspections"].rows) == 4
    assert "4001567890" in f["applications"].details["feis"]


def test_dq06_feis_without_inspection(audit):
    feis = {x.details["fei"] for x in audit.findings if x.rule_id == "DQ06_fei_no_inspection"}
    assert feis == {"3007891234", "4001567890"}


def test_dq07_fy_straddle_includes_sandoz_princeton(audit):
    msgs = [x.message for x in audit.findings if x.rule_id == "DQ07_fy_boundary_straddle"]
    assert len(msgs) == 13
    assert any("3004455667" in m and "FY2024" in m and "FY2025" in m for m in msgs)


def test_dq08_stale_current_count_at_default_as_of(audit):
    assert len([x for x in audit.findings if x.rule_id == "DQ08_stale_current"]) == 34


def test_lineage_attaches_conflict_to_amoxicillin_row(audit):
    w = audit.warnings_for([RowRef(table="drug_shortages", line=2, key="DS-2023-0142@2024-01-10")])
    codes = {x.code for x in w}
    assert "DQ01_status_conflict" in codes
    assert "DQ08_stale_current" in codes


def test_lineage_is_silent_for_clean_row(audit):
    # inspections line 2 (ICU Medical OAI 2024) has no straddle and no anomaly
    w = audit.warnings_for([RowRef(table="inspections", line=2, key="x")])
    assert w == []
