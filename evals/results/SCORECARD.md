# Eval scorecard

_Generated 2026-11-08 01:01 UTC. Numbers are measured by `evals/run_evals.py`; nothing here is estimated._

## regression suite — 9 cases × 1 trial(s)

| Metric | Value |
|---|---|
| Case pass@k (any trial) | **56%** |
| Case pass^k (all trials) | **56%** |
| Hallucinated-number rate (digits in answer not present in evidence) | **22.2%** |
| Claims verified / flagged after revision | 179 / 2 (precision 98.9%) |
| Runs where the verifier caught something on first pass | 67% |
| Tier distribution (1/2/3/4) | 3 / 0 / 6 / 0 |
| Planner escalation rate | 0% |
| LLM-SQL (Tier 2 path) rate | 0% |
| Avg latency / LLM calls / tool calls | 90175.2 ms / 7.4 / 2.2 |
| Avg tokens in / out | 31316.3 / 12398.9 |
| Avg rows cited per answer | 28.9 |
| Total cost (USD, from pricing.json) | n/a — pricing table not configured |
| Errors | 0 |

| Case | Pass | Tiers | Failed checks | Failed judges |
|---|---|---|---|---|
| `reg_q1_default` | ❌ 0% | [1] |  | ambiguity_surfaced |
| `reg_q1_as_of_early_2025` | ✅ 100% | [3] |  |  |
| `reg_q1_pinned_certified` | ❌ 0% | [3] | tier_in |  |
| `reg_q2_default` | ✅ 100% | [1] |  |  |
| `reg_q2_pinned_certified` | ✅ 100% | [1] |  |  |
| `reg_q2_as_of_dec_2023_resolved_then` | ✅ 100% | [3] |  |  |
| `reg_trap_amoxicillin_resolved` | ✅ 100% | [3] |  |  |
| `reg_q3_since_fy2024` | ❌ 0% | [3] | markdown_contains:3010234567, verified_numbers_only |  |
| `reg_q3_default` | ❌ 0% | [3] | tier_in, verified_numbers_only |  |
