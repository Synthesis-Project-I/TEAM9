import pandas as pd

from utils.config import (
    CLEAN_HISTORY_FILE,
    CLIENTS_FILE,
    INTERIM_DATA_DIR,
    RAW_EXCEL_FILE,
    TRANSLATOR_STATS_FILE,
)


def load_excel_data(path=RAW_EXCEL_FILE):
    """Load the original Excel workbook as a dictionary of DataFrames."""
    return pd.read_excel(path, sheet_name=None)


def load_interim_data(path=INTERIM_DATA_DIR):
    """Load the raw sheets converted to CSV (one row per source record)."""
    return {
        "Data": pd.read_csv(path / "data.csv", low_memory=False),
        "Schedules": pd.read_csv(path / "schedules.csv"),
        "Clients": pd.read_csv(path / "clients.csv"),
        "TranslatorsCost+Pairs": pd.read_csv(path / "translatorsCostPairs.csv"),
    }


def load_processed_data():
    """Load the cleaned, model-ready tables produced by build_processed_data.py.

    Returns:
        (history_df, clients_df, translators_df) ready for the pipeline.
    """
    history_df = pd.read_csv(CLEAN_HISTORY_FILE, low_memory=False)
    clients_df = pd.read_csv(CLIENTS_FILE)
    translators_df = pd.read_csv(TRANSLATOR_STATS_FILE)
    return history_df, clients_df, translators_df
