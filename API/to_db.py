import pandas as pd
import sqlite3

con = sqlite3.connect("./data/database.db")

df = pd.read_excel("./data/260319_GrauIAI_data.xlsx", None)

for name, dataframe in df.items():
    dataframe.to_csv(f"{name}.csv")
    dataframe.to_sql(name, con)

con.close()
