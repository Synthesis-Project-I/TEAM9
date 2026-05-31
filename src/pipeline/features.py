import numpy as np
import pandas as pd


def clean_history_data(data_df):
    """Create the cleaned historical task table used by the CSP and ML code."""
    df1 = data_df.copy()
    df1 = df1.drop(columns=["PROJECT_ID", "PM", "TASK_ID", "ASSIGNED", "RECEIVED", "CLOSE", "HOURLY_RATE", "MANUFACTURER_SECTOR"], errors="ignore")
    cols = ["TRANSLATOR"] + [c for c in df1.columns if c != "TRANSLATOR"]
    df1 = df1[cols]

    df1["START"] = pd.to_datetime(df1["START"], errors="coerce")
    df1["END"] = pd.to_datetime(df1["END"], errors="coerce")
    df1["TASK_LENGTH"] = (df1["END"] - df1["START"]).dt.total_seconds() / 3600

    df1["WORKING"] = pd.to_datetime(df1["WORKING"], errors="coerce")
    df1["DELIVERED"] = pd.to_datetime(df1["DELIVERED"], errors="coerce")
    df1["TRANSLATOR_WORKING_TIME"] = (df1["DELIVERED"] - df1["WORKING"]).dt.total_seconds() / 3600

    cost_col = "COST" if "COST" in df1.columns else None
    if cost_col:
        df1 = df1[(df1["TASK_LENGTH"] > 0.01) & (df1["TRANSLATOR_WORKING_TIME"] > 0.01) & (df1["SOURCE_LANG"] != df1["TARGET_LANG"]) & (df1[cost_col] > 0)]
    else:
        df1 = df1[(df1["TASK_LENGTH"] > 0.01) & (df1["TRANSLATOR_WORKING_TIME"] > 0.01) & (df1["SOURCE_LANG"] != df1["TARGET_LANG"])]

    df1["ON_TIME"] = (df1["END"] >= df1["DELIVERED"]).astype(int)
    return df1


def build_translator_statistics(history_df, schedules_df, translators_cost_pairs_df):
    """Create the translator statistics/information datasheet."""
    df1 = history_df.copy()
    df2 = schedules_df.copy()
    df4 = translators_cost_pairs_df.copy()

    translators_df = df2[[c for c in df2.columns]].copy()

    df4["PAIR"] = df4["SOURCE_LANG"] + "_" + df4["TARGET_LANG"]
    pivot = df4.pivot_table(
        index="TRANSLATOR",
        columns="PAIR",
        values="HOURLY_RATE",
        aggfunc="first",
    ).reset_index()

    translators_df = translators_df.merge(
        pivot,
        left_on="NAME",
        right_on="TRANSLATOR",
        how="left",
    )

    translators_df = translators_df.merge(
        df1.groupby("TRANSLATOR")["QUALITY_EVALUATION"]
            .mean()
            .reset_index()
            .rename(columns={"TRANSLATOR": "NAME", "QUALITY_EVALUATION": "AVERAGE_QUALITY"}),
        on="NAME",
        how="left",
    )

    translators_df = translators_df.merge(
        df1.groupby("TRANSLATOR")["ON_TIME"]
            .mean()
            .reset_index()
            .rename(columns={"TRANSLATOR": "NAME", "ON_TIME": "ON_TIME_SCORE"}),
        on="NAME",
        how="left",
    )

    task_exp = df1.copy()
    task_exp["TASK_TYPE"] = task_exp["TASK_TYPE"] + "_experience"
    pivot = task_exp.pivot_table(
        index="TRANSLATOR",
        columns="TASK_TYPE",
        values="TRANSLATOR_WORKING_TIME",
        aggfunc="sum",
    ).reset_index()
    pivot = pivot.rename(columns={"TRANSLATOR": "NAME"})
    translators_df = translators_df.merge(pivot, on="NAME", how="left")
    exp_cols = [c for c in translators_df.columns if c.endswith("_experience")]
    translators_df[exp_cols] = translators_df[exp_cols].fillna(0)

    translators_df["TIME_TO_START"] = np.nan

    df1["SUB_CLEAN"] = "SUB_" + df1["MANUFACTURER_SUBINDUSTRY"].astype(str)
    sub_pivot = df1.pivot_table(index="TRANSLATOR", columns="SUB_CLEAN", values="TRANSLATOR_WORKING_TIME", aggfunc="sum").reset_index()
    sub_pivot = sub_pivot.rename(columns={"TRANSLATOR": "NAME"})
    translators_df = translators_df.merge(sub_pivot, on="NAME", how="left")

    df1["IND_CLEAN"] = "IND_" + df1["MANUFACTURER_INDUSTRY"].astype(str)
    ind_pivot = df1.pivot_table(index="TRANSLATOR", columns="IND_CLEAN", values="TRANSLATOR_WORKING_TIME", aggfunc="sum").reset_index()
    ind_pivot = ind_pivot.rename(columns={"TRANSLATOR": "NAME"})
    translators_df = translators_df.merge(ind_pivot, on="NAME", how="left")

    df1["GRP_CLEAN"] = "GRP_" + df1["MANUFACTURER_INDUSTRY_GROUP"].astype(str)
    grp_pivot = df1.pivot_table(index="TRANSLATOR", columns="GRP_CLEAN", values="TRANSLATOR_WORKING_TIME", aggfunc="sum").reset_index()
    grp_pivot = grp_pivot.rename(columns={"TRANSLATOR": "NAME"})
    translators_df = translators_df.merge(grp_pivot, on="NAME", how="left")

    industry_cols = [c for c in translators_df.columns if str(c).startswith("SUB_") or str(c).startswith("IND_") or str(c).startswith("GRP_")]
    translators_df[industry_cols] = translators_df[industry_cols].fillna(0)

    return translators_df


def prepare_pipeline_tables(data_dict):
    """Prepare the cleaned history table and translator statistics table from the workbook sheets."""
    history_df = clean_history_data(data_dict["Data"])
    translators_df = build_translator_statistics(
        history_df,
        data_dict["Schedules"],
        data_dict["TranslatorsCost+Pairs"],
    )
    return history_df, data_dict["Clients"], translators_df
