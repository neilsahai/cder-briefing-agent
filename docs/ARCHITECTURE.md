# Architecture (one page)

```mermaid
flowchart TD
    Q[Analyst question] --> G[Gate · Haiku<br/>answerable? ambiguous terms? literals?]
    G -- out of scope / unsafe --> T4[Tier 4 · says what CAN be answered]
    G --> M{Certified-query<br/>match?}
    M -- yes --> X[Runner executes verified plan → E1]
    M -- no --> P
    X --> P[Planner · Sonnet → Opus on rule<br/>1 declare_interpretations<br/>2 resolve_entity<br/>3 certified tools<br/>4 sql_query → guard → 3 candidates<br/>5 finish]
    P --> D[(DuckDB + 13-rule audit<br/>row citations · lineage warnings)]
    D --> P
    P --> N[Narrator · Sonnet<br/>placeholders + citations, no digits]
    N --> R[Render<br/>substitute from evidence; reject anything not in evidence]
    R -- fail --> N
    R --> V[Verifier · Opus<br/>atomic claims × evidence × source table]
    V -- flagged --> N
    V --> T[Trust tier · deterministic<br/>1 Certified · 2 Derived · 3 Qualified · 4 N/A]
    T --> A[Answer + evidence + trace → persisted]
    A --> B[Briefing builder · sign-off · docx/md]
    A --> C[Certify → registry · audit log]
    A --> E[Evals · scorecard]
    O[(ontology.yaml · DECISIONS.md)] -.read by.-> G
    O -.read by.-> P
    O -.SYS evidence.-> N
    O -.SYS evidence.-> V
```

| Layer | Code | Tests |
|---|---|---|
| Data + audit | `backend/app/data/` | `tests/test_store_and_audit.py` |
| Certified tools, certified queries, SQL guard | `backend/app/tools/` | `tests/test_certified_queries.py`, `tests/test_entities_and_specs.py` |
| Agent (gate, planner, narrator, render, verifier, tier, SQL candidates, trace) | `backend/app/agent/` | `tests/test_evidence_render.py` |
| Model routing + provider (Anthropic / Bedrock) | `backend/app/llm/` | — |
| Certified registry, runs, analytics | `backend/app/registry/` | `tests/test_registry.py` |
| API, briefings, MCP | `backend/app/api.py`, `briefings.py`, `mcp_server.py` | `tests/test_api_and_mcp.py` |
| Frontend | `frontend/src/` | built in CI |
| Evals | `evals/` | run against the live model |

Design rationale: `AGENTIC_DESIGN.md`. Trust model: `TRUST_AND_HALLUCINATION.md`. Interpretive defaults: `../DECISIONS.md`.
