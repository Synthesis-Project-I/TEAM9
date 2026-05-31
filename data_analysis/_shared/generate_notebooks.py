from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent

import nbformat as nbf
from nbclient import NotebookClient


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ANALYSIS_DIR = PROJECT_ROOT / "data_analysis"


COMMON_SETUP = dedent(
    """
    from pathlib import Path
    import sys
    import warnings

    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    import seaborn as sns
    from IPython.display import Markdown, display

    ROOT = Path.cwd().resolve()
    while not (ROOT / "agents.md").exists():
        if ROOT.parent == ROOT:
            raise RuntimeError("Could not locate project root from notebook directory.")
        ROOT = ROOT.parent

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    warnings.filterwarnings("ignore")
    pd.options.display.max_columns = 120
    pd.options.display.max_rows = 50

    from data_analysis._shared.eda_utils import (
        ENRICHED_PATH,
        FEATURE_GROUPS,
        NUMERIC_OUTLIER_COLUMNS,
        build_enriched_tasks,
        categorical_variants,
        cross_sheet_consistency_report,
        detect_outliers,
        diagnose_client_unmatched,
        diagnose_pair_unmatched,
        diagnose_schedule_unmatched,
        dtype_audit,
        exact_duplicates,
        join_datasets,
        load_all_data,
        load_enriched_tasks,
        missing_summary,
        missingness_by_group,
        missingness_correlation,
        near_duplicates_data,
        proofread_reviewer_comparison,
        same_language_examples,
        same_language_report,
        set_plot_style,
        sheet_dimensions_report,
        summarize_join_integrity,
        timestamp_logic_report,
        timestamp_violation_samples,
        translator_on_time_summary,
        translator_quality_summary,
        wilson_interval,
        zero_value_report,
    )

    set_plot_style()
    sheets = load_all_data()
    data = sheets["data"]
    schedules = sheets["schedules"]
    clients = sheets["clients"]
    pairs = sheets["pairs"]
    print(f"Loaded Data={data.shape}, Schedules={schedules.shape}, Clients={clients.shape}, Pairs={pairs.shape}")
    """
).strip()


def md(text: str):
    return nbf.v4.new_markdown_cell(dedent(text).strip())


def code(text: str):
    return nbf.v4.new_code_cell(dedent(text).strip())


