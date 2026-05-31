from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import seaborn as sns


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_WORKBOOK = PROJECT_ROOT / "data" / "raw" / "data.xlsx"
CACHE_DIR = PROJECT_ROOT / "data" / "interim" / "analysis_cache"
ENRICHED_PATH = PROJECT_ROOT / "data" / "interim" / "enriched_tasks.csv"

SHEET_NAME_MAP = {
    "data": "Data",
    "schedules": "Schedules",
    "clients": "Clients",
    "pairs": "TranslatorsCost+Pairs",
}

PARQUET_MAP = {
    "data": CACHE_DIR / "data.parquet",
    "schedules": CACHE_DIR / "schedules.parquet",
    "clients": CACHE_DIR / "clients.parquet",
    "pairs": CACHE_DIR / "translators_cost_pairs.parquet",
}

DATA_DATETIME_COLUMNS = [
    "START",
    "END",
    "ASSIGNED",
    "READY",
    "WORKING",
    "DELIVERED",
    "RECEIVED",
    "CLOSE",
]

DATA_ENRICHMENT_COLUMNS = [
    "PROJECT_ID",
    "TASK_ID",
    "START",
    "END",
    "TASK_TYPE",
    "SOURCE_LANG",
    "TARGET_LANG",
    "TRANSLATOR",
    "ASSIGNED",
    "READY",
    "WORKING",
    "DELIVERED",
    "HOURS",
    "HOURLY_RATE",
    "COST",
    "QUALITY_EVALUATION",
    "MANUFACTURER",
    "MANUFACTURER_SECTOR",
    "TASK_TYPE_CLEAN",
    "SOURCE_LANG_CLEAN",
    "TARGET_LANG_CLEAN",
    "TRANSLATOR_KEY",
    "CLIENT_KEY",
]

SCHEDULE_DAY_COLUMNS = ["MON", "TUES", "WED", "THURS", "FRI", "SAT", "SUN"]
NUMERIC_OUTLIER_COLUMNS = ["HOURS", "HOURLY_RATE", "COST", "QUALITY_EVALUATION"]
QUALITY_THRESHOLD = 8.0

TASK_TYPE_NORMALIZATION_MAP = {
    "miscelaneous": "Miscellaneous",
    "miscellaneous": "Miscellaneous",
    "proofreading": "ProofReading",
    "proofreadingonly": "ProofReadingOnly",
    "translationonly": "TranslationOnly",
    "languagelead": "LanguageLead",
    "postediting": "PostEditing",
}

EXPECTED_TYPES = {
    "Data": {
        "datetime": DATA_DATETIME_COLUMNS,
        "numeric": [
            "PROJECT_ID",
            "TASK_ID",
            "HOURS",
            "HOURLY_RATE",
            "COST",
            "QUALITY_EVALUATION",
        ],
    },
    "Schedules": {
        "time_like": ["START", "END"],
        "numeric": SCHEDULE_DAY_COLUMNS,
    },
    "Clients": {
        "numeric": ["SELLING_HOURLY_PRICE", "MIN_QUALITY"],
        "categorical": ["CLIENT_NAME", "WILDCARD"],
    },
    "TranslatorsCost+Pairs": {
        "numeric": ["HOURLY_RATE"],
        "categorical": ["TRANSLATOR", "SOURCE_LANG", "TARGET_LANG"],
    },
}

FEATURE_GROUPS = {
    "experience": [
        "PRIOR_HOURS_TRANSLATOR",
        "PRIOR_HOURS_CLIENT",
        "PRIOR_HOURS_SECTOR",
        "PRIOR_HOURS_TASK_TYPE",
        "PRIOR_TASKS_LANGUAGE_PAIR",
    ],
    "quality": [
        "PRIOR_QUALITY_MEAN_TRANSLATOR",
        "ROLLING_QUALITY_MEAN_5",
        "ROLLING_QUALITY_STD_5",
        "PRIOR_QUALITY_MEAN_PAIR",
        "PRIOR_QUALITY_MEAN_TASK_TYPE",
        "PRIOR_QUALITY_COUNT_TRANSLATOR",
    ],
    "punctuality": [
        "PRIOR_ON_TIME_RATE_TRANSLATOR",
        "PRIOR_ON_TIME_RATE_TASK_TYPE",
        "PRIOR_AVG_LATENESS_MINUTES",
        "ROLLING_ON_TIME_RATE_5",
        "PUNCTUALITY_TREND_DELTA",
    ],
    "cost": [
        "PAIR_HOURLY_RATE",
        "RATE_DISCREPANCY",
        "MARGIN_TASK_RATE",
        "MARGIN_PAIR_RATE",
        "RATE_EXCEEDS_SELLING_PRICE",
    ],
    "availability": [
        "WORKING_DAYS_PER_WEEK",
        "WEEKEND_WORKER",
        "NIGHT_SHIFT",
        "SHIFT_HOURS_PER_DAY",
        "AVAILABLE_HOURS_IN_WINDOW",
        "SHIFT_OVERLAP_PCT",
    ],
}


@dataclass(frozen=True)
class JoinIntegritySummary:
    data_to_clients_match_rate: float
    data_to_pairs_match_rate: float
    data_to_schedules_match_rate: float


def set_plot_style() -> None:
    sns.set_theme(style="whitegrid", context="talk")


def ensure_analysis_cache(force_refresh: bool = False) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_missing = force_refresh or any(not path.exists() for path in PARQUET_MAP.values())
    if not cache_missing:
        return

    workbook = pd.ExcelFile(RAW_WORKBOOK, engine="openpyxl")
    for short_name, sheet_name in SHEET_NAME_MAP.items():
        df = pd.read_excel(RAW_WORKBOOK, sheet_name=sheet_name, engine="openpyxl")
        df = _clean_sheet(short_name, df)
        df.to_parquet(PARQUET_MAP[short_name], index=False)


