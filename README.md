# TEAM9

# Translator Assignment Recommendation System (TARS)

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Pipeline Architecture](#pipeline-architecture)
3. [File Structure](#file-structure)
4. [Data Schema Reference](#data-schema-reference)
5. [Development Workflow](#development-workflow)

---

## Project Overview #TODO

Explain the objective of the project

---

## Pipeline Architecture #TODO

How does our code handle the task?
How does the data flow through our intended architecture?

---

## File Structure

```
tars/
│
├── README.md
├── requirements.txt
├── .gitignore
├── .env.example
│
├── data/
│   ├── raw/                   ← Original files as received. NEVER modify these.
│   │   └── data.xlsx
│   ├── interim/               ← Mid-pipeline intermediate outputs (.xlsx converted to csv)
│   ├── processed/             ← Final cleaned & feature-engineered data ready for the models
│   └── processing_scripts/    ← Scripts that transform raw → interim → processed
│
├── data_analysis/             ← Comprehensive analysis notebooks to understand the data
│
├── utils/                     ← Shared utilities used across the entire codebase
│   ├── data_loader.py         ← Load data sheets into DataFrames; shared by all modules
│   └── config.py              ← Single source of truth for several variables across the code base
│
├── models/                    ← Serialized model artifacts ready to be loaded by the pipeline
│
├── src/
│   ├── pipeline/              ← Pipeline stages
│   │   ├── ingestion.py       ← Validate and parse the incoming task
│   │   ├── filtering.py       ← Hard constraints filtering
│   │   ├── scoring.py         ← ML model
│   │   └── output.py          ← Format top-N recommendations with per-dimension rationale
│   │
│   └── api/                   ← Backend API served to the web interface
│
├── web/                       ← Frontend web interface for project managers
│
├── tests/                     ← Testing for different parts of the code
│   ├── test_filtering.py
│   ├── test_scoring.py
│   └── test_ranking.py
│
└── scripts/
    ├── model_training/        ← Scripts that train and serialize models into models/
    ├── run_pipeline.py        ← CLI entrypoint: takes a task JSON, prints recommendations
    └── evaluate.py            ← Backtesting and model evaluation
```

### Why this structure?

**`data/raw/` is read-only** — Raw data lives in a protected folder; all transformations produce new files in `interim/` or `processed/`. This makes it easy to re-run everything from scratch.

**`data/interim/`** — Intermediate outputs that are too expensive to recompute every time but aren't the final cleaned dataset yet. For example, the Excel sheets converted to CSVs. Keeping this separate from `processed/` makes it clear what is "done" vs "in progress".

**`data/processing_scripts/`** — All data transformation code lives here, not in notebooks or `src/`.

**`data_analysis/`** — Exploration and findings stay completely separate from both the data transformation scripts and production code. This is not part of the final output; it is only for analytical and exploratory purposes.

**`utils/`** — Shared utilities needed across multiple parts of the codebase. These include functions and classes that can be used anywhere as is.

**`models/`** — Holds serialized model artifacts (e.g. `.pkl`, `.joblib`) ready to be loaded by the pipeline. The scripts that train and produce these models live in `scripts/model_training/`. Nothing in `models/` should be hand-edited; it is always the output of a training script.

**`src/pipeline/`** — The five ordered stages that process an incoming task and produce ranked recommendations. Each stage is a thin module: heavy logic belongs in `utils/` or as dedicated helper functions within the stage file itself.

**`src/api/`** — The web interface needs a backend to call. The API layer sits between the pipeline logic and the web frontend, keeping both sides cleanly decoupled.

**`web/`** — The PM-facing interface. It submits task parameters to `src/api/` and renders the ranked recommendations. Keeping it as a sibling to `src/` (not inside it) signals that it is a separate deployable.

**`tests/`** — Automated checks that verify the project works as expected. Every new piece of pipeline behaviour needs at least one corresponding test here.

**`scripts/`** — Files meant to be run directly from the command line. `run_pipeline.py` is the CLI entrypoint for the recommendation pipeline; `evaluate.py` handles backtesting and model evaluation; `model_training/` contains the scripts that train models and write their artifacts to `models/`.

---

## Data Schema Reference

### `Data` sheet — Historical task log

| Field | Type | Description |
|---|---|---|
| `PROJECT_ID` | str | Project code |
| `PM` | str | Responsible PM team |
| `TASK_ID` | int | Unique task identifier |
| `START` | datetime | Planned task start |
| `END` | datetime | Planned delivery deadline |
| `TASK_TYPE` | str | Type: Translation, PostEditing, ProofReading, Spotcheck, etc. |
| `SOURCE_LANG` | str | Source language |
| `TARGET_LANG` | str | Target language |
| `TRANSLATOR` | str | Assigned translator name |
| `ASSIGNED` | datetime | Time task was pre-assigned (Kanban notification) |
| `READY` | datetime | Time translator was told to start |
| `WORKING` | datetime | Time translator began work |
| `DELIVERED` | datetime | Time translator delivered |
| `RECEIVED` | datetime | Time PM received delivery |
| `CLOSE` | datetime | Time PM closed the task |
| `HOURS` | float | Actual hours worked |
| `HOURLY_RATE` | float | Translator's cost rate |
| `COST` | float | Total task cost |
| `QUALITY_EVALUATION` | float | Quality score (scale TBD) |
| `MANUFACTURER` | str | Client name |
| `MANUFACTURER_SECTOR` | str | Client sector (L1) |
| `MANUFACTURER_INDUSTRY_GROUP` | str | Client industry group (L2) |
| `MANUFACTURER_INDUSTRY` | str | Client industry (L3) |
| `MANUFACTURER_SUBINDUSTRY` | str | Client sub-industry (L4) |

### `Schedules` sheet — Translator availability

| Field | Type | Description |
|---|---|---|
| `NAME` | str | Translator name (join key with `Data.TRANSLATOR`) |
| `START` | time | Workday start time |
| `END` | time | Workday end time |
| `MON`–`SUN` | int (0/1) | Working days flag |

### `Clients` sheet — Client constraints

| Field | Type | Description |
|---|---|---|
| `CLIENT_NAME` | str | Client name (join key with `Data.MANUFACTURER`) |
| `SELLING_HOURLY_PRICE` | float | Price billed to client per hour |
| `MIN_QUALITY` | float | Minimum acceptable translator quality score |
| `WILDCARD` | str | Which constraint to relax when no perfect match: `"Quality"` or `"Price"` |

### `TranslatorsCost+Pairs` sheet — Translator rates & language pairs

| Field | Type | Description |
|---|---|---|
| `TRANSLATOR` | str | Translator name |
| `SOURCE_LANG` | str | Source language |
| `TARGET_LANG` | str | Target language |
| `HOURLY_RATE` | float | Cost per hour for this language pair |

---

## Development Workflow

### Setup
```bash
# Clone the project repository from GitHub to your local machine
git clone https://github.com/Synthesis-Project-I/TEAM9 

# Create a virtual environment for the project
python -m venv .venv

# Activate the virtual environment
source .venv/bin/activate  # Mac/Linux
.venv\Scripts\activate  # Windows

# Install all required project dependencies
pip install -r requirements.txt

# Copy the example environment file to create your local .env configuration file
cp .env.example .env
```

**Setup** prepares the local development environment so the project can run consistently. This usually includes creating a virtual environment, installing dependencies, and making sure the required files and configuration are in place before starting development.


### Running the pipeline #TODO
How to run the pipeline?

### Running tests #TODO
How to run tests?

### Web and API development
To run the UI and the API in development mode (with live refreshing of code) run:

```bash
docker compose up --build
```
