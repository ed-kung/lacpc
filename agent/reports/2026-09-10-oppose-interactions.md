# Do any factors mitigate the effect of public opposition?

Most covariates in the preferred ordered logit do not moderate public opposition. The only statistically detectable interactions are with the text-embedding clusters: the opposition penalty is concentrated in cluster 1 (discretionary CUPs and code amendments) and is close to zero in cluster 2 (incentive-program housing). Public support, consent-calendar placement, atypicality, project type, and incentive-program suffixes do not produce significant interactions with `log2_oppose`. After Benjamini–Hochberg adjustment of the 16 tests, no interaction remains significant at 5%.

## Setup

The baseline is column (4) of the ordered logit in `src/R/15-ordered-logit.R`: outcome in {0 = delayed/denied, 1 = approved with conditions, 2 = approved}, with project-type, physical, letter-count, hearing, and atypicality controls plus suffix-group, council-district, year, and embedding-cluster dummies. N = 818. Baseline `log2_oppose` = −0.154 (SE 0.057, p = 0.007).

Each candidate is entered one at a time as an interaction with `log2_oppose`. A positive interaction means a *weaker* opposition penalty (mitigation). Continuous moderators are demeaned in the product term so the main `log2_oppose` coefficient is the slope at the sample mean. Candidates are the covariates already in the preferred specification, plus TOC / Density Bonus / HCA suffixes (incentive programs that constrain CPC discretion).

## Results

| Moderator | Interaction | SE | p | BH p | Direction |
|---|---|---|---|---|---|
| Embedding cluster 1 | −0.286 | 0.103 | 0.005 | 0.084 | Amplifies |
| Embedding cluster 2 | +0.207 | 0.102 | 0.042 | 0.339 | Mitigates |
| Log square footage | +0.018 | 0.009 | 0.064 | 0.341 | Mitigates (marginal) |
| Incentive-program suffix | +0.143 | 0.103 | 0.165 | 0.511 | — |
| Density Bonus | +0.162 | 0.119 | 0.172 | 0.511 | — |
| Mixed-use | +0.131 | 0.109 | 0.231 | 0.511 | — |
| Number of agenda items | +0.028 | 0.024 | 0.242 | 0.511 | — |
| Consent calendar | −0.276 | 0.243 | 0.256 | 0.511 | — |
| Height | +0.0004 | 0.0005 | 0.355 | 0.631 | — |
| Public support (log2) | −0.021 | 0.025 | 0.403 | 0.645 | — |
| Housing Crisis Act | +0.096 | 0.173 | 0.577 | 0.840 | — |
| Transit Oriented Communities | +0.051 | 0.143 | 0.722 | 0.962 | — |
| Non-residential | +0.021 | 0.119 | 0.859 | 0.996 | — |
| Agenda order | +0.004 | 0.025 | 0.871 | 0.996 | — |
| Residential | +0.007 | 0.110 | 0.951 | 0.997 | — |
| Atypicality | +0.000 | 0.070 | 0.997 | 0.997 | — |

Implied `log2_oppose` slopes from the two cluster interactions:

- Not cluster 1: −0.036 (p = 0.62); cluster 1: −0.322 (p = 0.0001)
- Not cluster 2: −0.262 (p = 0.0008); cluster 2: −0.054 (p = 0.47)

Cluster 1 is discretionary land-use entitlements (CUPs, citywide/plan code amendments). Cluster 2 is primarily residential projects using density bonus, TOC, and other incentives. The opposition penalty is therefore concentrated where the CPC retains discretion, and is statistically absent among incentive-program housing cases.

Incentive-program *suffixes* point in the same direction but are noisy. For example, the implied oppose slope is −0.217 (p = 0.003) without an incentive-program suffix and −0.074 (p = 0.36) with one; Density Bonus is −0.195 (p = 0.003) vs −0.033 (p = 0.75). Those differences are not significant as interactions.

Public support does not offset opposition (`log2_oppose × log2_support` = −0.021, p = 0.40). Atypicality, consent calendar, project type, and agenda order likewise do not moderate the oppose coefficient.

## Why cluster 1 vs cluster 2?

The residential dummy did not moderate opposition. What differs is residual legal discretion, not whether the project is housing.

Cluster 1 is mostly conditional use permits and citywide or planwide code amendments. A CUP is permission to do something the zone does not otherwise allow (alcohol service, a school, a large assembly use). The findings are subjective: compatibility with surrounding uses, not detrimental to public welfare. Opposition letters in this dataset disproportionately cite neighborhood character, building dimensions, and procedure—exactly the evidence those findings ask for. The entitlement is also *designed* to be conditioned. Hours, security, parking, and operating limits are the point of a conditional use, so attaching conditions (or continuing the item so the applicant can negotiate with neighbors) is a legally available and politically cheap response to a fire alarm. Approving a contested CUP is an attributable vote; delay is not. That is the paper’s oversight-risk mechanism, and it has bite because the commissioner can still say no.

Cluster 2 is mostly TOC, Density Bonus, and Housing Crisis Act housing. Those programs exist to take subjective neighborhood opposition off the table. State density-bonus law requires the city to grant the bonus and concessions if the project is eligible; local government generally cannot deny an eligible project because neighbors dislike the density. The Housing Crisis Act, in the paper’s own suffix description, “limits local discretion over qualifying housing projects.” TOC base incentives are as-of-right if the site and affordable set-aside qualify. Opposition letters still arrive, and they still sound like fire alarms, but they are often legally off-point. The commissioner can approve a contested project by pointing to objective eligibility rather than taking a political side. Delay and extra conditions are not cheap in this setting: they can be treated as a de facto denial of a mandated incentive and can create Housing Accountability Act exposure. In the paper’s notation, χ raises the monitoring penalty M(a, e, χ) only if action a is actually a choice. Incentive programs shrink that action set, so Proposition 2 (opposition reduces approvals) should be weaker.

A secondary institutional detail points the same way. Cluster 2 cases at the CPC are often appeals of a Director determination that already granted TOC or density-bonus incentives. On appeal the question is whether the prior determination was legally in error, not whether commissioners like the project. Neighborhood opposition does not, by itself, establish error. Cluster 1 CUPs are more often original discretionary grants, where opposition is on-point.

The suffix-based incentive dummies pointed in the same direction but were noisier. Cluster membership is a coarser grouping: cluster 2 is 84% incentive-program suffixes, cluster 1 is 6%. The cluster result should be read as residual discretion, not as a clean TOC or HCA coefficient.

Because 16 tests were run, the cluster interactions remain exploratory (BH p = 0.08 for cluster 1; 0.34 for cluster 2).

## Artifacts

Written under `AGENT_DATA_PATH/oppose_interactions/`:

- `one_at_a_time_interactions.csv` / `.parquet`
- `simple_slopes.csv` / `.parquet`
- `interaction_coefs.png`

Script: `agent/src/oppose-interactions.R`
