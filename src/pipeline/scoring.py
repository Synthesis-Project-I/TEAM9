import pandas as pd


def rank_candidates(candidates_df, task_reqs):
    """
    POST-CSP OPTIMIZATION: Grades eligible translators on a 100-point scale.
    Features 'Resource Conservation Mode' to prevent wasting top-tier talent on low-tier tasks.
    """
    if candidates_df.empty:
        return candidates_df

    df = candidates_df.copy()

    w_qual, w_rel, w_marg, w_exp = 40, 30, 20, 10

    wildcard = task_reqs.get("wildcard", "balanced").lower()
    task_type = task_reqs.get("task_type", "Translation")

    if wildcard == "quality":
        w_qual, w_rel, w_marg, w_exp = 60, 20, 10, 10
    elif wildcard == "price":
        w_qual, w_rel, w_marg, w_exp = 20, 20, 50, 10
    elif wildcard in ["deadline", "time", "schedule"]:
        w_qual, w_rel, w_marg, w_exp = 20, 60, 10, 10

    if task_type == "TEST":
        w_qual, w_rel, w_marg, w_exp = 80, 0, 0, 20

    min_quality = task_reqs.get("min_quality", 0.0)

    if wildcard == "quality" or task_type == "TEST":
        norm_quality = df["AVERAGE_QUALITY"] / 10.0
    else:
        excess_quality = (df["AVERAGE_QUALITY"] - min_quality).clip(lower=0)
        norm_quality = (1.0 - (excess_quality / 10.0)).clip(lower=0, upper=1.0)

    norm_reliability = df["ON_TIME_SCORE"]

    pair = task_reqs.get("language_pair")
    max_rate = task_reqs.get("max_hourly_rate", df[pair].max())
    if max_rate > 0:
        norm_margin = ((max_rate - df[pair]) / max_rate).clip(lower=0)
    else:
        norm_margin = 0

    exp_score = pd.Series(0, index=df.index)
    for level, prefix in [("required_subindustry", "SUB"), ("required_industry", "IND"), ("required_industry_group", "GRP")]:
        if level in task_reqs and task_reqs[level]:
            for item in task_reqs[level]:
                col_name = f"{prefix}_{item}"
                if col_name in df.columns:
                    exp_score += df[col_name]
            break

    if wildcard == "quality" or task_type == "TEST":
        norm_expertise = (exp_score / 50.0).clip(upper=1.0)
    else:
        min_exp = 1.0
        excess_exp = (exp_score - min_exp).clip(lower=0)
        norm_expertise = (1.0 - (excess_exp / 50.0)).clip(lower=0, upper=1.0)

    df["SUITABILITY_SCORE"] = (
        (norm_quality * w_qual) +
        (norm_reliability * w_rel) +
        (norm_margin * w_marg) +
        (norm_expertise * w_exp)
    ).round(1)

    return df.sort_values(by="SUITABILITY_SCORE", ascending=False)