def _read_parquet_in_batches(
    path: Path,
    columns: Iterable[str] | None = None,
    batch_size: int = 25_000,
) -> pd.DataFrame:
    column_list = list(columns) if columns is not None else None
    parquet_file = pq.ParquetFile(path)
    frames = [
        batch.to_pandas(types_mapper=pd.ArrowDtype)
        for batch in parquet_file.iter_batches(
            batch_size=batch_size,
            columns=column_list,
            use_threads=False,
        )
    ]
    if not frames:
        return pd.DataFrame(columns=column_list)
    return pd.concat(frames, ignore_index=True, copy=False)


def load_sheet(
    name: str,
    force_refresh: bool = False,
    columns: Iterable[str] | None = None,
) -> pd.DataFrame:
    if name not in PARQUET_MAP:
        raise KeyError(f"Unknown sheet name: {name}")
    ensure_analysis_cache(force_refresh=force_refresh)
    column_list = list(columns) if columns is not None else None
    if name == "data":
        return _read_parquet_in_batches(PARQUET_MAP[name], columns=column_list)
    try:
        return pd.read_parquet(
            PARQUET_MAP[name],
            columns=column_list,
            dtype_backend="pyarrow",
            use_threads=False,
        )
    except (pa.ArrowMemoryError, MemoryError):
        return _read_parquet_in_batches(PARQUET_MAP[name], columns=column_list)


def load_all_data(
    force_refresh: bool = False,
    columns_by_sheet: dict[str, Iterable[str]] | None = None,
) -> dict[str, pd.DataFrame]:
    columns_by_sheet = columns_by_sheet or {}
    return {
        name: load_sheet(
            name,
            force_refresh=force_refresh,
            columns=columns_by_sheet.get(name),
        )
        for name in SHEET_NAME_MAP
    }


def _clean_sheet(name: str, df: pd.DataFrame) -> pd.DataFrame:
    clean = df.copy()
    clean.columns = [str(col).strip() for col in clean.columns]

    if name == "data":
        for col in DATA_DATETIME_COLUMNS:
            clean[col] = pd.to_datetime(clean[col], errors="coerce")
        clean["TASK_TYPE_CLEAN"] = normalize_task_type(clean["TASK_TYPE"])
        clean["SOURCE_LANG_CLEAN"] = normalize_series(clean["SOURCE_LANG"])
        clean["TARGET_LANG_CLEAN"] = normalize_series(clean["TARGET_LANG"])
        clean["TRANSLATOR_KEY"] = normalize_series(clean["TRANSLATOR"])
        clean["CLIENT_KEY"] = normalize_series(clean["MANUFACTURER"])
    elif name == "schedules":
        clean["START"] = clean["START"].astype(str).str.strip()
        clean["END"] = clean["END"].astype(str).str.strip()
        clean["NAME_KEY"] = normalize_series(clean["NAME"])
        for col in SCHEDULE_DAY_COLUMNS:
            clean[col] = pd.to_numeric(clean[col], errors="coerce").fillna(0).astype("Int64")
    elif name == "clients":
        clean["CLIENT_KEY"] = normalize_series(clean["CLIENT_NAME"])
        clean["WILDCARD_CLEAN"] = clean["WILDCARD"].astype("string").str.strip().str.title()
    elif name == "pairs":
        clean["TRANSLATOR_KEY"] = normalize_series(clean["TRANSLATOR"])
        clean["SOURCE_LANG_CLEAN"] = normalize_series(clean["SOURCE_LANG"])
        clean["TARGET_LANG_CLEAN"] = normalize_series(clean["TARGET_LANG"])

    for column in clean.select_dtypes(include="object").columns:
        clean[column] = clean[column].astype("string").str.strip()

    return clean


def normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    text = " ".join(text.split())
    return text.casefold()


def normalize_series(series: pd.Series) -> pd.Series:
    return series.astype("string").fillna("").str.strip().str.replace(r"\s+", " ", regex=True).str.casefold()


def normalize_task_type(series: pd.Series) -> pd.Series:
    normalized = normalize_series(series).str.replace(r"\s+", "", regex=True)
    mapped = normalized.map(TASK_TYPE_NORMALIZATION_MAP)
    fallback = series.astype("string").fillna("").str.strip()
    return mapped.fillna(fallback)


def sheet_dimensions_report(sheets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for short_name, df in sheets.items():
        rows.append(
            {
                "sheet": SHEET_NAME_MAP[short_name],
                "rows": len(df),
                "columns": len(df.columns),
            }
        )
    return pd.DataFrame(rows).sort_values("sheet").reset_index(drop=True)


def dtype_audit(df: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
    expectations = EXPECTED_TYPES.get(sheet_name, {})
    expectation_lookup: dict[str, str] = {}
    for expected_group, columns in expectations.items():
        for column in columns:
            expectation_lookup[column] = expected_group

    rows = []
    for column in df.columns:
        expected = expectation_lookup.get(column, "unspecified")
        rows.append(
            {
                "column": column,
                "dtype": str(df[column].dtype),
                "expected": expected,
                "matches_expectation": _dtype_matches(df[column], expected),
            }
        )
    return pd.DataFrame(rows)


def _dtype_matches(series: pd.Series, expected: str) -> bool:
    if expected == "datetime":
        return pd.api.types.is_datetime64_any_dtype(series)
    if expected == "numeric":
        return pd.api.types.is_numeric_dtype(series)
    if expected == "categorical":
        return pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)
    if expected == "time_like":
        return pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)
    return True


def missing_summary(df: pd.DataFrame) -> pd.DataFrame:
    summary = pd.DataFrame(
        {
            "column": df.columns,
            "missing_count": df.isna().sum().values,
            "missing_pct": df.isna().mean().mul(100).round(2).values,
        }
    )
    return summary.sort_values(["missing_count", "column"], ascending=[False, True]).reset_index(drop=True)


