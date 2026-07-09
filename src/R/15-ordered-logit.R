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



# ---- Data loading and cleaning

in_filename <- paste0(DATA_PATH, "/intermediate_data/cpc/ologit_regression_data.parquet")

df <- read_parquet(in_filename)

df$outcome_y <- df$outcome
df$outcome <- as.factor(df$outcome)

df$cluster_fe1 <- df$cluster==1
df$cluster_fe2 <- df$cluster==2

# ---- Run regressions

project_type <- c("is_residential", "is_mixed_use", "is_nonresidential")
physical <- c("log_square_footage", "log_square_footage_missing", "height", "height_missing")
letters <- c("log2_support", "log2_oppose")
hearing <- c("agenda_order", "num_agenda_items", "is_consent_calendar")
atypicality <- c("atypicality")

cluster_fe <- c("cluster_fe1", "cluster_fe2")
sfx_fe <- grep("^sfx_grp_", names(df), value = TRUE)[-1]
cd_fe <- paste0("cd_", 1:15)
yr_fe <- paste0("yr_", 2019:2026)

keepvars <- c(
  project_type,
  c("log_square_footage", "height"),
  letters,
  hearing,
  atypicality
)

rnull <- polr(outcome ~ 1, data=df)
null_LL <- as.numeric(logLik(rnull))

r1 <- polr(
  build_fmla("outcome", c(project_type, physical, letters, hearing, atypicality, sfx_fe)),
  data=df, Hess=TRUE
)
r2 <- polr(
  build_fmla("outcome", c(project_type, physical, letters, hearing, atypicality, sfx_fe, cd_fe)),
  data=df, Hess=TRUE
)
r3 <- polr(
  build_fmla("outcome", c(project_type, physical, letters, hearing, atypicality, sfx_fe, cd_fe, yr_fe)),
  data=df, Hess=TRUE
)
r4 <- polr(
  build_fmla("outcome", c(project_type, physical, letters, hearing, atypicality, sfx_fe, cd_fe, yr_fe, cluster_fe)),
  data=df, Hess=TRUE
)


stargazer(
  r1, r2, r3, r4,
  type="text",
  keep=keepvars,
  add.lines=list(
    c("Suffix Group Dummies",      "Y", "Y", "Y", "Y"),
    c("Council District Dummies",  "N", "Y", "Y", "Y"),
    c("Year Dummies",              "N", "N", "Y", "Y"),
    c("Embedding Cluster Dummies", "N", "N", "N", "Y")
  )
)


coefs_df <- rbind(
  extract_reg(r1, "r1", null_LL),
  extract_reg(r2, "r2", null_LL),
  extract_reg(r3, "r3", null_LL),
  extract_reg(r4, "r4", null_LL)
)

out_filename <- paste0(DATA_PATH, "/intermediate_data/cpc/ologit_regression_coefs.parquet")
write_parquet(coefs_df, out_filename)
 
 
# ---- Oster (2019) robustness check

vars1 <- c(atypicality)
vars2 <- c(project_type, physical, letters, hearing, sfx_fe, cd_fe, yr_fe, cluster_fe)

short_reg <- lm(
  build_fmla("outcome_y", vars1),
  data = df
)
controlled_reg <- lm(
  build_fmla("outcome_y", c(vars1, vars2)),
  data = df
)
Rmax <- min(1.3*summary(controlled_reg)$r.squared, 1)


oster_delta <- o_delta(
  y = "outcome_y",
  x = "atypicality",
  con = paste0(vars2, collapse=" + "),
  beta = 0,
  R2max = Rmax,
  type = "lm",
  data = df
)

out_filename <- paste0(DATA_PATH, "/intermediate_data/cpc/ologit_oster_delta.parquet")
write_parquet(oster_delta, out_filename)


# ---- Marginals

m4 <- avg_slopes(r4)
m4$regression_name <- "r4"

marginals_df <- m4
 
out_filename <- paste0(DATA_PATH, "/intermediate_data/cpc/ologit_regression_marginals.parquet")
write_parquet(marginals_df, out_filename)




# ---- Regressions on non-delay outcomes

dfb <- filter(df, project_result!="DELAYED")

dfb$outcome <- dfb$outcome_y
dfb$outcome[dfb$outcome==1] <- 0
dfb$outcome[dfb$outcome==2] <- 1

rnullb <- glm(outcome ~ 1, data=dfb, family=binomial(link="logit"))
nullb_LL <- as.numeric(logLik(rnullb))

r1b <- glm(
  build_fmla("outcome", c(project_type, physical, letters, hearing, atypicality, sfx_fe)),
  data=dfb, family=binomial(link="logit")
)
r2b <- glm(
  build_fmla("outcome", c(project_type, physical, letters, hearing, atypicality, sfx_fe, cd_fe)),
  data=dfb, family=binomial(link="logit")
)
r3b <- glm(
  build_fmla("outcome", c(project_type, physical, letters, hearing, atypicality, sfx_fe, cd_fe, yr_fe)),
  data=dfb, family=binomial(link="logit")
)
r4b <- glm(
  build_fmla("outcome", c(project_type, physical, letters, hearing, atypicality, sfx_fe, cd_fe, yr_fe, cluster_fe)),
  data=dfb, family=binomial(link="logit")
)

stargazer(
  r1b, r2b, r3b, r4b, type="text",
  keep=keepvars,
  add.lines=list(
    c("Suffix Group Dummies",      "Y", "Y", "Y", "Y"),
    c("Council District Dummies",  "N", "Y", "Y", "Y"),
    c("Year Dummies",              "N", "N", "Y", "Y"),
    c("Embedding Cluster Dummies", "N", "N", "N", "Y")
  )
)


coefs_df <- rbind(
  extract_reg(r1b, "r1b", nullb_LL),
  extract_reg(r2b, "r2b", nullb_LL),
  extract_reg(r3b, "r3b", nullb_LL),
  extract_reg(r4b, "r4b", nullb_LL)
)

out_filename <- paste0(DATA_PATH, "/intermediate_data/cpc/ologit_regression_coefs_nodelay.parquet")
write_parquet(coefs_df, out_filename)
