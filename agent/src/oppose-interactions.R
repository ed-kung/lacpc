# Explore whether covariates moderate the effect of public opposition
# (log2_oppose) in the preferred ordered logit from src/R/15-ordered-logit.R.
#
# A positive interaction with log2_oppose means the moderator *mitigates*
# the opposition penalty (outcome is 0=delay/deny, 2=full approval).
# A negative interaction means the moderator *amplifies* that penalty.

rm(list = ls())

library(dplyr)
library(yaml)
library(arrow)
library(MASS)
library(broom)
library(ggplot2)

this_file <- function() {
  cmd_args <- commandArgs(trailingOnly = FALSE)
  match <- grep("^--file=", cmd_args, value = TRUE)
  if (length(match) > 0) {
    return(normalizePath(sub("^--file=", "", match)))
  }
  normalizePath("oppose-interactions.R")
}

ROOT <- normalizePath(file.path(dirname(this_file()), "../.."))
LOCAL_CONFIG <- read_yaml(file.path(ROOT, "config.local.yaml"))
DATA_PATH <- LOCAL_CONFIG[["DATA_PATH"]]
AGENT_DATA_PATH <- LOCAL_CONFIG[["AGENT_DATA_PATH"]]
OUT_DIR <- file.path(AGENT_DATA_PATH, "oppose_interactions")
dir.create(OUT_DIR, recursive = TRUE, showWarnings = FALSE)

INPUT_FILEPATH <- file.path(DATA_PATH, "intermediate_data/cpc/ologit_regression_data.parquet")


# ---- Helpers -----------------------------------------------------------------

build_fmla <- function(yvar, covars) {
  covars_fmla <- if (length(covars) > 0) paste(covars, collapse = " + ") else "1"
  as.formula(paste(yvar, "~", covars_fmla))
}

p_from_t <- function(stat) {
  2 * pnorm(-abs(stat))
}

stars <- function(p) {
  ifelse(is.na(p), "",
         ifelse(p < 0.01, "***",
                ifelse(p < 0.05, "**",
                       ifelse(p < 0.1, "*", ""))))
}

tidy_polr <- function(reg) {
  td <- tidy(reg)
  td$p.value <- p_from_t(td$statistic)
  td
}

fit_polr <- function(covars, data) {
  fmla <- build_fmla("outcome", covars)
  tryCatch(
    polr(fmla, data = data, Hess = TRUE),
    error = function(e) {
      message("polr failed: ", conditionMessage(e))
      NULL
    }
  )
}

ll <- function(reg) as.numeric(logLik(reg))


# ---- Data (mirrors first part of 15-ordered-logit.R) ------------------------

df <- read_parquet(INPUT_FILEPATH)

df$outcome_y <- df$outcome
df$outcome <- as.factor(df$outcome)

df$cluster_fe1 <- as.numeric(df$cluster == 1)
df$cluster_fe2 <- as.numeric(df$cluster == 2)
df$is_consent_calendar <- as.numeric(df$is_consent_calendar)
df$is_residential <- as.numeric(df$is_residential)
df$is_mixed_use <- as.numeric(df$is_mixed_use)
df$is_nonresidential <- as.numeric(df$is_nonresidential)

for (v in c("sfx_TOC", "sfx_DB", "sfx_HCA", "sfx_grp_IP")) {
  df[[v]] <- as.numeric(df[[v]])
}

project_type <- c("is_residential", "is_mixed_use", "is_nonresidential")
physical <- c("log_square_footage", "log_square_footage_missing", "height", "height_missing")
letters <- c("log2_support", "log2_oppose")
hearing <- c("agenda_order", "num_agenda_items", "is_consent_calendar")
atypicality <- c("atypicality")
cluster_fe <- c("cluster_fe1", "cluster_fe2")
sfx_fe <- grep("^sfx_grp_", names(df), value = TRUE)[-1]
cd_fe <- paste0("cd_", 1:15)
yr_fe <- paste0("yr_", 2019:2026)

base_covars <- c(
  project_type, physical, letters, hearing, atypicality,
  sfx_fe, cd_fe, yr_fe, cluster_fe
)

rnull <- polr(outcome ~ 1, data = df)
null_LL <- ll(rnull)

r_base <- fit_polr(base_covars, df)
if (is.null(r_base)) stop("Baseline preferred specification failed to estimate.")
base_LL <- ll(r_base)

cat("\nBaseline log2_oppose (preferred spec r4):\n")
print(tidy_polr(r_base)[tidy_polr(r_base)$term == "log2_oppose", ])
cat("Baseline n =", nobs(r_base), "  McFadden pseudo-R2 =", 1 - base_LL / null_LL, "\n")


