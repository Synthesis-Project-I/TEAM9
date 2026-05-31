import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.pipeline.features import prepare_pipeline_tables
from utils.config import PROCESSED_DATA_DIR, TRANSLATOR_STATS_FILE
from utils.data_loader import load_interim_data


def main():
    data_dict = load_interim_data()
    history_df, clients_df, translators_df = prepare_pipeline_tables(data_dict)
    PROCESSED_DATA_DIR.mkdir(exist_ok=True)
    history_df.to_csv(PROCESSED_DATA_DIR / "clean_history.csv", index=False)
    translators_df.to_csv(TRANSLATOR_STATS_FILE, index=False)
    print(TRANSLATOR_STATS_FILE)


if __name__ == "__main__":
    main()
