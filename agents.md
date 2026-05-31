# agents.md — LLM Session Log
> **Attach this file to every prompt when asking an LLM for help on this project.**
> It gives the model the context it needs to give you consistent, accurate answers.

---

## How to use this file

1. Copy the full content of this file and paste it at the **start** of your prompt.
2. After the session, fill in a new entry in [Session History](#session-history) summarising what was done and what files changed.
3. Commit this file alongside any code changes so the whole team stays in sync.

---

## Project Summary (always include)

**Project name:** Translator Assignment Recommendation System (TARS)

**Client/context:** iDISC — a translation & technology company. iDISC manages roughly **70,000 tasks per year** across a **24/7** operation, with about **30,000 PM hours** currently spent on manual assignment decisions. The goal of TARS is to build a recommendation pipeline that suggests the best available translator(s) for an incoming task so project managers can make faster, more consistent, and more data-driven decisions.

**Tech stack:** Python 3.11+, pandas, pytest for the backend pipeline. Web interface (framework TBD — e.g. React or plain HTML/JS) served via a backend API (framework TBD — e.g. Flask or FastAPI) in `src/api/`. No frontend or backend framework is locked in yet.

**Core recommendation criteria:**
- **Experience** — hours logged with this client, industry sector, or task type
- **Quality** — historical quality evaluation scores
- **Punctuality** — delivery reliability, derived from `END` vs `DELIVERED`
- **Cost** — translator `HOURLY_RATE` vs client `SELLING_HOURLY_PRICE`
- **Availability** — schedule compatibility with the task time window

**Data sources (4 sheets from an Excel file):**
- `Data` — historical task log with task metadata, language pair, assigned translator, workflow timestamps, hours, cost, quality score, and client/industry classification
- `Schedules` — translator working hours and working days
- `Clients` — per-client minimum quality threshold, selling price, and wildcard (which constraint to relax when no perfect match exists)
- `TranslatorsCost+Pairs` — translator hourly rates per language pair

**Pipeline stages (in order):**
1. `ingestion.py` — validate and parse the incoming task dict
2. `filtering.py` — hard constraints: language pair, schedule availability, minimum quality
3. `scoring.py` — soft scores: experience, quality, punctuality, cost margin, client/sector familiarity
4. `ranking.py` — weighted aggregation + wildcard fallback logic
5. `output.py` — format top-N recommendations with per-dimension rationale

**Key business rules to keep in mind:**
- `ProofReading` and `Spotcheck` tasks require a *different* translator than the one who did the preceding step, and the reviewer must have a *higher* historical quality score.
- `TEST` tasks: assign the highest quality translator regardless of cost.
- `Training` tasks: quality and experience are irrelevant.
- The `WILDCARD` field in `Clients` tells us which constraint (`Quality` or `Price`) can be dropped when no translator satisfies all hard filters.
- Punctuality is derived by comparing `END` (planned deadline) vs `DELIVERED` (actual delivery datetime).
- Experience is measured as hours worked for a specific client, client sector/industry, or task type — not just task count.

**Repository/file-structure guardrails:**
- Project root is `tars/`.
- `data/raw/` is read-only; transformations must write new outputs to `data/interim/` or `data/processed/`.
- `data/processing_scripts/` contains data preparation code; notebooks belong in `data_analysis/`, not in `src/`.
- `utils/` is at the **root level** (not inside `src/`) — it is shared by both the pipeline in `src/` and the data preparation scripts in `data/processing_scripts/`. `data_loader.py` loads data sheets; `config.py` is the single source of truth for weights, thresholds, and tunable constants.
- `models/` holds serialized model artifacts at the root level. Training scripts that produce them live in `scripts/model_training/`. Only finalized artifacts belong here — never experimental outputs.
- `src/pipeline/` contains the five ordered pipeline stage files: `ingestion.py`, `filtering.py`, `scoring.py`, `ranking.py`, `output.py`. Keep these thin.
- `src/api/` exists as the backend boundary for the PM-facing web interface.
- `web/` is a separate frontend application that talks to the backend through `src/api/` only.
- `scripts/model_training/` contains training scripts; `scripts/evaluate.py` covers both backtesting and model evaluation.

**File structure root:** `tars/` — see `README.md` for the full tree. Key top-level folders: `data/` (raw, interim, processed, processing_scripts), `data_analysis/`, `utils/`, `models/`, `src/` (pipeline, api), `web/`, `tests/`, `scripts/` (model_training, run_pipeline, evaluate).

---

## Current State

> **Update this section before each LLM session.**

- [ ] Ingestion stage implemented
- [ ] Filtering stage implemented
- [ ] Scoring stage implemented
- [ ] Ranking stage implemented
- [ ] Output stage implemented
- [ ] End-to-end test with mock data passing
- [ ] Backtesting script (`scripts/evaluate.py`) implemented

**Active branch:** _(fill in, e.g. `feature/filtering-stage`)_
**Files recently changed:** _(fill in)_
**Known bugs / open questions:** _(fill in)_

---

## Session History

### Session 3 — 2026-03-30
**Who:** Pepe
**Tool:** Claude Sonnet 4.6
**Task:** Finalize and clean up the repository structure; update both `README.md` and `agents.md` to reflect all decisions made.
**Prompt summary:** Discussed where ML models should live, what `src/pipeline/` should contain, why `utils/` should be at the root level instead of inside `src/`, and where model training/evaluation scripts belong. Then reviewed and revised `README.md` to incorporate all of these decisions.
**Files created/changed:**
- `README.md` — added pipeline stage files to `src/pipeline/` in the tree; moved `utils/` to root level with updated rationale; added `models/` rationale; updated `scripts/` rationale to cover `model_training/` and evaluation; clarified contribution guideline about `utils/`; added guideline about not committing experimental model artifacts
- `agents.md` — updated repository guardrails to reflect root-level `utils/`, `models/`, pipeline stage files, and `scripts/model_training/`; updated file structure summary; logged this session

**Key decisions made:**
- `utils/` lives at the **root level**, not inside `src/`, so that both `src/pipeline/` and `data/processing_scripts/` can import from it without creating a cross-dependency between those two parts of the codebase.
- `models/` lives at the **root level** and holds only finalized, versioned model artifacts. Experimental outputs should not be committed here.
- `scripts/model_training/` is where training scripts live; they write their outputs to `models/`.
- `scripts/evaluate.py` covers both pipeline backtesting and model evaluation — no separate file needed unless it grows too large.
- `src/pipeline/` contains exactly five files: `ingestion.py`, `filtering.py`, `scoring.py`, `ranking.py`, `output.py`. Each is a thin module; heavy logic goes in root-level `utils/`.
- `data_analysis/` is the home for model experimentation notebooks as well as data EDA — it is not limited to data exploration only.

**Anything the LLM got wrong / needed correcting:** —

---

### Session 2 — 2026-03-27
**Who:** Pepe
**Tool:** ChatGPT
**Task:** Sync `agents.md` with the clearer README wording so future LLM sessions start from the same project understanding.
**Prompt summary:** Incorporated the newer README clarifications into `agents.md`, especially the business context and project scale, the five recommendation criteria, and the repository guardrails for data, API, and web layers.
**Files created/changed:**
- `agents.md` — expanded project context, added recommendation criteria, added repository/file-structure guardrails, and logged this session

**Key decisions made:**
- `agents.md` should mirror the high-level project narrative from `README.md`, not just the pipeline steps.
- Future LLM context should include the operational scale of the problem (`~70,000 tasks/year`, `24/7`, `~30,000 PM hours`) because it explains why automation matters.
- Future LLM context should always include the five recommendation dimensions: experience, quality, punctuality, cost, and availability.
- Future LLM context should explicitly state the repo boundaries: `data/raw/` read-only, data prep in `data/processing_scripts/`, backend in `src/api/`, frontend in `web/`, and configuration centralized in `src/utils/config.py`.

**Anything the LLM got wrong / needed correcting:** README had been manually clarified and `agents.md` was lagging behind; this session aligned them.

---

### Session 1 — 2026-03-27
**Who:** _(your name)_
**Tool:** Claude Sonnet 4.6
**Task:** Restructure the file tree and update both docs.
**Prompt summary:** Replaced the file structure with the team's agreed folder layout (`data/raw`, `data/interim`, `data/processed`, `data/processing_scripts`, `data_analysis/`). Removed the `features/` subfolder and all example filenames from non-data folders. Added `web/` and `src/api/` to reflect the planned website interface. Updated team ownership table and contribution guidelines accordingly.
**Files created/changed:**
- `README.md` — new file structure section, updated ownership table, updated guidelines
- `agents.md` — updated tech stack, file structure summary, added this session entry

**Key decisions made:**
- `features/` folder removed; scoring logic will live directly in `scoring.py` and `utils/`
- `data/interim/` added for mid-pipeline outputs that are expensive to recompute
- `data/processing_scripts/` keeps all data prep code in one reviewable place
- `data_analysis/` is the new home for EDA/notebooks, completely separate from `src/`
- A `web/` frontend + `src/api/` backend layer is now part of the architecture
- Web framework (frontend and backend) not yet decided

**Anything the LLM got wrong / needed correcting:**

---

### Session 0 — 2026-03-27
**Who:** _(your name)_
**Tool:** Claude Sonnet 4.6
**Task:** Initial project setup. Generated `README.md` with pipeline architecture, file structure rationale, and data schema. Generated `agents.md` (this file).
**Files created/changed:**
- `README.md` — full project overview, file structure, schema, workflow
- `agents.md` — this file

**Key decisions made:**
- Separate `src/pipeline/` (control flow) from `src/features/` (reusable computations) to avoid circular imports and make individual features independently testable.
- `data/raw/` is read-only; all transformations output to `data/processed/`.
- `src/utils/config.py` is the single source of truth for all weights and thresholds.
- Notebooks never import from `src/` — exploration is kept separate from production code.

**Anything the LLM got wrong / needed correcting:** _(fill in after session)_

---

<!-- Add new sessions above this line, newest first -->
