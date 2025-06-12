# City Planning Commission Documents

## Setup local config

Before starting, create a file named `config.local.yaml` containing:

```
LOCAL_PATH: "<path to this repo on your machine>"
OPENAI_API_KEY: "<your openai api key>"
PINECONE_API_KEY: "<your pinecone api key>"
CHROMEDRIVER: "<path to chromedriver>"
TESSERACT: "<path to your tesseract cmd>"
```

## Download the documents

`download-docs.ipynb`

Downloads the raw pdf documents. It can be run again to download any new documents which have been uploaded to the Planning Department website. By default, already downloaded documents won't be re-downloaded. You can change this by setting the `overwrite` flag in the notebook.

## Identify document boundaries for supplemental docs

`supplemental-docs-splits.csv`

Supplemental documents are spliced together in one giant PDF file. So far, I have found that existing LLMs are not great at identifying the document boundaries (I've tried ChatGPT, Claude, and Google NotebookLM). Thus, I've manually identified document boundaries and put them in `supplemental-docs-splits.csv`. This contains the page ranges of individual documents inside `supplemental-docs.pdf`, along with notes for whether the document contains attachments or a major report that should be ignored for analysis.

All page ranges not contained in this file are single page documents.

## Extract raw PDFs into text files

`extract-pdf-to-text.ipynb`

Extracts the PDF files into raw text documents, with pages separated by `<PAGE BREAK>`. Resulting text files are stored in `intermediate_data/cpc/<year>/<date>`.

## Create the list of meetings for analysis

`create-meetings-manifest.ipynb`

Creates a list of meetings that will be used for analysis. A meeting will be used for analysis if it contains all three of `agenda.pdf`, `minutes.pdf`, `supplemental-docs.pdf`, and has entries in `supplemental-docs-splits.csv`.

## Split the supplemental documents files

`split-supplemental-docs.ipynb`

Uses `supplemental-docs-splits.csv` to split `supplemental-docs.pdf` for all meetings contained in `meetings-manifest.csv`. Text content of each individual supplemental document is stored in `supplemental-docs.pkl`.

## Summarize agenda items

`summarize-agenda-items.ipynb`

Uses ChatGPT to summarize individual agenda items from the raw text. Responses are stored in `agenda-item-summaries.txt`.

## Split agenda items

`split-agenda-items.ipynb`

Parse the extracted summaries and split into individual agenda items. Store the results in a dataframe: `agenda-items.pkl`.

## Split minutes items

`split-minutes-items.ipynb`

Generates two files: `minutes.pkl` and `minutes-items.pkl`.

`minutes.pkl` is the split of the raw minutes text into individual items, showing the start and end line of each split.

`minutes-items.pkl` is organized by agenda item and finds all the sections of the minutes that were relevant to that agenda item.

## Summarize minutes items

`summarize-minutes.ipynb`

For each agenda item and related minutes, summarizes the minutes using ChatGPT. Stores results in a dataframe: `minutes-summaries.pkl`.

## Summarize supplemental docs

`summarize-supplemental-docs.ipynb`

Summarizes each supplemental document using ChatGPT. Stores results in a dataframe: `supplemental-docs-summaries.pkl`.


## Run Order


7. `generate-minutes-summaries.ipynb`
    - Generates summaries of the deliberations of each agenda item by the CPC
    - Stores the summaries a dataframe in `intermediate_data/cpc/<year>/<date>/minutes-summaries.pkl`
    - Uses ChatGPT

8. `generate-supplemental-docs-summaries.ipynb`
    - Generates summaries of the supplemental documents
    - Stores the summares in a dataframe in `intermediate_data/cpc/<year>/<date>/supplemental-docs-summaries.pkl`
    - Uses ChatGPT

9. `generate-casedata.ipynb`
    - Generates information on all relevant cases extracted from the minutes
    - Stores the data in a dataframe `intermediate_data/cpc/case-data.pkl`
    - Uses URL requests to PDIS

10. `construct-evals.ipynb`
    - Construct examples of ChatGPT responses for manual evaluation
    
11. `explore-cpc-docs.ipynb`
    - Generates summary statistics for the documents collection 

# Land Use Regulation Language Model

## Data Requirements

The following files should be in `raw_data` on your local machine.

- `lamunicipalcode.html`
- `LA Business Council Data Request - 20220823.xlsx`

## Run in following order
- `parse0.ipynb`
- `parse2.ipynb`
- `embed_and_upsert.ipynb`
- `query_test.ipynb`

