# Product thinking — who this is for today, and what has to change before a hearing

## The user, concretely

A policy analyst in ODSS, two days before the Deputy Center Director testifies, with three databases open in
three tabs and an Excel sheet that cross-references them by hand. Not a data scientist. Under deadline. The
question that matters to them is not "what's the answer" — it is "can I put this in the Deputy Director's
binder without a correction letter."

Today's product fits that person: it answers the questions they already ask, in the vocabulary they already
use, and tells them exactly how much weight each answer bears. It is **not** a tool for the Deputy Director
to use live in a hearing (latency, and nobody should be reading un-reviewed output aloud).

## The cost of being wrong vs. the cost of being slow

The brief gives the number that matters: one wrong status word → a formal correction letter to a Senate
committee. That asymmetry drives every design choice that costs latency or money:

- the verifier runs on the strongest model, every time (~40% of per-question cost);
- a question with an ambiguous reading is *Qualified* until a person pins it, even when every number is right;
- an answer the renderer cannot verify is withheld rather than approximated.

Sixty to ninety seconds per question is an acceptable price for an answer that carries its own evidence.
If the product were optimized for speed, it would be optimized for the wrong failure.

## Before / after — measured, not estimated

**Manual process for required query 1** (from the brief: three databases, cross-referenced in Excel):

| Step | Lookups |
|---|---|
| Scan shortage file for Current + quality reason | 1 scan of 150 rows → 6 records |
| Look up each record's application in Drugs@FDA | 6 |
| Look up each application's FEI | 6 |
| Pull inspection history for each FEI and assign fiscal years by hand | 6 scans of an 80-row file; 5 FEIs have records |
| Decide, per site, whether an OAI falls in the window (which FY basis? which window?) | 5 judgment calls, undocumented |
| Check whether any shortage status has conflicting revisions | usually skipped |

≈ 30 cross-file lookups plus 5 undocumented judgment calls. The tool's answer for the same question cites
17–42 source rows (depending on alternates computed) in one traced run of 60–100 s, with every judgment
call named and its alternate shown. The in-app tile "replaced ≈N manual lookups" is computed from the rows
actually cited in that run — it is a count, not a projection.

What is **not** claimed: hours saved per week, FTE equivalents, or a dollar ROI. Those need the client's
actual query volume and are hypotheses to test in the pilot, not numbers to put in a README.

## Cost per claim

At Anthropic list prices (Nov 2026), measured across 33 eval runs: **$0.20–0.29 per question**, ~26 cited
rows per answer, ~$0.011 per cited row. A ten-item briefing memo costs roughly $3 to draft and verify.
At 50 questions a day across the office that is ~$14/day, ~$300/month — stated assumptions: list prices,
no batch discount, current prompt sizes.

## Value tree

```
Mission outcome                      Capability                              Feature
─────────────────────────────────    ──────────────────────────────────────  ──────────────────────────────
Credible congressional engagement ─▶ No unverifiable number reaches text ──▶ placeholder renderer, verifier
                                  ─▶ Every claim traceable to a row      ──▶ row citations, evidence tab
                                  ─▶ Ambiguity resolved by a person      ──▶ interpretation pins, tiers
Faster shortage response          ─▶ Answers in minutes, not hours       ──▶ certified tools, trace
                                  ─▶ Off-script questions still answered ──▶ guarded SQL, candidates
Staff time back on supply work    ─▶ Review, don't re-derive             ──▶ briefing builder, sign-off
                                  ─▶ Institutional memory of definitions ──▶ ontology, certified registry
Defensible process                ─▶ Audit trail for every answer        ──▶ persisted traces, audit log
                                  ─▶ Measured reliability                ──▶ eval suites, scorecard
```

## 30 / 60 / 90 — how this becomes real

**Days 1–30 — shadow mode.** Two analysts run their actual briefing questions through the tool alongside the
Excel process. Nothing from the tool goes in a binder. We measure: agreement with the manual answer, verifier
catch rate on real questions, and which questions land Tier 2/3 (the certification backlog). A staff
pharmacist reviews and certifies the first ~20 queries. Week one is discovery (`WEEK_ONE_QUESTIONS.md`):
the ontology is rewritten in ODSS's own definitions.

**Days 31–60 — internal briefings.** Tier 1 answers with pharmacist sign-off go into internal briefings for
the Deputy Center Director. The data layer connects to the real sources (Drug Shortage Database,
Drugs@FDA, the FEI registry and inspection classification data) instead of a snapshot; the audit runs
nightly and diffs. Bedrock deployment in the agency's AWS boundary.

**Days 61–90 — first external use.** One externally facing memo built entirely from certified, signed
items. Decide on scale: which other CDER offices share the same three sources, and what their ontology
deltas are.

## What must change before a real congressional briefing

1. **Real data, with provenance.** The snapshot's 77% join gap would be unacceptable; the production
   application registry closes it. Every source gets a fetch timestamp printed on the memo.
2. **ODSS's definitions, not FDA's public ones.** "Resolved," "foreign," "quality" — confirmed with the
   office in week one and versioned.
3. **Named reviewers with authority.** Sign-off must map to real roles (staff pharmacist, division
   director), with identity, not a free-text name.
4. **Deployment inside the boundary.** Claude on Bedrock in AWS GovCloud; no data leaves the agency account.
5. **Reliability measured on real questions.** The capability suite is seeded from the pilot's backlog,
   and pass^k on the regression suite gates every change.
6. **Latency budget for live use.** If the Deputy Director's staff want it in the room, the verifier moves
   in-line and certified queries are pre-computed before the hearing.

## Reusability — what Deloitte would take to the next office

Everything client-independent is reusable: the pipeline (gate → plan → render → verify → tier), the trust
tiers, the certified registry and promotion loop, the eval harness and graders, the briefing builder, the
MCP exposure. Everything client-specific is isolated: `ontology.yaml`, `DECISIONS.md`, the certified tools
over the client's tables, and the audit rules. For another CDER office, the second set is a one- to
two-week engagement; for another agency that briefs Congress from multiple databases, it is the same shape
with different nouns.

## Usage analytics the product keeps

Tier distribution, certified rate, verifier flag rate, average rows cited, latency, cost, and the
**certification backlog** — the questions analysts keep asking that are not yet Tier 1, ordered by
frequency. That backlog is the pharmacist's review queue and the product's roadmap at the same time.
