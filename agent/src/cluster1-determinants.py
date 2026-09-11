"""Identify observables that most strongly determine embedding cluster 1.

Cluster membership is from K-means on agenda-item text embeddings
(see 04descriptives.tex). This script asks which *structured* variables in
ologit_regression_data.parquet recover that partition — i.e. which case
characteristics the embedding cluster is picking up.

Embedding-derived fields (atypicality / distances) and post-decision fields
(votes, outcome) are excluded as predictors.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
import statsmodels.api as sm
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
with open(ROOT / "config.local.yaml") as f:
    CFG = yaml.safe_load(f)
DATA_PATH = Path(CFG["DATA_PATH"])
AGENT_DATA_PATH = Path(CFG["AGENT_DATA_PATH"])
OUT_DIR = AGENT_DATA_PATH / "cluster1_determinants"
OUT_DIR.mkdir(parents=True, exist_ok=True)

INPUT_PATH = DATA_PATH / "intermediate_data/cpc/ologit_regression_data.parquet"

SFX_GRP_LABELS = {
    "sfx_grp_SPR": "Site Plan Review",
    "sfx_grp_APP": "Appeals",
    "sfx_grp_IP": "Incentive programs",
    "sfx_grp_CUP": "Conditional use permits",
    "sfx_grp_VAE": "Variances / adjustments / exceptions",
    "sfx_grp_CR": "Compliance review",
    "sfx_grp_CPA": "Code or plan amendments",
    "sfx_grp_DA": "Development agreements",
    "sfx_grp_OTH": "Other suffixes",
}

SFX_LABELS = {
    "sfx_SPR": "Site Plan Review (SPR)",
    "sfx_1A": "Appeal, 1st (1A)",
    "sfx_DB": "Density Bonus (DB)",
    "sfx_CU": "Conditional Use (CU)",
    "sfx_HCA": "Housing Crisis Act (HCA)",
    "sfx_TOC": "Transit Oriented Communities (TOC)",
    "sfx_HD": "Height District (HD)",
    "sfx_SPP": "Specific Plan Project Permit (SPP)",
    "sfx_MCUP": "Master CUP (MCUP)",
    "sfx_ZC": "Zone Change (ZC)",
    "sfx_GPA": "General Plan Amendment (GPA)",
    "sfx_VZC": "Vesting Zone Change (VZC)",
    "sfx_WDI": "Waiver of Dedication (WDI)",
    "sfx_VHCA": "Vesting HCA (VHCA)",
    "sfx_CA": "Code Amendment (CA)",
    "sfx_CUB": "CUP Beverage (CUB)",
    "sfx_PHP": "Priority Housing (PHP)",
    "sfx_ZV": "Zone Variance (ZV)",
    "sfx_TDR": "Transfer of Development Rights (TDR)",
    "sfx_SP": "Specific Plan (SP)",
    "sfx_ZAA": "ZA Adjustment (ZAA)",
    "sfx_DRB": "Design Review Board (DRB)",
    "sfx_GPAJ": "GPA Measure JJJ (GPAJ)",
}

STRUCT_LABELS = {
    "is_residential": "Residential (incl. PSH / senior)",
    "is_mixed_use": "Mixed-use",
    "is_nonresidential": "Non-residential",
    "is_appeal": "Appeal case",
    "is_consent_calendar": "Consent calendar",
    "log_square_footage": "Log square footage",
    "log_square_footage_missing": "Square footage missing",
    "height": "Height (ft)",
    "height_missing": "Height missing",
    "log2_support": "Log2 support letters",
    "log2_oppose": "Log2 oppose letters",
    "agenda_order": "Agenda order",
    "num_agenda_items": "Number of agenda items",
    "num_requested_actions": "Number of requested actions",
    "times_appeared": "Times appeared",
    "n_docs": "Number of supplemental docs",
    "cd_CITYWIDE": "Citywide (no district)",
}

PREFIX_LABELS = {
    "prefix_CPC": "Prefix CPC",
    "prefix_DIR": "Prefix DIR (Director)",
    "prefix_VTT": "Prefix VTT (tract map)",
    "prefix_ZA": "Prefix ZA",
}

PT_LABELS = {
    "pt_CODE OR PLAN AMENDMENT": "Project type: code/plan amendment",
    "pt_CONDITIONAL USE PERMIT": "Project type: CUP",
    "pt_MIXED-USE DEVELOPMENT": "Project type: mixed-use",
    "pt_NON-RESIDENTIAL DEVELOPMENT": "Project type: non-residential",
    "pt_OTHER": "Project type: other",
    "pt_PERMANENT SUPPORTIVE HOUSING / HOMELESS SHELTER": "Project type: PSH / shelter",
    "pt_RESIDENTIAL DEVELOPMENT": "Project type: residential",
    "pt_SENIOR CARE / ASSISTED LIVING FACILITY": "Project type: senior care",
}


def label_of(name: str) -> str:
    for d in (SFX_GRP_LABELS, SFX_LABELS, STRUCT_LABELS, PREFIX_LABELS, PT_LABELS):
        if name in d:
            return d[name]
    return name


def to_float(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s.astype(float)
    return pd.to_numeric(s, errors="coerce").astype(float)


# ---- Load -------------------------------------------------------------------

df = pd.read_parquet(INPUT_PATH)
n = len(df)
df["cluster_1"] = (df["cluster"] == 1).astype(int)
y = df["cluster_1"].to_numpy()
base_rate = float(y.mean())

# Prefix and project-type dummies (kept as analysis covariates, not in ologit FE set)
for p in ["CPC", "DIR", "VTT", "ZA"]:
    df[f"prefix_{p}"] = (df["prefix"] == p).astype(float)
for pt in df["project_type"].unique():
    df[f"pt_{pt}"] = (df["project_type"] == pt).astype(float)

sfx_grp = list(SFX_GRP_LABELS)
sfx_freq = [c for c in SFX_LABELS if c in df.columns]
struct = list(STRUCT_LABELS)
prefix_dummies = list(PREFIX_LABELS)
pt_dummies = [c for c in df.columns if c.startswith("pt_")]

ologit_covars = [
    "is_residential",
    "is_mixed_use",
    "is_nonresidential",
    "log_square_footage",
    "log_square_footage_missing",
    "height",
    "height_missing",
    "log2_support",
    "log2_oppose",
    "agenda_order",
    "num_agenda_items",
    "is_consent_calendar",
]


def univ_auc(x: np.ndarray, y: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    mask = np.isfinite(x)
    if mask.sum() < 20 or np.nanstd(x[mask]) == 0:
        return np.nan
    auc = roc_auc_score(y[mask], x[mask])
    return max(auc, 1.0 - auc)


def univariate_row(name: str, x: pd.Series) -> dict:
    xv = to_float(x)
    mask = xv.notna()
    xm = xv[mask].to_numpy()
    ym = y[mask.to_numpy()]
    auc = univ_auc(xm, ym)
    is_bin = set(pd.unique(xm)).issubset({0.0, 1.0})
    row = {
        "variable": name,
        "label": label_of(name),
        "auc": auc,
        "n": int(mask.sum()),
        "kind": "binary" if is_bin else "continuous",
    }
    if is_bin:
        on = xm == 1.0
        n_on = int(on.sum())
        p_on = float(ym[on].mean()) if n_on else np.nan
        p_off = float(ym[~on].mean()) if (~on).any() else np.nan
        share_c1 = float(xm[ym == 1].mean()) if (ym == 1).any() else np.nan
        share_not = float(xm[ym == 0].mean()) if (ym == 0).any() else np.nan
        row.update(
            n_on=n_on,
            p_cluster1_if_on=p_on,
            p_cluster1_if_off=p_off,
            lift=p_on - base_rate,
            share_of_cluster1=share_c1,
            share_of_not_cluster1=share_not,
            mean_cluster1=np.nan,
            mean_not=np.nan,
            smd=np.nan,
        )
    else:
        m1 = float(np.mean(xm[ym == 1]))
        m0 = float(np.mean(xm[ym == 0]))
        sd = float(np.std(xm, ddof=1))
        row.update(
            n_on=np.nan,
            p_cluster1_if_on=np.nan,
            p_cluster1_if_off=np.nan,
            lift=np.nan,
            share_of_cluster1=np.nan,
            share_of_not_cluster1=np.nan,
            mean_cluster1=m1,
            mean_not=m0,
            smd=(m1 - m0) / sd if sd > 0 else np.nan,
        )
    return row


candidate_vars = sfx_grp + sfx_freq + struct + prefix_dummies + pt_dummies
univ_rows = [univariate_row(v, df[v]) for v in candidate_vars if v in df.columns]
univ = pd.DataFrame(univ_rows).sort_values("auc", ascending=False)
univ.to_csv(OUT_DIR / "univariate.csv", index=False)
univ.to_parquet(OUT_DIR / "univariate.parquet", index=False)


# ---- Grouped CV AUC ---------------------------------------------------------

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)


def X_of(cols):
    return np.column_stack([to_float(df[c]).fillna(0.0).to_numpy() for c in cols])


def cv_auc(cols, C=1.0):
    if not cols:
        return 0.5
    X = X_of(cols)
    pipe = make_pipeline(
        StandardScaler(with_mean=True, with_std=True),
        LogisticRegression(max_iter=4000, C=C, solver="lbfgs"),
    )
    scores = cross_val_score(pipe, X, y, cv=cv, scoring="roc_auc")
    return float(scores.mean()), float(scores.std())


groups = [
    ("Suffix groups", sfx_grp),
    ("Frequent individual suffixes", sfx_freq),
    ("Project type (8 categories)", pt_dummies),
    ("Case prefix (CPC/DIR/VTT/ZA)", prefix_dummies),
    ("Ologit covariates (type/size/letters/hearing)", ologit_covars),
    ("Ologit project-type dummies only", ["is_residential", "is_mixed_use", "is_nonresidential"]),
    ("Physical size / missingness", ["log_square_footage", "log_square_footage_missing", "height", "height_missing"]),
    ("Letters and hearing process", ["log2_support", "log2_oppose", "agenda_order", "num_agenda_items", "is_consent_calendar", "is_appeal"]),
    ("Suffix groups + project type", sfx_grp + pt_dummies),
    ("Suffix groups + prefix + project type", sfx_grp + prefix_dummies + pt_dummies),
    ("Full structured set", sfx_grp + prefix_dummies + pt_dummies + ologit_covars + ["is_appeal", "num_requested_actions", "n_docs", "cd_CITYWIDE"]),
]

group_rows = []
for name, cols in groups:
    mu, sd = cv_auc(cols)
    group_rows.append({"group": name, "n_vars": len(cols), "cv_auc": mu, "cv_auc_sd": sd})
group_df = pd.DataFrame(group_rows).sort_values("cv_auc", ascending=False)
group_df.to_csv(OUT_DIR / "grouped_cv_auc.csv", index=False)
group_df.to_parquet(OUT_DIR / "grouped_cv_auc.parquet", index=False)


# ---- Statsmodels logit: suffix groups + ologit structural -------------------
# Drop project_type categories that perfectly separate (CUP / code amendment).
# Suffix groups do not perfectly separate, so coefficients are identified.

logit_vars = sfx_grp + ologit_covars + ["is_appeal"]
X_sm = sm.add_constant(pd.DataFrame({v: to_float(df[v]).fillna(0.0) for v in logit_vars}))
logit = sm.Logit(y, X_sm).fit(disp=False, cov_type="HC1")
margeff = logit.get_margeff(at="overall")
me = pd.DataFrame(
    {
        "variable": logit_vars,
        "label": [label_of(v) for v in logit_vars],
        "coef": logit.params[1:].to_numpy(),
        "se": logit.bse[1:].to_numpy(),
        "z": logit.tvalues[1:].to_numpy(),
        "p": logit.pvalues[1:].to_numpy(),
        "ame": margeff.margeff,
        "ame_se": margeff.margeff_se,
        "ame_p": margeff.pvalues,
    }
)
me["ame_abs"] = me["ame"].abs()
me = me.sort_values("ame_abs", ascending=False)
me.to_csv(OUT_DIR / "logit_ame.csv", index=False)
me.to_parquet(OUT_DIR / "logit_ame.parquet", index=False)

pseudo_r2 = 1.0 - logit.llf / logit.llnull


# ---- Random forest permutation importance -----------------------------------

rf_vars = sfx_grp + prefix_dummies + pt_dummies + ologit_covars + ["is_appeal", "num_requested_actions", "n_docs"]
X_rf = X_of(rf_vars)
rf = RandomForestClassifier(
    n_estimators=500,
    max_depth=8,
    min_samples_leaf=8,
    random_state=42,
    n_jobs=-1,
)
rf.fit(X_rf, y)
rf_in_auc = float(roc_auc_score(y, rf.predict_proba(X_rf)[:, 1]))
rf_cv = float(cross_val_score(rf, X_rf, y, cv=cv, scoring="roc_auc").mean())

perm = permutation_importance(
    rf, X_rf, y, n_repeats=30, random_state=42, scoring="roc_auc", n_jobs=-1
)
perm_df = pd.DataFrame(
    {
        "variable": rf_vars,
        "label": [label_of(v) for v in rf_vars],
        "importance": perm.importances_mean,
        "importance_sd": perm.importances_std,
    }
).sort_values("importance", ascending=False)
perm_df.to_csv(OUT_DIR / "rf_permutation_importance.csv", index=False)
perm_df.to_parquet(OUT_DIR / "rf_permutation_importance.parquet", index=False)


# ---- Composition tables -----------------------------------------------------

pt_tab = (
    pd.crosstab(df["project_type"], df["cluster"], margins=True)
    .reset_index()
    .rename(columns={0: "cluster_0", 1: "cluster_1", 2: "cluster_2"})
)
pt_share = pd.crosstab(df["project_type"], df["cluster"], normalize="index")
pt_tab["p_cluster1"] = pt_tab["project_type"].map(pt_share[1]).fillna(np.nan)
# margin row
pt_tab.loc[pt_tab["project_type"] == "All", "p_cluster1"] = base_rate
pt_tab.to_csv(OUT_DIR / "project_type_by_cluster.csv", index=False)

prefix_tab = pd.crosstab(df["prefix"], df["cluster"], margins=True).reset_index()
prefix_tab.to_csv(OUT_DIR / "prefix_by_cluster.csv", index=False)

sfx_comp = univ[univ["variable"].isin(sfx_grp)].copy()
sfx_comp.to_csv(OUT_DIR / "suffix_group_univariate.csv", index=False)

# Simple rules
rules = []
for name, mask in [
    ("project_type is CODE OR PLAN AMENDMENT", df["project_type"] == "CODE OR PLAN AMENDMENT"),
    ("project_type is CONDITIONAL USE PERMIT", df["project_type"] == "CONDITIONAL USE PERMIT"),
    ("either of the two above", df["project_type"].isin(["CODE OR PLAN AMENDMENT", "CONDITIONAL USE PERMIT"])),
    ("sfx_grp_CPA", df["sfx_grp_CPA"].astype(bool)),
    ("sfx_grp_IP", df["sfx_grp_IP"].astype(bool)),
    ("not sfx_grp_IP", ~df["sfx_grp_IP"].astype(bool)),
    ("is_nonresidential", df["is_nonresidential"].astype(bool)),
    ("prefix DIR", df["prefix"] == "DIR"),
    ("prefix VTT", df["prefix"] == "VTT"),
    ("sfx_CA", df["sfx_CA"].astype(bool)),
    ("sfx_TOC or sfx_DB or sfx_HCA or sfx_VHCA", df[["sfx_TOC", "sfx_DB", "sfx_HCA", "sfx_VHCA"]].any(axis=1)),
]:
    m = mask.to_numpy()
    rules.append(
        {
            "rule": name,
            "n": int(m.sum()),
            "n_cluster1": int(((y == 1) & m).sum()),
            "precision_cluster1": float(y[m].mean()) if m.any() else np.nan,
            "recall_cluster1": float(m[y == 1].mean()) if (y == 1).any() else np.nan,
        }
    )
rules_df = pd.DataFrame(rules)
rules_df.to_csv(OUT_DIR / "simple_rules.csv", index=False)


# ---- Figure: top univariate AUCs --------------------------------------------

plot = univ.dropna(subset=["auc"]).head(18).iloc[::-1]
fig, ax = plt.subplots(figsize=(8.2, 6.8))
ax.barh(plot["label"], plot["auc"], color="#3b6ea5")
ax.axvline(0.5, color="gray", linewidth=0.8, linestyle="--")
ax.set_xlabel("Univariate AUC for cluster 1 (max(AUC, 1−AUC))")
ax.set_xlim(0.48, 1.02)
ax.set_title("Variables most associated with embedding cluster 1")
fig.tight_layout()
fig.savefig(OUT_DIR / "univariate_auc.png", dpi=150)
plt.close(fig)


# ---- Summary json-ish table for the report ----------------------------------

summary = pd.DataFrame(
    [
        {"stat": "n", "value": n},
        {"stat": "n_cluster1", "value": int(y.sum())},
        {"stat": "share_cluster1", "value": base_rate},
        {"stat": "logit_pseudo_r2_sfx_plus_ologit", "value": float(pseudo_r2)},
        {"stat": "rf_cv_auc", "value": rf_cv},
        {"stat": "rf_in_sample_auc", "value": rf_in_auc},
        {"stat": "cv_auc_suffix_groups", "value": float(group_df.loc[group_df.group == "Suffix groups", "cv_auc"].iloc[0])},
        {"stat": "cv_auc_project_type", "value": float(group_df.loc[group_df.group == "Project type (8 categories)", "cv_auc"].iloc[0])},
        {"stat": "cv_auc_ologit_covars", "value": float(group_df.loc[group_df.group == "Ologit covariates (type/size/letters/hearing)", "cv_auc"].iloc[0])},
        {"stat": "cv_auc_full", "value": float(group_df.loc[group_df.group == "Full structured set", "cv_auc"].iloc[0])},
    ]
)
summary.to_csv(OUT_DIR / "summary_stats.csv", index=False)

print("N =", n, " cluster 1 =", int(y.sum()), f"({base_rate:.3f})")
print("\nTop univariate AUCs:")
print(univ[["label", "auc", "kind", "n_on", "p_cluster1_if_on", "lift", "share_of_cluster1", "smd"]].head(20).to_string(index=False))
print("\nGrouped 5-fold CV AUC:")
print(group_df.to_string(index=False))
print("\nLogit AMEs (suffix groups + ologit covars + appeal):")
print(me[["label", "ame", "ame_se", "ame_p"]].head(15).to_string(index=False))
print(f"\nMcFadden pseudo-R2 = {pseudo_r2:.3f}")
print("\nRF permutation importance (top 15):")
print(perm_df.head(15).to_string(index=False))
print(f"RF CV AUC = {rf_cv:.3f}")
print("\nSimple rules:")
print(rules_df.to_string(index=False))
print("\nWrote", OUT_DIR)
