# DATA CLEANING AND NEW FEATURES

The notebook starts by loading all sheets from the Excel workbook and assigning them to:

- `df1`: `Data`
- `df2`: `Schedules`
- `df3`: `Clients`
- `df4`: `TranslatorsCost+Pairs`

The cleaning stage removes unused columns, moves `TRANSLATOR` to the first column, parses dates, calculates `TASK_LENGTH`, calculates `TRANSLATOR_WORKING_TIME`, filters inconsistent rows, and adds `ON_TIME`.

# TRANSLATOR STATISTICS/INFORMATION DATASHEET

The notebook creates a translator-level table from schedules, language pairs, average quality, on-time score, task-type experience, and client sector experience.

For pandas, the notebook uses one column per language pair. It creates a `PAIR` column in `TranslatorsCost+Pairs`, pivots the hourly rates, and merges the result into the translator table.

The notebook also creates:

- `AVERAGE_QUALITY`
- `ON_TIME_SCORE`
- one `*_experience` column per task type
- `TIME_TO_START`
- `SUB_*`, `IND_*`, and `GRP_*` experience columns

# CSP

The CSP solver is the decision engine that connects HR data, CRM data, and historical task data. It applies hard constraints for language, budget, quality, on-time delivery, schedule capacity, task type rules, and hierarchical expertise.

It also includes fallback logic:

- strict subindustry match
- industry match
- industry group match
- wildcard relaxation
- global relaxation
- multi-day split
- multi-translator split

# Weighted Score model

While the Constraint Satisfaction Problem solver is responsible for feasibility, the system also needs an objective function to decide who is the best choice among the survivors.

The weighted model scores translators on a 100-point scale using normalized quality, reliability, margin, and expertise. The weights change based on the client's wildcard and the task type.

Baseline weights:

- quality: 40
- reliability: 30
- profit margin: 20
- expertise: 10

Wildcard behavior:

- `quality`: increases quality weight
- `price`: increases margin weight
- `deadline`, `time`, or `schedule`: increases reliability weight
- `TEST`: prioritizes quality and expertise

# TESTING CSP

The notebook contains backtesting helpers that sample historical rows, rebuild task requirements, run the CSP solver, and compare whether the real historical translator appears in the eligible candidates.

# ML MODEL

The ML section creates a target variable called `TARGET_EFFICIENCY`, trains an XGBoost model, and uses it to rank eligible translators by predicted efficiency.

The training features are:

- `req_quality`
- `req_daily_capacity`
- `client_budget`
- `trans_quality`
- `trans_on_time`
- `trans_rate`
- `trans_daily_capacity`
- `quality_gap`
- `margin_gap`

# Comparison

The comparison section tests historical tasks and compares human PM choices with the ML top choice using cost and efficiency metrics.
