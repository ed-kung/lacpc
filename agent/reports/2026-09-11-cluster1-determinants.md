# What variables determine embedding cluster 1?

Cluster 1 is an entitlement-type partition, not a hearing-process or opposition partition. The strongest single predictor is the incentive-program suffix group: 4.9% of TOC / Density Bonus / HCA cases are in cluster 1 versus 69.8% of cases without those suffixes. Project types “code or plan amendment” and “conditional use permit” are 100% cluster 1 (128/128). Suffix groups alone classify cluster 1 at 5-fold CV AUC 0.935; adding letters, agenda order, and consent calendar does not.

## Setup

Base file: `DATA_PATH/intermediate_data/cpc/ologit_regression_data.parquet` (N = 818). Target is `cluster == 1` (317 cases, 38.8%). Predictors are structured case characteristics. Embedding-derived distances / atypicality are excluded because they are defined inside clusters. Vote tallies and the ordered-logit outcome are excluded as post-decision.

Three complementary rankings: (i) univariate AUC, (ii) grouped 5-fold CV AUC from L2-penalized logit, (iii) logit average marginal effects and random-forest permutation importance.

## Main findings

**Incentive programs vs code/plan amendments.** `sfx_grp_IP` univariate AUC = 0.841. Density Bonus, TOC, HCA, and vesting HCA are each 0–5% cluster 1. `sfx_grp_CPA` is 85.5% cluster 1 and covers 43% of cluster 1. Code Amendment suffixes are 44/44 cluster 1. Citywide (no council district) items are 43/43 cluster 1.

**Project type is nearly a hard partition.**

| Project type | C0 | C1 | C2 | N | % C1 |
|---|---:|---:|---:|---:|---:|
| Code or plan amendment | 0 | 87 | 0 | 87 | 100 |
| Conditional use permit | 0 | 41 | 0 | 41 | 100 |
| Non-residential | 5 | 106 | 17 | 128 | 83 |
| Mixed-use | 29 | 42 | 191 | 262 | 16 |
| Residential | 9 | 8 | 201 | 218 | 4 |
| PSH / shelter | 1 | 2 | 19 | 22 | 9 |

Prefix VTT (tract maps) is cluster 0 (61/63). Prefix DIR is mostly cluster 2 (142/156). Cluster 1 is 90% prefix CPC.

**CUP suffix is not the same as CUP project type.** Cases with a CUP-group suffix are 50% cluster 1. Conditional on no incentive-program suffix that rate is 80%; with an incentive-program suffix it is 6%. The project-type label “CONDITIONAL USE PERMIT” (n = 41) is the clean CUP marker.

**Physical variables are proxies.** Height missing (AUC 0.731) and fewer requested actions (AUC 0.819) mark code amendments and unstacked entitlements rather than building size per se. Cluster 1 log square footage is lower because many of those cases have no building.

**Letters and hearing process do not assign the cluster.** Log2 oppose AUC 0.552; log2 support 0.535. Letters + hearing jointly CV-AUC 0.664.

**Grouped CV AUC.** Suffix groups 0.935; 8-category project type 0.919; ologit covariates 0.895; suffix groups + project type 0.959; full structured set 0.969. A logit of cluster 1 on suffix groups + ologit covariates + appeal has McFadden R² = 0.67. AMEs: code/plan amendments +14 pp, incentive programs −9 pp, residential −14 pp, mixed-use −13 pp, height missing +15 pp. RF CV AUC 0.979; permutation importance ranks `sfx_grp_IP`, height, then `sfx_grp_CPA`. Unique RF drops are small because those variables are collinear readings of the same split.

This matches the paper’s qualitative cluster-1 description (discretionary CUPs and citywide/plan code amendments) and the earlier finding that cluster 1 is 6% incentive-program suffixes.

## Artifacts

Written under `AGENT_DATA_PATH/cluster1_determinants/`:

- `univariate.csv` / `.parquet`
- `grouped_cv_auc.csv` / `.parquet`
- `logit_ame.csv` / `.parquet`
- `rf_permutation_importance.csv` / `.parquet`
- `project_type_by_cluster.csv`, `prefix_by_cluster.csv`, `simple_rules.csv`, `summary_stats.csv`
- `univariate_auc.png`

Script: `agent/src/cluster1-determinants.py`
