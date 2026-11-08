# CDER Drug Shortage Briefing Agent

**Deloitte Federal FDE take-home #3 — FDA / CDER scenario.** An agentic briefing tool for Dr. Whitmore's
Office of Drug Shortage Staff that answers natural-language questions over the shortage, application, and
inspection data — and labels every answer with how much weight it can bear in a Senate hearing.

> Last year's tool failed because semantic decisions happened at runtime, inside a model, invisibly. This one
> moves them to modeling time in an ontology you can read, makes numbers structurally unable to pass through
> the model, labels every claim with a trust tier, and ships with the eval suite that proves it.

## Measured, not claimed

| Metric (from `evals/results/SCORECARD.md`) | Regression (9 cases) | Capability (24 off-script + adversarial) | Rehearsal (20 panel-style) |
|---|---|---|---|
| Cases passing, latest complete single-trial run | **100%** (9/9) | **79%** (19/24) — range across 4 full runs of the current design: 79–96% | **100%** (20/20) |
| Hallucinated-number rate — digits in an answer not present in evidence | **0.0%** | **0.0%** | **0.0%** |
| Claims verified / flagged after revision | 221 / 0 | 393 / 0 | 403 / 3 |
| Runs where the independent verifier caught something on the first draft | 22% | 25% | 20% |
| Adversarial cases (fake FEI, fake drug, fake year, root cause, blame, testimony language, prompt injection, out of scope…) | — | 10 / 10 on every run | 3 / 3 |
| Avg latency · LLM calls · rows cited per answer | 72 s · 6.4 · 25 | 67 s · 6.8 · 16 | 62 s · 7.1 · 14 |
| Cost per question (Anthropic list prices, Nov 2026) | $0.26 | $0.22 | $0.24 |

**On the capability range.** The hallucinated-number check and citation checks have held at 0.0% / 100% on
every run (300+ answers). The misses are of three kinds: (a) the Opus verifier still flags a claim after the
revision pass, which demotes the answer to Tier 3 — the intended, cautious failure direction, and it counts as a
fail here; (b) a model-judge dimension disagrees (faithfulness, ambiguity_surfaced) — sometimes a real framing
error the verifier missed (a headline that read "7 under either basis" when the default basis gives 6),
sometimes judge variance (the same answer passes on the next run) or a judge that returns no verdict;
(c) earlier in the build, two grader/renderer bugs that the harness itself exposed (see `BUILD_LOG.md`).
That variance is why the harness supports `--trials 3` and reports pass^k. A 3-trial run of the final build was
started and stopped at 23/72 trials when the API credit ran out: 4 failures, three of type (a) and one of
type (b). It will be re-run in full.

The red-team report (`docs/RED_TEAM_REPORT.md`) lists the 15 traps planted in the data — including the exact
amoxicillin status conflict from the brief's backstory — with the naive result and this system's result for each.

## Thirty-second tour

```
cp .env.example .env                       # add ANTHROPIC_API_KEY
pip install -r backend/requirements.txt
cd frontend && npm install && npm run build && cd ..
cd backend && uvicorn app.api:app --port 8787        # http://localhost:8787
```

Or from the terminal:

```
cd backend && python scripts/ask.py "Is the amoxicillin shortage resolved?"
```

Answer: **No** — latest status Current; the earlier Resolved record is disclosed; Tier 1 Certified; every value
cites a row. (`drug_shortages.csv` line 2 and line 3 are the conflict.)

## What is in the box

