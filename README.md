# TEAM 9
# Translator Assignment Recommendation System (TARS)

---

## Table of Contents
1. [Overview](#overview)
2. [Pipeline Architecture](#pipeline-architecture)
3. [File Structure](#file-structure)
4. [Data Schema Reference](#data-schema-reference)
5. [Development Workflow](#development-workflow)
6. [API Reference](#api-reference)
---

## Overview

Given an incoming task (client, language pair, time window, deadline, task type), the
system returns a ranked shortlist of translators who can take it.

**Input** — a task described by these fields:

| Field | Example | Notes |
|---|---|---|
| `company_name` | `"Appcelerate"` | Must match a `CLIENT_NAME` in the clients table |
| `task_date` | `"2024-10-10"` | Planned start date |
| `task_deadline` | `"2024-10-12"` | Delivery deadline; spans the scheduling window |
| `task_start_time` | `"09:00"` | Shift start the task should fit into |
| `task_end_time` | `"17:00"` | Shift end |
| `task_length_hours` | `3.5` | Effort in hours |
| `language_pair` | `"English_Spanish (LA)"` | `SOURCE_LANG_TARGET_LANG`; must be a rate column |
| `task_type` | `"ProofReading"` | `Translation`, `ProofReading`, `Spotcheck`, `TEST`, `Training`, … (defaults to `Translation`) |
| `followed_by` | `"ProofReading"` | Optional — the next step after this task |

**Output** — a table of up to 10 recommended translators, each row carrying a score
plus the per-dimension values behind it (language-pair rate, daily capacity, average
quality, on-time score, and the relevant industry-experience column).

**Two rankers produce the score:**
- A **rule-based weighted scorer** (`SUITABILITY_SCORE`, 0–100) — used by the CLI.
- A **trained XGBoost regressor** (`ML_PREDICTED_SCORE`) — used by the API.

Both consume the same eligible-candidate set produced by the constraint engine.

---

## Pipeline Architecture

### Data preparation (offline)

Raw sheets (committed as CSVs under `src/api/`) → `data/interim/` → `data/processed/`.

```
src/api/*.csv ──seed──▶ data/interim/*.csv ──build_processed_data.py──▶ data/processed/*.csv
```

`build_processed_data.py` calls `prepare_pipeline_tables` (`src/pipeline/features.py`), which:
- cleans the historical task log (parses timestamps, derives `TASK_LENGTH`,
  `TRANSLATOR_WORKING_TIME`, and the `ON_TIME` flag, drops invalid rows), and
- builds the per-translator statistics table (language-pair rates, `AVERAGE_QUALITY`,
  `ON_TIME_SCORE`, and per-task-type / per-industry experience hours).

`setup_env.py` runs both seeding and building on a fresh clone.

### Recommendation flow (online)

Implemented in `scripts/run_pipeline.py` (CLI) and `src/api/api.py` (HTTP). Stages:

1. **Ingestion** (`ingestion.py`) — validate and normalize the task dict.
2. **Requirement build** (`filtering.TaskAssignmentCSP.build_client_requirements`) —
   look up the client's constraints (`SELLING_HOURLY_PRICE` → budget, `MIN_QUALITY`,
   `MIN_ON_TIME_SCORE`, `WILDCARD`), derive the required sub-industry / industry /
   industry-group from the client's history, and compute the delivery window. Returns
   `None` if the client is unknown.
3. **Constraint filtering with escalation** (`get_translators_with_fallback`) — apply the
   hard constraints, relaxing one level at a time until candidates appear:
   `Sub-Industry → Industry → Industry Group → Wildcard → Global`.
   The **wildcard** step relaxes the single dimension the client nominated:
   `quality` (lower min quality), `price` (raise budget 25%), or `deadline` (relax
   on-time / schedule). Hard filters cover: task-type experience, language pair,
   budget, quality, on-time score, working-day & shift-window availability, daily
   capacity, and industry experience.
4. **Splitting fallbacks** — if no single translator fits, try
   `split_task_across_days` (one translator over the window) and
   `split_task_across_translators` (a parallel team). Order depends on the wildcard.
5. **Diagnosis** — if everything fails, `diagnose_bottleneck` prints which constraint
   eliminated the last candidates, and the pipeline returns an empty result.
6. **Ranking** — score the eligible set:
   - `scoring.rank_candidates` → `SUITABILITY_SCORE` (CLI), or
   - `ml.rank_candidates_ml` → `ML_PREDICTED_SCORE` (API, loads a model from `models/`).
7. **Output** (`output.format_recommendations`) — select the rationale columns and
   return the top *N* (default 10).

### Task-type business rules (`get_eligible_translators`)

- **`TEST`** — ignore the budget; pick on quality.
- **`Training`** — quality and experience requirements dropped.
- **`Translation` followed by `ProofReading`** — relax the min-quality threshold by 1.
- **`ProofReading` / `Spotcheck`** — when a previous translator's experience is supplied,
  require a candidate with *strictly higher* experience than the previous step.

### Ranking weights (`scoring.rank_candidates`)

Base weights (quality / reliability / margin / experience) are `40 / 30 / 20 / 10`, re-weighted by wildcard:

| Mode | Quality | Reliability | Margin | Experience |
|---|---|---|---|---|
| balanced | 40 | 30 | 20 | 10 |
| quality | 60 | 20 | 10 | 10 |
| price | 20 | 20 | 50 | 10 |
| deadline | 20 | 60 | 10 | 10 |
| `TEST` | 80 | 0 | 0 | 20 |

Outside `quality`/`TEST` mode, quality and experience use **resource-conservation**
normalization: a translator who only just clears the minimum scores higher than an
over-qualified one, to avoid spending premium talent on low-tier tasks. The XGBoost
ranker (`ml.py`) targets the same idea via a "Goldilocks" efficiency label (profit
margin minus an over-specification penalty).

---

## File Structure

```
TEAM9/
│
├── README.md
├── agents.md                  ← LLM session log (see Contribution Guidelines)
├── requirements.txt
├── docker-compose.yml         ← Runs web + api together for development
├── setup_env.py               ← One-shot local bootstrap (venv, deps, data)
├── .gitignore
│
├── data/
│   ├── interim/               ← Raw sheets as CSV (seeded from src/api/ by setup_env.py)
│   ├── processed/             ← Cleaned, model-ready tables the pipeline consumes
│   └── processing_scripts/
│       ├── build_processed_data.py   ← interim → processed
│       ├── csv_extraction.py
│       └── data_cleaning.py
│
├── data_analysis/             ← EDA & model-experimentation notebooks (not production)
│
├── utils/                     ← Shared, root-level utilities
│   ├── data_loader.py         ← Load excel / interim / processed tables
│   └── config.py              ← Project paths (single source of truth for locations)
│
├── models/                    ← Serialized model artifacts (xgboost_ranker*.pkl)
│
├── src/
│   ├── pipeline/              ← Recommendation stages
│   │   ├── ingestion.py       ← Validate & parse the incoming task
│   │   ├── filtering.py       ← TaskAssignmentCSP: hard constraints, fallback, splitting
│   │   ├── features.py        ← Build cleaned history + translator statistics tables
│   │   ├── scoring.py         ← Rule-based weighted ranker (SUITABILITY_SCORE)
│   │   ├── ml.py              ← XGBoost training + ML ranker (ML_PREDICTED_SCORE)
│   │   └── output.py          ← Select rationale columns, return top-N
│   │
│   └── api/                   ← FastAPI backend + committed source CSVs + SQLite builder
│       ├── api.py
│       ├── to_db.py / read_db.py
│       ├── *.csv              ← Committed raw sheets (seed source for data/interim/)
│       └── Dockerfile
│
├── web/                       ← React + Vite + TypeScript frontend (PM-facing UI)
│
├── tests/
│   ├── test_filtering.py
│   ├── test_scoring.py
│   └── test_ranking.py        ← Covers output.format_recommendations
│
└── scripts/
    ├── model_training/
    │   ├── train_ml_ranker.py            ← Trains & serializes the XGBoost ranker
    │   └── ML_translator_predictor_XGboost.ipynb
    └── run_pipeline.py        ← CLI entrypoint: task JSON → recommendations
```

### Notes on the layout

- **`utils/` is at the root**, not inside `src/`, so both `src/pipeline/` and
  `data/processing_scripts/` can import it without a cross-dependency. `config.py`
  centralizes filesystem paths; `data_loader.py` loads the excel / interim / processed
  tables.
- **`data/interim/` and `data/processed/` are git-ignored.** They are regenerated by
  `setup_env.py` from the CSVs committed under `src/api/`.
- **`models/`** holds only finalized, versioned artifacts. Training scripts in
  `scripts/model_training/` produce them; nothing here is hand-edited.
- **`data_analysis/`** is exploratory only and never imported by production code.
- **`web/`** is a separate deployable that talks to the backend through `src/api/` only.

---

## Data Schema Reference

### Source sheets

#### `Data` — Historical task log

| Field | Type | Description |
|---|---|---|
| `PROJECT_ID` | str | Project code |
| `PM` | str | Responsible PM team |
| `TASK_ID` | int | Unique task identifier |
| `START` | datetime | Planned task start |
| `END` | datetime | Planned delivery deadline |
| `TASK_TYPE` | str | `Translation`, `PostEditing`, `ProofReading`, `Spotcheck`, … |
| `SOURCE_LANG` | str | Source language |
| `TARGET_LANG` | str | Target language |
| `TRANSLATOR` | str | Assigned translator name |
| `ASSIGNED` | datetime | Pre-assignment time (Kanban notification) |
| `READY` | datetime | Time translator was told to start |
| `WORKING` | datetime | Time translator began work |
| `DELIVERED` | datetime | Time translator delivered |
| `RECEIVED` | datetime | Time PM received delivery |
| `CLOSE` | datetime | Time PM closed the task |
| `HOURS` | float | Actual hours worked |
| `HOURLY_RATE` | float | Translator's cost rate |
| `COST` | float | Total task cost |
| `QUALITY_EVALUATION` | float | Quality score |
| `MANUFACTURER` | str | Client name |
| `MANUFACTURER_SECTOR` | str | Client sector (L1) |
| `MANUFACTURER_INDUSTRY_GROUP` | str | Client industry group (L2) |
| `MANUFACTURER_INDUSTRY` | str | Client industry (L3) |
| `MANUFACTURER_SUBINDUSTRY` | str | Client sub-industry (L4) |

#### `Schedules` — Translator availability

| Field | Type | Description |
|---|---|---|
| `NAME` | str | Translator name (join key with `Data.TRANSLATOR`) |
| `START` | time | Workday start time |
| `END` | time | Workday end time |
| `MON`, `TUES`, `WED`, `THURS`, `FRI`, `SAT`, `SUN` | int (0/1) | Working-day flags |

#### `Clients` — Client constraints

| Field | Type | Description |
|---|---|---|
| `CLIENT_NAME` | str | Client name (join key with `Data.MANUFACTURER`) |
| `SELLING_HOURLY_PRICE` | float | Price billed to client per hour (used as the budget ceiling) |
| `MIN_QUALITY` | float | Minimum acceptable translator quality score |
| `MIN_ON_TIME_SCORE` | float | Optional minimum on-time score |
| `WILDCARD` | str | Constraint to relax when no perfect match: `Quality`, `Price`, or `Deadline` |

#### `TranslatorsCost+Pairs` — Rates & language pairs

| Field | Type | Description |
|---|---|---|
| `TRANSLATOR` | str | Translator name |
| `SOURCE_LANG` | str | Source language |
| `TARGET_LANG` | str | Target language |
| `HOURLY_RATE` | float | Cost per hour for this language pair |

### Processed tables (`data/processed/`)

| File | Key columns added beyond the source sheets |
|---|---|
| `clean_history.csv` | `TASK_LENGTH`, `TRANSLATOR_WORKING_TIME`, `ON_TIME` (drops PM/ID/timestamp bookkeeping columns) |
| `clients.csv` | Client constraints, as above |
| `translator_statistics.csv` | One row per translator: schedule, one rate column per `SOURCE_LANG_TARGET_LANG` pair, `AVERAGE_QUALITY`, `ON_TIME_SCORE`, `<TaskType>_experience`, and `SUB_*` / `IND_*` / `GRP_*` experience-hour columns |

---

## Development Workflow

### Setup

```bash
# Clone
git clone https://github.com/Synthesis-Project-I/TEAM9
cd TEAM9

# One-shot bootstrap: creates .venv, installs requirements, seeds data/interim/
# from the CSVs in src/api/, and builds data/processed/
python setup_env.py

# Activate the environment
.venv\Scripts\activate          # Windows
source .venv/bin/activate        # macOS / Linux
```

Flags: `python setup_env.py --no-install` (skip venv/deps) or `--no-data`
(skip seeding/building). To rebuild only the processed tables later:

```bash
python data/processing_scripts/build_processed_data.py
```

### Running the pipeline (CLI)

Create a task JSON and run the entrypoint:

```json
{
  "company_name": "Appcelerate",
  "task_date": "2024-10-10",
  "task_deadline": "2024-10-12",
  "task_start_time": "09:00",
  "task_end_time": "17:00",
  "task_length_hours": 3.5,
  "language_pair": "English_Spanish (LA)",
  "task_type": "ProofReading"
}
```

```bash
python scripts/run_pipeline.py task.json
```

The CLI ranks with the rule-based scorer and prints the recommendation table (or a
diagnostic message when no candidate is found).

### Running the web app

```bash
cd web
npm install      # first time only
npm run dev
```

Serves the UI on `http://localhost:5173`. It needs the API running (see
[Web and API](#web-and-api-development)); point it at the backend via `VITE_API_URL`.

### Training the ML ranker

```bash
# --samples N (sampled tasks) or --samples all (full history); --output names the .pkl
python scripts/model_training/train_ml_ranker.py --samples 200 --output xgboost_ranker.pkl
```

The serialized model is written to `models/`. The API loads `xgboost_ranker_full.pkl`.

### Running tests

```bash
python -m pytest -q
```

### Web and API (development)

Runs the React UI and the FastAPI backend together with live reload:

```bash
docker compose up --build
```

The UI is served on `http://localhost:5173` and calls the API at
`http://localhost:8000` (`VITE_API_URL`).

---

## API Reference

FastAPI app in `src/api/api.py`. Data endpoints read the SQLite database built by
`to_db.py`; `/recommendations` runs the pipeline with the XGBoost ranker.

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `GET` | `/recommendations` | Ranked translators for a task (query params mirror the task fields, plus `top_n`) |
| `GET` | `/translators` | Translator statistics |
| `GET` | `/schedules` | Translator schedules |
| `GET` | `/clients` | Client constraints |
| `GET` | `/tasks` | Historical tasks |

`/recommendations` returns `{ "data": [...], "task_requirements": {...}, "model": "..." }`,
or `{ "data": [], "message": "..." }` when the client is unknown or no translator fits.

---