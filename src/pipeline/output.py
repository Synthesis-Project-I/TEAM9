def recommendation_columns(task_reqs, language_pair):
    """Format top-N recommendations with per-dimension rationale."""
    columns = ["NAME", language_pair, "DAILY_CAPACITY", "AVERAGE_QUALITY", "ON_TIME_SCORE"]
    if "required_subindustry" in task_reqs and task_reqs["required_subindustry"]:
        columns.append(f"SUB_{task_reqs['required_subindustry'][0]}")
    elif "required_industry" in task_reqs and task_reqs["required_industry"]:
        columns.append(f"IND_{task_reqs['required_industry'][0]}")
    elif "required_industry_group" in task_reqs and task_reqs["required_industry_group"]:
        columns.append(f"GRP_{task_reqs['required_industry_group'][0]}")
    return columns


def format_recommendations(candidates_df, task_reqs, language_pair, top_n=10):
    """Return the recommendation columns that exist in the candidate table."""
    columns = recommendation_columns(task_reqs, language_pair)
    if "SUITABILITY_SCORE" in candidates_df.columns:
        columns = ["SUITABILITY_SCORE"] + columns
    if "ML_PREDICTED_SCORE" in candidates_df.columns:
        columns = ["ML_PREDICTED_SCORE"] + columns
    final_cols = [col for col in columns if col in candidates_df.columns]
    return candidates_df[final_cols].head(top_n)
