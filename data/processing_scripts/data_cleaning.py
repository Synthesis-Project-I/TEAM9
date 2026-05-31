import os
import re
import sys
import json
import unicodedata
import pandas as pd

# Get paths
path_base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # Base path of the repository
path_raw = os.path.join(path_base, "data", "raw") # Path to the raw folder
path_interim = os.path.join(path_base, "data", "interim")
input_file = "data.xlsx" # Input file name

print(f"[PATHS] Base      : {path_base}")
print(f"[PATHS] Raw       : {path_raw}")
print(f"[PATHS] Interim   : {path_interim}")
print(f"[PATHS] Input file: {input_file}")

# # Load and clean CSVs
print("\n" + "=" * 60)
print("LOADING & CLEANING CSVs")
print("=" * 60)

expected_csvs = {
    "clients": os.path.join(path_interim, "clients.csv"),
    "data": os.path.join(path_interim, "data.csv"),
    "schedules": os.path.join(path_interim, "schedules.csv"),
    "translatorsCostPairs": os.path.join(path_interim, "translatorsCostPairs.csv"),
}

# Check all expected files exist before loading
for name, path in expected_csvs.items():
    if not os.path.exists(path):
        print(f"[ERROR] Expected CSV not found: {path}")
        sys.exit(1)

try:
    df_clients = pd.read_csv(expected_csvs["clients"])
    df_data = pd.read_csv(expected_csvs["data"])
    df_schedules = pd.read_csv(expected_csvs["schedules"])
    df_translators = pd.read_csv(expected_csvs["translatorsCostPairs"])
except Exception as e:
    print(f"[ERROR] Failed to load CSV files: {e}")
    sys.exit(1)

print(f"\n[LOADED] Raw shapes:")
print(f"  clients             : {df_clients.shape}")
print(f"  data                : {df_data.shape}")
print(f"  schedules           : {df_schedules.shape}")
print(f"  translatorsCostPairs: {df_translators.shape}")


# --- Clean: clients ---
print(f"\n[CLEAN] clients")
n_before = len(df_clients)
df_clients = df_clients.drop_duplicates()
n_dupes = n_before - len(df_clients)
df_clients = df_clients.dropna()
n_nulls = n_before - n_dupes - len(df_clients)
print(f"  Removed {n_dupes} duplicate row(s), {n_nulls} row(s) with nulls | {len(df_clients)} rows remaining")
try:
    df_clients.to_csv(expected_csvs["clients"], index=False)
    print(f"  [SAVED] {expected_csvs['clients']}")
except Exception as e:
    print(f"  [ERROR] Failed to save clients CSV: {e}")
    sys.exit(1)


# --- Clean: data ---
print(f"\n[CLEAN] data")
n_before = len(df_data)
df_data = df_data.drop_duplicates()
n_dupes = n_before - len(df_data)
print(f"  Removed {n_dupes} duplicate row(s) | {len(df_data)} rows remaining")
try:
    df_data.to_csv(expected_csvs["data"], index=False)
    print(f"  [SAVED] {expected_csvs['data']}")
except Exception as e:
    print(f"  [ERROR] Failed to save data CSV: {e}")
    sys.exit(1)


# --- Clean: schedules ---
print(f"\n[CLEAN] schedules")

required_cols = {"START", "END"}
missing_cols = required_cols - set(df_schedules.columns)
if missing_cols:
    print(f"  [ERROR] Missing required column(s) in schedules: {missing_cols}")
    sys.exit(1)

# Ensure columns are strings before regex/string operations
df_schedules["START"] = df_schedules["START"].astype(str)
df_schedules["END"] = df_schedules["END"].astype(str)

time_pattern = re.compile(r"^\d{2}:\d{2}:\d{2}$")

invalid_before = df_schedules[
    ~df_schedules["START"].str.match(time_pattern) | ~df_schedules["END"].str.match(time_pattern)
]
print(f"  Invalid time rows BEFORE cleaning: {len(invalid_before)}")
if len(invalid_before) > 0:
    print(f"  Sample invalid rows:\n{invalid_before[['START', 'END']].head().to_string()}")

# Strip leading date portion (e.g. "2024-01-15 08:30:00" -> "08:30:00")
df_schedules["START"] = df_schedules["START"].str.split(" ").str[-1]
df_schedules["END"] = df_schedules["END"].str.split(" ").str[-1]

invalid_after = df_schedules[
    ~df_schedules["START"].str.match(time_pattern) | ~df_schedules["END"].str.match(time_pattern)
]
print(f"  Invalid time rows AFTER cleaning : {len(invalid_after)}")
if len(invalid_after) > 0:
    print(f"  [WARNING] Rows still invalid after cleaning:\n{invalid_after[['START', 'END']].to_string()}")

try:
    df_schedules.to_csv(expected_csvs["schedules"], index=False)
    print(f"  [SAVED] {expected_csvs['schedules']}")
except Exception as e:
    print(f"  [ERROR] Failed to save schedules CSV: {e}")
    sys.exit(1)


# --- Clean: translators ---
print(f"\n[CLEAN] translatorsCostPairs")
n_before = len(df_translators)
df_translators = df_translators.drop_duplicates()
n_dupes = n_before - len(df_translators)
df_translators = df_translators.dropna()
n_nulls = n_before - n_dupes - len(df_translators)
print(f"  Removed {n_dupes} duplicate row(s), {n_nulls} row(s) with nulls | {len(df_translators)} rows remaining")
try:
    df_translators.to_csv(expected_csvs["translatorsCostPairs"], index=False)
    print(f"  [SAVED] {expected_csvs['translatorsCostPairs']}")
