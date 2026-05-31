from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
MODELS_DIR = PROJECT_ROOT / "models"

RAW_EXCEL_FILE = RAW_DATA_DIR / "data.xlsx"
TRANSLATOR_STATS_FILE = PROCESSED_DATA_DIR / "translator_statistics.csv"