| Deliverable | Where |
|---|---|
| The product — React workspace + FastAPI | `frontend/`, `backend/app/api.py` |
| Agent: gate → interpretations → planner (certified tools, guarded SQL) → placeholder narrator → Opus verifier → trust tier | `backend/app/agent/` |
| Ontology and the rationale for every interpretive default | `ontology.yaml`, `DECISIONS.md` |
| Data audit (13 detectors with lineage) and certified tools | `backend/app/data/`, `backend/app/tools/` |
| Certified-query registry with promotion / revoke / audit log; interpretation pins | `backend/app/registry/` |
| Briefing builder with analyst sign-off and footnoted `.docx` / `.md` export | `backend/app/briefings.py`, `deliverables/briefing_memo.docx` |
| MCP server exposing the certified tools to Claude Desktop / any agent | `backend/app/mcp_server.py` |
| Eval harness: regression + capability suites, code graders + per-dimension judges, pass^k, scorecard | `evals/` |
| 50 deterministic tests; CI on every push | `backend/tests/`, `.github/workflows/ci.yml` |
| Red-team report, trust & hallucination, agentic design, product thinking (30/60/90, value tree, cost of being wrong), week-one client questions, security & deployment | `docs/` |
| Build log — how Claude was used, and where it was wrong and what caught it | `BUILD_LOG.md` |
| Walkthrough script and slide deck | `docs/WALKTHROUGH_SCRIPT.md`, `deliverables/walkthrough_deck.pptx` |

## The three required queries

Run `cd backend && python -m pytest tests/test_certified_queries.py -v` for the golden answers under default
**and** alternate readings. In short, as of the data's latest date (2025-10-23):

1. **Quality shortages / OAI sites** — 6 drugs (strict `Quality: cGMP Issue`); 4 linked sites with an OAI in
   FY2024–25 (Baxter Deerfield, Pfizer McPherson, ICU Medical Lake Forest, Fresenius Kabi Wilson); Hospira
   is VAI-only; the Meropenem site has no inspection record. Broad reading: 15 drugs. "As of early 2025"
   per the PDF wording: FY23–24, only Pfizer and ICU Medical.
2. **Amoxicillin oral suspension** — 6 applications for the ingredient (no dosage-form column exists):
   4 fully approved, 2 tentative, 3 actively marketed, 1 discontinued. One oral-suspension record Current
   (`DS-2023-0142`, with a disclosed earlier Resolved revision); one Discontinued.
3. **Foreign sites not inspected since FY2021** — 4 (Aurobindo Unit IV, Zhejiang Tianyu, Macleods, Shanxi
   Zhendong); 2 never-inspected sites with UNKNOWN country reported separately; coverage 13 of 57 current
   records, stated in the answer.

## Trust tiers

| Tier | Meaning |
|---|---|
| 1 Certified | Certified tools or a certified query; verifier passed; ambiguity resolved or pinned. Eligible for testimony with sign-off. |
| 2 Derived | Depends on LLM-authored SQL — validated, executed, candidates compared — not certified. |
| 3 Qualified | A reading changes the answer (shown side by side) or the verifier raised a concern. One-click pin → re-run → Tier 1. |
| 4 Not answerable | Out of scope, or the data lacks the field; says what can be answered instead. |

## Model routing

By role, with rule-based escalation (no "complexity classifier"): Haiku 5.5 gate · Sonnet 5.5 planner,
escalating to Opus 5.5 when two readings diverge or SQL is needed · Sonnet narrator · **Opus verifier,
always** · Sonnet + Opus SQL candidates. `PROVIDER=bedrock` switches the same code to Claude on Amazon
Bedrock (GovCloud path in `docs/SECURITY_AND_DEPLOYMENT.md`).

## Run the evals

```
python evals/run_evals.py --suite regression --trials 1
python evals/run_evals.py --suite capability --trials 1 --concurrency 4
python evals/run_evals.py --suite all --trials 3          # pass^3
```

## MCP

```
cd backend && python -m app.mcp_server     # stdio; 15 certified tools + ontology/decisions resources
```

---
Synthetic data provided with the assignment; no real patient or manufacturer data. Built with Claude
(design) and Claude Code (implementation) — see `BUILD_LOG.md` for the honest account, including the
three times the verifier or the tests caught the model being wrong.