except Exception as e:
    print(f"  [ERROR] Failed to save translatorsCostPairs CSV: {e}")
    sys.exit(1)


# # Build JSON dictionaries
print("\n" + "=" * 60)
print("BUILDING LANGUAGE DICTIONARIES")
print("=" * 60)

required_translator_cols = {"TRANSLATOR", "SOURCE_LANG", "TARGET_LANG", "HOURLY_RATE"}
missing_translator_cols = required_translator_cols - set(df_translators.columns)
if missing_translator_cols:
    print(f"[ERROR] Missing required column(s) in translators: {missing_translator_cols}")
    sys.exit(1)

dict_translator_langs = {}  # Dictionary by translator
dict_source_langs = {}      # Dictionary by source language
dict_target_langs = {}      # Dictionary by target language

skipped_rows = 0
for idx, row in df_translators.iterrows():
    str_translator = row["TRANSLATOR"]
    str_source = row["SOURCE_LANG"]
    str_target = row["TARGET_LANG"]
    num_rate = row["HOURLY_RATE"]

    # Skip rows with any null key fields
    if pd.isna(str_translator) or pd.isna(str_source) or pd.isna(str_target) or pd.isna(num_rate):
        print(f"  [WARNING] Skipping row {idx} due to null value(s): {row[list(required_translator_cols)].to_dict()}")
        skipped_rows += 1
        continue

    # Translator dict
    dict_translator_langs.setdefault(str_translator, {}).setdefault(str_source, {})[str_target] = num_rate
    # Source lang dict
    dict_source_langs.setdefault(str_source, {}).setdefault(str_target, {})[str_translator] = num_rate
    # Target lang dict
    dict_target_langs.setdefault(str_target, {}).setdefault(str_source, {})[str_translator] = num_rate

if skipped_rows:
    print(f"[WARNING] Skipped {skipped_rows} row(s) with null key fields during dict build")

print(f"\n[SUMMARY] Language dictionaries built:")
print(f"  Translators   : {len(dict_translator_langs)}")
print(f"  Source langs  : {len(dict_source_langs)}")
print(f"  Target langs  : {len(dict_target_langs)}")


# # Rate discrepancy analysis
print("\n" + "=" * 60)
print("RATE DISCREPANCY ANALYSIS")
print("=" * 60)

required_data_cols = {"TRANSLATOR", "SOURCE_LANG", "TARGET_LANG", "HOURLY_RATE"}
missing_data_cols = required_data_cols - set(df_data.columns)
if missing_data_cols:
    print(f"[ERROR] Missing required column(s) in data: {missing_data_cols}")
    sys.exit(1)

df_merged = df_data.copy()
print(f"[INFO] df_merged shape: {df_merged.shape}")

def get_specific_pair_rate(row):
    str_translator = row["TRANSLATOR"]
    str_source = row["SOURCE_LANG"]
    str_target = row["TARGET_LANG"]
    if (str_translator in dict_translator_langs and
        str_source in dict_translator_langs[str_translator] and
        str_target in dict_translator_langs[str_translator][str_source]):
        return dict_translator_langs[str_translator][str_source][str_target]
    return None

print("[INFO] Applying latest hourly rate lookup to all rows...")
df_merged["TRANSLATOR_HOURLY_RATE_LATEST"] = df_merged.apply(get_specific_pair_rate, axis=1)

n_unmatched = df_merged["TRANSLATOR_HOURLY_RATE_LATEST"].isna().sum()
if n_unmatched > 0:
    print(f"  [WARNING] {n_unmatched} row(s) had no matching rate in translators dict (TRANSLATOR_HOURLY_RATE_LATEST = None)")

df_merged["DISCREPANCY_HOURLY_RATE"] = df_merged["HOURLY_RATE"] - df_merged["TRANSLATOR_HOURLY_RATE_LATEST"]

discrepancies = df_merged[
    df_merged["DISCREPANCY_HOURLY_RATE"].notnull() & (df_merged["DISCREPANCY_HOURLY_RATE"] != 0)
]
print(f"\n[RESULT] Rate discrepancies found: {len(discrepancies)}")
if len(discrepancies) > 0:
    print(f"  Sample discrepancies:\n")
    print(discrepancies[["TRANSLATOR", "SOURCE_LANG", "TARGET_LANG", "HOURLY_RATE", "TRANSLATOR_HOURLY_RATE_LATEST", "DISCREPANCY_HOURLY_RATE"]].head().to_string())
    print()

print("[OK] Translator cost pairs merge completed")


# # Save JSON files
print("\n" + "=" * 60)
print("SAVING JSON DICTIONARIES")
print("=" * 60)

json_outputs = {
    "translatorLanguages.json": dict_translator_langs,
    "sourceLanguages.json": dict_source_langs,
    "targetLanguages.json": dict_target_langs,
}

for filename, data in json_outputs.items():
    path = os.path.join(path_interim, filename)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"  [SAVED] {path}")
    except Exception as e:
        print(f"  [ERROR] Failed to save {filename}: {e}")
        sys.exit(1)

print("\n" + "=" * 60)
print("ALL DONE")
print("=" * 60)
