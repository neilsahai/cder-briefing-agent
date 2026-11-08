# BUILD_LOG.md — how this was built, with Claude

The assignment says how AI tooling is used is part of what is evaluated. This is the honest record.
Design conversations happened in Claude (claude.ai); implementation ran in the same session's
Claude Code harness against this repo. Neil made the decisions recorded in DECISIONS.md and
reviewed every phase; Claude wrote most of the code and all first drafts.

## Timeline

### Nov 7 — Discovery and design (Claude chat)
- Read the recruiter email and the PDF; profiled the three CSVs with pandas before writing any
  design. Found 13 planted data traps (see DECISIONS.md and `ontology.yaml:data_quality_rules`).
  The amoxicillin status conflict from the backstory is literally in the data (`DS-2023-0142`).
- Reviewed the May 2026 Meridian take-home that did not advance. Post-mortem: one LLM call doing
  formatting, six hardcoded handlers, zero evals, trust asserted not enforced. Decided the new
  build must be a product with evidence, not an artifact with a story.
- Researched how Snowflake Cortex Analyst (verified query repository), Databricks Genie
  (trusted assets, ontology → 50%→84.5%), Uber QueryGPT (intent agent), Palantir (ontology),
  and Anthropic's agent/eval guidance approach the same problem. Adopted: trust tiers, a
  promotion loop, an explicit ontology, multi-candidate SQL, placeholder narration, claim-level
  verification with source attribution, capability vs regression evals.
- Decisions Neil made: React + FastAPI over Streamlit; model routing by role (Opus on the
  verifier, rule-based planner escalation) rather than a "complexity" classifier; build the
  promotion loop for real; Bedrock as a one-flag deploy option, no Databricks; no fabricated ROI.

### Nov 7 — Phase 0/1 (Claude Code)
- Wrote DECISIONS.md and ontology.yaml first, before any code, so tools and tests share one
  source of truth for every interpretive choice.
- Data layer: DuckDB with CSV line numbers on every row so any fact cites `table#Lnn`.
- Audit: 13 detectors + a lineage index. Warnings attach to answers automatically when evidence
  touches a flagged row — the status-conflict warning reaches the amoxicillin answer without
  anyone asking for it.
- 9 certified tools + 3 certified queries; 35 tests pin golden answers under default AND
  alternate interpretations (e.g. as-of "early 2025" per the PDF wording → FY23–24 → only
  Pfizer McPherson and ICU Medical have OAIs; as-of 2023-12-01 → amoxicillin correctly reports
  *Resolved* for that date while still carrying the conflict warning).

## Where Claude was wrong and something caught it
1. **Fuzzy entity resolution invented a drug.** First version of `resolve_entity` returned the
   closest fuzzy match as a *resolution*. Test `test_resolve_unknown_does_not_invent` fed it
   "Xyzzyomycin" and it resolved to **Azithromycin**. That is precisely the invented-literal
   failure the brief warns about. Fix: fuzzy hits are candidates only (`resolved=[]`,
   HIGH warning, "confirm with user"). The test that caught it stays as a regression eval.
2. **`itertuples` silently renamed `_line`.** pandas renames underscore-prefixed columns to
   positional names in `itertuples()`, so `r._line` raised. Caught on first run of Q1; renamed
   to `line_no` everywhere. Lesson recorded because it is the kind of silent rename that could
   have produced wrong row citations if it had failed quietly instead of loudly.
3. **Per-row warnings flooded merged results.** Q3 produced five separate "stale" lines. Added
   `warnings_util.consolidate` so repeated codes collapse to one line with the union of rows —
   nothing is dropped, it is grouped.

## Things Neil overruled or redirected
- (to be filled as they happen)
