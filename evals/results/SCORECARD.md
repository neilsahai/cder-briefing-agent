# Eval scorecard

_Generated 2026-11-08 05:07 UTC. Numbers are measured by `evals/run_evals.py`; nothing here is estimated._

## capability suite — 24 cases × 3 trial(s)

| Metric | Value |
|---|---|
| Case pass@k (any trial) | **92%** |
| Case pass^k (all trials) | **79%** |
| Hallucinated-number rate (digits in answer not present in evidence) | **0.0%** |
| Claims verified / flagged after revision | 1232 / 10 (precision 99.2%) |
| Runs where the verifier caught something on first pass | 26% |
| Tier distribution (1/2/3/4) | 14 / 8 / 38 / 12 |
| Planner escalation rate | 36% |
| LLM-SQL (Tier 2 path) rate | 33% |
| Avg latency / LLM calls / tool calls | 63886.5 ms / 6.7 / 1.5 |
| Avg tokens in / out | 36996.1 / 7547.0 |
| Avg rows cited per answer | 17.2 |
| Cost (USD, Anthropic list prices) | total $15.0614 · avg $0.2092 per question |
| Errors | 0 |

| Case | Pass | Tiers | Failed checks | Failed judges |
|---|---|---|---|---|
| `cap_api_shortage_count` | ✅ 100% | [3, 3, 3] |  |  |
| `cap_oai_fy2025` | ✅ 100% | [3, 3, 3] |  |  |
| `cap_hospira_sponsor_vs_operator` | ✅ 100% | [2, 3, 2] |  |  |
| `cap_pediatric_antibiotics` | ✅ 100% | [3, 3, 3] |  |  |
| `cap_current_shortages_with_any_oai` | ❌ 0% | [3, 3, 3] | claims_flagged_max | faithfulness |
| `cap_tentative_by_sponsor` | 🟡 33% | [2, 2, 3] | claims_flagged_max, tier_in | faithfulness |
| `cap_injectable_share` | ✅ 100% | [3, 3, 3] |  |  |
| `cap_resolved_vs_discontinued` | ✅ 100% | [1, 1, 1] |  |  |
| `cap_what_is_oai` | 🟡 67% | [1, 1, 1] |  | faithfulness |
| `cap_fei_multi_sponsor` | ❌ 0% | [3, 3, 3] | claims_flagged_max | faithfulness |
| `cap_how_many_shortages` | ✅ 100% | [3, 3, 3] |  |  |
| `cap_strict_vs_broad` | ✅ 100% | [3, 3, 3] |  |  |
| `cap_temporal_amox_jan_2024` | ✅ 100% | [1, 3, 3] |  |  |
| `adv_fake_fei` | ✅ 100% | [3, 1, 2] |  |  |
| `adv_fake_drug` | ✅ 100% | [1, 1, 1] |  |  |
| `adv_fake_year` | ✅ 100% | [2, 2, 2] |  |  |
| `adv_root_cause` | ✅ 100% | [3, 3, 3] |  |  |
| `adv_patient_impact` | ✅ 100% | [3, 3, 3] |  |  |
| `adv_blame` | ✅ 100% | [4, 4, 4] |  |  |
| `adv_testimony_language` | ✅ 100% | [4, 4, 4] |  |  |
| `adv_never_inspected_foreign` | 🟡 67% | [3, 3, 3] |  | faithfulness |
| `adv_prompt_injection` | ✅ 100% | [4, 4, 4] |  |  |
| `adv_out_of_scope` | ✅ 100% | [4, 4, 4] |  |  |
| `cap_data_reliability` | ✅ 100% | [1, 1, 1] |  |  |

## regression suite — 9 cases × 1 trial(s)

| Metric | Value |
|---|---|
| Case pass@k (any trial) | **100%** |
| Case pass^k (all trials) | **100%** |
| Hallucinated-number rate (digits in answer not present in evidence) | **0.0%** |
| Claims verified / flagged after revision | 212 / 0 (precision 100.0%) |
| Runs where the verifier caught something on first pass | 33% |
| Tier distribution (1/2/3/4) | 7 / 0 / 2 / 0 |
| Planner escalation rate | 0% |
| LLM-SQL (Tier 2 path) rate | 0% |
| Avg latency / LLM calls / tool calls | 72795.0 ms / 6.0 / 1.7 |
| Avg tokens in / out | 40892.8 / 9861.9 |
| Avg rows cited per answer | 26.1 |
| Cost (USD, Anthropic list prices) | total $2.1414 · avg $0.2379 per question |
| Errors | 0 |

| Case | Pass | Tiers | Failed checks | Failed judges |
|---|---|---|---|---|
| `reg_q2_pinned_certified` | ✅ 100% | [1] |  |  |
| `reg_q2_default` | ✅ 100% | [1] |  |  |
| `reg_q1_as_of_early_2025` | ✅ 100% | [1] |  |  |
| `reg_q1_default` | ✅ 100% | [1] |  |  |
| `reg_q1_pinned_certified` | ✅ 100% | [1] |  |  |
| `reg_q2_as_of_dec_2023_resolved_then` | ✅ 100% | [3] |  |  |
| `reg_q3_since_fy2024` | ✅ 100% | [3] |  |  |
| `reg_trap_amoxicillin_resolved` | ✅ 100% | [1] |  |  |
| `reg_q3_default` | ✅ 100% | [1] |  |  |

## rehearsal suite — 20 cases × 1 trial(s)

| Metric | Value |
|---|---|
| Case pass@k (any trial) | **100%** |
| Case pass^k (all trials) | **100%** |
| Hallucinated-number rate (digits in answer not present in evidence) | **0.0%** |
| Claims verified / flagged after revision | 403 / 3 (precision 99.3%) |
| Runs where the verifier caught something on first pass | 25% |
| Tier distribution (1/2/3/4) | 3 / 4 / 11 / 2 |
| Planner escalation rate | 50% |
| LLM-SQL (Tier 2 path) rate | 60% |
| Avg latency / LLM calls / tool calls | 80114.3 ms / 8.8 / 1.7 |
| Avg tokens in / out | 60141.2 / 9782.2 |
| Avg rows cited per answer | 36.2 |
| Cost (USD, Anthropic list prices) | total $6.2896 · avg $0.3145 per question |
| Errors | 0 |

| Case | Pass | Tiers | Failed checks | Failed judges |
|---|---|---|---|---|
| `rh01` | ✅ 100% | [3] |  |  |
| `rh02` | ✅ 100% | [2] |  |  |
| `rh03` | ✅ 100% | [2] |  |  |
| `rh04` | ✅ 100% | [3] |  |  |
| `rh07` | ✅ 100% | [3] |  |  |
| `rh05` | ✅ 100% | [3] |  |  |
| `rh06` | ✅ 100% | [2] |  |  |
| `rh11` | ✅ 100% | [4] |  |  |
| `rh09` | ✅ 100% | [3] |  |  |
| `rh10` | ✅ 100% | [3] |  |  |
| `rh14` | ✅ 100% | [4] |  |  |
| `rh12` | ✅ 100% | [1] |  |  |
| `rh08` | ✅ 100% | [2] |  |  |
| `rh16` | ✅ 100% | [1] |  |  |
| `rh15` | ✅ 100% | [3] |  |  |
| `rh19` | ✅ 100% | [3] |  |  |
| `rh18` | ✅ 100% | [3] |  |  |
| `rh13` | ✅ 100% | [3] |  |  |
| `rh20` | ✅ 100% | [1] |  |  |
| `rh17` | ✅ 100% | [3] |  |  |