def missingness_correlation(df: pd.DataFrame, min_missing: int = 1) -> pd.DataFrame:
    missing_counts = df.isna().sum()
    candidate_columns = missing_counts[missing_counts >= min_missing].index.tolist()
    if len(candidate_columns) < 2:
        return pd.DataFrame()
    return df[candidate_columns].isna().corr().round(3)


def missingness_by_group(
    df: pd.DataFrame,
    target_columns: Iterable[str],
    group_column: str,
) -> pd.DataFrame:
    subset = df[[group_column, *target_columns]].copy()
    grouped = subset.groupby(group_column, dropna=False)
    report = grouped[target_columns].apply(lambda part: part.isna().mean().mul(100))
    return report.reset_index()


def exact_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    return df[df.duplicated(keep=False)].copy()


def near_duplicates_data(data: pd.DataFrame) -> dict[str, pd.DataFrame]:
    same_task_different_project = (
        data.groupby("TASK_ID")["PROJECT_ID"]
        .nunique(dropna=True)
        .rename("project_count")
        .reset_index()
        .query("project_count > 1")
        .merge(data, on="TASK_ID", how="left")
        .sort_values(["TASK_ID", "PROJECT_ID", "START"])
    )

    translator_same_window = data[
        data.duplicated(["TRANSLATOR", "START", "END"], keep=False)
    ].sort_values(["TRANSLATOR", "START", "END", "TASK_ID"])

    translator_same_task_window = data[
        data.duplicated(["TASK_ID", "TRANSLATOR", "START", "END"], keep=False)
    ].sort_values(["TASK_ID", "TRANSLATOR", "START"])

    return {
        "same_task_id_different_projects": same_task_different_project,
        "translator_same_window": translator_same_window,
        "translator_same_task_window": translator_same_task_window,
    }


