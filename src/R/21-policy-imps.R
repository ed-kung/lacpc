rm(list=ls())

library(dplyr)
library(yaml)
library(arrow)
library(MASS)
library(stargazer)
library(broom)
library(marginaleffects)
library(robomit)


LOCAL_CONFIG <- read_yaml("../../config.local.yaml")
LOCAL_PATH <- LOCAL_CONFIG["LOCAL_PATH"][[1]]
DATA_PATH <- LOCAL_CONFIG["DATA_PATH"][[1]]
INPUT_FILEPATH <- paste0(DATA_PATH, "/intermediate_data/cpc/ologit_regression_data.parquet")

# ---- Helper functions --------------------------------------------------------

# building formulas
build_fmla <- function(yvar, covars) {
  if (length(covars)>0) {
    covars_fmla <- paste(covars, collapse = " + ")
  }
  else {
    covars_fmla <- "1"
  }
  as.formula(paste(yvar, " ~ ", covars_fmla))
}

# extracting regression results
extract_reg <- function(reg, reg_name, null_LL) {
  # coefficients
  tidy_df <- tidy(reg)
  coef_df <- data.frame(
    regression_name = reg_name, 
    coef_name = tidy_df$term,
    estimate = tidy_df$estimate,
    serr = tidy_df$std.error
  )
  # stats
  stats_df <- data.frame(
    regression_name = reg_name,
    coef_name = c("num_obs", "pseudo_r2"),
    estimate = c(nobs(reg), 1 - as.numeric(logLik(reg))/null_LL),
    serr = NA_real_
  )
  return(rbind(coef_df, stats_df))
}


# ---- Data loading and cleaning -----------------------------------------------

df <- read_parquet(INPUT_FILEPATH)

df$outcome_y <- df$outcome
df$outcome <- as.factor(df$outcome)

df$cluster_fe0 <- df$cluster==0
df$cluster_fe1 <- df$cluster==1
df$cluster_fe2 <- df$cluster==2

df$support_X_cluster0 <- df$log2_support * df$cluster_fe0
df$support_X_cluster1 <- df$log2_support * df$cluster_fe1
df$support_X_cluster2 <- df$log2_support * df$cluster_fe2

df$oppose_X_cluster0 <- df$log2_oppose * df$cluster_fe0
df$oppose_X_cluster1 <- df$log2_oppose * df$cluster_fe1
df$oppose_X_cluster2 <- df$log2_oppose * df$cluster_fe2

df$consent_calendar_X_cluster0 <- df$is_consent_calendar * df$cluster_fe0
df$consent_calendar_X_cluster1 <- df$is_consent_calendar * df$cluster_fe1
df$consent_calendar_X_cluster2 <- df$is_consent_calendar * df$cluster_fe2

df$order_X_cluster0 <- df$agenda_order * df$cluster_fe0
df$order_X_cluster1 <- df$agenda_order * df$cluster_fe1
df$order_X_cluster2 <- df$agenda_order * df$cluster_fe2

df$atypicality_X_cluster0 <- df$atypicality * df$cluster_fe0
df$atypicality_X_cluster1 <- df$atypicality * df$cluster_fe1
df$atypicality_X_cluster2 <- df$atypicality * df$cluster_fe2

# ---- Run regressions

project_type <- c("is_residential", "is_mixed_use", "is_nonresidential")
physical <- c("log_square_footage", "log_square_footage_missing", "height", "height_missing")
letters <- c("log2_support", "log2_oppose")
lettersX <- c("log2_support", "support_X_cluster1", "support_X_cluster2", "log2_oppose", "oppose_X_cluster1", "oppose_X_cluster2")
hearing <- c("agenda_order", "num_agenda_items", "is_consent_calendar")
hearingX <- c("agenda_order", "order_X_cluster1", "order_X_cluster2", "num_agenda_items", "is_consent_calendar", "consent_calendar_X_cluster1", "consent_calendar_X_cluster2")
atypicality <- c("atypicality")
atypicalityX <- c("atypicality", "atypicality_X_cluster1", "atypicality_X_cluster2")

cluster_fe <- c("cluster_fe1", "cluster_fe2")
sfx_fe <- grep("^sfx_grp_", names(df), value = TRUE)[-1]
cd_fe <- paste0("cd_", 1:15)
yr_fe <- paste0("yr_", 2019:2026)

keepvars <- c(
  project_type,
  c("log_square_footage", "height"),
  lettersX,
  hearingX,
  atypicalityX
)


# ---- Run main ologit regressions ---------------------------------------------

rnull <- polr(outcome ~ 1, data=df)
null_LL <- as.numeric(logLik(rnull))

r1 <- polr(
  build_fmla("outcome", c(project_type, physical, lettersX, hearing, atypicality, sfx_fe, cd_fe, yr_fe, cluster_fe)),
  data=df, Hess=TRUE
)
r2 <- polr(
  build_fmla("outcome", c(project_type, physical, letters, hearingX, atypicality, sfx_fe, cd_fe, yr_fe, cluster_fe)),
  data=df, Hess=TRUE
)
r3 <- polr(
  build_fmla("outcome", c(project_type, physical, letters, hearing, atypicalityX, sfx_fe, cd_fe, yr_fe, cluster_fe)),
  data=df, Hess=TRUE
)
r4 <- polr(
  build_fmla("outcome", c(project_type, physical, lettersX, hearingX, atypicalityX, sfx_fe, cd_fe, yr_fe, cluster_fe)),
  data=df, Hess=TRUE
)



stargazer(
  r1, r2, r3, r4,
  type="text",
  keep=keepvars
)

coefs_df <- rbind(
  extract_reg(r1, "r1", null_LL),
  extract_reg(r2, "r2", null_LL),
  extract_reg(r3, "r3", null_LL),
  extract_reg(r4, "r4", null_LL)
)

out_filename <- paste0(DATA_PATH, "/intermediate_data/cpc/policy_imps_coefs.parquet")
write_parquet(coefs_df, out_filename)
 