# ---- Candidate moderators ----------------------------------------------------
# Variables from the preferred specification, plus incentive-program suffixes
# that constrain CPC discretion. Continuous moderators are demeaned in the
# product term so log2_oppose is the slope at the sample mean of M.

candidates <- list(
  list(name = "log2_support", label = "Public support (log2)", already_in = TRUE, center = TRUE, type = "continuous"),
  list(name = "is_consent_calendar", label = "Consent calendar", already_in = TRUE, center = FALSE, type = "binary"),
  list(name = "agenda_order", label = "Agenda order", already_in = TRUE, center = TRUE, type = "continuous"),
  list(name = "num_agenda_items", label = "Number of agenda items", already_in = TRUE, center = TRUE, type = "continuous"),
  list(name = "atypicality", label = "Atypicality", already_in = TRUE, center = TRUE, type = "continuous"),
  list(name = "is_residential", label = "Residential", already_in = TRUE, center = FALSE, type = "binary"),
  list(name = "is_mixed_use", label = "Mixed-use", already_in = TRUE, center = FALSE, type = "binary"),
  list(name = "is_nonresidential", label = "Non-residential", already_in = TRUE, center = FALSE, type = "binary"),
  list(name = "log_square_footage", label = "Log square footage", already_in = TRUE, center = TRUE, type = "continuous"),
  list(name = "height", label = "Height (ft)", already_in = TRUE, center = TRUE, type = "continuous"),
  list(name = "sfx_grp_IP", label = "Incentive-program suffix group", already_in = TRUE, center = FALSE, type = "binary"),
  list(name = "sfx_TOC", label = "Transit Oriented Communities", already_in = FALSE, center = FALSE, type = "binary"),
  list(name = "sfx_DB", label = "Density Bonus", already_in = FALSE, center = FALSE, type = "binary"),
  list(name = "sfx_HCA", label = "Housing Crisis Act", already_in = FALSE, center = FALSE, type = "binary"),
  list(name = "cluster_fe1", label = "Embedding cluster 1", already_in = TRUE, center = FALSE, type = "binary"),
  list(name = "cluster_fe2", label = "Embedding cluster 2", already_in = TRUE, center = FALSE, type = "binary")
)


# ---- One-at-a-time interactions ---------------------------------------------

int_rows <- list()
simple_slope_rows <- list()

for (cand in candidates) {
  m <- cand$name
  int_name <- paste0("oppose_X_", m)
  x <- as.numeric(df[[m]])
  x_for_prod <- if (isTRUE(cand$center)) x - mean(x, na.rm = TRUE) else x
  df[[int_name]] <- df$log2_oppose * x_for_prod

  extra <- if (isTRUE(cand$already_in)) character(0) else m
  covars <- unique(c(base_covars, extra, int_name))

  reg <- fit_polr(covars, df)
  if (is.null(reg)) {
    message("Skipping ", m, " (did not converge)")
    next
  }

  td <- tidy_polr(reg)
  int_hit <- td[td$term == int_name, ]
  opp_hit <- td[td$term == "log2_oppose", ]

  n_added <- 1 + as.integer(!isTRUE(cand$already_in))
  lr_stat <- 2 * (ll(reg) - base_LL)
  lr_p <- pchisq(lr_stat, df = n_added, lower.tail = FALSE)

  row <- data.frame(
    moderator = m,
    label = cand$label,
    type = cand$type,
    centered = isTRUE(cand$center),
    oppose_est = if (nrow(opp_hit)) opp_hit$estimate else NA_real_,
    oppose_se = if (nrow(opp_hit)) opp_hit$std.error else NA_real_,
    oppose_p = if (nrow(opp_hit)) opp_hit$p.value else NA_real_,
    interaction_est = if (nrow(int_hit)) int_hit$estimate else NA_real_,
    interaction_se = if (nrow(int_hit)) int_hit$std.error else NA_real_,
    interaction_t = if (nrow(int_hit)) int_hit$statistic else NA_real_,
    interaction_p = if (nrow(int_hit)) int_hit$p.value else NA_real_,
    lr_stat = lr_stat,
    lr_df = n_added,
    lr_p = lr_p,
    nobs = nobs(reg),
    pseudo_r2 = 1 - ll(reg) / null_LL,
    stringsAsFactors = FALSE
  )
  int_rows[[length(int_rows) + 1]] <- row

  if (cand$type == "binary") {
    slope0 <- row$oppose_est
    se0 <- row$oppose_se
    slope1 <- row$oppose_est + row$interaction_est
    vc <- vcov(reg)
    if (all(c("log2_oppose", int_name) %in% rownames(vc))) {
      se1 <- sqrt(vc["log2_oppose", "log2_oppose"] +
                    vc[int_name, int_name] +
                    2 * vc["log2_oppose", int_name])
    } else {
      se1 <- NA_real_
    }
    share1 <- mean(x, na.rm = TRUE)
    simple_slope_rows[[length(simple_slope_rows) + 1]] <- data.frame(
      moderator = m, label = cand$label, at = "M=0", at_value = 0,
      share = 1 - share1, slope = slope0, se = se0,
      p.value = p_from_t(slope0 / se0), stringsAsFactors = FALSE
    )
    simple_slope_rows[[length(simple_slope_rows) + 1]] <- data.frame(
      moderator = m, label = cand$label, at = "M=1", at_value = 1,
      share = share1, slope = slope1, se = se1,
      p.value = p_from_t(slope1 / se1), stringsAsFactors = FALSE
    )
  } else {
    sdx <- sd(x, na.rm = TRUE)
    mx <- mean(x, na.rm = TRUE)
    vc <- vcov(reg)
    for (k in c(-1, 0, 1)) {
      slope <- row$oppose_est + k * sdx * row$interaction_est
      if (all(c("log2_oppose", int_name) %in% rownames(vc))) {
        se <- sqrt(vc["log2_oppose", "log2_oppose"] +
                     (k * sdx)^2 * vc[int_name, int_name] +
                     2 * k * sdx * vc["log2_oppose", int_name])
      } else {
        se <- NA_real_
      }
      lab <- if (k == 0) "mean(M)" else if (k < 0) "mean(M)-1 SD" else "mean(M)+1 SD"
      simple_slope_rows[[length(simple_slope_rows) + 1]] <- data.frame(
        moderator = m, label = cand$label, at = lab, at_value = mx + k * sdx,
        share = NA_real_, slope = slope, se = se,
        p.value = p_from_t(slope / se), stringsAsFactors = FALSE
      )
    }
  }
}

