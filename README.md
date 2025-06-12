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

Uses `supplemental-docs-splits.csv` to split `supplemental-docs.pdf` for all meetings contained in `meetings-manifest.csv`. Text content of each individual supplemental document is stored in `intermediate_data/cpc/<year>/<date>/supplemental-docs.pkl`.

## Split and summarize agenda items

`summarize-agenda-items.ipynb`

Uses ChatGPT to extract and summarize individual agenda items from the raw text. Responses are stored in `intermediate_data/cpc/<year>/<date>/agenda-item-summaries.txt`.




## Run Order


3. `generate-meetings-metadata.ipynb`
    - Generates `intermediate_data/cpc/meetings_metadata.csv` for a list of meetings that contains all three of `agenda.pdf`, `supplemental-docs.pdf`, and `minutes.pdf`
  
4. `extract-agenda-items.ipynb`
    - Goes through each agenda's text and extracts the individual agenda items, along with a summary of each agenda item
    - Stores result in `intermediate_data/cpc/<year>/<date>/agenda-item-summaries.txt`
    - Uses ChatGPT

5. `split-agenda-items.ipynb`
    - Using the extracted summaries, parses through the text again to extract hard data about each agenda item
    - Stores the extracted data in `intermediate_data/cpc/<year>/<date>/agenda-items.pkl`
    - Does not use ChatGPT

6. `split-minutes-items.ipynb`
    - Use the extracted agenda items to parse through the minutes and extract the sections of the minutes matched to each agenda item
    - Stores the extracted data in `intermediate_data/cpc/<year>/<date>/minutes-items.pkl`
    - Does not use ChatGPT

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

