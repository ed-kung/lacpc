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


# ---- Helper functions

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
extract_reg <- function(reg, reg_name, null_LL=NA) {
  # coefficients
  tidy_df <- tidy(reg)
  coef_df <- data.frame(
    regression_name = reg_name, 
    coef_name = tidy_df$term,
    estimate = tidy_df$estimate,
    serr = tidy_df$std.error
  )
  # stats
  if (is.na(null_LL)) {
    r2 <- summary(reg)$r.squared
  } else {
    r2 <- 1 - as.numeric(logLik(reg))/null_LL
  }
  stats_df <- data.frame(
    regression_name = reg_name,
    coef_name = c("num_obs", "r2"),
    estimate = c(nobs(reg), r2),
    serr = NA_real_
  )
  return(rbind(coef_df, stats_df))
}




# ---- Data loading and cleaning

df <- read_parquet(INPUT_FILEPATH)

df$log2_support_po <- log2(df$n_support_po + 1)

df$outcome_y <- df$outcome
df$outcome <- as.factor(df$outcome)

df$cluster_fe1 <- df$cluster==1
df$cluster_fe2 <- df$cluster==2

# ---- Run regressions

project_type <- c("is_residential", "is_mixed_use", "is_nonresidential")
physical <- c("log_square_footage", "log_square_footage_missing", "height", "height_missing")
time_factors <- c("weeks_til_due", "weeks_til_due_missing")
hearing <- c("agenda_order", "num_agenda_items", "is_consent_calendar")
letters <- c("log2_support", "log2_oppose")
letters2 <- c("log2_support", "log2_support_po", "log2_oppose")
atypicality <- c("atypicality")

cluster_fe <- c("cluster_fe1", "cluster_fe2")
sfx_fe <- grep("^sfx_grp_", names(df), value = TRUE)[-1]
cd_fe <- paste0("cd_", 1:15)
yr_fe <- paste0("yr_", 2019:2026)

keepvars <- c(
  project_type,
  c("log_square_footage", "height"),
  letters2,
  atypicality,
  hearing,
  time_factors
)

rnull <- polr(outcome ~ 1, data=df)
null_LL <- as.numeric(logLik(rnull))

r1 <- polr(
  build_fmla("outcome", c(project_type, physical, letters, hearing, time_factors, atypicality, sfx_fe, cd_fe, yr_fe, cluster_fe)),
  data=df, Hess=TRUE
) # reproduction of main ologit specification

r2 <- polr(
  build_fmla("outcome", c(project_type, physical, letters2, time_factors, atypicality, sfx_fe, cd_fe, yr_fe, cluster_fe)),
  data=df, Hess=TRUE
) # main specification but without potentially endogenous agenda setting

r3 <- glm(
  build_fmla("is_consent_calendar", c(project_type, physical, letters2, time_factors, atypicality, sfx_fe, cd_fe, yr_fe, cluster_fe)),
  data=df, family=binomial(link="logit")
)

r4 <- lm(
  build_fmla("agenda_order", c(project_type, physical, letters2, time_factors, atypicality, sfx_fe, cd_fe, yr_fe, cluster_fe)),
  data=filter(df, !is_consent_calendar)
)


stargazer(
  r1, r2, r3, r4,
  type="text",
  keep=keepvars,
  add.lines=list(
    c("Suffix Group Dummies",      "Y", "Y", "Y", "Y"),
    c("Council District Dummies",  "Y", "Y", "Y", "Y"),
    c("Year Dummies",              "Y", "Y", "Y", "Y"),
    c("Embedding Cluster Dummies", "Y", "Y", "Y", "Y")
  )
)

# note: coefficient on atypicality goes down from r1 to r2
# suggests that some atypical cases are on the consent calendar, thus not 
# including consent calendar in the regression is masking the effect of 
# being atypical AND not on the consent calendar (r3 bears this out)
# (Why would some atypical cases be on the consent calendar; they may be
# atypical but not controversial?)

coefs_df <- rbind(
  extract_reg(r1, "r1", null_LL),
  extract_reg(r2, "r2", null_LL),
  extract_reg(r3, "r3", null_LL),
  extract_reg(r4, "r4", NA)
)

out_filename <- paste0(DATA_PATH, "/intermediate_data/cpc/endogenous_agenda_coefs.parquet")
write_parquet(coefs_df, out_filename)

