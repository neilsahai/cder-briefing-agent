import tempfile
from pathlib import Path

from app.registry.certified import CertifiedRegistry, similarity


def fresh():
    return CertifiedRegistry(Path(tempfile.mkdtemp()) / "r.sqlite")


def test_seeded_with_three_required_queries():
    r = fresh()
    names = [e["name"] for e in r.list()]
    assert names == ["q1_quality_shortages_oai_sites", "q2_amoxicillin_oral_suspension_supply", "q3_foreign_sites_not_inspected_since_fy2021"]
    assert all("seed" in e["verified_by"] for e in r.list())


def test_exact_and_paraphrase_match():
    r = fresh()
    m = r.match("Which foreign manufacturing establishments supplying drugs currently in shortage have not been inspected since FY2021?")
    assert m and m["name"].startswith("q3") and m["match_kind"] == "lexical"
    m = r.match("how many drugs are in shortage due to quality problems and which of their sites got an OAI in the last two fiscal years")
    assert m and m["name"].startswith("q1")


def test_unrelated_question_does_not_match():
    r = fresh()
    assert r.match("Which sponsors hold the most tentative approvals?") is None
    assert similarity("sponsors tentative approvals", "foreign establishments inspected") < 0.3


def test_promote_and_revoke_with_audit():
    r = fresh()
    e = r.promote(name="tentative_by_sponsor", question="Which sponsors hold the most tentative approvals?", tool="sql_query",
                  args={"sql": "SELECT 1"}, pins={}, verified_by="pharmacist A", source_run_id="abc123", notes="reviewed")
    assert e["status"] == "active" and e["version"] == 1
    assert r.match("Which sponsors hold the most tentative approvals?")["name"] == "tentative_by_sponsor"
    e2 = r.promote(name="tentative_by_sponsor", question="Which sponsors hold the most tentative approvals?", tool="sql_query",
                   args={"sql": "SELECT 2"}, pins={}, verified_by="pharmacist B", source_run_id="def456")
    assert e2["version"] == 2
    r.revoke("tentative_by_sponsor", actor="pharmacist B", reason="superseded")
    assert r.match("Which sponsors hold the most tentative approvals?") is None
    actions = [a["action"] for a in r.audit()]
    assert actions[:3] == ["revoke", "recertify", "promote"]
