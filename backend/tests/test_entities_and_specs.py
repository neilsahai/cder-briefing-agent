from app.tools import REGISTRY, anthropic_tool_specs, call_tool


def test_resolve_synonym_and_exact():
    r = call_tool("resolve_entity", {"text": "pip-tazo", "kind": "generic_name"})
    assert r.value["resolved"] == ["Piperacillin-Tazobactam"] and r.value["method"] == "ontology_synonym"
    r = call_tool("resolve_entity", {"text": "Vancomycin HCl", "kind": "generic_name"})
    assert r.value["method"] == "exact"


def test_resolve_amoxicillin_flags_clavulanate_sibling():
    r = call_tool("resolve_entity", {"text": "amoxicillin", "kind": "generic_name"})
    assert r.value["resolved"] == ["Amoxicillin"]
    assert any("Amoxicillin-Clavulanate" in i.alternatives for i in r.interpretations)


def test_resolve_failed_inspection_maps_to_oai_with_caveat():
    r = call_tool("resolve_entity", {"text": "failed inspection", "kind": "classification"})
    assert r.value["resolved"] == ["OAI"]
    assert r.interpretations[0].decision_ref == "D8"


def test_resolve_unknown_does_not_invent():
    r = call_tool("resolve_entity", {"text": "Xyzzyomycin", "kind": "generic_name"})
    assert r.value["resolved"] == []
    assert r.warnings[0].code == "ENTITY_NOT_FOUND"


def test_resolve_presentation_family():
    r = call_tool("resolve_entity", {"text": "oral suspension", "kind": "presentation"})
    assert r.value["resolved"] == ["Oral Suspension%"]


def test_tool_specs_are_valid_anthropic_shape():
    specs = anthropic_tool_specs()
    assert len(specs) == len(REGISTRY) >= 12
    for s in specs:
        assert set(s) == {"name", "description", "input_schema"}
        assert s["input_schema"]["type"] == "object"
        assert len(s["description"]) > 40
