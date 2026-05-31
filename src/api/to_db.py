import pandas as pd
import sqlite3
from pathlib import Path

base = Path(__file__).resolve().parent
data_dir = base / "data"
data_dir.mkdir(exist_ok=True)
con = sqlite3.connect(data_dir / "database.db")

files = {
    "Clients": base / "Clients.csv",
    "Data": base / "Data.csv",
    "Schedules": base / "Schedules.csv",
    "TranslatorsCost+Pairs": base / "TranslatorsCost+Pairs.csv",
}

for name, path in files.items():
    dataframe = pd.read_csv(path)
    dataframe.to_sql(name, con, if_exists="replace")

con.close()
