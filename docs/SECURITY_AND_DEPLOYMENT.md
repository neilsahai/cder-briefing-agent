# Security posture and deployment path

## What the system can and cannot touch

- **Read-only data.** The three CSVs load into an in-memory DuckDB. No tool writes to them. The only writable
  stores are the certified-query registry (SQLite) and run/briefing JSON, both local to the backend.
- **SQL guard.** LLM-authored SQL is parsed (sqlglot) and must be a single `SELECT`/CTE over an allowlist of
  tables and views, with known columns only. Rejected: DDL/DML, multiple statements, file/extension functions,
  and clock/random functions (`now()`, `current_date`, `random()`) — the as-of date must come from the ontology.
  Execution uses a per-call DuckDB cursor; results are capped at 500 rows.
- **Cell values are data, never instructions.** Tool outputs (which originate in CSV cells) are handed to the
  narrator as JSON inside a clearly delimited evidence block. The gate rejects questions that ask the system to
  ignore its rules (eval `adv_prompt_injection` → Tier 4). Residual risk is phrasing steering via hostile cells;
  the renderer and verifier bound what that can achieve. Production ingestion would add provenance controls.
- **No PII.** The dataset is synthetic. The prompts send no user identity to the model. Logs contain the
  question, tool calls, and model outputs — treat as internal.
- **Secrets.** `ANTHROPIC_API_KEY` is read from the environment / `.env` (gitignored). The frontend never sees it.
- **Dependencies** are pinned by floor in `requirements.txt` and `package-lock.json`; CI runs the deterministic
  test suite on every push.
- **No outbound calls** except to the model provider. No web retrieval, no document RAG.

## Deployment paths

### Local (what the panel can run in two minutes)
```
cp .env.example .env            # add ANTHROPIC_API_KEY
pip install -r backend/requirements.txt
cd frontend && npm install && npm run build && cd ..
cd backend && uvicorn app.api:app --port 8787
# open http://localhost:8787
```

### Hosted demo
Backend on Render (Docker, `render.yaml`), frontend built into the backend's static mount — one service,
one URL. Secrets as Render environment variables.

### Federal path — Claude on Amazon Bedrock
The model client is behind a one-flag provider interface (`PROVIDER=bedrock`, `backend/app/llm/provider.py`).
Same code, same prompts, same evals; the client becomes `AnthropicBedrock` with the agency's IAM role and
region. For FDA that means Claude in **AWS GovCloud** inside the agency's FedRAMP High boundary: prompts,
evidence, and answers never leave the account; CloudTrail logs every invocation; the existing DuckDB layer is
replaced by the agency's governed warehouse and the ontology becomes its metric layer. No Databricks or
Kubernetes is required for this product at this scale; at FDA volume the data layer, not the agent, is what
scales.

### What is deliberately not here
Authentication/SSO, multi-tenant isolation, and role-based access are not in the prototype. They are the
first items in the "before a real hearing" list in `PRODUCT_THINKING.md`.
