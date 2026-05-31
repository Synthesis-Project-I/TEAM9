import numpy as np
import pandas as pd


def calculate_efficiency_score(task_reqs, candidate_row):
    """
    The Goldilocks Formula: Rewards high profit margin,
    but strictly penalizes Over-Specification (wasting premium talent).
    """
    budget = task_reqs.get("max_hourly_rate", 100)
    rate = candidate_row.get(task_reqs["language_pair"], budget)
    margin = max(0, budget - rate) / budget

    req_qual = task_reqs.get("min_quality", 0)
    trans_qual = candidate_row.get("AVERAGE_QUALITY", 0)
    excess_quality = max(0, trans_qual - req_qual)
    alpha = 0.15
    quality_efficiency = max(0, 1.0 - (alpha * excess_quality))

    score = (0.6 * margin) + (0.4 * quality_efficiency)
    return round(score, 4)


def generate_ml_training_data(n_samples, raw_historical_df, clients_df, translators_df, csp_solver):
    """
    Builds the Training Dataset. For every historical task, it extracts the features
    and calculates the Target Label (Y) for the XGBoost model.
    """
    print(f"--- GENERATING ML TRAINING DATA ({n_samples} TASKS) ---")
    training_data = []

    indices = np.random.choice(raw_historical_df.index, n_samples, replace=False)

    for idx in indices:
        row = raw_historical_df.loc[idx]
        try:
            start_dt = pd.to_datetime(row["START"])
            end_dt = pd.to_datetime(row["END"])
            task_length = float(row.get("HOURS", row.get("FORECAST", row.get("TRANSLATOR_WORKING_TIME", 2.0))))
            window = max(1, (end_dt - start_dt).days + 1)

            task_reqs = csp_solver.build_client_requirements(
                company_name=str(row["MANUFACTURER"]).strip(),
                clients_df=clients_df,
                historical_df=raw_historical_df,
                task_date=start_dt.strftime("%Y-%m-%d"),
                task_deadline=end_dt.strftime("%Y-%m-%d"),
                task_start_time=start_dt.strftime("%H:%M"),
                task_end_time=end_dt.strftime("%H:%M"),
                task_length_hours=task_length,
                language_pair=f"{str(row['SOURCE_LANG']).strip()}_{str(row['TARGET_LANG']).strip()}",
                task_type=str(row["TASK_TYPE"]).strip(),
            )
            if not task_reqs:
                continue
        except Exception:
            continue

        candidates = csp_solver.get_eligible_translators(task_reqs)
        if candidates.empty:
            continue

        for _, candidate in candidates.iterrows():
            budget = task_reqs.get("max_hourly_rate", 100)
            rate = candidate.get(task_reqs["language_pair"], budget)
            req_qual = task_reqs.get("min_quality", 0)
            trans_qual = candidate.get("AVERAGE_QUALITY", 0)

            features = {
                "req_quality": req_qual,
                "req_daily_capacity": task_length / window,
                "client_budget": budget,
                "trans_quality": trans_qual,
                "trans_on_time": candidate.get("ON_TIME_SCORE", 0),
                "trans_rate": rate,
                "trans_daily_capacity": candidate.get("DAILY_CAPACITY", 0),
                "quality_gap": trans_qual - req_qual,
                "margin_gap": budget - rate,
                "TARGET_EFFICIENCY": calculate_efficiency_score(task_reqs, candidate),
            }
            training_data.append(features)

    df_train = pd.DataFrame(training_data)
    print(f"SUCCESS: Generated {len(df_train)} training rows.")
    return df_train


def train_xgboost_model(ml_dataset):
    """
    Trains the gradient boosting model to predict resource efficiency
    and plots the learning curve to prove the model is converging.
    """
    import matplotlib.pyplot as plt
    import xgboost as xgb
    from sklearn.model_selection import train_test_split

    print("\n--- TRAINING XGBOOST MODEL ---")

    X = ml_dataset.drop(columns=["TARGET_EFFICIENCY"])
    y = ml_dataset["TARGET_EFFICIENCY"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = xgb.XGBRegressor(
        objective="reg:squarederror",
        n_estimators=100,
        learning_rate=0.1,
        max_depth=4,
        random_state=42,
    )

    model.fit(
        X_train,
        y_train,
        eval_set=[(X_train, y_train), (X_test, y_test)],
        verbose=10,
    )

    print("\n XGBoost Model successfully trained!")

    results = model.evals_result()
    epochs = len(results["validation_0"]["rmse"])
    x_axis = range(0, epochs)

    plt.figure(figsize=(10, 5))
    plt.plot(x_axis, results["validation_0"]["rmse"], label="Train Loss (Error)", color="blue", linewidth=2)
    plt.plot(x_axis, results["validation_1"]["rmse"], label="Validation Loss (Error)", color="orange", linewidth=2)
    plt.title("XGBoost Learning Curve")
    plt.xlabel("Boosting Rounds (Number of Trees)")
    plt.ylabel("RMSE (Root Mean Squared Error)")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.show()

    importance = pd.DataFrame({
        "Feature": X.columns,
        "Importance": model.feature_importances_,
    }).sort_values(by="Importance", ascending=False)

    print("\n--- ML FEATURE IMPORTANCE ---")
    print(importance)

    return model


def rank_candidates_ml(candidates_df, task_reqs, ml_model):
    """
    PRODUCTION RANKER: Uses the trained XGBoost model to instantly predict
    the 'Goldilocks' efficiency score for all eligible candidates.
    """
    if candidates_df.empty:
        return candidates_df

    df = candidates_df.copy()

    budget = task_reqs.get("max_hourly_rate", 100)
    req_qual = task_reqs.get("min_quality", 0)
    window = task_reqs.get("window_days", 1)
    req_daily = task_reqs.get("task_length_hours", 8) / window
    pair = task_reqs.get("language_pair")

    X_pred = pd.DataFrame({
        "req_quality": req_qual,
        "req_daily_capacity": req_daily,
        "client_budget": budget,
        "trans_quality": df["AVERAGE_QUALITY"],
        "trans_on_time": df["ON_TIME_SCORE"],
        "trans_rate": df[pair].fillna(budget),
        "trans_daily_capacity": df.get("DAILY_CAPACITY", 0),
        "quality_gap": df["AVERAGE_QUALITY"] - req_qual,
        "margin_gap": budget - df[pair].fillna(budget),
    })

    df["ML_PREDICTED_SCORE"] = ml_model.predict(X_pred)
    return df.sort_values(by="ML_PREDICTED_SCORE", ascending=False)
