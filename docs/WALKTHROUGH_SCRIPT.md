# Walkthrough script — 8 minutes, then questions

Timing is tight on purpose. Say less; let the product and the numbers talk. Every claim below is on screen
or in the repo.

## 0:00 — The incident, replayed (90 s)

Open the Ask page. Type: **"Is the amoxicillin shortage resolved?"**

While it runs (trace streams on the right): "This is the question that produced the correction letter. The
old tool said yes. Watch what happens."

Answer lands: **No — latest status Current, not Resolved**, the earlier Resolved record disclosed. It may land Tier 1 or Tier 3 — Tier 3 when the planner shows the Resolved-vs-Discontinued reading side by side (the answer is the same under both; the strict rule labels it anyway). If it is Tier 3, say so: "this is the strict rule Neil chose — same answer under both readings, but it says so rather than deciding for you."
Click `[E2]` → the evidence → click `drug_shortages#L3` → the actual Resolved row, then `#L2`, the Current
row. "Two rows, same record, different status, 56 days apart. The system picked the latest revision — and
told you it did."

One line on the trap being real: "That conflict is in the file you sent. So are fourteen others."

## 1:30 — What I built, in one sentence (30 s)

"Last year's tool failed because semantic decisions happened at runtime, inside a model, invisibly. This one
moves them to modeling time in an ontology you can read, makes numbers structurally unable to pass through
the model, labels every claim with a trust tier, and ships with the eval suite that proves it."

## 2:00 — Architecture (90 s) — one diagram, `docs/AGENTIC_DESIGN.md`

Walk the pipeline left to right, pointing at the trace from the run still on screen:

- Gate (Haiku) — answerable or not, before any data.
- Planner (Sonnet; escalates to Opus on a *rule*, shown in the trace) — declares every ambiguous term
  first, resolves literals, calls certified tools; SQL only as last resort, and then three models write it.
- Narrator — placeholders only. "It physically cannot write a number."
- Verifier (Opus, always) — claim by claim, against the evidence *and the right source table*.
- Tier — deterministic.

"Where the model is **not** used: arithmetic, joins, dedup, fiscal years, FEI checks, the tier decision.
All Python, 50 tests."

## 3:30 — Ambiguity is a decision, not a defect (60 s)

Run required query 1 (click the suggestion). It comes back Tier 1 because it matches a certified query.
Open **Interpretations**: strict vs broad (6 vs 15 drugs), FY24–25 vs FY25–26 (4 vs 2 sites), both computed.
"Ask the same thing in different words and it's Tier 3 — Qualified — with pin chips. Pin a reading, it
re-runs, Tier 1. The person decides; the system remembers."

## 4:30 — The loop that makes it a product (60 s)

Ask an off-script question: **"Which sponsors hold the most tentative approvals, and for which ingredients?"**
→ Tier 2 Derived; show the three SQL candidates agreeing in the evidence. Click **Certify this answer**,
name it, "verified by: staff pharmacist." Open **Certified queries** — it's there, with version and audit log.
"Next time anyone asks, the runner executes the verified plan first and it's Tier 1. That's how the
uncertified surface shrinks."

## 5:30 — The memo (45 s)

Open **Briefing**. Four items, each Tier 1 and signed → Senate-ready. Download the `.docx`; show one page:
headline, interpretation pinned, caveats, footnoted row citations. "This is what goes in the binder."

## 6:15 — Evidence it works (60 s)

Open **Evals**. Point at four numbers: hallucinated-number rate 0.0%; 395 claims / 1 flagged; verifier
caught something on 17–33% of first drafts; all ten adversarial cases pass. "Capability started at 42%.
The harness found the bugs; the build log has them."

## 7:15 — Where it still fails (45 s) — say it before they ask

1. Correct number, wrong frame — the verifier usually catches it; when it doesn't, a certified answer is
   wrong. That's why sign-off exists.
2. 77% of current shortages can't be linked to a site in this data. The system says so every time; it
   can't fix the registry.
3. 60–90 seconds a question. Right for briefing prep, wrong for a live hearing.

## 8:00 — What's next

30/60/90 in `PRODUCT_THINKING.md`: shadow mode → internal briefings on real sources → first external memo,
on Bedrock in GovCloud. Week one is sixteen questions for ODSS that each change one line in the ontology.

---

## Likely questions and the honest answers

- **"Isn't this just RAG?"** No retrieval over documents at all. Every answer is a structured query over
  governed tables through typed tools; the ontology is the context, not embeddings. Databricks' own
  benchmark is the argument: same model, 50% → 84.5% with an ontology.
- **"Why Opus for the verifier if it costs 40% of the run?"** Because the failure it prevents cost a
  correction letter. The asymmetry decides it.
- **"Why not a complexity classifier for routing?"** A classifier is one more model opinion. A rule is a
  fact in the trace: "escalated because two interpretations diverged."
- **"What did Claude get wrong while you built this?"** Three concrete things, in `BUILD_LOG.md`: the first
  entity resolver fuzzy-matched a nonsense drug to Azithromycin (a test caught it); the narrator wrote
  "never inspected" for "no inspection record" (the verifier caught it); the narrator claimed a mislink
  didn't affect counts it did affect (the verifier caught it).
- **"How would this scale?"** The agent doesn't need to; the data layer does. DuckDB → the agency's
  warehouse; ontology → its metric layer; same tools, same evals.
- **"What would you cut?"** Nothing in the trust path. I'd cut the React UI to a CLI before I'd cut the verifier.
