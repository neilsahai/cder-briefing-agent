"""MCP server exposing the certified tools (and the certified queries) to any MCP client — Claude Desktop,
Claude Code, or another agent. The same contracts, the same row citations, the same warnings.

Run:  python -m app.mcp_server            (stdio)
Claude Desktop config:
  {"mcpServers": {"cder-shortages": {"command": "python", "args": ["-m", "app.mcp_server"], "cwd": "<repo>/backend"}}}
"""
from __future__ import annotations

import json
from typing import Any

from mcp.server.mcpserver import MCPServer

from .tools import REGISTRY, call_tool
from .data.audit import get_audit

mcp = MCPServer("cder-shortages", instructions=(
    "Certified tools over an FDA CDER drug-shortage snapshot (drug_shortages, applications, inspections). "
    "Every result carries row citations (table#Lnn), the interpretation applied for ambiguous terms (DECISIONS.md refs), "
    "and data-quality warnings. Never state a number that is not in a result. Resolved and Discontinued are different statuses."))


def _serialize(res) -> str:
    return json.dumps({
        "tool": res.tool, "value": res.value, "rows": [r.id for r in res.rows], "source_tables": res.source_tables,
        "interpretations": [i.model_dump() for i in res.interpretations],
        "warnings": [{"code": w.code, "severity": w.severity.value, "message": w.message} for w in res.warnings],
        "coverage": res.coverage, "as_of": res.as_of.isoformat() if res.as_of else None,
    }, default=str)


def _make(name: str):
    t = REGISTRY[name]
    model = t.input_model

    def handler(params: model) -> str:  # type: ignore[valid-type]
        return _serialize(call_tool(name, params.model_dump(exclude_none=True)))

    handler.__name__ = name
    handler.__doc__ = t.description + ("\n\n[CERTIFIED]" if t.certified else "\n\n[NOT certified — LLM-authored SQL path]") + f"\nDecision refs: {', '.join(t.decision_refs)}"
    handler.__annotations__ = {"params": model, "return": str}
    return handler


for _name in REGISTRY:
    mcp.tool(name=_name)(_make(_name))


@mcp.tool()
def data_health_summary() -> str:
    """Summary of the data-quality audit (rule ids, severities, affected row counts)."""
    return json.dumps(get_audit().summary(), default=str)


@mcp.resource("cder://ontology")
def ontology_resource() -> str:
    """The ontology (entities, definitions, ambiguous terms, synonyms, defaults)."""
    from .config import ONTOLOGY_PATH
    return ONTOLOGY_PATH.read_text()


@mcp.resource("cder://decisions")
def decisions_resource() -> str:
    """DECISIONS.md — the rationale for every interpretive default."""
    from .config import REPO_ROOT
    return (REPO_ROOT / "DECISIONS.md").read_text()


if __name__ == "__main__":
    mcp.run()
