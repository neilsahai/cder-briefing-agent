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

### Nov 7 — Phase 2 first live runs (Claude Code, Anthropic API)
- Q1/Q2/Q3 run end to end through gate → planner → narrator → verifier. Q3 landed Tier 1 Certified
  on its first clean run with 0 flagged claims. The planner escalated itself to Opus on Q1 because two
  interpretations diverged (a deterministic rule, visible in the trace) and ran the certified query
  under four interpretation combinations unprompted.
- API realities discovered live: this SDK generation has no `temperature`; Sonnet/Opus 5.5 reject
  forced `tool_choice` while Haiku accepts it (added a structured-output helper that falls back to
  auto + validation + one retry); Haiku invented a gate category outside the enum
  (`partially_answerable`) — now validated and coerced with the raw value kept in the trace.

## Where Claude was wrong and something caught it (continued)
4. **Verifier catch #1 (Q1):** narrator wrote "FEI 3007891234 has *never been inspected*". Evidence only
   supports "has *no inspection record in this dataset*". Opus verifier flagged it as unsupported
   overstatement. This is exactly the Senate-grade distinction the brief describes.
5. **Verifier catch #2 (Q2):** narrator added "the mislink does not change the amoxicillin counts above" —
   but ANDA078201 (the mislinked application) IS one of the 4 approved / 3 marketed. Verifier flagged it
   as an unsupported scope-limiting claim that played down a high-severity warning. Added a one-pass
   revision loop (evaluator-optimizer): narrator rewrites flagged claims, verifier re-checks. On re-run
   Q2 went flagged → revised → pass.
6. **Renderer caught the renderer.** Narration kept failing on `status_timelines["DS-2023-0142"]` — the
   model was right to use a bracketed key; my placeholder grammar didn't support it. Fixed the grammar.
   Then the pure "no digits" rule rejected `DS-2023-0142` and `18 months` that the narrator had correctly
   copied from warning text. Replaced with a verified-literal rule: a digit-bearing token is allowed
   only if it appears as a whole token somewhere in the evidence (values, warnings, interpretations,
   row ids). Same guarantee — no number that is not in evidence can reach the reader — fewer false
   rejections. One of the new tests then rejected `DS-2023-0200` in a Q1 answer, which exposed that
   the Q1 certified query wasn't returning the shortage records themselves; fixed the data, kept the
   renderer strict.

## Things Neil overruled or redirected
- (to be filled as they happen)
