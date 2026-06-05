import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.pipeline.filtering import TaskAssignmentCSP
from src.pipeline.output import format_recommendations
from src.pipeline.scoring import rank_candidates
from utils.data_loader import load_processed_data


def run_pipeline(task):
    history_df, clients_df, translators_df = load_processed_data()
    csp_solver = TaskAssignmentCSP(translators_df)

    task_requirements = csp_solver.build_client_requirements(
        company_name=task["company_name"],
        clients_df=clients_df,
        historical_df=history_df,
        task_date=task["task_date"],
        task_deadline=task["task_deadline"],
        task_start_time=task["task_start_time"],
        task_end_time=task["task_end_time"],
        task_length_hours=float(task["task_length_hours"]),
        language_pair=task["language_pair"],
        task_type=task.get("task_type", "Translation"),
        followed_by=task.get("followed_by"),
    )

    if not task_requirements:
        return None

    candidates = csp_solver.get_translators_with_fallback(task_requirements)

    if candidates.empty:
        wildcard = task_requirements.get("wildcard", "balanced").lower()
        if wildcard in ["deadline"]:
            candidates = csp_solver.split_task_across_days(task_requirements)
            if candidates.empty:
                candidates = csp_solver.split_task_across_translators(task_requirements, num_translators=2)
        else:
            candidates = csp_solver.split_task_across_translators(task_requirements, num_translators=2)
            if candidates.empty:
                candidates = csp_solver.split_task_across_days(task_requirements)

    if candidates.empty:
        csp_solver.diagnose_bottleneck(task_requirements)
        return candidates

    ranked = rank_candidates(candidates, task_requirements)
    return format_recommendations(ranked, task_requirements, task["language_pair"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("task_json")
    args = parser.parse_args()

    with open(args.task_json, "r", encoding="utf-8") as f:
        task = json.load(f)

    result = run_pipeline(task)
    if result is None:
        print("Client not found.")
    elif result.empty:
        print("No eligible translators found.")
    else:
        print(result.to_string(index=False))


if __name__ == "__main__":
    main()
