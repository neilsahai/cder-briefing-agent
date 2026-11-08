"""Core evidence models. Every tool output is a ToolResult; every fact traces to RowRefs."""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Severity(str, Enum):
    info = "info"
    low = "low"
    medium = "medium"
    high = "high"


class RowRef(BaseModel):
    """A citation to one physical row in one source file."""

    table: Literal["drug_shortages", "applications", "inspections"]
    line: int = Field(description="1-based line number in the CSV (header = line 1).")
    key: str = Field(description="Human-readable natural key, e.g. 'DS-2023-0142@2024-01-10'.")

    @property
    def id(self) -> str:
        return f"{self.table}#L{self.line}"

    def __hash__(self) -> int:
        return hash((self.table, self.line))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, RowRef) and (self.table, self.line) == (other.table, other.line)


class Warning(BaseModel):
    """A data-quality or interpretation warning attached to an answer."""

    code: str = Field(description="DQxx rule id or INTERP/COVERAGE/etc.")
    severity: Severity
    message: str
    rows: list[RowRef] = Field(default_factory=list)


class Interpretation(BaseModel):
    """Which reading of an ambiguous term was applied, and what else was possible."""

    term: str
    chosen: str
    alternatives: list[str] = Field(default_factory=list)
    decision_ref: str = Field(description="DECISIONS.md section, e.g. 'D5'.")
    note: str | None = None
    alternate_result: Any | None = Field(default=None, description="Headline value under the alternate reading, when computed.")
    differs: bool | None = Field(default=None, description="True if the alternate reading changes the headline answer.")


class ToolResult(BaseModel):
    """The atomic unit of evidence. Numbers in `value` are the ONLY numbers allowed in narration."""

    tool: str
    value: Any
    rows: list[RowRef] = Field(default_factory=list)
    source_tables: list[str] = Field(default_factory=list)
    interpretations: list[Interpretation] = Field(default_factory=list)
    warnings: list[Warning] = Field(default_factory=list)
    as_of: date | None = None
    coverage: str | None = Field(default=None, description="e.g. 'sites known for 13 of 57 current records'")

    def row_ids(self) -> list[str]:
        return [r.id for r in self.rows]


class AuditFinding(BaseModel):
    rule_id: str
    severity: Severity
    message: str
    rows: list[RowRef]
    details: dict[str, Any] = Field(default_factory=dict)
