# Agentic workflow design — why this structure

## The shape

```
question
  │
  ▼
[gate: Haiku] ─── out of scope / unsafe ──▶ Tier 4, say what CAN be answered
  │ answerable / partially
  ▼
[certified-query match]  ──▶ runner executes the verified plan itself ──▶ E1
  │
  ▼
[planner: Sonnet, escalates to Opus on a rule]
   1. declare_interpretations  (every ambiguous term, default + alternates, BEFORE any data)
   2. resolve_entity           (no literal is used unless it exists in the data)
   3. certified tools  ◀──────────────────────────── DuckDB + audit lineage
   4. sql_query (last resort) ──▶ guard ──▶ 2 more candidates (Sonnet, Opus) ──▶ agree / disagree
   5. finish                   (evidence ids, divergences, what cannot be answered)
  │
  ▼
[narrator: Sonnet]  placeholders + [E#]/[SYS] citations; no digits ──▶ [render] ──▶ withhold on any failure
  │
  ▼
[verifier: Opus]  atomic claims × evidence × source table ──▶ flagged? ──▶ one revision ──▶ re-verify
  │
  ▼
[tier]  1 Certified · 2 Derived · 3 Qualified · 4 Not answerable   (deterministic rules)
  │
  ▼
answer + evidence + trace  ──▶ persisted ──▶ briefing / certify / replay / evals
```

## Workflow where it can be a workflow, agent only where it must be

Anthropic's guidance is to use the simplest pattern that passes evaluation. Most of this system is a fixed
workflow: gate → plan → narrate → render → verify → tier is the same every time, auditable, and testable.
The only genuinely agentic span is the planner's tool loop (step 3–5), where the number and order of tool
calls depend on the question. That is the one place where "the model decides" buys something — the ability
to answer questions nobody wrote a handler for — and it is boxed on both sides by deterministic code.

## Role-based model routing, rule-based escalation

| Role | Model | Why |
|---|---|---|
| Gate, entity confirmation | Haiku 5.5 | Classification; cheap; easy to eval |
| Planner | Sonnet 5.5 → **Opus 5.5** when ≥2 interpretations diverge, or SQL is required, or the gate says in-scope-not-in-data | The trigger is a rule visible in the trace ("escalated: 2 interpretations diverged"), not another model's opinion of difficulty |
| Narrator | Sonnet 5.5 | Prose around placeholders; numbers cannot leak |
| Verifier | **Opus 5.5** always | The Senate-letter line of defense; never economized |
| SQL candidates | Sonnet ×2 + Opus ×1 | Model diversity makes agreement meaningful |
| Eval judges | Sonnet 5.5, one call per dimension | Separate judges give uncorrelated scores |

Measured: 11% of regression runs and 42% of capability runs escalated the planner. Cost per question
$0.20–0.29 at list prices, of which the Opus verifier is roughly 40%.

## Where the LLM is deliberately NOT used

Arithmetic, joins, dedup (latest revision per `shortage_id`), fiscal-year assignment, FEI format checks,
status semantics, coverage math, and the trust-tier decision. All of it is Python, unit-tested
(`backend/tests`, 50 tests), and the same code the evals run. The model does intent, interpretation
enumeration, SQL authoring (validated), narration, and verification — the parts that need language.

## Certified queries and the promotion loop

The three required queries ship as certified queries — not hardcoded answers, but verified *plans*
(tool + args + pinned readings + who verified + when + version). When a new question matches one, the
runner executes the plan before the planner starts, so certified evidence is always present and the planner
cannot wander. A reviewer can promote any clean Tier 2/3 answer to certified from the UI and revoke it later;
every action lands in an audit log. This is the mechanism by which the uncertified surface shrinks over time —
the same pattern as Snowflake's verified-query repository and Databricks' trusted assets.

## Interpretation pins

A question with a reading that changes the answer is *Qualified*, shown side by side, with one-click pins.
Pinning re-runs the question with the term resolved and the answer becomes Certified. The ambiguity is
not a defect to hide; it is a decision that belongs to a person, and the interface makes it a one-click
decision with a paper trail.

## Multi-candidate SQL

When no certified tool can express a question, the planner writes SQL. Two more models independently write
SQL for the same stated purpose; all three run through the same guard (single SELECT, known tables and
columns, no clock or random functions, row citations required). Results are compared on their common
columns: *agree* raises confidence, *disagree* is surfaced as a HIGH warning ("this value is contested"),
*incomparable* is labeled. Tier 2 either way.

## The trace is the audit log

Every step records model, tokens, latency, cost, status, input and output. It streams to the UI as it
happens and is persisted with the answer for replay. The "Runs" page is built from it; so is the
certification backlog.

## What I would change with another week

1. Move the narrator to a constrained-decoding grammar so placeholders are the only way to emit values,
   removing the retry loop.
2. Replace lexical certified-query matching with a small embedding index and a confirmation step.
3. Add a `dosage_form` join by scraping the presentation string into normalized form/strength fields,
   with its own audit rule.
4. Run the verifier as a critic *during* narration (token-level) rather than after, cutting latency.
5. Promote the data audit to a scheduled job against the live FDA sources, with diffs between snapshots.
