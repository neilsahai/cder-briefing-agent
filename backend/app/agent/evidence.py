"""Evidence registry + placeholder rendering.

The narrator never writes a number, date, identifier, or status value. It writes
    "{{E2.counts.distinct_drugs}} drugs are currently in shortage for quality reasons [E2]."
and `render()` substitutes from tool outputs. Any digit outside a placeholder is rejected.
Any placeholder that fails to resolve blocks the answer. [DECISIONS D12]
"""
from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field

from ..models import ToolResult

PLACEHOLDER = re.compile(r"\{\{\s*(E\d+)((?:\.[A-Za-z_][A-Za-z0-9_]*|\[\d+\])*)\s*(?:\|\s*(\w+))?\s*\}\}")
CITATION = re.compile(r"\[(E\d+(?:\s*,\s*E\d+)*)\]")
DIGIT = re.compile(r"\d")

# Words the narrator may use that contain digits in normal English (none). Fiscal years must be placeholders.
MAX_RECORDS_SHOWN = 30


class Evidence(BaseModel):
    id: str
    tool: str
    args: dict[str, Any]
    result: ToolResult
    certified: bool = True

    def compact_value(self) -> Any:
        """Value as shown to the narrator/verifier; long record lists are truncated with a count."""
        return _truncate(self.result.value)


def _truncate(v: Any, depth: int = 0) -> Any:
    if isinstance(v, list):
        if len(v) > MAX_RECORDS_SHOWN:
            return [_truncate(x, depth + 1) for x in v[:MAX_RECORDS_SHOWN]] + [f"... {len(v) - MAX_RECORDS_SHOWN} more items (total {len(v)})"]
        return [_truncate(x, depth + 1) for x in v]
    if isinstance(v, dict):
        return {k: _truncate(x, depth + 1) for k, x in v.items()}
    return v


class EvidenceRegistry(BaseModel):
    items: list[Evidence] = Field(default_factory=list)

    def add(self, tool: str, args: dict[str, Any], result: ToolResult, certified: bool = True) -> Evidence:
        e = Evidence(id=f"E{len(self.items) + 1}", tool=tool, args=args, result=result, certified=certified)
        self.items.append(e)
        return e

    def get(self, eid: str) -> Evidence | None:
        return next((e for e in self.items if e.id == eid), None)

    def for_prompt(self) -> str:
        parts = []
        for e in self.items:
            parts.append(f"### {e.id} — tool `{e.tool}` args={json.dumps(e.args, default=str)}")
            parts.append(f"source_tables: {e.result.source_tables}; rows cited: {len(e.result.rows)}; certified_tool: {e.certified}")
            if e.result.interpretations:
                parts.append("interpretations: " + "; ".join(f"{i.term} → {i.chosen} (alt: {i.alternatives}) [{i.decision_ref}]" for i in e.result.interpretations))
            if e.result.warnings:
                parts.append("warnings: " + " | ".join(f"[{w.severity.value}] {w.code}: {w.message}" for w in e.result.warnings))
            parts.append("value:\n```json\n" + json.dumps(e.compact_value(), indent=1, default=str) + "\n```")
        return "\n".join(parts)

    def all_rows(self) -> list:
        seen, out = set(), []
        for e in self.items:
            for r in e.result.rows:
                if r.id not in seen:
                    seen.add(r.id); out.append(r)
        return out

    def all_warnings(self):
        from ..tools.warnings_util import consolidate
        return consolidate([w for e in self.items for w in e.result.warnings])

    def all_interpretations(self):
        seen, out = set(), []
        for e in self.items:
            for i in e.result.interpretations:
                k = (i.term, i.chosen)
                if k not in seen:
                    seen.add(k); out.append(i)
        return out


# ----------------------------------------------------------------------------- rendering
class RenderError(Exception):
    pass


def _resolve_path(root: Any, path: str) -> Any:
    cur = root
    for tok in re.findall(r"\.([A-Za-z_][A-Za-z0-9_]*)|\[(\d+)\]", path):
        key, idx = tok
        if key:
            if isinstance(cur, dict) and key in cur:
                cur = cur[key]
            else:
                raise RenderError(f"key '{key}' not found")
        else:
            if isinstance(cur, list) and int(idx) < len(cur):
                cur = cur[int(idx)]
            else:
                raise RenderError(f"index [{idx}] out of range")
    return cur


def _format(v: Any, fmt: str | None) -> str:
    if fmt == "count" or fmt == "len":
        return str(len(v)) if isinstance(v, (list, dict)) else str(v)
    if isinstance(v, list):
        items = [str(x) if not isinstance(x, dict) else json.dumps(x, default=str) for x in v]
        if fmt == "and":
            return ", ".join(items[:-1]) + (" and " if len(items) > 1 else "") + items[-1] if items else "none"
        return ", ".join(items) if items else "none"
    if isinstance(v, dict):
        return json.dumps(v, default=str)
    if isinstance(v, bool):
        return "yes" if v else "no"
    return str(v)


def render(template: str, registry: EvidenceRegistry) -> tuple[str, list[dict[str, Any]]]:
    """Substitute placeholders. Returns (rendered_text, substitutions). Raises RenderError on any failure
    or on any digit appearing outside a placeholder."""
    # 1. digits outside placeholders are forbidden
    stripped = PLACEHOLDER.sub("", template)
    stripped = CITATION.sub("", stripped)
    if DIGIT.search(stripped):
        bad = DIGIT.search(stripped)
        ctx = stripped[max(0, bad.start() - 30): bad.end() + 30]
        raise RenderError(f"narration contains a literal digit outside a placeholder near: '...{ctx}...'")

    subs: list[dict[str, Any]] = []

    def repl(m: re.Match) -> str:
        eid, path, fmt = m.group(1), m.group(2) or "", m.group(3)
        e = registry.get(eid)
        if e is None:
            raise RenderError(f"placeholder references unknown evidence {eid}")
        try:
            v = _resolve_path(e.result.value, path)
        except RenderError as ex:
            raise RenderError(f"{eid}{path}: {ex}") from ex
        s = _format(v, fmt)
        subs.append({"placeholder": m.group(0), "evidence": eid, "path": path, "value": v, "rendered": s})
        return s

    out = PLACEHOLDER.sub(repl, template)
    return out, subs


def citations_in(text: str) -> list[str]:
    ids: list[str] = []
    for m in CITATION.finditer(text):
        for x in m.group(1).split(","):
            x = x.strip()
            if x not in ids:
                ids.append(x)
    return ids
