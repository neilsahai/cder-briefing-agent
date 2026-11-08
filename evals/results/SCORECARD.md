# Eval scorecard

_Generated 2026-11-08 01:11 UTC. Numbers are measured by `evals/run_evals.py`; nothing here is estimated._

## regression suite — 2 cases × 1 trial(s)

| Metric | Value |
|---|---|
| Case pass@k (any trial) | **100%** |
| Case pass^k (all trials) | **100%** |
| Hallucinated-number rate (digits in answer not present in evidence) | **0.0%** |
| Claims verified / flagged after revision | 41 / 0 (precision 100.0%) |
| Runs where the verifier caught something on first pass | 0% |
| Tier distribution (1/2/3/4) | 2 / 0 / 0 / 0 |
| Planner escalation rate | 0% |
| LLM-SQL (Tier 2 path) rate | 0% |
| Avg latency / LLM calls / tool calls | 68444.5 ms / 5.0 / 1.0 |
| Avg tokens in / out | 20212.5 / 8849.0 |
| Avg rows cited per answer | 17.0 |
| Total cost (USD, from pricing.json) | n/a — pricing table not configured |
| Errors | 0 |

| Case | Pass | Tiers | Failed checks | Failed judges |
|---|---|---|---|---|
| `reg_q1_pinned_certified` | ✅ 100% | [1] |  |  |
| `reg_q1_default` | ✅ 100% | [1] |  |  |
