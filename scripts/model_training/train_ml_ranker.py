import argparse
import pickle
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.pipeline.features import prepare_pipeline_tables
from src.pipeline.filtering import TaskAssignmentCSP
from src.pipeline.ml import calculate_efficiency_score, generate_ml_training_data, train_xgboost_model
from utils.config import MODELS_DIR
from utils.data_loader import load_interim_data


def generate_full_historical_training_data(history_df, clients_df, translators_df):
    training_data = []
    clients = clients_df.drop_duplicates("CLIENT_NAME").set_index("CLIENT_NAME")
    translators = translators_df.drop_duplicates("NAME").set_index("NAME")

    for _, row in history_df.iterrows():
        company = str(row.get("MANUFACTURER", "")).strip()
        translator = str(row.get("TRANSLATOR", "")).strip()
        if company not in clients.index or translator not in translators.index:
            continue

        try:
            start_dt = pd.to_datetime(row["START"])
            end_dt = pd.to_datetime(row["END"])
            task_length = float(row.get("HOURS", row.get("FORECAST", row.get("TRANSLATOR_WORKING_TIME", 2.0))))
            window = max(1, (end_dt - start_dt).days + 1)
        except Exception:
            continue

        client = clients.loc[company]
        candidate = translators.loc[translator]
        language_pair = f"{str(row['SOURCE_LANG']).strip()}_{str(row['TARGET_LANG']).strip()}"
        budget = float(client.get("SELLING_HOURLY_PRICE", 100))
        req_qual = float(client.get("MIN_QUALITY", 0))
        rate = candidate.get(language_pair, row.get("HOURLY_RATE", budget))
        if pd.isna(rate):
            rate = row.get("HOURLY_RATE", budget)
        rate = float(rate)
        trans_qual = float(candidate.get("AVERAGE_QUALITY", 0))

        task_reqs = {
            "language_pair": language_pair,
            "max_hourly_rate": budget,
            "min_quality": req_qual,
        }

        training_data.append({
            "req_quality": req_qual,
            "req_daily_capacity": task_length / window,
            "client_budget": budget,
            "trans_quality": trans_qual,
            "trans_on_time": float(candidate.get("ON_TIME_SCORE", 0)),
            "trans_rate": rate,
            "trans_daily_capacity": 0,
            "quality_gap": trans_qual - req_qual,
            "margin_gap": budget - rate,
            "TARGET_EFFICIENCY": calculate_efficiency_score(task_reqs, candidate),
        })

    return pd.DataFrame(training_data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", default="200")
    parser.add_argument("--output", default="xgboost_ranker.pkl")
    args = parser.parse_args()

    data_dict = load_interim_data()
    history_df, clients_df, translators_df = prepare_pipeline_tables(data_dict)
    csp_solver = TaskAssignmentCSP(translators_df)

    if str(args.samples).lower() == "all":
        ml_dataset = generate_full_historical_training_data(history_df, clients_df, translators_df)
        print(f"SUCCESS: Generated {len(ml_dataset)} full historical training rows.")
    else:
        samples = int(args.samples)
        ml_dataset = generate_ml_training_data(
            n_samples=samples,
            raw_historical_df=history_df,
            clients_df=clients_df,
            translators_df=translators_df,
            csp_solver=csp_solver,
        )
    model = train_xgboost_model(ml_dataset)

    MODELS_DIR.mkdir(exist_ok=True)
    output_path = MODELS_DIR / args.output
    with open(output_path, "wb") as f:
        pickle.dump(model, f)
    print(output_path)


if __name__ == "__main__":
    main()
