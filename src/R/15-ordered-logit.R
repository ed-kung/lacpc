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
    estimate = c(nobs(reg)),
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

atypicality <- c("atypicality", "cluster_fe1", "cluster_fe2")
project_type <- c("is_residential", "is_nonresidential")
letters <- c("log2_support", "log2_oppose")
hearing <- c("agenda_order", "num_agenda_items", "is_consent_calendar")
physical <- c("log_square_footage", "log_square_footage_missing", "height", "height_missing")
sfx_fe <- grep("^sfx_grp_", names(df), value = TRUE)[-1]

r1 <- polr(
  build_fmla("outcome", c(project_type, physical)),
  data=df, Hess=TRUE
)
r2 <- polr(
  build_fmla("outcome", c(project_type, physical, sfx_fe)),
  data=df, Hess=TRUE
)
r3 <- polr(
  build_fmla("outcome", c(project_type, physical, sfx_fe, letters, hearing)),
  data=df, Hess=TRUE
)
r4 <- polr(
  build_fmla("outcome", c(project_type, physical, sfx_fe, letters, hearing, atypicality)),
  data=df, Hess=TRUE
)
r5 <- polr(
  build_fmla("outcome", c(project_type, physical, sfx_fe, atypicality)),
  data=df, Hess=TRUE
)
r6 <- polr(
  build_fmla("outcome", c(project_type, physical, atypicality)),
  data=df, Hess=TRUE
)
r7 <- polr(
  build_fmla("outcome", c(atypicality)),
  data=df, Hess=TRUE
)




stargazer(r1, r2, r3, r4, r5, r6, r7, type="text")


vars1 <- c("atypicality")
vars2 <- c("agenda_order", "num_agenda_items", "is_consent_calendar", 
           "log2_support", "log2_oppose")
cluster_fe <- c("cluster_fe1", "cluster_fe2")
cd_fe <- paste0("cd_", 1:15)

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
  keep=c(vars1, vars2, cluster_fe, cd_fe, sfx_fe),
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


# ---- Oster (2019) robustness check

short_reg <- lm(
  build_fmla("outcome_y", vars1), 
  data = df
)
controlled_reg <- lm(
  build_fmla("outcome_y", c(vars1, vars2, cluster_fe, cd_fe, sfx_fe)),
  data = df
)
Rmax <- min(1.3*summary(controlled_reg)$r.squared, 1)


oster_delta <- o_delta(
  y = "outcome_y", 
  x = "atypicality",
  con = paste0(c(vars2, cluster_fe, cd_fe, sfx_fe), collapse=" + "),
  beta = 0,
  R2max = Rmax,
  type = "lm",
  data = df
)

out_filename <- paste0(DATA_PATH, "/intermediate_data/cpc/ologit_oster_delta.parquet")
write_parquet(oster_delta, out_filename)


# ---- Marginals

m1 <- avg_slopes(r1)
m1$regression_name <- "r1"
m2 <- avg_slopes(r2)
m2$regression_name <- "r2"
m3 <- avg_slopes(r3)
m3$regression_name <- "r3"
m4 <- avg_slopes(r4)
m4$regression_name <- "r4"

marginals_df <- rbind(m1, m2, m3, m4)

out_filename <- paste0(DATA_PATH, "/intermediate_data/cpc/ologit_regression_marginals.parquet")
write_parquet(marginals_df, out_filename)



# ---- Regressions on non-delay outcomes

dfb <- filter(df, project_result!="DELAYED")

dfb$outcome <- dfb$outcome_y
dfb$outcome[dfb$outcome==1] <- 0
dfb$outcome[dfb$outcome==2] <- 1

dfb$log2_letters <- log2(1+dfb$n_support+dfb$n_oppose)

vars3 <- c("agenda_order", "num_agenda_items", "is_consent_calendar", 
           "log2_letters")

#sfx_fe_2 <- sfx_fe[sapply(df_nodelay[sfx_fe], var, na.rm=TRUE) != 0]

r1b <- glm(
  build_fmla("outcome", vars1),
  data=dfb, family=binomial(link="logit")
)
r2b <- glm(
  build_fmla("outcome", c(vars1,vars2,cluster_fe)),
  data=dfb, family=binomial(link="logit")
)
r3b <- glm(
  build_fmla("outcome", c(vars1,vars2,cluster_fe,cd_fe)),
  data=dfb, family=binomial(link="logit")
)
r4b <- glm(
  build_fmla("outcome", c(vars1,vars2,cluster_fe,cd_fe,sfx_fe)),
  data=dfb, family=binomial(link="logit")
)
r5b <- glm(
  build_fmla("outcome", c(vars1,vars3,cluster_fe,cd_fe,sfx_fe)),
  data=dfb, family=binomial(link="logit")
)

stargazer(
  r1b, r2b, r3b, r4b, r5b, type="text",
  keep=c(vars1, vars2, vars3),
  add.lines=list(
    c("Cluster FE",          "N", "Y", "Y", "Y", "Y"),
    c("Council District FE", "N", "N", "Y", "Y", "Y"),
    c("Case Suffix FE",      "N", "N", "N", "Y", "Y")
  )
)


coefs_df <- rbind(
  extract_reg(r1b, "r1b"),
  extract_reg(r2b, "r2b"),
  extract_reg(r3b, "r3b"),
  extract_reg(r4b, "r4b"),
  extract_reg(r5b, "r5b")
)

out_filename <- paste0(DATA_PATH, "/intermediate_data/cpc/ologit_regression_coefs_nodelay.parquet")
write_parquet(coefs_df, out_filename)
