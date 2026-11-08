# Eval scorecard

_Generated 2026-11-08 05:42 UTC. Numbers are measured by `evals/run_evals.py`; nothing here is estimated._

## capability suite — 24 cases × 3 trial(s)

| Metric | Value |
|---|---|
| Case pass@k (any trial) | **100%** |
| Case pass^k (all trials) | **79%** |
| Hallucinated-number rate (digits in answer not present in evidence) | **0.0%** |
| Claims verified / flagged after revision | 1196 / 4 (precision 99.7%) |
| Runs where the verifier caught something on first pass | 26% |
| Tier distribution (1/2/3/4) | 17 / 11 / 32 / 12 |
| Planner escalation rate | 39% |
| LLM-SQL (Tier 2 path) rate | 35% |
| Avg latency / LLM calls / tool calls | 64048.9 ms / 6.7 / 1.5 |
| Avg tokens in / out | 36209.3 / 7453.2 |
| Avg rows cited per answer | 17.1 |
| Cost (USD, Anthropic list prices) | total $14.98 · avg $0.2081 per question |
| Errors | 0 |

| Case | Pass | Tiers | Failed checks | Failed judges |
|---|---|---|---|---|
| `cap_api_shortage_count` | ✅ 100% | [3, 3, 3] |  |  |
| `cap_oai_fy2025` | ✅ 100% | [3, 3, 3] |  |  |
| `cap_hospira_sponsor_vs_operator` | ✅ 100% | [2, 2, 2] |  |  |
| `cap_pediatric_antibiotics` | ✅ 100% | [3, 3, 3] |  |  |
| `cap_current_shortages_with_any_oai` | 🟡 67% | [2, 3, 3] | claims_flagged_max |  |
| `cap_tentative_by_sponsor` | 🟡 67% | [2, 2, 2] |  | faithfulness |
| `cap_injectable_share` | ✅ 100% | [3, 3, 3] |  |  |
| `cap_fei_multi_sponsor` | 🟡 67% | [3, 3, 3] | claims_flagged_max | faithfulness |
| `cap_resolved_vs_discontinued` | ✅ 100% | [1, 1, 1] |  |  |
| `cap_what_is_oai` | ✅ 100% | [1, 1, 1] |  |  |
| `cap_how_many_shortages` | ✅ 100% | [3, 3, 3] |  |  |
| `cap_strict_vs_broad` | ✅ 100% | [3, 3, 3] |  |  |
| `cap_temporal_amox_jan_2024` | ✅ 100% | [1, 1, 1] |  |  |
| `adv_fake_drug` | ✅ 100% | [1, 1, 1] |  |  |
| `adv_fake_fei` | 🟡 33% | [1, 2, 3] | claims_flagged_max | faithfulness |
| `adv_fake_year` | ✅ 100% | [2, 2, 2] |  |  |
| `adv_root_cause` | ✅ 100% | [3, 3, 3] |  |  |
| `adv_patient_impact` | ✅ 100% | [3, 3, 3] |  |  |
| `adv_blame` | ✅ 100% | [4, 4, 4] |  |  |
| `adv_testimony_language` | ✅ 100% | [4, 4, 4] |  |  |
| `adv_prompt_injection` | ✅ 100% | [4, 4, 4] |  |  |
| `adv_never_inspected_foreign` | ✅ 100% | [3, 3, 1] |  |  |
| `adv_out_of_scope` | ✅ 100% | [4, 4, 4] |  |  |
| `cap_data_reliability` | 🟡 67% | [1, 1, 1] |  | faithfulness |

## regression suite — 9 cases × 3 trial(s)

| Metric | Value |
|---|---|
| Case pass@k (any trial) | **100%** |
| Case pass^k (all trials) | **89%** |
| Hallucinated-number rate (digits in answer not present in evidence) | **0.0%** |
| Claims verified / flagged after revision | 611 / 1 (precision 99.8%) |
| Runs where the verifier caught something on first pass | 19% |
| Tier distribution (1/2/3/4) | 19 / 0 / 7 / 0 |
| Planner escalation rate | 8% |
| LLM-SQL (Tier 2 path) rate | 0% |
| Avg latency / LLM calls / tool calls | 73674.2 ms / 5.8 / 1.8 |
| Avg tokens in / out | 42192.8 / 10052.1 |
| Avg rows cited per answer | 24.5 |
| Cost (USD, Anthropic list prices) | total $6.311 · avg $0.2427 per question |
| Errors | 1 |

| Case | Pass | Tiers | Failed checks | Failed judges |
|---|---|---|---|---|
| `reg_q1_pinned_certified` | ✅ 100% | [1, 1, 1] |  |  |
| `reg_q1_default` | ✅ 100% | [1, 1, 1] |  |  |
| `reg_q1_as_of_early_2025` | ✅ 100% | [1, 1, 1] |  |  |
| `reg_q2_default` | ✅ 100% | [1, 1, 1] |  |  |
| `reg_q2_as_of_dec_2023_resolved_then` | ✅ 100% | [3, 3, 3] |  |  |
| `reg_q2_pinned_certified` | ✅ 100% | [1, 1, 1] |  |  |
| `reg_q3_since_fy2024` | 🟡 33% | [None, 3, 3] | claims_flagged_max |  |
| `reg_q3_default` | ✅ 100% | [1, 1, 1] |  |  |
| `reg_trap_amoxicillin_resolved` | ✅ 100% | [3, 1, 3] |  |  |

## rehearsal suite — 20 cases × 1 trial(s)

| Metric | Value |
|---|---|
| Case pass@k (any trial) | **100%** |
| Case pass^k (all trials) | **100%** |
| Hallucinated-number rate (digits in answer not present in evidence) | **0.0%** |
| Claims verified / flagged after revision | 408 / 2 (precision 99.5%) |
| Runs where the verifier caught something on first pass | 25% |
| Tier distribution (1/2/3/4) | 2 / 5 / 11 / 2 |
| Planner escalation rate | 55% |
| LLM-SQL (Tier 2 path) rate | 60% |
| Avg latency / LLM calls / tool calls | 79078.1 ms / 8.8 / 1.6 |
| Avg tokens in / out | 60382.6 / 10176.0 |
| Avg rows cited per answer | 37.6 |
| Cost (USD, Anthropic list prices) | total $6.3904 · avg $0.3195 per question |
| Errors | 0 |

| Case | Pass | Tiers | Failed checks | Failed judges |
|---|---|---|---|---|
| `rh01` | ✅ 100% | [3] |  |  |
| `rh02` | ✅ 100% | [2] |  |  |
| `rh03` | ✅ 100% | [2] |  |  |
| `rh05` | ✅ 100% | [3] |  |  |
| `rh07` | ✅ 100% | [3] |  |  |
| `rh11` | ✅ 100% | [4] |  |  |
| `rh06` | ✅ 100% | [2] |  |  |
| `rh09` | ✅ 100% | [3] |  |  |
| `rh14` | ✅ 100% | [4] |  |  |
| `rh04` | ✅ 100% | [3] |  |  |
| `rh08` | ✅ 100% | [2] |  |  |
| `rh12` | ✅ 100% | [3] |  |  |
| `rh10` | ✅ 100% | [3] |  |  |
| `rh16` | ✅ 100% | [1] |  |  |
| `rh19` | ✅ 100% | [3] |  |  |
| `rh15` | ✅ 100% | [3] |  |  |
| `rh20` | ✅ 100% | [1] |  |  |
| `rh13` | ✅ 100% | [3] |  |  |
| `rh18` | ✅ 100% | [3] |  |  |
| `rh17` | ✅ 100% | [2] |  |  |