def notebook_specs() -> dict[Path, list]:
    specs: dict[Path, list] = {}

    specs[DATA_ANALYSIS_DIR / "01_data_quality" / "data_quality_report.ipynb"] = [
        md(
            """
            # Data Quality Report

            This notebook audits all four source sheets used for the TARS exploratory analysis.
            """
        ),
        code(COMMON_SETUP),
        code(
            """
            display(sheet_dimensions_report(sheets))
            """
        ),
        code(
            """
            for short_name, sheet_name in {
                "data": "Data",
                "schedules": "Schedules",
                "clients": "Clients",
                "pairs": "TranslatorsCost+Pairs",
            }.items():
                display(Markdown(f"## {sheet_name} dtype audit"))
                audit = dtype_audit(sheets[short_name], sheet_name)
                display(audit)
                mismatches = audit.loc[~audit["matches_expectation"]]
                if not mismatches.empty:
                    display(Markdown("Columns with expectation mismatches"))
                    display(mismatches)
            """
        ),
        code(
            """
            for short_name, sheet_name in {
                "data": "Data",
                "schedules": "Schedules",
                "clients": "Clients",
                "pairs": "TranslatorsCost+Pairs",
            }.items():
                display(Markdown(f"## Missing values: {sheet_name}"))
                display(missing_summary(sheets[short_name]))

            data_missing_cols = missing_summary(data).query("missing_count > 0")["column"].tolist()
            top_missing_cols = data_missing_cols[:6]
            if top_missing_cols:
                display(Markdown("## Missingness correlation for the most-missing Data columns"))
                corr = missingness_correlation(data[top_missing_cols])
                if not corr.empty:
                    plt.figure(figsize=(8, 6))
                    sns.heatmap(corr, annot=True, cmap="Blues", fmt=".2f")
                    plt.title("Missingness correlation")
                    plt.show()

                display(Markdown("## Missingness by task type"))
                display(missingness_by_group(data, top_missing_cols, "TASK_TYPE_CLEAN").sort_values("TASK_TYPE_CLEAN"))

                display(Markdown("## Missingness by task start year"))
                data_with_year = data.assign(START_YEAR=data["START"].dt.year)
                display(missingness_by_group(data_with_year, top_missing_cols, "START_YEAR").sort_values("START_YEAR"))
            """
        ),
        code(
            """
            duplicate_summary = pd.DataFrame(
                [
                    {"sheet": "Data", "exact_duplicate_rows": len(exact_duplicates(data))},
                    {"sheet": "Schedules", "exact_duplicate_rows": len(exact_duplicates(schedules))},
                    {"sheet": "Clients", "exact_duplicate_rows": len(exact_duplicates(clients))},
                    {"sheet": "TranslatorsCost+Pairs", "exact_duplicate_rows": len(exact_duplicates(pairs))},
                ]
            )
            display(duplicate_summary)

            near_dup = near_duplicates_data(data)
            near_dup_summary = pd.DataFrame(
                [
                    {"check": key, "rows_flagged": len(value)}
                    for key, value in near_dup.items()
                ]
            )
            display(near_dup_summary)

            for key, value in near_dup.items():
                display(Markdown(f"### Sample rows: {key}"))
                display(value.head(20))
            """
        ),
        code(
            """
            outlier_report = detect_outliers(data, NUMERIC_OUTLIER_COLUMNS)
            display(outlier_report)

            fig, axes = plt.subplots(4, 2, figsize=(14, 18))
            for idx, column in enumerate(NUMERIC_OUTLIER_COLUMNS):
                sns.boxplot(x=data[column], ax=axes[idx, 0], color="#7fb3d5")
                axes[idx, 0].set_title(f"{column} boxplot")

                sns.histplot(data[column].dropna(), bins=60, ax=axes[idx, 1], color="#2874a6")
                axes[idx, 1].set_title(f"{column} histogram")
                if column in {"HOURS", "COST"}:
                    axes[idx, 1].set_xscale("log")
                    axes[idx, 1].set_title(f"{column} histogram (log x-scale)")
            plt.tight_layout()
            plt.show()
            """
        ),
        code(
            """
            display(Markdown("## Categorical inconsistencies"))
            for column in ["TASK_TYPE", "SOURCE_LANG", "TARGET_LANG", "TRANSLATOR", "MANUFACTURER"]:
                display(Markdown(f"### Variants for {column}"))
                variants = categorical_variants(data[column])
                display(variants.head(50) if not variants.empty else pd.DataFrame({"message": [f"No multi-variant normalized families detected for {column}."]}))
            """
        ),
        code(
            """
            display(timestamp_logic_report(data))
            violation_samples = timestamp_violation_samples(data)
            for check_name, sample_df in violation_samples.items():
                display(Markdown(f"### Sample violations: {check_name}"))
                display(sample_df)
            """
        ),
        code(
            """
            display(zero_value_report(data))

            zero_cases = data.loc[(data["HOURS"].fillna(0) == 0) | (data["COST"].fillna(0) == 0)].copy()
            display(
                zero_cases.groupby("TASK_TYPE_CLEAN")
                .agg(
                    rows=("TASK_ID", "size"),
                    total_hours=("HOURS", "sum"),
                    total_cost=("COST", "sum"),
                    median_duration_hours=("HOURS", "median"),
                )
                .sort_values("rows", ascending=False)
                .head(20)
            )

            display(same_language_report(data))
            display(same_language_examples(data, limit=25))
            if not same_language_examples(data, limit=1).empty:
                same_lang_subset = data.loc[
                    data["SOURCE_LANG_CLEAN"].eq(data["TARGET_LANG_CLEAN"]),
                    ["TRANSLATOR", "MANUFACTURER", "TASK_ID"],
                ]
                display(
                    same_lang_subset.groupby("TRANSLATOR").size().sort_values(ascending=False).head(15).rename("tasks").reset_index()
                )
                display(
                    same_lang_subset.groupby("MANUFACTURER").size().sort_values(ascending=False).head(15).rename("tasks").reset_index()
                )
            """
        ),
        code(
            """
            display(cross_sheet_consistency_report(data, schedules, clients, pairs))

            joined = join_datasets()
            client_diag = diagnose_client_unmatched(joined, clients)
            pair_diag = diagnose_pair_unmatched(joined, pairs)
            schedule_diag = diagnose_schedule_unmatched(joined, schedules)

            display(Markdown("## Unmatched client diagnostics"))
            display(client_diag["diagnosis"].value_counts(dropna=False).rename_axis("diagnosis").reset_index(name="rows"))
            display(client_diag.head(30))

            display(Markdown("## Unmatched pair diagnostics"))
            display(pair_diag["diagnosis"].value_counts(dropna=False).rename_axis("diagnosis").reset_index(name="rows"))
            display(pair_diag.head(30))

            display(Markdown("## Unmatched schedule diagnostics"))
            display(schedule_diag["diagnosis"].value_counts(dropna=False).rename_axis("diagnosis").reset_index(name="rows"))
            display(schedule_diag.head(30))
            """
        ),
    ]

    specs[DATA_ANALYSIS_DIR / "02_descriptive_overview" / "overview.ipynb"] = [
        md(
            """
            # Descriptive Overview

            High-level descriptive statistics for the historical task log.
            """
        ),
        code(COMMON_SETUP),
        code(
            """
            overview = pd.DataFrame(
                [
                    {"metric": "Total tasks", "value": len(data)},
                    {"metric": "Unique projects", "value": data["PROJECT_ID"].nunique()},
                    {"metric": "Unique PMs", "value": data["PM"].nunique()},
                    {"metric": "Unique translators", "value": data["TRANSLATOR"].nunique()},
                    {"metric": "Unique clients", "value": data["MANUFACTURER"].nunique()},
                ]
            )
            display(overview)
            """
        ),
        code(
            """
            task_type_dist = (
                data["TASK_TYPE_CLEAN"]
                .value_counts(dropna=False)
                .rename_axis("TASK_TYPE")
                .reset_index(name="task_count")
            )
            task_type_dist["proportion_pct"] = (task_type_dist["task_count"] / len(data) * 100).round(2)
            display(task_type_dist)

            plt.figure(figsize=(12, 6))
            sns.barplot(data=task_type_dist, x="TASK_TYPE", y="task_count", color="#1f77b4")
            plt.xticks(rotation=35, ha="right")
            plt.title("Task type distribution")
            plt.show()
            """
        ),
        code(
            """
            source_dist = data["SOURCE_LANG"].value_counts().rename_axis("SOURCE_LANG").reset_index(name="count")
            target_dist = data["TARGET_LANG"].value_counts().rename_axis("TARGET_LANG").reset_index(name="count")
            display(source_dist.head(20))
            display(target_dist.head(20))

            fig, axes = plt.subplots(1, 2, figsize=(18, 8))
            sns.barplot(data=source_dist.head(20), x="count", y="SOURCE_LANG", ax=axes[0], color="#2a9d8f")
            axes[0].set_title("Top 20 source languages")
            sns.barplot(data=target_dist.head(20), x="count", y="TARGET_LANG", ax=axes[1], color="#e76f51")
            axes[1].set_title("Top 20 target languages")
            plt.tight_layout()
            plt.show()
            """
        ),
        code(
            """
            data["LANGUAGE_PAIR"] = data["SOURCE_LANG"] + " -> " + data["TARGET_LANG"]
            pair_dist = data["LANGUAGE_PAIR"].value_counts().head(20).rename_axis("language_pair").reset_index(name="count")
            display(pair_dist)

            plt.figure(figsize=(12, 8))
            sns.barplot(data=pair_dist, x="count", y="language_pair", color="#577590")
            plt.title("Top 20 language pairs")
            plt.show()
            """
        ),
        code(
            """
            quality_stats = data["QUALITY_EVALUATION"].agg(["count", "mean", "median", "std", "min", "max"]).to_frame("value")
            display(quality_stats)

            plt.figure(figsize=(10, 5))
            sns.histplot(data["QUALITY_EVALUATION"].dropna(), bins=30, color="#264653")
            plt.title("Quality evaluation distribution")
            plt.show()
            """
        ),
        code(
            """
            fig, axes = plt.subplots(1, 2, figsize=(16, 6))
            sns.histplot(data["HOURS"].dropna(), bins=80, ax=axes[0], color="#457b9d")
            axes[0].set_xscale("log")
            axes[0].set_title("Hours distribution (log x-scale)")

            sns.histplot(data["COST"].dropna(), bins=80, ax=axes[1], color="#f4a261")
            axes[1].set_title("Cost distribution")
            plt.tight_layout()
            plt.show()

            cost_hours_sample = data[["HOURS", "COST"]].dropna().sample(30000, random_state=42)
            plt.figure(figsize=(8, 6))
            sns.scatterplot(data=cost_hours_sample, x="HOURS", y="COST", alpha=0.25, s=15)
            plt.xscale("log")
            plt.yscale("log")
            plt.title("Cost vs hours")
            plt.show()
            """
        ),
        code(
            """
            hourly_rate_compare = pd.DataFrame(
                {
                    "Data sheet": data["HOURLY_RATE"].dropna(),
                    "TranslatorsCost+Pairs sheet": pairs["HOURLY_RATE"].dropna(),
                }
            )
            display(
                pd.DataFrame(
                    {
                        "Data sheet": data["HOURLY_RATE"].describe(),
                        "TranslatorsCost+Pairs sheet": pairs["HOURLY_RATE"].describe(),
                    }
                )
            )

            plt.figure(figsize=(10, 6))
            sns.kdeplot(data["HOURLY_RATE"].dropna(), label="Data sheet", fill=True, alpha=0.35)
            sns.kdeplot(pairs["HOURLY_RATE"].dropna(), label="TranslatorsCost+Pairs sheet", fill=True, alpha=0.35)
            plt.title("Hourly rate distributions")
            plt.legend()
            plt.show()
            """
        ),
        code(
            """
            pm_dist = data["PM"].value_counts().rename_axis("PM").reset_index(name="task_count")
            display(pm_dist.head(20))

            plt.figure(figsize=(10, 6))
            sns.barplot(data=pm_dist.head(15), x="task_count", y="PM", color="#8d99ae")
            plt.title("Top 15 PMs by task count")
            plt.show()
            """
        ),
        code(
            """
            sector_dist = data["MANUFACTURER_SECTOR"].value_counts().rename_axis("sector").reset_index(name="task_count")
            display(sector_dist)

            pie_data = sector_dist.head(10).copy()
            pie_data.loc[len(pie_data)] = {
                "sector": "Other",
                "task_count": sector_dist.iloc[10:]["task_count"].sum(),
            }
            plt.figure(figsize=(8, 8))
            plt.pie(pie_data["task_count"], labels=pie_data["sector"], autopct="%1.1f%%", startangle=90)
            plt.title("Sector share of tasks")
            plt.show()
            """
        ),
    ]

    specs[DATA_ANALYSIS_DIR / "03_translators" / "translator_profiles.ipynb"] = [
        md(
            """
            # Translator Profiles

            Workload, quality, punctuality, rate consistency, and schedule patterns at translator level.
            """
        ),
        code(COMMON_SETUP),
        code(
            """
            display(pd.DataFrame([{"metric": "Unique translators in task log", "value": data["TRANSLATOR"].nunique()}]))

            task_count_per_translator = (
                data.groupby("TRANSLATOR")
                .size()
                .rename("task_count")
                .reset_index()
                .sort_values("task_count", ascending=False)
            )
            display(task_count_per_translator.head(20))

            plt.figure(figsize=(10, 6))
            sns.histplot(task_count_per_translator["task_count"], bins=60, color="#3a86ff")
            plt.yscale("log")
            plt.title("Task count per translator")
            plt.show()
            """
        ),
        code(
            """
            hours_per_translator = (
                data.groupby("TRANSLATOR")["HOURS"]
                .sum()
                .sort_values(ascending=False)
                .rename("total_hours")
                .reset_index()
            )
            display(hours_per_translator.head(20))

            plt.figure(figsize=(10, 6))
            sns.histplot(hours_per_translator["total_hours"], bins=60, color="#2a9d8f")
            plt.yscale("log")
            plt.title("Total hours per translator")
            plt.show()
            """
        ),
        code(
            """
            quality_summary = translator_quality_summary(data)
            display(quality_summary.head(20))
            display(
                quality_summary.query("scored_tasks >= 30")
                .sort_values("avg_quality", ascending=False)
                .head(20)
            )

            quality_sample = quality_summary.query("scored_tasks >= 5").copy()
            plt.figure(figsize=(8, 6))
            sns.scatterplot(
                data=quality_sample,
                x="scored_tasks",
                y="avg_quality",
                size="task_count",
                alpha=0.5,
                sizes=(20, 400),
            )
            plt.xscale("log")
            plt.title("Average quality vs scored task count")
            plt.show()
            """
        ),
        code(
            """
            enriched = load_enriched_tasks()
            on_time_summary = translator_on_time_summary(enriched)
            display(on_time_summary.head(20))

            plt.figure(figsize=(10, 6))
            sns.histplot(on_time_summary["on_time_rate"].dropna(), bins=40, color="#ffb703")
            plt.title("On-time delivery rate per translator")
            plt.show()
            """
        ),
        code(
            """
            pair_counts = (
                data.assign(language_pair=data["SOURCE_LANG"] + " -> " + data["TARGET_LANG"])
                .groupby(["TRANSLATOR", "language_pair"])
                .size()
                .rename("pair_tasks")
                .reset_index()
            )
            pair_coverage = pair_counts.groupby("TRANSLATOR").agg(
                distinct_pairs=("language_pair", "nunique"),
                top_pair_tasks=("pair_tasks", "max"),
                total_pair_tasks=("pair_tasks", "sum"),
            )
            pair_coverage["top_pair_share"] = pair_coverage["top_pair_tasks"] / pair_coverage["total_pair_tasks"]
            pair_coverage["profile_type"] = np.select(
                [
                    (pair_coverage["distinct_pairs"] <= 2) | (pair_coverage["top_pair_share"] >= 0.8),
                    (pair_coverage["distinct_pairs"] >= 6) & (pair_coverage["top_pair_share"] < 0.5),
                ],
                ["Specialist", "Generalist"],
                default="Mixed",
            )
            display(pair_coverage["profile_type"].value_counts().rename_axis("profile_type").reset_index(name="translators"))
            display(pair_coverage.sort_values("distinct_pairs", ascending=False).head(20))

            plt.figure(figsize=(10, 6))
            sns.histplot(pair_coverage["distinct_pairs"], bins=30, color="#8338ec")
            plt.title("Distinct language pairs per translator")
            plt.show()
            """
        ),
        code(
            """
            joined = join_datasets()
            rate_compare = joined.loc[joined["PAIR_HOURLY_RATE"].notna(), ["TRANSLATOR", "HOURLY_RATE", "PAIR_HOURLY_RATE"]].copy()
            rate_compare["rate_gap"] = rate_compare["HOURLY_RATE"] - rate_compare["PAIR_HOURLY_RATE"]
            display(rate_compare["rate_gap"].describe().to_frame("value"))
            display(rate_compare.groupby("TRANSLATOR")["rate_gap"].mean().sort_values(ascending=False).head(20).rename("avg_gap").reset_index())
            display(rate_compare.groupby("TRANSLATOR")["rate_gap"].mean().sort_values().head(20).rename("avg_gap").reset_index())
            """
        ),
        code(
            """
            schedules = schedules.copy()
            schedules["WORKING_DAYS_PER_WEEK"] = schedules[["MON", "TUES", "WED", "THURS", "FRI", "SAT", "SUN"]].sum(axis=1)
            schedules["WEEKEND_WORKER"] = ((schedules["SAT"] == 1) | (schedules["SUN"] == 1))

            shift_start = pd.to_datetime(schedules["START"], format="%H:%M:%S", errors="coerce")
            shift_end = pd.to_datetime(schedules["END"], format="%H:%M:%S", errors="coerce")
            schedules["SHIFT_START_HOUR"] = shift_start.dt.hour + shift_start.dt.minute / 60
            schedules["SHIFT_END_HOUR"] = shift_end.dt.hour + shift_end.dt.minute / 60
            schedules["NIGHT_SHIFT"] = schedules["SHIFT_END_HOUR"] <= schedules["SHIFT_START_HOUR"]

            display(schedules["WORKING_DAYS_PER_WEEK"].value_counts().sort_index().rename_axis("working_days").reset_index(name="translators"))
            display(schedules.loc[schedules["WEEKEND_WORKER"], ["NAME", "START", "END"]].head(25))
            display(schedules.loc[schedules["NIGHT_SHIFT"], ["NAME", "START", "END"]].head(25))

            fig, axes = plt.subplots(1, 2, figsize=(14, 5))
            sns.histplot(schedules["SHIFT_START_HOUR"].dropna(), bins=24, ax=axes[0], color="#06d6a0")
            axes[0].set_title("Shift start hour")
            sns.histplot(schedules["SHIFT_END_HOUR"].dropna(), bins=24, ax=axes[1], color="#ef476f")
            axes[1].set_title("Shift end hour")
            plt.tight_layout()
            plt.show()
            """
        ),
        code(
            """
            tenure = (
                data.groupby("TRANSLATOR")
                .agg(first_task=("START", "min"), last_task=("START", "max"), total_tasks=("TASK_ID", "size"))
                .reset_index()
            )
            tenure["active_days"] = (tenure["last_task"] - tenure["first_task"]).dt.days
            display(tenure.sort_values("active_days", ascending=False).head(20))

            plt.figure(figsize=(10, 6))
            sns.histplot(tenure["active_days"].dropna(), bins=50, color="#118ab2")
            plt.title("Translator active span in days")
            plt.show()
            """
        ),
    ]

    specs[DATA_ANALYSIS_DIR / "04_clients_and_tasks" / "clients_and_task_types.ipynb"] = [
        md(
            """
            # Clients and Task Types

            Client mix, client constraints, sector/task patterns, and review workflow behavior.
            """
        ),
        code(COMMON_SETUP),
        code(
            """
            overlap = len(set(data["MANUFACTURER"]) & set(clients["CLIENT_NAME"]))
            display(
                pd.DataFrame(
                    [
                        {"metric": "Unique clients in Data", "value": data["MANUFACTURER"].nunique()},
                        {"metric": "Unique clients in Clients sheet", "value": clients["CLIENT_NAME"].nunique()},
                        {"metric": "Exact overlap", "value": overlap},
                    ]
                )
            )
            """
        ),
        code(
            """
            client_volume = (
                data.groupby("MANUFACTURER")
                .agg(task_count=("TASK_ID", "size"), total_hours=("HOURS", "sum"))
                .sort_values("task_count", ascending=False)
                .reset_index()
            )
            display(client_volume.head(20))
            display(client_volume.sort_values("total_hours", ascending=False).head(20))
            """
        ),
        code(
            """
            display(clients["MIN_QUALITY"].describe().to_frame("value"))
            zero_threshold_share = (clients["MIN_QUALITY"].fillna(0) == 0).mean() * 100
            display(pd.DataFrame([{"metric": "Clients with MIN_QUALITY = 0 (%)", "value": round(zero_threshold_share, 2)}]))

            plt.figure(figsize=(10, 5))
            sns.histplot(clients["MIN_QUALITY"].dropna(), bins=25, color="#90be6d")
            plt.title("Client minimum quality threshold")
            plt.show()
            """
        ),
        code(
            """
            display(clients["SELLING_HOURLY_PRICE"].describe().to_frame("value"))
            plt.figure(figsize=(10, 5))
            sns.histplot(clients["SELLING_HOURLY_PRICE"].dropna(), bins=30, color="#f3722c")
            plt.title("Selling hourly price distribution")
            plt.show()

            wildcard_dist = clients["WILDCARD_CLEAN"].value_counts(dropna=False).rename_axis("wildcard").reset_index(name="clients")
            display(wildcard_dist)
            plt.figure(figsize=(8, 5))
            sns.barplot(data=wildcard_dist, x="wildcard", y="clients", color="#577590")
            plt.title("Wildcard distribution")
            plt.show()
            """
        ),
        code(
            """
            top_clients = data["MANUFACTURER"].value_counts().head(12).index
            client_task_mix = pd.crosstab(
                data.loc[data["MANUFACTURER"].isin(top_clients), "MANUFACTURER"],
                data.loc[data["MANUFACTURER"].isin(top_clients), "TASK_TYPE_CLEAN"],
                normalize="index",
            )
            display(client_task_mix)

            plt.figure(figsize=(12, 8))
            sns.heatmap(client_task_mix, cmap="YlGnBu", annot=True, fmt=".2f")
            plt.title("Task type mix for the most active clients")
            plt.show()
            """
        ),
        code(
            """
            sector_breakdown = (
                data["MANUFACTURER_SECTOR"]
                .value_counts()
                .rename_axis("sector")
                .reset_index(name="task_count")
            )
            display(sector_breakdown)

            plt.figure(figsize=(12, 7))
            sns.barplot(data=sector_breakdown.head(15), x="task_count", y="sector", color="#43aa8b")
            plt.title("Top sectors by task volume")
            plt.show()
            """
        ),
        code(
            """
            client_quality = (
                data.groupby("MANUFACTURER")
                .agg(avg_quality=("QUALITY_EVALUATION", "mean"), scored_tasks=("QUALITY_EVALUATION", "count"))
                .query("scored_tasks >= 20")
                .sort_values("avg_quality", ascending=False)
                .reset_index()
            )
            display(client_quality.head(20))
            display(client_quality.tail(20))
            """
        ),
        code(
            """
            proofread_compare = proofread_reviewer_comparison(data)
            display(proofread_compare)

            workflow = data.sort_values(["PROJECT_ID", "START", "TASK_ID"]).copy()
            workflow["NEXT_TASK_TYPE"] = workflow.groupby("PROJECT_ID")["TASK_TYPE_CLEAN"].shift(-1)
            workflow["NEXT_TRANSLATOR"] = workflow.groupby("PROJECT_ID")["TRANSLATOR"].shift(-1)
            spotcheck = workflow[
                workflow["TASK_TYPE_CLEAN"].isin(["Translation", "TranslationOnly"])
                & workflow["NEXT_TASK_TYPE"].eq("Spotcheck")
            ].copy()
            spotcheck["same_translator"] = spotcheck["TRANSLATOR"] == spotcheck["NEXT_TRANSLATOR"]
            display(
                spotcheck["same_translator"]
                .value_counts(dropna=False)
                .rename_axis("same_translator")
                .reset_index(name="count")
            )
            """
        ),
        code(
            """
            test_tasks = data.loc[data["TASK_TYPE_CLEAN"].eq("TEST")].copy()
            display(
                pd.DataFrame(
                    [
                        {"metric": "TEST tasks", "value": len(test_tasks)},
                        {"metric": "Unique translators on TEST tasks", "value": test_tasks["TRANSLATOR"].nunique()},
                    ]
                )
            )
            display(test_tasks["TRANSLATOR"].value_counts().head(20).rename_axis("translator").reset_index(name="test_tasks"))
            """
        ),
    ]

    specs[DATA_ANALYSIS_DIR / "05_temporal" / "temporal_analysis.ipynb"] = [
        md(
            """
            # Temporal Analysis

            Time-based patterns in task volume, assignment timing, work duration, and punctuality.
            """
        ),
        code(COMMON_SETUP),
        code(
            """
            monthly_volume = (
                data.assign(YEAR_MONTH=data["START"].dt.to_period("M").astype(str))
                .groupby("YEAR_MONTH")
                .size()
                .rename("task_count")
                .reset_index()
            )
            yearly_volume = (
                data.assign(YEAR=data["START"].dt.year)
                .groupby("YEAR")
                .size()
                .rename("task_count")
                .reset_index()
            )
            display(yearly_volume)

            plt.figure(figsize=(14, 5))
            sns.lineplot(data=monthly_volume, x="YEAR_MONTH", y="task_count")
            plt.xticks(rotation=90)
            plt.title("Task volume by month")
            plt.show()
            """
        ),
        code(
            """
            seasonality = (
                data.assign(MONTH_NAME=data["START"].dt.month_name())
                .groupby(["START", "MONTH_NAME"])
            )
            month_summary = (
                data.assign(MONTH_NUM=data["START"].dt.month, MONTH_NAME=data["START"].dt.month_name())
                .groupby(["MONTH_NUM", "MONTH_NAME"])
                .size()
                .rename("task_count")
                .reset_index()
                .sort_values("MONTH_NUM")
            )
            display(month_summary)

            plt.figure(figsize=(12, 5))
            sns.barplot(data=month_summary, x="MONTH_NAME", y="task_count", color="#219ebc")
            plt.xticks(rotation=35, ha="right")
            plt.title("Seasonality by calendar month")
            plt.show()
            """
        ),
        code(
            """
            start_dow = (
                data.assign(START_DOW=data["START"].dt.day_name())
                .groupby("START_DOW")
                .size()
                .reindex(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
                .rename("task_count")
                .reset_index()
            )
            display(start_dow)

            assigned_hour = (
                data.assign(ASSIGNED_HOUR=data["ASSIGNED"].dt.hour)
                .groupby("ASSIGNED_HOUR")
                .size()
                .rename("task_count")
                .reset_index()
            )
            display(assigned_hour)

            fig, axes = plt.subplots(1, 2, figsize=(15, 5))
            sns.barplot(data=start_dow, x="START_DOW", y="task_count", ax=axes[0], color="#8ecae6")
            axes[0].tick_params(axis="x", rotation=35)
            axes[0].set_title("Task start day of week")
            sns.barplot(data=assigned_hour, x="ASSIGNED_HOUR", y="task_count", ax=axes[1], color="#ffb703")
            axes[1].set_title("Assignment hour of day")
            plt.tight_layout()
            plt.show()
            """
        ),
        code(
            """
            enriched = load_enriched_tasks()
            timing_metrics = enriched[
                [
                    "TIME_TO_START_HOURS",
                    "TIME_TO_ASSIGN_HOURS",
                    "TASK_DURATION_HOURS",
                    "ACTUAL_WORKING_HOURS",
                    "LATENESS_MINUTES",
                    "TASK_TYPE_CLEAN",
                ]
            ].copy()
            display(timing_metrics.describe(include="all"))

            fig, axes = plt.subplots(1, 2, figsize=(15, 5))
            sns.histplot(timing_metrics["TIME_TO_START_HOURS"].dropna(), bins=60, ax=axes[0], color="#06d6a0")
            axes[0].set_title("Time to start (WORKING - READY)")
            sns.histplot(timing_metrics["TIME_TO_ASSIGN_HOURS"].dropna(), bins=60, ax=axes[1], color="#ef476f")
            axes[1].set_title("Time to assign (ASSIGNED - START)")
            plt.tight_layout()
            plt.show()

            display(
                pd.DataFrame(
                    [
                        {
                            "metric": "Tasks assigned before START (%)",
                            "value": round((timing_metrics["TIME_TO_ASSIGN_HOURS"] < 0).mean() * 100, 2),
                        }
                    ]
                )
            )
            """
        ),
        code(
            """
            top_task_types = data["TASK_TYPE_CLEAN"].value_counts().head(8).index
            duration_subset = enriched.loc[enriched["TASK_TYPE_CLEAN"].isin(top_task_types)].copy()

            plt.figure(figsize=(12, 6))
            sns.boxplot(
                data=duration_subset,
                x="TASK_TYPE_CLEAN",
                y="TASK_DURATION_HOURS",
                showfliers=False,
                color="#118ab2",
            )
            plt.xticks(rotation=35, ha="right")
            plt.yscale("log")
            plt.title("Task duration by task type")
            plt.show()

            working_sample = enriched[["TASK_DURATION_HOURS", "ACTUAL_WORKING_HOURS"]].dropna().sample(30000, random_state=42)
            plt.figure(figsize=(8, 6))
            sns.scatterplot(data=working_sample, x="TASK_DURATION_HOURS", y="ACTUAL_WORKING_HOURS", alpha=0.2, s=15)
            plt.xscale("log")
            plt.yscale("log")
            plt.title("Actual working time vs planned task window")
            plt.show()
            """
        ),
        code(
            """
            late_tasks = enriched.loc[enriched["LATENESS_MINUTES"] > 0, "LATENESS_MINUTES"]
            display(late_tasks.describe().to_frame("lateness_minutes"))

            plt.figure(figsize=(10, 5))
            sns.histplot(late_tasks, bins=80, color="#d62828")
            plt.xscale("log")
            plt.title("Lateness distribution for late tasks")
            plt.show()

            on_time_over_time = (
                enriched.assign(YEAR=enriched["END"].dt.year)
                .groupby("YEAR")["ON_TIME"]
                .mean()
                .reset_index()
            )
            display(on_time_over_time)

            plt.figure(figsize=(10, 5))
            sns.lineplot(data=on_time_over_time, x="YEAR", y="ON_TIME", marker="o")
            plt.ylim(0, 1)
            plt.title("On-time rate over time")
            plt.show()
            """
        ),
    ]

    specs[DATA_ANALYSIS_DIR / "06_financial" / "financial_analysis.ipynb"] = [
        md(
            """
            # Financial Analysis

            Cost, selling price, and margin patterns after joining client and translator rate information.
            """
        ),
        code(COMMON_SETUP),
        code(
            """
            enriched = load_enriched_tasks()
            display(
                pd.DataFrame(
                    {
                        "task_hourly_rate": enriched["HOURLY_RATE"].describe(),
                        "selling_hourly_price": enriched["SELLING_HOURLY_PRICE"].describe(),
                        "pair_hourly_rate": enriched["PAIR_HOURLY_RATE"].describe(),
                    }
                )
            )

            fig, axes = plt.subplots(1, 3, figsize=(18, 5))
            sns.histplot(enriched["HOURLY_RATE"].dropna(), bins=40, ax=axes[0], color="#1d3557")
            axes[0].set_title("Task hourly rate")
            sns.histplot(enriched["SELLING_HOURLY_PRICE"].dropna(), bins=40, ax=axes[1], color="#f4a261")
            axes[1].set_title("Client selling hourly price")
            sns.histplot(enriched["PAIR_HOURLY_RATE"].dropna(), bins=40, ax=axes[2], color="#2a9d8f")
            axes[2].set_title("Pair hourly rate")
            plt.tight_layout()
            plt.show()
            """
        ),
        code(
            """
            margin_summary = pd.DataFrame(
                {
                    "task_rate_margin": enriched["MARGIN_TASK_RATE"].describe(),
                    "pair_rate_margin": enriched["MARGIN_PAIR_RATE"].describe(),
                }
            )
            display(margin_summary)

            fig, axes = plt.subplots(1, 2, figsize=(14, 5))
            sns.histplot(enriched["MARGIN_TASK_RATE"].dropna(), bins=80, ax=axes[0], color="#264653")
            axes[0].set_title("Margin using task hourly rate")
            sns.histplot(enriched["MARGIN_PAIR_RATE"].dropna(), bins=80, ax=axes[1], color="#e76f51")
            axes[1].set_title("Margin using pair hourly rate")
            plt.tight_layout()
            plt.show()

            loss_rate = (enriched["MARGIN_PAIR_RATE"] < 0).mean() * 100
            display(pd.DataFrame([{"metric": "Loss-making tasks by pair-rate margin (%)", "value": round(loss_rate, 2)}]))
            """
        ),
        code(
            """
            pair_margin = (
                enriched.assign(language_pair=enriched["SOURCE_LANG"] + " -> " + enriched["TARGET_LANG"])
                .groupby("language_pair")
                .agg(tasks=("TASK_ID", "size"), avg_margin=("MARGIN_PAIR_RATE", "mean"))
                .query("tasks >= 50")
                .sort_values("avg_margin", ascending=False)
                .reset_index()
            )
            display(pair_margin.head(20))
            display(pair_margin.tail(20))
            """
        ),
        code(
            """
            client_financials = (
                enriched.groupby("MANUFACTURER")
                .agg(
                    tasks=("TASK_ID", "size"),
                    revenue=("COST", "sum"),
                    avg_margin=("MARGIN_PAIR_RATE", "mean"),
                    total_margin=("MARGIN_PAIR_RATE", "sum"),
                )
                .sort_values("revenue", ascending=False)
                .reset_index()
            )
            display(client_financials.head(20))
            display(client_financials.sort_values("total_margin", ascending=False).head(20))
            """
        ),
        code(
            """
            quality_scatter = enriched[["PAIR_HOURLY_RATE", "HOURLY_RATE", "QUALITY_EVALUATION"]].dropna().sample(30000, random_state=42)
            plt.figure(figsize=(8, 6))
            sns.scatterplot(data=quality_scatter, x="PAIR_HOURLY_RATE", y="QUALITY_EVALUATION", alpha=0.2, s=18)
            plt.title("Pair hourly rate vs quality evaluation")
            plt.show()

            corr_pair_quality = quality_scatter["PAIR_HOURLY_RATE"].corr(quality_scatter["QUALITY_EVALUATION"])
            corr_task_quality = quality_scatter["HOURLY_RATE"].corr(quality_scatter["QUALITY_EVALUATION"])
            display(
                pd.DataFrame(
                    [
                        {"metric": "Correlation: pair hourly rate vs quality", "value": round(corr_pair_quality, 3)},
                        {"metric": "Correlation: task hourly rate vs quality", "value": round(corr_task_quality, 3)},
                    ]
                )
            )
            """
        ),
        code(
            """
            zero_financial = enriched.loc[(enriched["HOURS"].fillna(0) == 0) | (enriched["COST"].fillna(0) == 0)].copy()
            display(
                zero_financial.groupby("TASK_TYPE_CLEAN")
                .agg(
                    rows=("TASK_ID", "size"),
                    hours=("HOURS", "sum"),
                    cost=("COST", "sum"),
                    avg_margin=("MARGIN_PAIR_RATE", "mean"),
                )
                .sort_values("rows", ascending=False)
            )
            """
        ),
    ]

    specs[DATA_ANALYSIS_DIR / "07_ml_feature_analysis" / "target_variables.ipynb"] = [
        md(
            """
            # Target Variables

            Exploratory review of the punctuality and quality targets that a ranking model could learn from.
            """
        ),
        code(COMMON_SETUP),
        code(
            """
            enriched = load_enriched_tasks()
            on_time_balance = (
                pd.to_numeric(enriched["ON_TIME"], errors="coerce")
                .value_counts(dropna=False, normalize=True)
                .rename_axis("ON_TIME")
                .reset_index(name="share")
            )
            display(on_time_balance)

            quality_stats = enriched["QUALITY_EVALUATION"].agg(["count", "mean", "median", "std", "min", "max"]).to_frame("value")
            display(quality_stats)

            high_quality_balance = (
                pd.to_numeric(enriched["HIGH_QUALITY_8"], errors="coerce")
                .value_counts(dropna=False, normalize=True)
                .rename_axis("HIGH_QUALITY_8")
                .reset_index(name="share")
            )
            display(high_quality_balance)
            """
        ),
        code(
            """
            fig, axes = plt.subplots(1, 2, figsize=(14, 5))
            sns.histplot(enriched["QUALITY_EVALUATION"].dropna(), bins=30, ax=axes[0], color="#118ab2")
            axes[0].set_title("Continuous quality target")
            sns.barplot(data=high_quality_balance, x="HIGH_QUALITY_8", y="share", ax=axes[1], color="#ffb703")
            axes[1].set_title("Binary high-quality target")
            plt.tight_layout()
            plt.show()
            """
        ),
        code(
            """
            scored_tasks = (
                enriched.groupby("TRANSLATOR")["QUALITY_EVALUATION"]
                .count()
                .rename("scored_tasks")
                .reset_index()
                .sort_values("scored_tasks", ascending=False)
            )
            display(scored_tasks.head(20))
            unreliable = scored_tasks.loc[scored_tasks["scored_tasks"] < 5].copy()
            display(pd.DataFrame([{"metric": "Translators with <5 scored tasks", "value": len(unreliable)}]))
            display(unreliable.head(30))
            """
        ),
        code(
            """
            valid_target = enriched[["ON_TIME", "QUALITY_EVALUATION"]].dropna().copy()
            valid_target["ON_TIME"] = pd.to_numeric(valid_target["ON_TIME"], errors="coerce")
            task_level_corr = valid_target["ON_TIME"].corr(valid_target["QUALITY_EVALUATION"])

            translator_level = (
                enriched.groupby("TRANSLATOR")
                .agg(on_time_rate=("ON_TIME", lambda s: pd.to_numeric(s, errors="coerce").mean()), avg_quality=("QUALITY_EVALUATION", "mean"))
                .dropna()
                .reset_index()
            )
            translator_corr = translator_level["on_time_rate"].corr(translator_level["avg_quality"])
            display(
                pd.DataFrame(
                    [
                        {"metric": "Task-level correlation between ON_TIME and QUALITY_EVALUATION", "value": round(task_level_corr, 3)},
                        {"metric": "Translator-level correlation between ON_TIME and QUALITY_EVALUATION", "value": round(translator_corr, 3)},
                    ]
                )
            )

            plt.figure(figsize=(8, 6))
            sns.boxplot(
                data=valid_target.assign(ON_TIME=valid_target["ON_TIME"].astype(int)),
                x="ON_TIME",
                y="QUALITY_EVALUATION",
                color="#8ecae6",
            )
            plt.title("Quality by on-time outcome")
            plt.show()
            """
        ),
    ]

    specs[DATA_ANALYSIS_DIR / "07_ml_feature_analysis" / "feature_engineering_candidates.ipynb"] = [
        md(
            """
            # Feature Engineering Candidates

            Candidate features grouped by experience, quality, punctuality, cost, and availability.
            """
        ),
        code(COMMON_SETUP),
        code(
            """
            enriched = load_enriched_tasks()

            feature_rows = []
            for group_name, columns in FEATURE_GROUPS.items():
                for column in columns:
                    series = pd.to_numeric(enriched[column], errors="coerce") if column in enriched.columns else pd.Series(dtype=float)
                    feature_rows.append(
                        {
                            "feature_group": group_name,
                            "feature": column,
                            "missing_pct": round(enriched[column].isna().mean() * 100, 2) if column in enriched.columns else 100.0,
                            "n_unique": enriched[column].nunique(dropna=True) if column in enriched.columns else 0,
                            "median": series.median() if column in enriched.columns else np.nan,
                            "p95": series.quantile(0.95) if column in enriched.columns else np.nan,
                        }
                    )
            feature_catalog = pd.DataFrame(feature_rows)
            display(feature_catalog)
            """
        ),
        code(
            """
            for group_name, columns in FEATURE_GROUPS.items():
                display(Markdown(f"## {group_name.title()} features"))
                available_columns = [column for column in columns if column in enriched.columns]
                if not available_columns:
                    continue
                numeric_subset = enriched[available_columns].apply(pd.to_numeric, errors="coerce")
                display(numeric_subset.describe().T)

                plot_columns = available_columns[: min(4, len(available_columns))]
                fig, axes = plt.subplots(1, len(plot_columns), figsize=(5 * len(plot_columns), 4))
                axes = np.atleast_1d(axes)
                for ax, column in zip(axes, plot_columns):
                    sns.histplot(pd.to_numeric(enriched[column], errors="coerce").dropna(), bins=50, ax=ax, color="#457b9d")
                    ax.set_title(column)
                    if column.startswith("PRIOR_") or column.endswith("_HOURS") or column.endswith("_COUNT_TRANSLATOR"):
                        ax.set_xscale("symlog")
                plt.tight_layout()
                plt.show()
            """
        ),
        code(
            """
            decay_days = np.arange(0, 365)
            plt.figure(figsize=(10, 5))
            for half_life in [30, 90, 180]:
                weights = np.exp(-np.log(2) * decay_days / half_life)
                plt.plot(decay_days, weights, label=f"Half-life {half_life}d")
            plt.title("Illustrative exponential decay schemes for recency weighting")
            plt.xlabel("Days since past task")
            plt.ylabel("Weight")
            plt.legend()
            plt.show()
            """
        ),
        code(
            """
            reliability_notes = pd.DataFrame(
                [
                    {
                        "feature_group": "Experience",
                        "reliability_note": "Strong coverage and low missingness because experience can be accumulated from nearly every historical task.",
                    },
                    {
                        "feature_group": "Quality",
                        "reliability_note": "Useful but noisier for translators with few scored tasks; rolling quality features should be gated by score count.",
                    },
                    {
                        "feature_group": "Punctuality",
                        "reliability_note": "Generally computable, but timestamp anomalies and missing workflow timestamps can distort delay-based features.",
                    },
                    {
                        "feature_group": "Cost",
                        "reliability_note": "Reliable when exact client and pair joins exist; unmatched joins create structured missingness.",
                    },
                    {
                        "feature_group": "Availability",
                        "reliability_note": "Available for most translators, but overlap features are approximate for night shifts because schedules are recurring weekly templates.",
                    },
                ]
            )
            display(reliability_notes)
            display(
                enriched["AVAILABILITY_FEATURE_RELIABILITY"]
                .value_counts(dropna=False)
                .rename_axis("reliability_flag")
                .reset_index(name="rows")
            )
            """
        ),
    ]

    specs[DATA_ANALYSIS_DIR / "07_ml_feature_analysis" / "feature_correlations.ipynb"] = [
        md(
            """
            # Feature Correlations

            Correlation structure, predictive signal proxies, and multicollinearity risks.
            """
        ),
        code(COMMON_SETUP),
        code(
            """
            from sklearn.feature_selection import mutual_info_classif, mutual_info_regression

            enriched = load_enriched_tasks()
            candidate_features = []
            for columns in FEATURE_GROUPS.values():
                candidate_features.extend(columns)
            candidate_features = list(dict.fromkeys(candidate_features))

            numeric_frame = enriched[candidate_features + ["ON_TIME", "QUALITY_EVALUATION", "HIGH_QUALITY_8"]].apply(pd.to_numeric, errors="coerce")
            corr = numeric_frame.corr()
            plt.figure(figsize=(18, 14))
            sns.heatmap(corr, cmap="coolwarm", center=0)
            plt.title("Correlation matrix of candidate features and targets")
            plt.show()
            """
        ),
        code(
            """
            def binned_average_plot(df, x_col, y_col, title):
                subset = df[[x_col, y_col]].dropna().copy()
                if subset.empty:
                    return
                subset["bin"] = pd.qcut(subset[x_col], q=10, duplicates="drop")
                summary = subset.groupby("bin").agg(x_mean=(x_col, "mean"), y_mean=(y_col, "mean")).reset_index(drop=True)
                plt.figure(figsize=(7, 4))
                sns.lineplot(data=summary, x="x_mean", y="y_mean", marker="o")
                plt.title(title)
                plt.show()

            binned_average_plot(numeric_frame, "PRIOR_HOURS_CLIENT", "QUALITY_EVALUATION", "Client experience vs quality")
            binned_average_plot(numeric_frame, "PRIOR_HOURS_SECTOR", "QUALITY_EVALUATION", "Sector experience vs quality")
            binned_average_plot(numeric_frame, "PRIOR_HOURS_TASK_TYPE", "ON_TIME", "Task-type experience vs on-time rate")
            binned_average_plot(numeric_frame, "PAIR_HOURLY_RATE", "QUALITY_EVALUATION", "Pair hourly rate vs quality")
            """
        ),
        code(
            """
            feature_matrix = numeric_frame[candidate_features].copy()
            feature_matrix = feature_matrix.fillna(feature_matrix.median(numeric_only=True))

            valid_on_time = numeric_frame["ON_TIME"].notna()
            mi_on_time = mutual_info_classif(
                feature_matrix.loc[valid_on_time],
                numeric_frame.loc[valid_on_time, "ON_TIME"].astype(int),
                random_state=42,
            )
            mi_high_quality = mutual_info_classif(
                feature_matrix.loc[numeric_frame["HIGH_QUALITY_8"].notna()],
                numeric_frame.loc[numeric_frame["HIGH_QUALITY_8"].notna(), "HIGH_QUALITY_8"].astype(int),
                random_state=42,
            )
            mi_quality = mutual_info_regression(
                feature_matrix.loc[numeric_frame["QUALITY_EVALUATION"].notna()],
                numeric_frame.loc[numeric_frame["QUALITY_EVALUATION"].notna(), "QUALITY_EVALUATION"],
                random_state=42,
            )

            mi_summary = pd.DataFrame(
                {
                    "feature": candidate_features,
                    "mi_on_time": mi_on_time,
                    "mi_high_quality": mi_high_quality,
                    "mi_quality_continuous": mi_quality,
                }
            ).sort_values("mi_quality_continuous", ascending=False)
            display(mi_summary)
            """
        ),
        code(
            """
            corr_candidates = numeric_frame[candidate_features].corr().abs()
            upper_triangle = corr_candidates.where(np.triu(np.ones(corr_candidates.shape), k=1).astype(bool))
            highly_correlated = (
                upper_triangle.stack()
                .reset_index()
                .rename(columns={"level_0": "feature_a", "level_1": "feature_b", 0: "abs_correlation"})
                .query("abs_correlation >= 0.8")
                .sort_values("abs_correlation", ascending=False)
            )
            display(highly_correlated)
            """
        ),
    ]

    specs[DATA_ANALYSIS_DIR / "07_ml_feature_analysis" / "cold_start_analysis.ipynb"] = [
        md(
            """
            # Cold Start Analysis

            What can be inferred when translators have little or no historical task data.
            """
        ),
        code(COMMON_SETUP),
        code(
            """
            data_translators = set(data["TRANSLATOR"])
            pair_translators = set(pairs["TRANSLATOR"])
            zero_task_translators = sorted(pair_translators - data_translators)

            display(
                pd.DataFrame(
                    [
                        {"metric": "Translators in pair sheet with zero tasks", "value": len(zero_task_translators)},
                        {"metric": "Share of pair-sheet translators with zero tasks (%)", "value": round(len(zero_task_translators) / len(pair_translators) * 100, 2)},
                    ]
                )
            )
            display(pd.DataFrame({"translator": zero_task_translators[:50]}))
            """
        ),
        code(
            """
            scored = data.dropna(subset=["QUALITY_EVALUATION"]).sort_values(["TRANSLATOR", "START"]).copy()
            scored["task_number"] = scored.groupby("TRANSLATOR").cumcount() + 1
            scored["rolling_quality_mean"] = (
                scored.groupby("TRANSLATOR")["QUALITY_EVALUATION"]
                .expanding()
                .mean()
                .reset_index(level=0, drop=True)
            )
            scored["final_quality_mean"] = scored.groupby("TRANSLATOR")["QUALITY_EVALUATION"].transform("mean")
            scored["distance_to_final"] = (scored["rolling_quality_mean"] - scored["final_quality_mean"]).abs()

            def first_stable_task(group, threshold=0.5):
                future_max = group["distance_to_final"].iloc[::-1].cummax().iloc[::-1]
                stable_rows = group.loc[future_max <= threshold, "task_number"]
                return stable_rows.iloc[0] if not stable_rows.empty else np.nan

            stability = (
                scored.groupby("TRANSLATOR")
                .apply(first_stable_task)
                .rename("stable_task_number")
                .dropna()
                .reset_index()
            )
            display(stability.describe())

            plt.figure(figsize=(10, 5))
            sns.histplot(stability["stable_task_number"], bins=30, color="#6a4c93")
            plt.title("Task count before rolling quality stabilizes")
            plt.show()
            """
        ),
        code(
            """
            cold_start_features = (
                pairs.loc[pairs["TRANSLATOR"].isin(zero_task_translators)]
                .groupby("TRANSLATOR")
                .agg(
                    listed_language_pairs=("TARGET_LANG", "size"),
                    avg_pair_rate=("HOURLY_RATE", "mean"),
                )
                .reset_index()
            )
            schedule_signals = schedules[["NAME", "START", "END", "MON", "TUES", "WED", "THURS", "FRI", "SAT", "SUN"]].copy()
            schedule_signals["working_days_per_week"] = schedule_signals[["MON", "TUES", "WED", "THURS", "FRI", "SAT", "SUN"]].sum(axis=1)
            cold_start_signals = cold_start_features.merge(schedule_signals, left_on="TRANSLATOR", right_on="NAME", how="left")
            display(cold_start_signals.head(30))
            """
        ),
        code(
            """
            client_baselines = (
                data.groupby("MANUFACTURER")
                .agg(client_quality=("QUALITY_EVALUATION", "mean"), tasks=("TASK_ID", "size"))
                .query("tasks >= 20")
                .reset_index()
            )
            sector_baselines = (
                data.groupby("MANUFACTURER_SECTOR")
                .agg(sector_quality=("QUALITY_EVALUATION", "mean"), tasks=("TASK_ID", "size"))
                .query("tasks >= 20")
                .reset_index()
            )
            display(client_baselines.head(20))
            display(sector_baselines.head(20))

            fallback_signal_summary = pd.DataFrame(
                [
                    {
                        "signal": "Pair rate and listed language pairs",
                        "availability": "High for translators in TranslatorsCost+Pairs",
                        "limitation": "No direct evidence about punctuality or quality",
                    },
                    {
                        "signal": "Weekly schedule template",
                        "availability": "High for translators present in Schedules",
                        "limitation": "Availability is template-based and not real-time",
                    },
                    {
                        "signal": "Client and sector averages",
                        "availability": "High for seen clients/sectors",
                        "limitation": "These are population priors, not translator-specific skill signals",
                    },
                ]
            )
            display(fallback_signal_summary)
            """
        ),
    ]

    specs[DATA_ANALYSIS_DIR / "08_cross_sheet_joins" / "join_integrity.ipynb"] = [
        md(
            """
            # Join Integrity

            Validate cross-sheet joins, diagnose unmatched rows, and export the enriched task dataset.
            """
        ),
        code(COMMON_SETUP),
        code(
            """
            joined = join_datasets(sheets=sheets)
            summary = summarize_join_integrity(joined)
            join_summary = pd.DataFrame(
                [
                    {"join": "Data -> Clients", "match_rate_pct": round(summary.data_to_clients_match_rate * 100, 3)},
                    {"join": "Data -> TranslatorsCost+Pairs", "match_rate_pct": round(summary.data_to_pairs_match_rate * 100, 3)},
                    {"join": "Data -> Schedules", "match_rate_pct": round(summary.data_to_schedules_match_rate * 100, 3)},
                ]
            )
            display(join_summary)
            """
        ),
        code(
            """
            client_diag = diagnose_client_unmatched(joined, clients)
            pair_diag = diagnose_pair_unmatched(joined, pairs)
            schedule_diag = diagnose_schedule_unmatched(joined, schedules)

            display(client_diag["diagnosis"].value_counts(dropna=False).rename_axis("diagnosis").reset_index(name="rows"))
            display(pair_diag["diagnosis"].value_counts(dropna=False).rename_axis("diagnosis").reset_index(name="rows"))
            display(schedule_diag["diagnosis"].value_counts(dropna=False).rename_axis("diagnosis").reset_index(name="rows"))

            display(client_diag.head(30))
            display(pair_diag.head(30))
            display(schedule_diag.head(30))
            """
        ),
        code(
            """
            import gc

            for frame_name in ["sheets", "data", "joined"]:
                globals().pop(frame_name, None)
            gc.collect()

            enriched = build_enriched_tasks(save=True)
            print(f"Saved enriched dataset to: {ENRICHED_PATH}")
            print(f"Enriched dataset shape: {enriched.shape}")

            key_columns = []
            for cols in FEATURE_GROUPS.values():
                key_columns.extend(cols)
            key_columns = list(dict.fromkeys(key_columns + ["ON_TIME", "HIGH_QUALITY_8", "SELLING_HOURLY_PRICE", "MIN_QUALITY"]))

            completeness = (
                enriched[key_columns]
                .isna()
                .mean()
                .mul(100)
                .round(2)
                .rename("missing_pct")
                .reset_index()
                .rename(columns={"index": "column"})
                .sort_values("missing_pct", ascending=False)
            )
            display(completeness)
            """
        ),
        code(
            """
            final_gap_summary = pd.DataFrame(
                [
                    {
                        "gap_area": "Client join gaps",
                        "rows_pct": round((~enriched["CLIENT_MATCH_EXACT"]).mean() * 100, 3),
                    },
                    {
                        "gap_area": "Pair join gaps",
                        "rows_pct": round((~enriched["PAIR_MATCH_EXACT"]).mean() * 100, 3),
                    },
                    {
                        "gap_area": "Schedule join gaps",
                        "rows_pct": round((~enriched["SCHEDULE_MATCH_EXACT"]).mean() * 100, 3),
                    },
                    {
                        "gap_area": "Approximate availability rows",
                        "rows_pct": round((enriched["AVAILABILITY_FEATURE_RELIABILITY"] == "approximate_night_shift").mean() * 100, 3),
                    },
                ]
            )
            display(final_gap_summary)
            """
        ),
    ]

    return specs


