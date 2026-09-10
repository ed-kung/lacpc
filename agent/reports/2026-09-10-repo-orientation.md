# Repo orientation

Read the Cursor rules, README, paper, and source layout to confirm what this repository is for. No analysis was run and no data files were modified.

This repo is the research codebase for *How Bureaucratic Capacity Shapes Regulatory Outcomes: Evidence from Land Use in Los Angeles* (Gabriel, Histen, and Kung). It studies Los Angeles City Planning Commission (CPC) hearings from 2018–2026. Public agendas, minutes, and supplemental documents are scraped, converted to text, and encoded with LLMs into a structured dataset of development decisions. The main empirical claim is that delay—not denial—is the salient CPC outcome, and that public opposition and process frictions (agenda order, consent calendar, case atypicality from text embeddings) predict delay more than project size or type. The paper is compiled from `00main.tex`.

The numbered notebooks in `src/notebooks/` are the main pipeline: download PDFs, extract text, split documents, LLM-summarize agendas/minutes/supplemental docs, build analysis data, compute embeddings and atypicality, then estimate ordered logits in R (`src/R/15-ordered-logit.R` and related scripts). Python helpers live in `src/python/` (LLM clients, scrapers, distance/cluster construction, table cleanup). `evals/` holds LLM extraction checks. `agent/src/` and `agent/reports/` are empty placeholders for agent work.

## Artifacts

None.