int_df <- bind_rows(int_rows)
int_df$interaction_p_bh <- p.adjust(int_df$interaction_p, method = "BH")
int_df$interaction_stars <- stars(int_df$interaction_p)
int_df$mitigates <- int_df$interaction_est > 0
int_df <- int_df[order(int_df$interaction_p), ]

slopes_df <- bind_rows(simple_slope_rows)

write_parquet(int_df, file.path(OUT_DIR, "one_at_a_time_interactions.parquet"))
write_parquet(slopes_df, file.path(OUT_DIR, "simple_slopes.parquet"))
write.csv(int_df, file.path(OUT_DIR, "one_at_a_time_interactions.csv"), row.names = FALSE)
write.csv(slopes_df, file.path(OUT_DIR, "simple_slopes.csv"), row.names = FALSE)

cat("\n===== One-at-a-time interactions with log2_oppose =====\n")
print(int_df[, c("label", "interaction_est", "interaction_se", "interaction_p",
                 "interaction_p_bh", "lr_p", "mitigates")], row.names = FALSE)

cat("\n===== Simple slopes =====\n")
print(slopes_df, row.names = FALSE)


# ---- Coefficient plot -------------------------------------------------------

plot_df <- int_df %>%
  mutate(
    lo = interaction_est - 1.96 * interaction_se,
    hi = interaction_est + 1.96 * interaction_se,
    label = factor(label, levels = rev(label[order(interaction_p)]))
  )

p <- ggplot(plot_df, aes(x = interaction_est, y = label)) +
  geom_vline(xintercept = 0, linetype = "dashed", color = "grey40") +
  geom_point(aes(color = interaction_p < 0.05), size = 2.4) +
  geom_errorbar(aes(xmin = lo, xmax = hi, color = interaction_p < 0.05),
                width = 0.2, orientation = "y") +
  scale_color_manual(values = c("FALSE" = "grey50", "TRUE" = "#b2182b"),
                     labels = c("p >= 0.05", "p < 0.05"),
                     name = NULL) +
  labs(
    x = "Interaction coefficient (log2_oppose x moderator)",
    y = NULL,
    title = "Does the covariate moderate public opposition?",
    subtitle = "Positive = mitigates opposition penalty; negative = amplifies. 95% CIs."
  ) +
  theme_bw(base_size = 12) +
  theme(legend.position = "bottom")

ggsave(file.path(OUT_DIR, "interaction_coefs.png"), p, width = 8.5, height = 6.5, dpi = 150)

cat("\nWrote artifacts to ", OUT_DIR, "\n", sep = "")
