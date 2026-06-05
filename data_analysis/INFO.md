# Data Analysis Summary (TARS)

A consolidated view of the findings from the notebooks in this folder. All figures
are taken from the executed notebook outputs; field *meanings* are not repeated here —
see the Data Schema Reference in the root [README](../README.md).

> **Scope / caveat.** These results were produced against the **full historical
> dataset (~1M task rows)**, not the 100-row sample CSVs committed under `src/api/`.
> One notebook even saved its enriched output to a path on another machine
> (`C:\Users\herme\...\enriched_tasks.csv`), so the full `data/raw/data.xlsx` is
> required to reproduce these numbers.

> **Known gaps in the analysis itself.** A few cells failed and their outputs are
> missing (flagged inline as *not reported*):
> - `03_translators` cell 5 raised a `MemoryError` on `load_enriched_tasks()`, so
>   per-translator on-time rates, pair-coverage tiering, rate-gap, schedule, and
>   tenure sections never ran (this also means **no dataset min/max date** was printed).
> - `01_data_quality` near-duplicate detection crashed with a numpy `ArrayMemoryError`.

---

## 1. Data sources

| Sheet | Rows | Columns |
|---|---|---|
| `Data` (task log) | 997,933 | 29* |
| `Schedules` | 983 | 11* |
| `Clients` | 2,645 | 6* |
| `TranslatorsCost+Pairs` | 4,688 | 7* |

\* Column counts include derived/normalized fields added by the analysis loader
(`*_CLEAN`, `*_KEY`, `WILDCARD_CLEAN`), not just raw source columns.

**Dtype audit.** Only one mismatch flagged: `Data.PROJECT_ID` is stored as string
but expected numeric. `Schedules.START` / `END` are strings (expected time-like).
Everything else matches expectations.

**Entity counts (from `Data`):** 997,933 tasks · 13,692 projects · **4 PMs** ·
983 translators · 2,645 clients · 13 task types.

---

## 2. Data quality

### Missing values
Missingness is negligible:
- `Data`: `COST` 7, `HOURLY_RATE` 7, `END` 2, `START` 1 (all ≈0.00%); the other 25 columns have none.
- `Schedules`, `Clients`: zero nulls.
- `TranslatorsCost+Pairs`: `HOURLY_RATE` 5 missing (0.11%).

Missing cost/rate concentrates in older years (2012: 0.54%, 2013: 0.22%) and the
`Miscellaneous` task type.

### Duplicates
**0 exact duplicate rows** in all four sheets. (Near-duplicate detection on
TRANSLATOR/START/END could not run — memory error.)

### Outliers & invalid values
| Column | min | median | p99 | max | IQR-outliers | Z-outliers |
|---|---|---|---|---|---|---|
| `HOURS` | 0.0 | 0.29 | 25.02 | **725.0** | 13.47% | 1.51% |
| `HOURLY_RATE` | 8.0 | 16.0 | 33.0 | 62.0 | 7.53% | 3.83% |
| `COST` | 0.0 | 4.94 | 419.43 | **14,105.0** | 13.23% | 1.35% |
| `QUALITY_EVALUATION` | 0.0 | 7.0 | 10.0 | 10.0 | 0.30% | 0.30% |

- **Zero-value tail:** ~69,034 tasks (6.92%) have **both HOURS = 0 and COST = 0**,
  overwhelmingly `ProofReading` (49,972) and `Miscellaneous` (11,310).
- **Timestamp logic:** **36,771 rows (3.69%) have START after END.** The other three
  workflow-order checks (ASSIGNED→READY→WORKING→DELIVERED) reported **0 violations**.
  (RECEIVED/CLOSE ordering was not checked.)
- **Same source = target language:** 1,643 rows (0.16%), e.g. Catalan→Catalan.
- **Categorical variants:** no spelling-variant families flagged after normalization
  (though raw rows still show encoding artifacts like `Ra�l`, `Miscelaneous`,
  `Guaran` for Guaraní).
- **Date outliers:** a task dated **1956** (1 row) and an on-time row dated **2050**
  appear at the boundaries — clear data-entry errors.

---

## 3. Cross-sheet join integrity

Joins are essentially complete:

| Join | Match rate |
|---|---|
| Data translators → Schedules | 100.000% |
| Data manufacturers → Clients | 100.000% |
| Data translators → TranslatorsCost+Pairs | 99.999% |

The only orphans are **5 translator/language-pair combinations** (~0.001% of rows) on
the Data→Pairs join, all attributed to language/name spelling variants (e.g.
`Acolmiztli — Spanish (LA)→Nahuatl`, `Octavi — Finnish→Finnish`).