def detect_outliers(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    rows = []
    for column in columns:
        numeric = pd.to_numeric(df[column], errors="coerce").dropna()
        if numeric.empty:
            continue
        q1 = numeric.quantile(0.25)
        q3 = numeric.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        iqr_mask = (numeric < lower) | (numeric > upper)

        std = numeric.std(ddof=0)
        if std == 0 or np.isnan(std):
            z_mask = pd.Series(False, index=numeric.index)
        else:
            z_scores = (numeric - numeric.mean()) / std
            z_mask = z_scores.abs() > 3

        rows.append(
            {
                "column": column,
                "count": int(numeric.shape[0]),
                "iqr_outliers": int(iqr_mask.sum()),
                "iqr_outlier_pct": round(iqr_mask.mean() * 100, 2),
                "zscore_outliers": int(z_mask.sum()),
                "zscore_outlier_pct": round(z_mask.mean() * 100, 2),
                "min": numeric.min(),
                "p01": numeric.quantile(0.01),
                "median": numeric.median(),
                "p99": numeric.quantile(0.99),
                "max": numeric.max(),
            }
        )
    return pd.DataFrame(rows)


def categorical_variants(series: pd.Series, min_frequency: int = 1) -> pd.DataFrame:
    frame = pd.DataFrame({"raw_value": series.astype("string"), "normalized": normalize_series(series)})
    frame = frame.dropna(subset=["raw_value"])
    counts = (
        frame.groupby(["normalized", "raw_value"], dropna=False)
        .size()
        .rename("count")
        .reset_index()
    )
    family_sizes = counts.groupby("normalized")["raw_value"].nunique().rename("variant_count")
    counts = counts.merge(family_sizes.reset_index(), on="normalized", how="left")
    counts = counts.query("variant_count > 1 and count >= @min_frequency")
    return counts.sort_values(["variant_count", "normalized", "count"], ascending=[False, True, False])


def timestamp_logic_report(data: pd.DataFrame) -> pd.DataFrame:
    checks = {
        "START_after_END": data["START"] > data["END"],
        "ASSIGNED_after_READY": data["ASSIGNED"] > data["READY"],
        "READY_after_WORKING": data["READY"] > data["WORKING"],
        "WORKING_after_DELIVERED": data["WORKING"] > data["DELIVERED"],
    }
    rows = []
    for name, mask in checks.items():
        rows.append(
            {
                "check": name,
                "violations": int(mask.fillna(False).sum()),
                "violation_pct": round(mask.fillna(False).mean() * 100, 3),
            }
        )
    return pd.DataFrame(rows)


def timestamp_violation_samples(data: pd.DataFrame) -> dict[str, pd.DataFrame]:
    checks = {
        "START_after_END": data["START"] > data["END"],
        "ASSIGNED_after_READY": data["ASSIGNED"] > data["READY"],
        "READY_after_WORKING": data["READY"] > data["WORKING"],
        "WORKING_after_DELIVERED": data["WORKING"] > data["DELIVERED"],
    }
    return {
        name: data.loc[mask.fillna(False), ["PROJECT_ID", "TASK_ID", "TRANSLATOR", "START", "END", "ASSIGNED", "READY", "WORKING", "DELIVERED"]]
        .head(20)
        .copy()
        for name, mask in checks.items()
    }


def zero_value_report(data: pd.DataFrame) -> pd.DataFrame:
    subsets = {
        "hours_zero": data["HOURS"].fillna(0).eq(0),
        "cost_zero": data["COST"].fillna(0).eq(0),
        "hours_and_cost_zero": data["HOURS"].fillna(0).eq(0) & data["COST"].fillna(0).eq(0),
    }
    rows = []
    for label, mask in subsets.items():
        subset = data.loc[mask]
        rows.append(
            {
                "segment": label,
                "rows": int(mask.sum()),
                "pct_of_tasks": round(mask.mean() * 100, 3),
                "median_hours": subset["HOURS"].median(),
                "median_cost": subset["COST"].median(),
            }
        )
    return pd.DataFrame(rows)


def same_language_report(data: pd.DataFrame) -> pd.DataFrame:
    mask = normalize_series(data["SOURCE_LANG"]) == normalize_series(data["TARGET_LANG"])
    subset = data.loc[mask].copy()
    if subset.empty:
        return pd.DataFrame(columns=["metric", "value"])
    rows = [
        {"metric": "rows", "value": int(len(subset))},
        {"metric": "share_pct", "value": round(len(subset) / len(data) * 100, 4)},
        {"metric": "unique_translators", "value": int(subset["TRANSLATOR"].nunique())},
        {"metric": "unique_clients", "value": int(subset["MANUFACTURER"].nunique())},
    ]
    return pd.DataFrame(rows)


def same_language_examples(data: pd.DataFrame, limit: int = 25) -> pd.DataFrame:
    mask = normalize_series(data["SOURCE_LANG"]) == normalize_series(data["TARGET_LANG"])
    return (
        data.loc[mask, ["PROJECT_ID", "TASK_ID", "TASK_TYPE", "SOURCE_LANG", "TARGET_LANG", "TRANSLATOR", "MANUFACTURER"]]
        .head(limit)
        .copy()
    )


def cross_sheet_consistency_report(
    data: pd.DataFrame,
    schedules: pd.DataFrame,
    clients: pd.DataFrame,
    pairs: pd.DataFrame,
) -> pd.DataFrame:
    translator_in_schedules = data["TRANSLATOR_KEY"].isin(set(schedules["NAME_KEY"]))
    translator_in_pairs = data["TRANSLATOR_KEY"].isin(set(pairs["TRANSLATOR_KEY"]))
    manufacturer_in_clients = data["CLIENT_KEY"].isin(set(clients["CLIENT_KEY"]))

    rows = [
        {
            "check": "Data translators present in Schedules",
            "matched_rows": int(translator_in_schedules.sum()),
            "match_rate_pct": round(translator_in_schedules.mean() * 100, 3),
            "unmatched_rows": int((~translator_in_schedules).sum()),
            "unmatched_unique_values": int(data.loc[~translator_in_schedules, "TRANSLATOR"].nunique()),
        },
        {
            "check": "Data translators present in TranslatorsCost+Pairs",
            "matched_rows": int(translator_in_pairs.sum()),
            "match_rate_pct": round(translator_in_pairs.mean() * 100, 3),
            "unmatched_rows": int((~translator_in_pairs).sum()),
            "unmatched_unique_values": int(data.loc[~translator_in_pairs, "TRANSLATOR"].nunique()),
        },
        {
            "check": "Data manufacturers present in Clients",
            "matched_rows": int(manufacturer_in_clients.sum()),
            "match_rate_pct": round(manufacturer_in_clients.mean() * 100, 3),
            "unmatched_rows": int((~manufacturer_in_clients).sum()),
            "unmatched_unique_values": int(data.loc[~manufacturer_in_clients, "MANUFACTURER"].nunique()),
        },
    ]
    return pd.DataFrame(rows)


def _deduplicate_join_table(df: pd.DataFrame, key_columns: list[str]) -> pd.DataFrame:
    if not df.duplicated(key_columns).any():
        return df.copy()
    deduped = (
        df.sort_values(key_columns)
        .drop_duplicates(key_columns, keep="first")
        .reset_index(drop=True)
    )
    return deduped


def _map_lookup(
    keys: pd.Series,
    lookup: pd.Series,
    default: object = pd.NA,
    dtype: str | type | None = None,
) -> pd.Series:
    mapping = lookup.to_dict()
    values = np.fromiter(
        (mapping.get(key, default) for key in keys),
        dtype=object if dtype is None else dtype,
        count=len(keys),
    )
    return pd.Series(values, index=keys.index)


def _map_pair_rates(data: pd.DataFrame, pairs: pd.DataFrame) -> np.ndarray:
    pair_rate_lookup = {
        (row.TRANSLATOR, row.SOURCE_LANG, row.TARGET_LANG): (
            np.nan if pd.isna(row.HOURLY_RATE) else float(row.HOURLY_RATE)
        )
        for row in pairs[["TRANSLATOR", "SOURCE_LANG", "TARGET_LANG", "HOURLY_RATE"]].itertuples(index=False)
    }
    return np.fromiter(
        (
            pair_rate_lookup.get((translator, source_lang, target_lang), np.nan)
            for translator, source_lang, target_lang in zip(
                data["TRANSLATOR"],
                data["SOURCE_LANG"],
                data["TARGET_LANG"],
            )
        ),
        dtype="float64",
        count=len(data),
    )


def join_datasets(sheets: dict[str, pd.DataFrame] | None = None) -> pd.DataFrame:
    if sheets is None:
        sheets = load_all_data(columns_by_sheet={"data": DATA_ENRICHMENT_COLUMNS})

    enriched = sheets["data"].copy(deep=False)
    clients = _deduplicate_join_table(sheets["clients"], ["CLIENT_NAME"])
    pairs = _deduplicate_join_table(sheets["pairs"], ["TRANSLATOR", "SOURCE_LANG", "TARGET_LANG"])
    schedules = _deduplicate_join_table(sheets["schedules"], ["NAME"])

    clients_lookup = clients.set_index("CLIENT_NAME", drop=False)
    enriched["SELLING_HOURLY_PRICE"] = _map_lookup(
        enriched["MANUFACTURER"],
        clients_lookup["SELLING_HOURLY_PRICE"],
        default=np.nan,
        dtype="float64",
    )
    enriched["MIN_QUALITY"] = _map_lookup(
        enriched["MANUFACTURER"],
        clients_lookup["MIN_QUALITY"],
        default=np.nan,
        dtype="float64",
    )
    enriched["WILDCARD"] = _map_lookup(enriched["MANUFACTURER"], clients_lookup["WILDCARD"])
    enriched["CLIENT_MATCH_EXACT"] = enriched["SELLING_HOURLY_PRICE"].notna()

    enriched["PAIR_HOURLY_RATE"] = _map_pair_rates(enriched, pairs)
    enriched["PAIR_MATCH_EXACT"] = enriched["PAIR_HOURLY_RATE"].notna()

    schedules_lookup = schedules.set_index("NAME", drop=False)
    enriched["SCHEDULE_START"] = _map_lookup(enriched["TRANSLATOR"], schedules_lookup["START"])
    enriched["SCHEDULE_END"] = _map_lookup(enriched["TRANSLATOR"], schedules_lookup["END"])
    for day_column in SCHEDULE_DAY_COLUMNS:
        enriched[day_column] = _map_lookup(
            enriched["TRANSLATOR"],
            schedules_lookup[day_column],
            default=0,
            dtype="int8",
        )
    enriched["SCHEDULE_MATCH_EXACT"] = pd.Series(
        enriched["SCHEDULE_START"],
        index=enriched.index,
    ).notna()

    return enriched


def summarize_join_integrity(joined: pd.DataFrame) -> JoinIntegritySummary:
    return JoinIntegritySummary(
        data_to_clients_match_rate=float(joined["CLIENT_MATCH_EXACT"].mean()),
        data_to_pairs_match_rate=float(joined["PAIR_MATCH_EXACT"].mean()),
        data_to_schedules_match_rate=float(joined["SCHEDULE_MATCH_EXACT"].mean()),
    )


def diagnose_client_unmatched(joined: pd.DataFrame, clients: pd.DataFrame) -> pd.DataFrame:
    unmatched = joined.loc[~joined["CLIENT_MATCH_EXACT"], ["MANUFACTURER", "CLIENT_KEY"]].drop_duplicates()
    if unmatched.empty:
        return pd.DataFrame(columns=["MANUFACTURER", "diagnosis"])

    normalized_clients = set(clients["CLIENT_KEY"])
    unmatched["diagnosis"] = np.where(
        unmatched["CLIENT_KEY"].isin(normalized_clients),
        "spelling_or_whitespace_variant",
        "missing_client",
    )
    return unmatched.sort_values(["diagnosis", "MANUFACTURER"]).reset_index(drop=True)


def diagnose_schedule_unmatched(joined: pd.DataFrame, schedules: pd.DataFrame) -> pd.DataFrame:
    unmatched = joined.loc[~joined["SCHEDULE_MATCH_EXACT"], ["TRANSLATOR", "TRANSLATOR_KEY"]].drop_duplicates()
    if unmatched.empty:
        return pd.DataFrame(columns=["TRANSLATOR", "diagnosis"])

    normalized_names = set(schedules["NAME_KEY"])
    unmatched["diagnosis"] = np.where(
        unmatched["TRANSLATOR_KEY"].isin(normalized_names),
        "spelling_or_whitespace_variant",
        "missing_translator",
    )
    return unmatched.sort_values(["diagnosis", "TRANSLATOR"]).reset_index(drop=True)


def diagnose_pair_unmatched(joined: pd.DataFrame, pairs: pd.DataFrame) -> pd.DataFrame:
    unmatched = joined.loc[
        ~joined["PAIR_MATCH_EXACT"],
        ["TRANSLATOR", "SOURCE_LANG", "TARGET_LANG", "TRANSLATOR_KEY", "SOURCE_LANG_CLEAN", "TARGET_LANG_CLEAN"],
    ].drop_duplicates()
    if unmatched.empty:
        return pd.DataFrame(columns=["TRANSLATOR", "SOURCE_LANG", "TARGET_LANG", "diagnosis"])

    translator_set = set(pairs["TRANSLATOR"])
    translator_key_set = set(pairs["TRANSLATOR_KEY"])
    normalized_triples = set(
        zip(pairs["TRANSLATOR_KEY"], pairs["SOURCE_LANG_CLEAN"], pairs["TARGET_LANG_CLEAN"])
    )
    translator_pair_keys = set(zip(pairs["TRANSLATOR"], pairs["SOURCE_LANG"], pairs["TARGET_LANG"]))
    translator_normalized_pairs = set(zip(pairs["TRANSLATOR_KEY"], pairs["SOURCE_LANG_CLEAN"]))

    diagnoses = []
    for row in unmatched.itertuples(index=False):
        if row.TRANSLATOR not in translator_set and row.TRANSLATOR_KEY not in translator_key_set:
            diagnosis = "translator_missing"
        elif (row.TRANSLATOR_KEY, row.SOURCE_LANG_CLEAN, row.TARGET_LANG_CLEAN) in normalized_triples:
            diagnosis = "language_or_name_spelling_variant"
        elif (row.TRANSLATOR_KEY, row.SOURCE_LANG_CLEAN) in translator_normalized_pairs:
            diagnosis = "target_language_not_listed"
        else:
            diagnosis = "language_pair_not_listed"
        diagnoses.append(diagnosis)

    unmatched = unmatched.assign(diagnosis=diagnoses)
    return unmatched.sort_values(["diagnosis", "TRANSLATOR", "SOURCE_LANG", "TARGET_LANG"]).reset_index(drop=True)


def _prepare_enriched_task_dtypes(df: pd.DataFrame) -> None:
    for column in DATA_DATETIME_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce")

    for column in [
        "HOURS",
        "HOURLY_RATE",
        "COST",
        "QUALITY_EVALUATION",
        "SELLING_HOURLY_PRICE",
        "MIN_QUALITY",
        "PAIR_HOURLY_RATE",
    ]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").astype("float64")

    if "TASK_ID" in df.columns:
        df["TASK_ID"] = pd.to_numeric(df["TASK_ID"], errors="coerce").fillna(-1).astype("int64")

    for column in df.select_dtypes(include=["string", "object"]).columns:
        df[column] = df[column].astype("category")


def _datetime_sort_key(series: pd.Series) -> np.ndarray:
    key = pd.to_datetime(series, errors="coerce").to_numpy(dtype="datetime64[ns]").view("int64")
    key = key.copy()
    key[key == np.iinfo(np.int64).min] = np.iinfo(np.int64).max
    return key


def _numeric_sort_key(series: pd.Series) -> np.ndarray:
    key = pd.to_numeric(series, errors="coerce").fillna(np.iinfo(np.int64).max)
    return key.to_numpy(dtype="int64")


def _sort_tasks_chronologically(df: pd.DataFrame) -> pd.DataFrame:
    order = np.lexsort(
        (
            _numeric_sort_key(df["TASK_ID"]),
            _datetime_sort_key(df["ASSIGNED"]),
            _datetime_sort_key(df["START"]),
        )
    )
    return df.take(order).reset_index(drop=True)


def build_enriched_tasks(
    save: bool = False,
    joined: pd.DataFrame | None = None,
) -> pd.DataFrame:
    enriched = join_datasets() if joined is None else joined
    _prepare_enriched_task_dtypes(enriched)
    enriched = _sort_tasks_chronologically(enriched)

    on_time_mask = enriched["DELIVERED"].notna() & enriched["END"].notna()
    enriched["ON_TIME"] = (enriched["DELIVERED"] <= enriched["END"]).astype("Int8").where(on_time_mask)
    quality_mask = enriched["QUALITY_EVALUATION"].notna()
    enriched["HIGH_QUALITY_8"] = (
        (enriched["QUALITY_EVALUATION"] >= QUALITY_THRESHOLD).astype("Int8").where(quality_mask)
    )
    enriched["TIME_TO_START_HOURS"] = (enriched["WORKING"] - enriched["READY"]).dt.total_seconds() / 3600
    enriched["TIME_TO_ASSIGN_HOURS"] = (enriched["ASSIGNED"] - enriched["START"]).dt.total_seconds() / 3600
    enriched["TASK_DURATION_HOURS"] = (enriched["END"] - enriched["START"]).dt.total_seconds() / 3600
    enriched["ACTUAL_WORKING_HOURS"] = (enriched["DELIVERED"] - enriched["WORKING"]).dt.total_seconds() / 3600
    late_mask = (enriched["DELIVERED"] > enriched["END"]).fillna(False)
    enriched["LATENESS_MINUTES"] = np.where(
        late_mask,
        (enriched["DELIVERED"] - enriched["END"]).dt.total_seconds() / 60,
        0.0,
    )

    enriched["RATE_DISCREPANCY"] = enriched["HOURLY_RATE"] - enriched["PAIR_HOURLY_RATE"]
    enriched["MARGIN_TASK_RATE"] = (enriched["SELLING_HOURLY_PRICE"] - enriched["HOURLY_RATE"]) * enriched["HOURS"]
    enriched["MARGIN_PAIR_RATE"] = (enriched["SELLING_HOURLY_PRICE"] - enriched["PAIR_HOURLY_RATE"]) * enriched["HOURS"]
    rate_mask = enriched["PAIR_HOURLY_RATE"].notna() & enriched["SELLING_HOURLY_PRICE"].notna()
    enriched["RATE_EXCEEDS_SELLING_PRICE"] = (
        (enriched["PAIR_HOURLY_RATE"] > enriched["SELLING_HOURLY_PRICE"]).astype("Int8").where(rate_mask)
    )

    _compute_schedule_features(enriched)
    _compute_history_features(enriched)

    if save:
        enriched.to_csv(ENRICHED_PATH, index=False)
    return enriched


def _compute_schedule_features(df: pd.DataFrame) -> None:
    for day_col in SCHEDULE_DAY_COLUMNS:
        df[day_col] = pd.to_numeric(df[day_col], errors="coerce").fillna(0)

    df["WORKING_DAYS_PER_WEEK"] = df[SCHEDULE_DAY_COLUMNS].sum(axis=1)
    df["WEEKEND_WORKER"] = ((df["SAT"] == 1) | (df["SUN"] == 1)).astype("Int64")

    schedule_start_minutes = _time_string_to_minutes(df["SCHEDULE_START"])
    schedule_end_minutes = _time_string_to_minutes(df["SCHEDULE_END"])
    df["SCHEDULE_START_MINUTES"] = schedule_start_minutes
    df["SCHEDULE_END_MINUTES"] = schedule_end_minutes
    df["NIGHT_SHIFT"] = (schedule_end_minutes <= schedule_start_minutes).astype("Int64")
    df["SHIFT_HOURS_PER_DAY"] = ((schedule_end_minutes - schedule_start_minutes) % (24 * 60)) / 60

    start_minutes = (
        df["START"].dt.hour.fillna(0) * 60
        + df["START"].dt.minute.fillna(0)
        + df["START"].dt.second.fillna(0) / 60
    )
    end_minutes = (
        df["END"].dt.hour.fillna(0) * 60
        + df["END"].dt.minute.fillna(0)
        + df["END"].dt.second.fillna(0) / 60
    )
    start_weekday = df["START"].dt.dayofweek
    end_weekday = df["END"].dt.dayofweek
    active_flags = df[SCHEDULE_DAY_COLUMNS].to_numpy(dtype=float)

    df["TASK_START_WORKDAY"] = [
        int(active_flags[idx, int(weekday)] == 1) if not pd.isna(weekday) else pd.NA
        for idx, weekday in enumerate(start_weekday)
    ]
    df["TASK_END_WORKDAY"] = [
        int(active_flags[idx, int(weekday)] == 1) if not pd.isna(weekday) else pd.NA
        for idx, weekday in enumerate(end_weekday)
    ]

    same_day_mask = df["START"].dt.normalize() == df["END"].dt.normalize()
    non_night = df["NIGHT_SHIFT"].fillna(0).eq(0)

    start_within = pd.Series(False, index=df.index)
    end_within = pd.Series(False, index=df.index)

    normal_mask = non_night & df["SCHEDULE_START_MINUTES"].notna() & df["SCHEDULE_END_MINUTES"].notna()
    start_within.loc[normal_mask] = (
        (start_minutes.loc[normal_mask] >= schedule_start_minutes.loc[normal_mask])
        & (start_minutes.loc[normal_mask] <= schedule_end_minutes.loc[normal_mask])
    )
    end_within.loc[normal_mask] = (
        (end_minutes.loc[normal_mask] >= schedule_start_minutes.loc[normal_mask])
        & (end_minutes.loc[normal_mask] <= schedule_end_minutes.loc[normal_mask])
    )

    night_mask = ~non_night & df["SCHEDULE_START_MINUTES"].notna() & df["SCHEDULE_END_MINUTES"].notna()
    start_within.loc[night_mask] = (
        (start_minutes.loc[night_mask] >= schedule_start_minutes.loc[night_mask])
        | (start_minutes.loc[night_mask] <= schedule_end_minutes.loc[night_mask])
    )
    end_within.loc[night_mask] = (
        (end_minutes.loc[night_mask] >= schedule_start_minutes.loc[night_mask])
        | (end_minutes.loc[night_mask] <= schedule_end_minutes.loc[night_mask])
    )

    df["TASK_START_WITHIN_SHIFT"] = np.where(df["START"].notna(), start_within.astype("Int64"), pd.NA)
    df["TASK_END_WITHIN_SHIFT"] = np.where(df["END"].notna(), end_within.astype("Int64"), pd.NA)
    df["SAME_DAY_TASK_WINDOW"] = same_day_mask.astype("Int64")

    day_flags = df[SCHEDULE_DAY_COLUMNS].fillna(0).astype(np.int8).to_numpy()
    weekmask_codes = day_flags.dot(np.array([64, 32, 16, 8, 4, 2, 1], dtype=np.int16))
    available_hours = pd.Series(np.nan, index=df.index)
    valid_mask = df["START"].notna() & df["END"].notna() & df["SHIFT_HOURS_PER_DAY"].notna()
    valid_array = valid_mask.to_numpy()

    for weekmask_code in np.unique(weekmask_codes[valid_array]):
        if weekmask_code == 0:
            continue
        idx = valid_array & (weekmask_codes == weekmask_code)
        if not idx.any():
            continue
        weekmask = format(int(weekmask_code), "07b")
        start_dates = df.loc[idx, "START"].dt.normalize().to_numpy(dtype="datetime64[D]")
        end_dates = (df.loc[idx, "END"].dt.normalize() + pd.Timedelta(days=1)).to_numpy(dtype="datetime64[D]")
        active_days = np.busday_count(start_dates, end_dates, weekmask=weekmask)
        hours = np.minimum(
            active_days * df.loc[idx, "SHIFT_HOURS_PER_DAY"].to_numpy(),
            df.loc[idx, "TASK_DURATION_HOURS"].clip(lower=0).to_numpy(),
        )
        available_hours.loc[idx] = hours

    df["AVAILABLE_HOURS_IN_WINDOW"] = available_hours
    df["SHIFT_OVERLAP_PCT"] = df["AVAILABLE_HOURS_IN_WINDOW"] / df["TASK_DURATION_HOURS"].replace(0, np.nan)
    df["AVAILABILITY_FEATURE_RELIABILITY"] = np.where(
        df["NIGHT_SHIFT"] == 1,
        "approximate_night_shift",
        "standard_day_shift",
    )


def _time_string_to_minutes(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series.astype("string"), format="%H:%M:%S", errors="coerce")
    return parsed.dt.hour * 60 + parsed.dt.minute + parsed.dt.second / 60


def _compute_history_features(df: pd.DataFrame) -> None:
    hours = df["HOURS"].fillna(0)
    on_time_numeric = pd.to_numeric(df["ON_TIME"], errors="coerce")
    lateness = df["LATENESS_MINUTES"].fillna(0)
    quality = pd.to_numeric(df["QUALITY_EVALUATION"], errors="coerce")

    df["PRIOR_HOURS_TRANSLATOR"] = _prior_cumsum(hours, [df["TRANSLATOR"]])
    df["PRIOR_HOURS_CLIENT"] = _prior_cumsum(hours, [df["TRANSLATOR"], df["MANUFACTURER"]])
    df["PRIOR_HOURS_SECTOR"] = _prior_cumsum(hours, [df["TRANSLATOR"], df["MANUFACTURER_SECTOR"]])
    df["PRIOR_HOURS_TASK_TYPE"] = _prior_cumsum(hours, [df["TRANSLATOR"], df["TASK_TYPE_CLEAN"]])
    df["PRIOR_TASKS_LANGUAGE_PAIR"] = _prior_count(
        [df["TRANSLATOR"], df["SOURCE_LANG"], df["TARGET_LANG"]]
    )

    df["PRIOR_QUALITY_COUNT_TRANSLATOR"] = _prior_valid_count(quality, [df["TRANSLATOR"]])
    df["PRIOR_QUALITY_MEAN_TRANSLATOR"] = _prior_mean(quality, [df["TRANSLATOR"]])
    df["PRIOR_QUALITY_MEAN_PAIR"] = _prior_mean(quality, [df["TRANSLATOR"], df["SOURCE_LANG"], df["TARGET_LANG"]])
    df["PRIOR_QUALITY_MEAN_TASK_TYPE"] = _prior_mean(quality, [df["TRANSLATOR"], df["TASK_TYPE_CLEAN"]])
    df["ROLLING_QUALITY_MEAN_5"] = (
        df.groupby("TRANSLATOR", sort=False, observed=True)["QUALITY_EVALUATION"]
        .transform(lambda s: s.shift().rolling(5, min_periods=1).mean())
    )
    df["ROLLING_QUALITY_STD_5"] = (
        df.groupby("TRANSLATOR", sort=False, observed=True)["QUALITY_EVALUATION"]
        .transform(lambda s: s.shift().rolling(5, min_periods=2).std())
    )

    df["PRIOR_ON_TIME_RATE_TRANSLATOR"] = _prior_mean(on_time_numeric, [df["TRANSLATOR"]])
    df["PRIOR_ON_TIME_RATE_TASK_TYPE"] = _prior_mean(
        on_time_numeric,
        [df["TRANSLATOR"], df["TASK_TYPE_CLEAN"]],
    )
    df["PRIOR_AVG_LATENESS_MINUTES"] = _prior_mean(lateness, [df["TRANSLATOR"]])
    df["ROLLING_ON_TIME_RATE_5"] = (
        df.groupby("TRANSLATOR", sort=False, observed=True)["ON_TIME"]
        .transform(lambda s: pd.to_numeric(s, errors="coerce").shift().rolling(5, min_periods=1).mean())
    )
    rolling_prev_5 = (
        df.groupby("TRANSLATOR", sort=False, observed=True)["ON_TIME"]
        .transform(lambda s: pd.to_numeric(s, errors="coerce").shift(5).rolling(5, min_periods=1).mean())
    )
    df["PUNCTUALITY_TREND_DELTA"] = df["ROLLING_ON_TIME_RATE_5"] - rolling_prev_5


def _prior_cumsum(values: pd.Series, groupers: list[pd.Series]) -> pd.Series:
    cumulative = values.groupby(groupers, observed=True).cumsum()
    return cumulative - values


def _prior_count(groupers: list[pd.Series]) -> pd.Series:
    base = pd.Series(1, index=groupers[0].index, dtype="int64")
    counts = base.groupby(groupers, observed=True).cumsum()
    return counts - 1


def _prior_valid_count(values: pd.Series, groupers: list[pd.Series]) -> pd.Series:
    valid = values.notna().astype(int)
    counts = valid.groupby(groupers, observed=True).cumsum()
    return counts - valid


def _prior_mean(values: pd.Series, groupers: list[pd.Series]) -> pd.Series:
    valid = values.notna().astype(int)
    filled = values.fillna(0)
    cumulative_sum = filled.groupby(groupers, observed=True).cumsum() - filled
    prior_count = valid.groupby(groupers, observed=True).cumsum() - valid
    return cumulative_sum / prior_count.replace(0, np.nan)


def translator_quality_summary(data: pd.DataFrame) -> pd.DataFrame:
    grouped = data.groupby("TRANSLATOR")
    summary = grouped.agg(
        task_count=("TASK_ID", "size"),
        total_hours=("HOURS", "sum"),
        avg_quality=("QUALITY_EVALUATION", "mean"),
        quality_std=("QUALITY_EVALUATION", "std"),
        scored_tasks=("QUALITY_EVALUATION", "count"),
    )
    summary["quality_ci_low"] = summary["avg_quality"] - 1.96 * (
        summary["quality_std"] / np.sqrt(summary["scored_tasks"].replace(0, np.nan))
    )
    summary["quality_ci_high"] = summary["avg_quality"] + 1.96 * (
        summary["quality_std"] / np.sqrt(summary["scored_tasks"].replace(0, np.nan))
    )
    summary = summary.reset_index().sort_values("task_count", ascending=False)
    return summary


def translator_on_time_summary(enriched: pd.DataFrame) -> pd.DataFrame:
    grouped = enriched.groupby("TRANSLATOR")
    summary = grouped.agg(
        tasks=("TASK_ID", "size"),
        on_time_tasks=("ON_TIME", lambda s: pd.to_numeric(s, errors="coerce").sum()),
        on_time_rate=("ON_TIME", lambda s: pd.to_numeric(s, errors="coerce").mean()),
    )
    ci_low, ci_high = wilson_interval(
        summary["on_time_tasks"].fillna(0).to_numpy(),
        summary["tasks"].to_numpy(),
    )
    summary["on_time_ci_low"] = ci_low
    summary["on_time_ci_high"] = ci_high
    return summary.reset_index().sort_values("tasks", ascending=False)


def wilson_interval(successes: np.ndarray, totals: np.ndarray, z: float = 1.96) -> tuple[np.ndarray, np.ndarray]:
    totals = totals.astype(float)
    successes = successes.astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        phat = successes / totals
        denominator = 1 + (z**2 / totals)
        centre = phat + z**2 / (2 * totals)
        spread = z * np.sqrt((phat * (1 - phat) + z**2 / (4 * totals)) / totals)
        lower = (centre - spread) / denominator
        upper = (centre + spread) / denominator
    lower = np.where(totals > 0, lower, np.nan)
    upper = np.where(totals > 0, upper, np.nan)
    return lower, upper


def proofread_reviewer_comparison(data: pd.DataFrame) -> pd.DataFrame:
    workflow = data.sort_values(["PROJECT_ID", "START", "TASK_ID"]).copy()
    workflow["NEXT_TASK_TYPE"] = workflow.groupby("PROJECT_ID")["TASK_TYPE_CLEAN"].shift(-1)
    workflow["NEXT_TRANSLATOR"] = workflow.groupby("PROJECT_ID")["TRANSLATOR"].shift(-1)
    transitions = workflow[
        workflow["TASK_TYPE_CLEAN"].isin(["Translation", "TranslationOnly"])
        & workflow["NEXT_TASK_TYPE"].eq("ProofReading")
    ].copy()
    if transitions.empty:
        return pd.DataFrame(columns=["same_translator", "count"])
    transitions["same_translator"] = transitions["TRANSLATOR"] == transitions["NEXT_TRANSLATOR"]
    return (
        transitions["same_translator"]
        .value_counts(dropna=False)
        .rename_axis("same_translator")
        .reset_index(name="count")
    )


def load_enriched_tasks(force_rebuild: bool = False) -> pd.DataFrame:
    if force_rebuild or not ENRICHED_PATH.exists():
        return build_enriched_tasks(save=True)
    available_columns = pd.read_csv(ENRICHED_PATH, nrows=0).columns
    date_columns = [column for column in DATA_DATETIME_COLUMNS if column in available_columns]
    return pd.read_csv(ENRICHED_PATH, parse_dates=date_columns)
