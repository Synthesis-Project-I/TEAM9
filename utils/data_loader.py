import pandas as pd

from utils.config import INTERIM_DATA_DIR, RAW_EXCEL_FILE, TRANSLATOR_STATS_FILE


def load_excel_data(path=RAW_EXCEL_FILE):
    """Load the original Excel workbook as a dictionary of DataFrames."""
    return pd.read_excel(path, sheet_name=None)


def load_interim_data(path=INTERIM_DATA_DIR):
    """Load the CSV files generated from the Excel workbook."""
    return {
        "Data": pd.read_csv(path / "data.csv", low_memory=False),
        "Schedules": pd.read_csv(path / "schedules.csv"),
        "Clients": pd.read_csv(path / "clients.csv"),
        "TranslatorsCost+Pairs": pd.read_csv(path / "translatorsCostPairs.csv"),
    }


def load_translator_statistics(path=TRANSLATOR_STATS_FILE):
    """Load the processed translator statistics table."""
    return pd.read_csv(path)