An enriched table of **(997,933 × 80)** was built by joining all sheets and computing
prior/rolling features; its highest missing rates are small (`SHIFT_OVERLAP_PCT` 0.50%,
`PRIOR_QUALITY_MEAN_PAIR` 0.47%).

---

## 4. Distributions

### Task types (n = 997,933)
ProofReading **43.1%** (430,554) and Translation **40.2%** (401,377) together are
**~83%** of all work. Then Miscellaneous 8.4%, PostEditing 6.8%, and a long tail
(Engineering, LanguageLead, Management, DTP, TEST 192, Spotcheck 47, Training 11, …).

### Languages — heavily English-sourced
- **Source:** English **965,047 (~96.7%)**; then German 15,502, Spanish (Iberian) 10,619.
- **Target:** Spanish (Iberian) **486,555 (~48.8%)**, Galician 136,447, Catalan 105,801,
  Spanish (LA) 93,528, Basque 34,119.
- **Top pair:** English→Spanish (Iberian) **471,597 (~47.3% of all tasks)**; 13 of the
  top 20 pairs are English-sourced.

### Quality evaluation
Scored on every task: mean **7.04**, median 7.0, std 1.46, range 0–10.

### Hourly rate — task sheet vs contract (Pairs) sheet
| Stat | Data (`HOURLY_RATE`) | Pairs sheet |
|---|---|---|
| mean | 17.06 | 21.16 |
| median | 16.0 | 18.0 |
| max | 62.0 | 62.0 |

Contract rates run higher and wider than the rates actually billed on tasks.

### Workload concentration
- **PMs:** only 4. RMT handles ~38.5% (384,044), then BMT, KMT, PMT.
- **Sectors:** IT (379,310) + Communication Services (310,322) ≈ **69%** of tasks.

---

## 5. Translators

