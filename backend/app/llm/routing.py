"""Model routing BY ROLE, with rule-based escalation. No LLM decides what is 'hard'.

Why by role (not a complexity classifier): the trigger for using a stronger model must be a fact
visible in the trace ("escalated: 2 interpretations diverged"), not a judgment call by another model.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

ROLE_MODELS = {
    "gate": os.environ.get("MODEL_GATE", "claude-haiku-5-5"),
    "entity": os.environ.get("MODEL_ENTITY", "claude-haiku-5-5"),
    "planner": os.environ.get("MODEL_PLANNER", "claude-sonnet-5-5"),
    "planner_escalated": os.environ.get("MODEL_PLANNER_ESCALATED", "claude-opus-5-5"),
    "narrator": os.environ.get("MODEL_NARRATOR", "claude-sonnet-5-5"),
    "verifier": os.environ.get("MODEL_VERIFIER", "claude-opus-5-5"),
    "sql_candidate_a": os.environ.get("MODEL_SQL_A", "claude-sonnet-5-5"),
    "sql_candidate_b": os.environ.get("MODEL_SQL_B", "claude-sonnet-5-5"),
    "sql_candidate_c": os.environ.get("MODEL_SQL_C", "claude-opus-5-5"),
    "judge": os.environ.get("MODEL_JUDGE", "claude-sonnet-5-5"),
}


@dataclass
class EscalationDecision:
    escalate: bool
    reasons: list[str]

    @property
    def role(self) -> str:
        return "planner_escalated" if self.escalate else "planner"


def planner_escalation(n_divergent_interpretations: int, needs_sql: bool, gate_category: str) -> EscalationDecision:
    """Deterministic. [DECISIONS D14]"""
    reasons = []
    if n_divergent_interpretations >= 2:
        reasons.append(f"{n_divergent_interpretations} ambiguous terms with materially different readings")
    if needs_sql:
        reasons.append("no certified tool covers the question; LLM-authored SQL required")
    if gate_category == "in_scope_not_in_data":
        reasons.append("question is in scope but the data may not support it; needs careful partial answer")
    return EscalationDecision(escalate=bool(reasons), reasons=reasons)


# ----------------------------------------------------------------------------- pricing
# USD per million tokens. Loaded from pricing.json if present; otherwise cost is reported as None
# (never guessed). Update from https://www.anthropic.com/pricing before quoting dollar figures.
_PRICING_PATH = Path(__file__).with_name("pricing.json")


def load_pricing() -> dict[str, dict[str, float]]:
    if _PRICING_PATH.exists():
        return json.loads(_PRICING_PATH.read_text())
    return {}


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int, cache_read: int = 0, cache_write: int = 0) -> float | None:
    p = load_pricing().get(model)
    if not p:
        return None
    cost = input_tokens * p.get("input", 0) + output_tokens * p.get("output", 0)
    cost += cache_read * p.get("cache_read", p.get("input", 0) * 0.1) + cache_write * p.get("cache_write", p.get("input", 0) * 1.25)
    return round(cost / 1_000_000, 6)
