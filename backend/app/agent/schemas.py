"""Structured-output tool schemas for the LLM roles (gate / declare_interpretations / finish / narrate / verify)."""
from __future__ import annotations

GATE_TOOL = {
    "name": "classify_question",
    "description": "Classify answerability of the question before any data access.",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {"type": "string", "enum": ["answerable", "in_scope_not_in_data", "out_of_scope", "unsafe_or_policy"]},
            "reason": {"type": "string"},
            "answerable_part": {"type": "string", "description": "What CAN be answered from the data (may be empty)."},
            "unanswerable_part": {"type": "string", "description": "What cannot, and which field would be needed (may be empty)."},
            "suggested_question": {"type": "string", "description": "For out_of_scope / unsafe_or_policy only: a concrete, safe question this tool CAN answer that serves the asker's underlying need (e.g. 'What is the status of each amoxicillin shortage record as of the snapshot?'). Empty if none."},
            "ambiguous_terms": {"type": "array", "items": {"type": "string"}},
            "literals_to_resolve": {"type": "array", "items": {"type": "object", "properties": {
                "text": {"type": "string"}, "kind": {"type": "string", "enum": ["generic_name", "presentation", "classification", "country", "firm", "application", "fei", "year"]}},
                "required": ["text", "kind"]}},
        },
        "required": ["category", "reason", "ambiguous_terms", "literals_to_resolve"],
    },
}

DECLARE_INTERPRETATIONS_TOOL = {
    "name": "declare_interpretations",
    "description": "Declare, BEFORE touching data, every ambiguous term in the question and the readings you will apply.",
    "input_schema": {
        "type": "object",
        "properties": {
            "restated_question": {"type": "string", "description": "The question in precise terms using ontology definitions."},
            "interpretations": {"type": "array", "items": {"type": "object", "properties": {
                "term": {"type": "string"},
                "default_reading": {"type": "string"},
                "alternates": {"type": "array", "items": {"type": "string"}},
                "will_compute_alternate": {"type": "boolean", "description": "True if you will run the alternate too so results can be compared."},
                "decision_ref": {"type": "string", "description": "DECISIONS.md section e.g. D5"},
            }, "required": ["term", "default_reading", "alternates", "will_compute_alternate"]}},
            "plan": {"type": "array", "items": {"type": "string"}, "description": "Ordered list of tool calls you intend to make."},
        },
        "required": ["restated_question", "interpretations", "plan"],
    },
}

FINISH_TOOL = {
    "name": "finish",
    "description": "Signal that evidence gathering is complete. Reference evidence ids; do not state numbers.",
    "input_schema": {
        "type": "object",
        "properties": {
            "evidence_used": {"type": "array", "items": {"type": "string"}, "description": "Evidence ids (E1, E2...) the answer should draw on."},
            "divergent_interpretations": {"type": "array", "items": {"type": "object", "properties": {
                "term": {"type": "string"}, "evidence_a": {"type": "string"}, "evidence_b": {"type": "string"},
                "differs_materially": {"type": "boolean"}, "how": {"type": "string"}}, "required": ["term", "differs_materially"]}},
            "used_sql": {"type": "boolean"},
            "cannot_answer": {"type": "array", "items": {"type": "string"}, "description": "Parts of the question the data cannot answer and why."},
            "analyst_notes": {"type": "string", "description": "Guidance for the narrator: what matters most, what to foreground. No numbers."},
        },
        "required": ["evidence_used", "divergent_interpretations", "used_sql", "cannot_answer", "analyst_notes"],
    },
}

NARRATE_TOOL = {
    "name": "write_answer",
    "description": "Return the answer in Markdown with placeholders and citations.",
    "input_schema": {
        "type": "object",
        "properties": {
            "markdown": {"type": "string", "description": "Markdown with {{E<n>.path}} placeholders for every value and [E<n>] citations on every factual sentence. No digits."},
            "headline": {"type": "string", "description": "One sentence, same placeholder rules, suitable to read aloud."},
        },
        "required": ["markdown", "headline"],
    },
}

VERIFY_TOOL = {
    "name": "verification_report",
    "description": "Claim-level verification of the rendered answer.",
    "input_schema": {
        "type": "object",
        "properties": {
            "claims": {"type": "array", "items": {"type": "object", "properties": {
                "text": {"type": "string"},
                "verdict": {"type": "string", "enum": ["supported", "misattributed", "unsupported", "interpretation"]},
                "evidence_ids": {"type": "array", "items": {"type": "string"}},
                "expected_source_table": {"type": "string"},
                "note": {"type": "string"},
            }, "required": ["text", "verdict", "evidence_ids"]}},
            "interpretations_disclosed": {"type": "boolean"},
            "high_warnings_surfaced": {"type": "boolean"},
            "status_semantics_respected": {"type": "boolean"},
            "no_country_asserted_for_unknown": {"type": "boolean"},
            "overall": {"type": "string", "enum": ["pass", "pass_with_notes", "fail"]},
            "summary": {"type": "string"},
        },
        "required": ["claims", "interpretations_disclosed", "high_warnings_surfaced", "status_semantics_respected",
                     "no_country_asserted_for_unknown", "overall", "summary"],
    },
}
