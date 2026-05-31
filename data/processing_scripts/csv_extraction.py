# # Create csv files from the excel
import os
import re
import sys
import json
import unicodedata
import pandas as pd


print("=" * 60)
print("STARTING EXCEL TO CSV CONVERSION")
print("=" * 60)

# Get paths
path_base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # Base path of the repository
path_raw = os.path.join(path_base, "data", "raw") # Path to the raw folder
path_interim = os.path.join(path_base, "data", "interim")
input_file = "data.xlsx" # Input file name

print(f"[PATHS] Base      : {path_base}")
print(f"[PATHS] Raw       : {path_raw}")
print(f"[PATHS] Interim   : {path_interim}")
print(f"[PATHS] Input file: {input_file}")

# Check that required directories exist
if not os.path.exists(path_raw):
    print(f"[ERROR] Raw data directory not found: {path_raw}")
    sys.exit(1)

if not os.path.exists(path_interim):
    print(f"[WARNING] Interim directory not found, creating it: {path_interim}")
    try:
        os.makedirs(path_interim)
        print(f"[OK] Created interim directory: {path_interim}")
    except OSError as e:
        print(f"[ERROR] Could not create interim directory: {e}")
        sys.exit(1)

# Check if input file exists
input_path = os.path.join(path_raw, input_file)
if not os.path.exists(input_path):
    print(f"[ERROR] Input file not found: {input_path}")
    sys.exit(1)

print(f"\n[OK] Input file found: {input_path}")

# Load all sheets from Excel file
print(f"\n[INFO] Loading Excel file: {input_file} ...")
try:
    excel_data = pd.read_excel(input_path, sheet_name=None)
    print(f"[OK] Loaded {len(excel_data)} sheet(s): {list(excel_data.keys())}")
except Exception as e:
    print(f"[ERROR] Failed to read Excel file: {e}")
    sys.exit(1)


def clean_sheet_name(sheet_name):
    normalized = unicodedata.normalize("NFKD", sheet_name) # Remove accents
    normalized = "".join([c for c in normalized if not unicodedata.combining(c)])
    clean_name = re.sub(r"[^a-zA-Z0-9]", "", normalized) # Remove special characters
    if clean_name:
        clean_name = clean_name[0].lower() + clean_name[1:] # Make just the first letter lowercase
    return clean_name

# Clean sheet names
original_names = list(excel_data.keys())
excel_data = {clean_sheet_name(sheet_name): df for sheet_name, df in excel_data.items()}
clean_names = list(excel_data.keys())
print(f"\n[INFO] Sheet name mapping:")
for orig, clean in zip(original_names, clean_names):
    marker = " (renamed)" if orig != clean else ""
    print(f"  '{orig}' -> '{clean}'{marker}")


# # Process and save each sheet to CSV
print("\n" + "=" * 60)
print("PROCESSING SHEETS -> CSV")
print("=" * 60)

for sheet_name, df in excel_data.items():
    print(f"\n[SHEET] '{sheet_name}' | {len(df)} rows x {len(df.columns)} cols")
    print(f"  Columns: {list(df.columns)}")

    if sheet_name == "data":
        if "HOURS" in df.columns:
            df.rename(columns={"HOURS": "FORECAST"}, inplace=True)
            print(f"  [RENAMED] 'HOURS' -> 'FORECAST'")
        else:
            print(f"  [SKIP] Column 'HOURS' not found, no rename needed")

        if "START" in df.columns:
            n_before = df["START"].notna().sum()
            df["START"] = pd.to_datetime(df["START"], errors="coerce")
            n_after = df["START"].notna().sum()
            n_coerced = n_before - n_after
            if n_coerced > 0:
                print(f"  [WARNING] {n_coerced} value(s) in 'START' could not be parsed as datetime and were set to NaT")
            df.sort_values(by="START", ascending=False, inplace=True)
            print(f"  [SORTED] By 'START' descending | {n_after} valid dates")
        else:
            print(f"  [WARNING] Column 'START' not found in sheet 'data', skipping sort")

    elif sheet_name == "clients":
        if "CLIENT_NAME" in df.columns:
            df.sort_values(by="CLIENT_NAME", ascending=True, inplace=True)
            print(f"  [SORTED] By 'CLIENT_NAME' ascending")
        else:
            print(f"  [WARNING] Column 'CLIENT_NAME' not found in sheet 'clients', skipping sort")

    elif sheet_name == "schedules":
        if "NAME" in df.columns:
            df.sort_values(by="NAME", ascending=True, inplace=True)
            print(f"  [SORTED] By 'NAME' ascending")
        else:
            print(f"  [WARNING] Column 'NAME' not found in sheet 'schedules', skipping sort")

    elif sheet_name == "translatorsCostPairs":
        if "TRANSLATOR" in df.columns:
            df.sort_values(by="TRANSLATOR", ascending=True, inplace=True)
            print(f"  [SORTED] By 'TRANSLATOR' ascending")
        else:
            print(f"  [WARNING] Column 'TRANSLATOR' not found in sheet 'translatorsCostPairs', skipping sort")

    # Save to CSV
    output_file = os.path.join(path_interim, f"{sheet_name}.csv")
    try:
        df.to_csv(output_file, index=False, sep=",")
        print(f"  [SAVED] {output_file}")
    except Exception as e:
        print(f"  [ERROR] Failed to save '{sheet_name}' to CSV: {e}")
        sys.exit(1)
        
print("\n" + "=" * 60)
print("ALL DONE")
print("=" * 60)
