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

### Nov 7–8 — Phase 3 (registry, pins, multi-candidate SQL, eval harness)
- Built the eval harness first as a tool for finding bugs, then as a scorecard. First regression run: 56%.
  First capability run: 42%. Both numbers were useful precisely because they were low.
- Fixes the harness forced, in order: (1) certified matching matched "since FY2024" to the FY2021
  certified query on word overlap — now numeric tokens must agree and certified credit requires the
  certified args to have actually been used; (2) the planner sometimes ignored the certified-plan hint
  and composed primitives — the runner now executes the certified plan itself before planning;
  (3) the trust tier depended on whether the planner *chose* to compute an alternate reading — certified
  queries now compute alternates deterministically and report `differs`; (4) the narrator made true
  methodological claims ("FY basis matches FDA's Data Dashboard", "this tool is certified") that no
  evidence item contained — the ontology/DECISIONS context is now a citable `SYS` evidence item;
  (5) the narrator guessed key names (`foreign_sites_not_inspected` vs `..._since`) and the renderer
  withheld the whole answer — the narrator now receives an explicit index of every valid placeholder
  path; (6) DuckDB and SQLite connections were not thread-safe under the eval runner's concurrency.
- Capability suite after fixes: 42% → 75% → 96%. Hallucinated-number rate: 0.0% on every run after
  the renderer/grader token rule was aligned. All 10 adversarial cases (fake FEI, fake drug, fake
  fiscal year, root cause, patient impact, blame, testimony language, prompt injection, out-of-scope,
  never-inspected-foreign) pass.
- Regression at 8/9–9/9 across runs. The recurring miss is the Opus verifier flagging a *framing*
  nit on an otherwise-correct answer, which demotes it to Tier 3 Qualified. That is the intended
  failure direction (caution), and pass^k exists to make that variance visible rather than hide it.
- Judge robustness: Sonnet occasionally emitted malformed tool JSON as a grader; added a retry.

### Nov 8 — Phase 4 (product surface)
- FastAPI with SSE streaming so the UI shows each pipeline step as it happens (gate → plan →
  tool calls → narrate → verify) rather than a spinner; `/api/ask_sync` kept for scripts and tests.
- React/Vite front end: Ask page with as-of date and interpretation pins, answer card with tabs
  (Answer / Evidence / Verifier / Interpretations / Caveats), citation chips that open the exact
  evidence item and row (`table#Lnn`), one-click "pin this reading → re-run", Add to briefing,
  Certify. Pages for Briefing (sign-off + readiness + export), Certified queries (promote / revoke /
  audit log), Data health (DQ01–13 with affected rows), Evals (latest scorecard), Runs.
- Briefing builder: pin runs, staff sign-off, readiness check (Tier 1 + signed), export .md/.docx.
- MCP server exposing the certified tools and `cder://ontology`, `cder://decisions` resources, so
  the same tools can be called from Claude Desktop/Code without the UI.
- Playwright screenshots against the built SPA confirmed the SSE flow and citation→row linking.
- Small catches: duplicate pin chips when two interpretations shared a term (dedupe by term);
  `mcp` 2.x dropped `mcp.server.fastmcp` (moved to `MCPServer` with pydantic params).

### Nov 8 — Phase 5 (deliverables)
- Docs under `docs/`: red-team report with computed naive-vs-system baselines, trust & hallucination
  design, agentic design, product thinking (cost of being wrong, 30/60/90, reusability — no
  invented ROI), week-one discovery questions, security & deployment, architecture, walkthrough
  script with likely panel questions. README carries the measured scorecard table.
- Exported briefing memo (`deliverables/briefing_memo.{md,docx}`): 4/4 items Senate-ready, demo sign-off.
- 11-slide walkthrough deck built from a pptxgenjs script (`deliverables/deck/build_deck.js`), native
  charts for the two ambiguity comparisons and the capability-pass-rate curve, speaker notes on every
  slide, schema-validated and visually QA'd from a LibreOffice render.
- Pricing in `backend/app/llm/pricing.json` taken from Anthropic's pricing page on 2026-11-07, not
  from memory.

