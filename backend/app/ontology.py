"""Load ontology.yaml once; expose typed accessors the tools and planner share."""
from __future__ import annotations

from functools import lru_cache
from typing import Any

import yaml

from .config import ONTOLOGY_PATH


@lru_cache(maxsize=1)
def load() -> dict[str, Any]:
    with open(ONTOLOGY_PATH) as f:
        return yaml.safe_load(f)


def defaults() -> dict[str, Any]:
    return load()["defaults"]


def definition(name: str) -> dict[str, Any]:
    return load()["definitions"][name]


def synonyms(kind: str) -> dict[str, str]:
    return {k.lower(): v for k, v in load()["synonyms"].get(kind, {}).items()}


def status_semantics() -> dict[str, Any]:
    return load()["status_semantics"]


def ambiguous_terms() -> dict[str, Any]:
    return load()["ambiguous_terms"]


def pediatric_antibiotics() -> dict[str, Any]:
    return load()["pediatric_antibiotics"]


def planner_view() -> str:
    """Compact text rendering of the ontology for the planner's system prompt.
    Deliberately excludes raw table names where a definition exists."""
    o = load()
    out = [f"# Domain: {o['domain']}", o["data_snapshot_note"].strip(), ""]
    out.append("## Entities")
    for name, e in o["entities"].items():
        out.append(f"### {name} — {e['description']}")
        out.append(f"grain: {e['grain']}")
        for c, meta in e["columns"].items():
            desc = meta.get("desc", "")
            vals = f" values={meta['values']}" if "values" in meta else ""
            out.append(f"- {c} ({meta['type']}){vals}: {desc}")
        for m in e.get("missing_fields", []):
            out.append(f"- MISSING FIELD: {m}")
        out.append("")
    out.append("## Relationships")
    for r in o["relationships"]:
        out.append(f"- {r['name']}: {r['from']} → {r['to']} ({r['cardinality']}). coverage: {r.get('coverage','')}")
        for d in r.get("known_defects", []):
            out.append(f"  - DEFECT: {d}")
    out.append("")
    out.append("## Status semantics (never collapse)")
    for k, v in o["status_semantics"].items():
        out.append(f"- {k} = FDA '{v['fda_label']}': {v['meaning']}")
    out.append("")
    out.append("## Ambiguous terms — enumerate interpretations BEFORE answering")
    for term, meta in o["ambiguous_terms"].items():
        interp = meta.get("interpretations", [])
        note = f" NOTE: {meta['note']}" if meta.get("note") else ""
        out.append(f"- \"{term}\" → {meta['definition']} interpretations={interp}{note}")
    out.append("")
    out.append("## Defaults (DECISIONS.md)")
    for k, v in o["defaults"].items():
        out.append(f"- {k}: {v}")
    return "\n".join(out)