983 translators. Workload is **strongly right-skewed** (log-scale histogram):
- Most active: **Isaias Venancio 65,209 tasks (~6.5% alone)**; the top 20 ≈ **48%** of all tasks.
- Hours ranking differs from task-count ranking (Severino tops hours at 38,256 but
  isn't in the task-count top 20) → per-task duration varies widely by translator.

**Quality by translator:** high-volume translators cluster near the global ~7.0;
a set of lower-volume specialists reach ~8–9 (with ≥30 scored tasks): Camille 8.99
(n=159), Eduardo 8.80 (n=1,906), Sara 8.76 (n=1,879), Breixo 8.73 (n=2,720).

*Not reported (cells crashed/never ran):* per-translator on-time rate,
Specialist/Generalist/Mixed tiering, rate-gap, schedule patterns, tenure.

---

## 6. Clients & task types

- 2,645 clients, perfectly matched between `Data` and the `Clients` sheet.
- **Revenue/volume concentration is high:** TrueConnect (258,435 tasks) + AeroSysTech
  (167,992) ≈ **43%** of tasks; top 5 ≈ **56%**.
- **Task mix varies by client:** ProofReading dominates most; MindSpark Media is
  Translation-heavy (0.69); NextGen Industries is an outlier (PostEditing 0.62).
- **Client constraints (`Clients` sheet):**
  - `MIN_QUALITY`: mean 5.0, median 7.0, max 8.0 — but **33% of clients set 0** (no quality floor).
  - `SELLING_HOURLY_PRICE`: mean 34.9, median 35, range 20–50.
  - `WILDCARD`: near even three-way split — Deadline 916, Quality 875, Price 854.
- **Business-rule checks:** ~98% of proofread pairs use a different translator than the
  original (False 214,985 vs True 4,692); TEST tasks = 192 across 93 translators.

---

## 7. Temporal

- **Growth:** tasks rose from 22,411 (2010) to a peak **120,049 (2020)**, then a mild
  decline (2021: 118,811; 2022: 115,509). Core range 2010–2022 (plus the 1956 / 2023 outliers).
- **Seasonality:** mild — peak October (92,246) & March; troughs January (69,649) & December.
- **Weekly:** weekday-concentrated; Sat+Sun ≈ **2.6%** of tasks.
- **Assignment hour:** business-hours profile, peaking 10:00 (141,048) with a distinct
  **14:00 lunch dip** (44,160).
- **Punctuality:** ~**75.8% on time / 24.2% late**. Among late tasks (241,261), median
  lateness ≈ 49 min but with an extreme tail. On-time rate dipped to 0.70 in 2017 then
  improved steadily to 0.83 (2022).
- **Workflow timing** (enriched, hours): note **negative minimums** in
  TIME_TO_ASSIGN and TASK_DURATION, confirming the timestamp-ordering issues; 23.94%
  of tasks were assigned before their START.

---

## 8. Financial

- **Selling price ≈ 2× cost rate:** selling mean 32.8 vs cost rate mean 17.06.
- **Margin (selling − cost rate):** median just **3.40/hr** with a very wide spread
  (min −4,178, max 7,975). **4.32% of tasks are loss-making** (negative margin);
  4.5% have cost rate exceeding selling price.
- **By language pair (≥50 tasks):** most profitable Spanish (LA)→Spanish (Iberian)
  (+271); most loss-making English→Korean (−158), English→Swedish (−139),
  English→Japanese (−133). High-volume English→Basque is barely profitable (+0.20)
  and English→Quechua is loss-making (−7.4 over 9,780 tasks).
- **By client:** AeroSysTech + TrueConnect ≈ 7.9M of total revenue. Margin efficiency
  varies wildly — MotorForge (avg margin 188/task) and Zenith Dynamics (299) are
  efficient; FrontierTech (5.9) and NexisOne (3.8) run thin.
- **Rate vs quality correlation: −0.014** — paying more buys no measurable quality.

---

## 9. Relationships between variables

The ML notebooks quantify signal via **mutual information (MI)**, not Pearson
(only multicollinearity and the target-pair correlations are given as coefficients).

**Predicting on-time** — dominated by availability/schedule structure:
SHIFT_HOURS_PER_DAY 0.163, WORKING_DAYS_PER_WEEK 0.146, WEEKEND_WORKER 0.117,
ROLLING_ON_TIME_RATE_5 0.108, PRIOR_ON_TIME_RATE_TRANSLATOR 0.058.

**Predicting quality** — weak across the board; the best are prior-quality aggregates:
PRIOR_QUALITY_MEAN_TASK_TYPE 0.027, PRIOR_QUALITY_MEAN_PAIR 0.022,
PRIOR_QUALITY_MEAN_TRANSLATOR 0.020. Rate vs quality MI ≈ 0.003 (negligible).

**Targets are nearly independent:** corr(ON_TIME, QUALITY) = **0.023** at task level
(0.110 at translator level) → punctuality and quality should be modeled separately.

**Multicollinearity (|corr| ≥ 0.8) — redundant features to prune:**
- MARGIN_TASK_RATE ↔ MARGIN_PAIR_RATE = **1.00** (perfectly redundant)
- PRIOR_ON_TIME_RATE_TRANSLATOR ↔ _TASK_TYPE = 0.92
- PRIOR_QUALITY_MEAN_TRANSLATOR ↔ _PAIR = 0.88
- WORKING_DAYS_PER_WEEK ↔ WEEKEND_WORKER = 0.82

---

## 10. Targets, feature engineering & cold start

**Candidate targets:** ON_TIME (75.8% / 24.2%), QUALITY_EVALUATION (mean 7.04),
HIGH_QUALITY_8 (≥8 → 41.1% positive).

**Degenerate engineered features (drop these):**
- `RATE_DISCREPANCY` — constant 0.
- `SHIFT_HOURS_PER_DAY` — constant 10.
- One of the identical MARGIN_TASK_RATE / MARGIN_PAIR_RATE pair.

**Other feature notes:** ~98% of translators work weekends; night shifts ≈ 0%;
`PRIOR_AVG_LATENESS_MINUTES` and `AVAILABLE_HOURS_IN_WINDOW` carry severe outliers /
negative values from the timestamp issues. A recency-weighting (exponential decay,
30/90/180-day half-lives) was proposed for prior-task signals.

**Cold start is really a *sparse-history* problem, not a zero-history one:**
- **0 translators** in the Pairs sheet have zero tasks.
- But **322 translators have <5 scored tasks** (unreliable quality labels).
- Quality estimates stabilize after a median of **4 tasks** (75th pct 12, max 1,667).
- Sector-average priors are weak: all sectors cluster ~7.0–7.2.

---

## 11. Implications & action list

**For the recommendation model**
- Quality is hard to predict and unrelated to cost — over-weighting quality (or paying
  for it) is not data-supported; punctuality is far more predictable, and mostly from
  schedule/availability features.
- Model on-time and quality as **separate** targets.
- Prune redundant features (margins, prior-rate pairs) and the constant ones.
- Handle sparse-history translators with population priors + score-count gating, not a
  zero-history cold-start mechanism (there are none).

**Data-quality fixes worth making upstream**
1. 36,771 rows (3.69%) with START after END.
2. ~69k rows (6.9%) with zero hours and zero cost (mostly ProofReading).
3. Boundary date errors (1956, 2050) and negative workflow durations.
4. `PROJECT_ID` dtype, and `Schedules` time fields stored as strings.
5. Re-run `03_translators` (fix the MemoryError) to fill the missing translator-level
   punctuality/coverage/schedule/tenure analysis.
