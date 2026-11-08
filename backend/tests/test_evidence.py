

def test_int_keys_in_evidence_are_indexable_and_renderable():
    from app.agent.evidence import EvidenceRegistry, render
    from app.models import ToolResult
    reg = EvidenceRegistry()
    reg.add("sql_query", {}, ToolResult(tool="sql_query", value={"by_year": {2024: 3, 2025: 5}}, rows=[], source_tables=["inspections"]), certified=False)
    idx = reg.path_index()
    assert '["2024"]' in idx
    text, _ = render('In 2025 there were {{E1.by_year["2025"]}} inspections.', reg)
    assert "5" in text


def test_token_allowed_suffix_on_identifier():
    from app.agent.evidence import token_allowed
    allowed = {"ANDA065440", "2018", "6"}
    assert token_allowed("ANDA065440-style", allowed)
    assert token_allowed("FY2018", allowed)
    assert token_allowed("6-site", allowed)
    assert not token_allowed("ANDA065441", allowed)
    assert not token_allowed("FY2019", allowed)
