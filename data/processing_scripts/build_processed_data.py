"""Build the processed, model-ready tables from the interim CSVs.

Reads data/interim/ (raw sheets as CSV) and writes the cleaned tables the
recommendation pipeline consumes to data/processed/:
    clean_history.csv          cleaned historical task log
    clients.csv                client constraints
    translator_statistics.csv  per-translator stats / language-pair rates
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.pipeline.features import prepare_pipeline_tables
from utils.config import CLEAN_HISTORY_FILE, CLIENTS_FILE, PROCESSED_DATA_DIR, TRANSLATOR_STATS_FILE
from utils.data_loader import load_interim_data


def main():
    data_dict = load_interim_data()
    history_df, clients_df, translators_df = prepare_pipeline_tables(data_dict)

    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    history_df.to_csv(CLEAN_HISTORY_FILE, index=False)
    clients_df.to_csv(CLIENTS_FILE, index=False)
    translators_df.to_csv(TRANSLATOR_STATS_FILE, index=False)
    print(f"Wrote processed tables to {PROCESSED_DATA_DIR}")


if __name__ == "__main__":
    main()
