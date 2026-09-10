# How Bureaucratic Capacity Shapes Regulatory Outcomes: Evidence from Land Use in Los Angeles

## Local Setup

Before starting, create a file named `config.local.yaml` containing:

```
LOCAL_PATH: "<path to this repo on your machine>"
DATA_PATH: "<path to data directory>"
OPENAI_API_KEY: "<your openai api key>"
PINECONE_API_KEY: "<your pinecone api key>"
CHROMEDRIVER: "<path to chromedriver>"
TESSERACT: "<path to your tesseract cmd>"
CLAUDE_API_KEY: "<your anthropic api key>"
```

## Directory Structure

```
lacpc/
|-- agent/ 
|   |-- src/:  agent's scripts are kept here
|   |-- reports/:  agent reports are kept here
|-- figures/:  figures (both .tex and image files) are kept here
|-- results/:  numerical results kept here
|-- src/
|   |-- noteboks/
|   |   |-- XX-slug.ipynb:  Jupyter notebooks where main analysis takes place, 
|   |                       listed in run order
|   |-- R/:  contains R scripts called by Jupyter notebooks
|   |-- python/:  contains Python modules called by Jupyter notebooks
|-- tables/:  tables (as .tex snippets) are kept here
|-- 00main.tex:  The main tex file to compile to produce the paper
|-- XXslug.tex:  .tex files called by 00main.tex
```

