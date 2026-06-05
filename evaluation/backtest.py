"""Simple backtest: does the recommender surface the translator actually used?

For a sample of historical tasks, rebuild the task requirements, run the CSP +
rule-based ranker, and check where the real historical translator lands.
Writes backtest_results.csv and backtest_summary.txt next to this script.
"""

import contextlib
import io
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.pipeline.filtering import TaskAssignmentCSP
from src.pipeline.scoring import rank_candidates
from utils.data_loader import load_processed_data

TOP_N = 5
SAMPLES = 200
OUT_DIR = Path(__file__).resolve().parent

history_df, clients_df, translators_df = load_processed_data()
csp = TaskAssignmentCSP(translators_df)

sample = history_df.sample(min(SAMPLES, len(history_df)), random_state=42)

rows = []
for _, task in sample.iterrows():
    actual = str(task["TRANSLATOR"]).strip()
    start = pd.to_datetime(task["START"])
    end = pd.to_datetime(task["END"])

    # The CSP prints a lot, silence it
    with contextlib.redirect_stdout(io.StringIO()):
        reqs = csp.build_client_requirements(
            company_name=str(task["MANUFACTURER"]).strip(),
            clients_df=clients_df,
            historical_df=history_df,
            task_date=start.strftime("%Y-%m-%d"),
            task_deadline=end.strftime("%Y-%m-%d"),
            task_start_time=start.strftime("%H:%M"),
            task_end_time=end.strftime("%H:%M"),
            task_length_hours=float(task.get("HOURS", task.get("TASK_LENGTH", 1)) or 1),
            language_pair=f"{str(task['SOURCE_LANG']).strip()}_{str(task['TARGET_LANG']).strip()}",
            task_type=str(task["TASK_TYPE"]).strip(),
        )
        candidates = csp.get_translators_with_fallback(reqs) if reqs else None

    if not reqs:
        rows.append({"actual": actual, "status": "client_not_found", "rank": None, "hit": 0})
        continue
    if candidates is None or candidates.empty:
        rows.append({"actual": actual, "status": "no_candidates", "rank": None, "hit": 0})
        continue

    ranked = rank_candidates(candidates, reqs)
    names = ranked["NAME"].astype(str).str.strip().tolist()
    rank = names.index(actual) + 1 if actual in names else None
    rows.append({"actual": actual, "status": "ok", "rank": rank, "hit": int(rank is not None and rank <= TOP_N)})

results = pd.DataFrame(rows)
results.to_csv(OUT_DIR / "backtest_results.csv", index=False)

summary = (
    f"samples:           {len(results)}\n"
    f"client_not_found:  {(results['status'] == 'client_not_found').sum()}\n"
    f"no_candidates:     {(results['status'] == 'no_candidates').sum()}\n"
    f"evaluated:         {(results['status'] == 'ok').sum()}\n"
    f"hit@{TOP_N} (actual in top {TOP_N}): {results['hit'].mean():.3f}\n"
    f"recall (actual anywhere in candidates): {results['rank'].notna().mean():.3f}\n"
    f"mean rank when found: {results['rank'].dropna().mean():.2f}\n"
)
(OUT_DIR / "backtest_summary.txt").write_text(summary)
print(summary)