def write_notebook(path: Path, cells: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    notebook = nbf.v4.new_notebook(cells=cells)
    notebook["metadata"]["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    notebook["metadata"]["language_info"] = {"name": "python", "version": "3.11"}
    with path.open("w", encoding="utf-8") as handle:
        nbf.write(notebook, handle)


def execute_notebook(path: Path) -> None:
    with path.open("r", encoding="utf-8") as handle:
        notebook = nbf.read(handle, as_version=4)

    client = NotebookClient(
        notebook,
        timeout=3600,
        kernel_name="python3",
        resources={"metadata": {"path": str(path.parent)}},
    )
    client.execute()

    with path.open("w", encoding="utf-8") as handle:
        nbf.write(notebook, handle)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the TARS EDA notebooks.")
    parser.add_argument("--execute", action="store_true", help="Execute notebooks after generating them.")
    args = parser.parse_args()

    specs = notebook_specs()
    ordered_paths = sorted(specs)
    for path in ordered_paths:
        write_notebook(path, specs[path])
        print(f"Wrote {path.relative_to(PROJECT_ROOT)}")

    if args.execute:
        for path in ordered_paths:
            print(f"Executing {path.relative_to(PROJECT_ROOT)}")
            execute_notebook(path)


if __name__ == "__main__":
    main()
