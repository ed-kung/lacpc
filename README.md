# City Planning Commission Documents

## Data Requirements

- CPC documents contained in `raw_data/cpc`
- Annotations for start and end pages of supplemental documents: `raw_data/cpc/cpc-supplemental-docs-splits.csv`

## Run Order

1. `extract-cpc-docs.ipynb`
    - Extracts the PDF files into raw text documents, separated by `<PAGE BREAK>`
    - `raw_data/cpc/<year>/<date>/<filename>.pdf` is converted to plain text and saved to `intermediate_data/cpc/<year>/<date>/<filename>.txt`
    - Also generates `intermediate_data/cpc/metadata.csv`

2. `split-supplemental-docs.ipynb`
    - Uses hand annotated start and end pages to split the supplemental documents
    - Text content of each supplemental document is stored in `intermediate_data/cpc/<year>/<date>/supplemental-docs.pkl`

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

9. `construct-evals.ipynb`
    - Construct examples of ChatGPT responses for manual evaluation
    
10. `explore-cpc-docs.ipynb`
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

