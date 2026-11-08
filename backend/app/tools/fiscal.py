"""Fiscal-year tools. [D2, D3]"""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from ..data.store import fiscal_year, fy_bounds, get_store
from ..models import Interpretation, ToolResult
from .base import tool


class FYWindowIn(BaseModel):
    n_years: int = Field(2, ge=1, le=10, description="How many fiscal years in the window.")
    as_of: str | None = Field(None, description="ISO date. Default = latest date in the dataset.")
    mode: Literal["completed", "include_current"] = Field(
        "completed", description="'completed' = most recent fully-ended FYs (default). 'include_current' = current partial FY + prior."
    )


@tool(
    "fiscal_year_window",
    """Compute which FDA fiscal years (Oct 1–Sep 30) a phrase like 'the last two fiscal years' refers to,
    relative to an as-of date. Returns the FY list and their date bounds under the chosen mode, and the
    alternate mode's answer so the difference can be disclosed. Use before any fiscal-year filter.""",
    decision_refs=("D2", "D3"),
)
def fiscal_year_window(p: FYWindowIn) -> ToolResult:
    store = get_store()
    as_of = store.resolve_as_of(p.as_of)
    current_fy = fiscal_year(as_of)
    completed_last = current_fy - 1 if as_of < fy_bounds(current_fy)[1] else current_fy

    def window(mode: str) -> list[int]:
        top = current_fy if mode == "include_current" else completed_last
        return list(range(top - p.n_years + 1, top + 1))

    chosen = window(p.mode)
    alt_mode = "include_current" if p.mode == "completed" else "completed"
    alt = window(alt_mode)
    value = {
        "as_of": as_of.isoformat(),
        "current_fy": current_fy,
        "fiscal_years": chosen,
        "bounds": {fy: [fy_bounds(fy)[0].isoformat(), fy_bounds(fy)[1].isoformat()] for fy in chosen},
        "alternate": {"mode": alt_mode, "fiscal_years": alt},
        "same_under_both_modes": chosen == alt,
    }
    return ToolResult(
        tool="fiscal_year_window",
        value=value,
        as_of=as_of,
        interpretations=[
            Interpretation(term="last N fiscal years", chosen=p.mode, alternatives=[alt_mode], decision_ref="D3",
                           note=f"{p.mode} → FY{chosen[0]}–FY{chosen[-1]}; {alt_mode} → FY{alt[0]}–FY{alt[-1]}"),
        ],
    )


def fy_of(d: date | None) -> int | None:
    return fiscal_year(d)
