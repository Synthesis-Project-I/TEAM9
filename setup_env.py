"""Bootstrap a local development environment for TARS.

Run once after cloning:

    python setup_env.py

This script:
1. Creates a local ``.venv`` virtual environment (if it does not exist).
2. Installs the pinned dependencies from ``requirements.txt`` into it.
3. Seeds ``data/interim/`` from the CSVs committed under ``src/api/`` so the
   recommendation pipeline (``scripts/run_pipeline.py`` and the API's
   ``/recommendations`` endpoint) can run on a fresh clone.

Flags:
    --no-install   Skip creating the venv / installing requirements.
    --no-data      Skip seeding ``data/interim/``.

After it finishes, activate the environment:
    .venv\\Scripts\\activate     (Windows)
    source .venv/bin/activate   (macOS / Linux)
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements.txt"
SRC_API_DIR = ROOT / "src" / "api"
INTERIM_DIR = ROOT / "data" / "interim"

# Committed source CSV -> filename the data loader expects in data/interim/.
# See utils/data_loader.load_interim_data.
CSV_MAP = {
    "Data.csv": "data.csv",
    "Schedules.csv": "schedules.csv",
    "Clients.csv": "clients.csv",
    "TranslatorsCost+Pairs.csv": "translatorsCostPairs.csv",
}


def venv_python():
    """Return the path to the Python executable inside the local venv."""
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def create_venv():
    """Create the .venv virtual environment if it is not already present."""
    if VENV_DIR.exists():
        print(f">> Virtual environment already exists at {VENV_DIR}")
        return
    print(f">> Creating virtual environment at {VENV_DIR}")
    subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)])


def install_requirements():
    """Install requirements.txt into the local venv."""
    python = venv_python()
    if not python.exists():
        raise FileNotFoundError(f"venv python not found at {python}; create the venv first.")
    print(">> Upgrading pip")
    subprocess.check_call([str(python), "-m", "pip", "install", "--upgrade", "pip"])
    print(f">> Installing dependencies from {REQUIREMENTS.name}")
    subprocess.check_call([str(python), "-m", "pip", "install", "-r", str(REQUIREMENTS)])


def seed_interim_data():
    """Copy the committed src/api CSVs into data/interim/ under the expected names."""
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    for src_name, dst_name in CSV_MAP.items():
        src_path = SRC_API_DIR / src_name
        if not src_path.exists():
            print(f"!! WARNING: {src_path} not found; skipping {dst_name}")
            continue
        shutil.copyfile(src_path, INTERIM_DIR / dst_name)
        print(f">> Seeded {INTERIM_DIR / dst_name}")


def main():
    parser = argparse.ArgumentParser(description="Set up a local TARS dev environment.")
    parser.add_argument("--no-install", action="store_true", help="Skip venv creation and dependency install.")
    parser.add_argument("--no-data", action="store_true", help="Skip seeding data/interim/.")
    args = parser.parse_args()

    if not args.no_install:
        create_venv()
        install_requirements()

    if not args.no_data:
        seed_interim_data()

    print("\nDone. Activate the environment with:")
    if os.name == "nt":
        print(r"    .venv\Scripts\activate")
    else:
        print("    source .venv/bin/activate")


if __name__ == "__main__":
    main()