### Nov 8 — Phase 6 (rehearsal: 20 off-script questions a panel might ask)
Wrote `evals/cases/rehearsal.yaml` — questions I had not tuned for (longest-open shortage, sites in
India, "is Pfizer responsible", share of injectables, status flips, average days to revision, "tell me
about heparin", "what would you fix before the Senate"). First pass 17/20. Each miss was a real defect:
1. **Integer dict keys crashed the placeholder index.** A grouped SQL result keyed by year (`{2024: 3}`)
   hit `re.fullmatch` with an int. Two questions died with a TypeError instead of an answer. Fixed in
   `path_index` and `_resolve_path`; unit test added.
2. **A forecast question earned Tier 1.** "When will the amoxicillin shortage end?" — the answer was
   right (refuses to predict, gives certified status) but carried a *Certified* label because every fact
   it did state was certified. Added a deterministic cap: when the gate finds the primary ask is not in
   the data, the tier is at most 3 Qualified. Documented under D13.
3. **Renderer and grader disagreed on `ANDA065440-style`.** `token_allowed` stripped prefix and suffix
   together, yielding `065440`, which is not a whole token in evidence. Now tries suffix-only first.
   This was the first non-zero hallucinated-number reading; it was a tokenizer bug, not a hallucination,
   and the grader is what found it.
4. **Narrator ran out of output tokens on a long answer** (FY2024 variant of Q3) and every retry hit the
   same wall because the retry message only talked about digits. Budget raised; a `max_tokens` stop now
   produces a "write a shorter answer" retry; the withheld message says why.
5. **Gate false positive on the word "Senate".** Haiku classified "which data quality problems would you
   want fixed before this goes in front of the Senate?" as unsafe_or_policy once in two runs. Gate prompt
   now states that mentioning testimony is not the trigger; asking to *write or assert* an unsupported
   claim is. Re-ran 3/3 stable; all 10 adversarial refusals still hold.
After fixes: regression 9/9 (221 claims, 0 flagged); rehearsal 19–20/20; hallucinated-number rate 0.0%.

### Nov 8 — Phase 6b (3-trial runs; two more design gaps)
- Ran capability and regression at `--trials 3`. The first 3-trial capability run: pass@3 100%, pass^3 79%.
  Failures clustered on one case (`cap_how_many_shortages`, 0/3): the narrator kept saying the
  "Current or Discontinued" alternate "was not computed". Root cause was structural, not prompt: the
  primitive `current_shortages` tool never computed it (only certified queries computed alternates), and
  even after it did, the number lived on the Interpretation object, not in the evidence value — so the
  narrator *could not* write it through a placeholder. Fixed in two places: tools compute the alternate,
  and `call_tool` exposes `alternate_readings` as an addressable path on every result. 3/3 after.
- That fix over-corrected: the new alternate `differs` on every count, demoting required query 3 to
  Tier 3 on all three trials. Added a `demotes` flag: alternates whose default is a *definition* in
  DECISIONS.md (D4 Discontinued ≠ in shortage, D6 record/presentation counts "also reported") are
  disclosed but do not demote; judgment-call readings (D3, D5, D9) still do. Regression back to 9/9.
- Registry: a live SQLite cursor returned from under the lock was invalidated by another thread
  (`IndexError: tuple index out of range`). Rows are now materialized inside the lock; 16-thread stress
  test clean.
- `sql_query` results now carry `as_of`, so "as of 2025-10-23" on a Tier 2 answer is a supported claim.
- Planner once emitted interpretations as bare strings → `AttributeError`; shapes are normalized.
- Final build, 3 trials: regression 25/27 trials (pass@3 100%, pass^3 89%); capability 66/72
  (pass@3 100%, pass^3 79%); rehearsal 20/20; 0 hallucinated numbers in 119 trials. Every failed trial
  is a verifier demotion to Tier 3 or a judge-dimension disagreement — never a wrong number.
- Two full runs were cut short by the API credit balance; aborted result files are kept, renamed
  `*_ABORTED_no_credits.json`, and never used for the scorecard.

## Things Neil overruled or redirected
- **Stricter Tier 3 rule.** Original plan let a certified query with a differing alternate reading
  stay Tier 1 if the default reading was documented. Neil chose the stricter rule: any reading that
  changes the answer demotes to Qualified until a person pins it. The registry and pins exist so
  that demotion is a one-click decision, not a dead end.
- **Role-based model routing, not one model.** Haiku for gate/entity, Sonnet for planning and
  narration, Opus for verification always and for planning only when a deterministic rule escalates.
  Neil's framing: easy tasks on the cheaper model, hard tasks on Opus, and the escalation visible in
  the trace.
- **No Databricks.** Bedrock (AWS GovCloud) as the deployment path; the provider switch is one env var.
- **No fabricated ROI.** Business-value material is a cost-of-being-wrong argument and a before/after
  workflow comparison, not an invented dollar figure.
- **Pricing from the source.** Cost-per-question uses Anthropic's published list prices, fetched, not recalled.
- **Hosting last.** The hosted walkthrough is deliberately the final step, after rehearsal.
