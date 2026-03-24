rm(list=ls())

library(dplyr)
library(yaml)
library(arrow)
library(MASS)
library(stargazer)
library(broom)


LOCAL_CONFIG <- read_yaml("../../config.local.yaml")
LOCAL_PATH <- LOCAL_CONFIG["LOCAL_PATH"][[1]]
DATA_PATH <- LOCAL_CONFIG["DATA_PATH"][[1]]

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
extract_reg <- function(reg, reg_name) {
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
    coef_name = c("num_obs"),
    estimate = c(reg$nobs),
    serr = NA_real_
  )
  return(rbind(coef_df, stats_df))
}



# ---- Data loading and cleaning

in_filename <- paste0(DATA_PATH, "/intermediate_data/cpc/ologit_regression_data.parquet")

df <- read_parquet(in_filename)

df$outcome <- as.factor(df$outcome)


# ---- Run regressions

vars1 <- c("mahalanobis")
vars2 <- c("agenda_order", "num_agenda_items", "is_consent_calendar", 
           "log2_support", "log2_oppose")
cluster_fe <- c("as.factor(cluster)")
cd_fe <- paste0("cd_", 1:15)
sfx_fe <- grep("^sfx_", names(df), value = TRUE)[-1]

r1 <- polr(
  build_fmla("outcome", vars1),
  data=df, Hess=TRUE
)
r2 <- polr(
  build_fmla("outcome", c(vars1,vars2,cluster_fe)),
  data=df, Hess=TRUE
)
r3 <- polr(
  build_fmla("outcome", c(vars1,vars2,cluster_fe,cd_fe)),
  data=df, Hess=TRUE
)
r4 <- polr(
  build_fmla("outcome", c(vars1,vars2,cluster_fe,cd_fe,sfx_fe)),
  data=df, Hess=TRUE
)

stargazer(
  r1, r2, r3, r4, type="text",
  keep=c(vars1, vars2),
  add.lines=list(
    c("Cluster FE",          "N", "Y", "Y", "Y"),
    c("Council District FE", "N", "N", "Y", "Y"),
    c("Case Suffix FE",      "N", "N", "N", "Y")
  )
)

coefs_df <- rbind(
  extract_reg(r1, "r1"),
  extract_reg(r2, "r2"),
  extract_reg(r3, "r3"),
  extract_reg(r4, "r4")
)

out_filename <- paste0(DATA_PATH, "/intermediate_data/cpc/ologit_regression_coefs.parquet")
write_parquet(coefs_df, out_filename)


