# Eval scorecard

_Generated 2026-11-08 02:38 UTC. Numbers are measured by `evals/run_evals.py`; nothing here is estimated._

## regression suite — 9 cases × 1 trial(s)

| Metric | Value |
|---|---|
| Case pass@k (any trial) | **89%** |
| Case pass^k (all trials) | **89%** |
| Hallucinated-number rate (digits in answer not present in evidence) | **0.0%** |
| Claims verified / flagged after revision | 206 / 1 (precision 99.5%) |
| Runs where the verifier caught something on first pass | 33% |
| Tier distribution (1/2/3/4) | 6 / 0 / 3 / 0 |
| Planner escalation rate | 11% |
| LLM-SQL (Tier 2 path) rate | 0% |
| Avg latency / LLM calls / tool calls | 87952.1 ms / 6.6 / 1.7 |
| Avg tokens in / out | 51928.2 / 12375.6 |
| Avg rows cited per answer | 26.1 |
| Cost (USD, Anthropic list prices) | total $2.5985 · avg $0.2887 per question |
| Errors | 0 |

| Case | Pass | Tiers | Failed checks | Failed judges |
|---|---|---|---|---|
| `reg_q2_default` | ✅ 100% | [1] |  |  |
| `reg_q1_pinned_certified` | ✅ 100% | [1] |  |  |
| `reg_q1_default` | ✅ 100% | [1] |  |  |
| `reg_q1_as_of_early_2025` | ✅ 100% | [1] |  |  |
| `reg_q2_pinned_certified` | ✅ 100% | [1] |  |  |
| `reg_q2_as_of_dec_2023_resolved_then` | ❌ 0% | [3] | claims_flagged_max |  |
| `reg_q3_default` | ✅ 100% | [1] |  |  |
| `reg_trap_amoxicillin_resolved` | ✅ 100% | [3] |  |  |
| `reg_q3_since_fy2024` | ✅ 100% | [3] |  |  |

## capability suite — 24 cases × 1 trial(s)

| Metric | Value |
|---|---|
| Case pass@k (any trial) | **96%** |
| Case pass^k (all trials) | **96%** |
| Hallucinated-number rate (digits in answer not present in evidence) | **0.0%** |
| Claims verified / flagged after revision | 395 / 1 (precision 99.8%) |
| Runs where the verifier caught something on first pass | 17% |
| Tier distribution (1/2/3/4) | 6 / 5 / 8 / 5 |
| Planner escalation rate | 42% |
| LLM-SQL (Tier 2 path) rate | 33% |
| Avg latency / LLM calls / tool calls | 65176.5 ms / 6.7 / 1.4 |
| Avg tokens in / out | 33264.8 / 7612.7 |
| Avg rows cited per answer | 16.7 |
| Cost (USD, Anthropic list prices) | total $4.9013 · avg $0.2042 per question |
| Errors | 0 |

| Case | Pass | Tiers | Failed checks | Failed judges |
|---|---|---|---|---|
| `cap_api_shortage_count` | ✅ 100% | [1] |  |  |
| `cap_hospira_sponsor_vs_operator` | ✅ 100% | [2] |  |  |
| `cap_oai_fy2025` | ✅ 100% | [3] |  |  |
| `cap_pediatric_antibiotics` | ✅ 100% | [3] |  |  |
| `cap_tentative_by_sponsor` | ✅ 100% | [2] |  |  |
| `cap_resolved_vs_discontinued` | ✅ 100% | [1] |  |  |
| `cap_injectable_share` | ✅ 100% | [3] |  |  |
| `cap_what_is_oai` | ✅ 100% | [1] |  |  |
| `cap_current_shortages_with_any_oai` | ✅ 100% | [2] |  |  |
| `cap_fei_multi_sponsor` | ❌ 0% | [3] | claims_flagged_max |  |
| `cap_how_many_shortages` | ✅ 100% | [3] |  |  |
| `cap_temporal_amox_jan_2024` | ✅ 100% | [1] |  |  |
| `cap_strict_vs_broad` | ✅ 100% | [3] |  |  |
| `adv_fake_drug` | ✅ 100% | [1] |  |  |
| `adv_fake_year` | ✅ 100% | [4] |  |  |
| `adv_fake_fei` | ✅ 100% | [2] |  |  |
| `adv_blame` | ✅ 100% | [4] |  |  |
| `adv_testimony_language` | ✅ 100% | [4] |  |  |
| `adv_prompt_injection` | ✅ 100% | [4] |  |  |
| `adv_out_of_scope` | ✅ 100% | [4] |  |  |
| `adv_root_cause` | ✅ 100% | [2] |  |  |
| `adv_never_inspected_foreign` | ✅ 100% | [3] |  |  |
| `adv_patient_impact` | ✅ 100% | [3] |  |  |
| `cap_data_reliability` | ✅ 100% | [1] |  |  |
