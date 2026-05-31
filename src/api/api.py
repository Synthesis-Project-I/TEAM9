from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from pathlib import Path
import pickle
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline.features import prepare_pipeline_tables
from src.pipeline.filtering import TaskAssignmentCSP
from src.pipeline.ml import rank_candidates_ml
from src.pipeline.output import format_recommendations
from utils.data_loader import load_interim_data

app = FastAPI()
_pipeline_cache = None
_ml_model = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (for development only)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

def get_db_connection():
    db_path = Path(__file__).resolve().parent / "data" / "database.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # returns dict-like rows
    return conn

def get_pipeline_cache():
    global _pipeline_cache
    if _pipeline_cache is None:
        data_dict = load_interim_data()
        history_df, clients_df, translators_df = prepare_pipeline_tables(data_dict)
        _pipeline_cache = {
            "history_df": history_df,
            "clients_df": clients_df,
            "csp_solver": TaskAssignmentCSP(translators_df),
        }
    return _pipeline_cache

def get_ml_model():
    global _ml_model
    if _ml_model is None:
        model_path = ROOT / "models" / "xgboost_ranker_full.pkl"
        with open(model_path, "rb") as f:
            _ml_model = pickle.load(f)
    return _ml_model

def clean_json(value):
    if isinstance(value, dict):
        return {key: clean_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean_json(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    return value

@app.get("/")
def read_root():
    return {"Hello": "World!!"}

@app.get("/recommendations")
def get_recommendations(
    company_name: str = Query("Appcelerate"),
    task_date: str = Query("2024-10-10"),
    task_deadline: str = Query("2024-10-12"),
    task_start_time: str = Query("09:00"),
    task_end_time: str = Query("17:00"),
    task_length_hours: float = Query(3.5),
    language_pair: str = Query("English_Spanish (LA)"),
    task_type: str = Query("ProofReading"),
    top_n: int = Query(10, ge=1, le=50),
):
    cache = get_pipeline_cache()
    csp_solver = cache["csp_solver"]

    task_requirements = csp_solver.build_client_requirements(
        company_name=company_name,
        clients_df=cache["clients_df"],
        historical_df=cache["history_df"],
        task_date=task_date,
        task_deadline=task_deadline,
        task_start_time=task_start_time,
        task_end_time=task_end_time,
        task_length_hours=task_length_hours,
        language_pair=language_pair,
        task_type=task_type,
    )

    if not task_requirements:
        return {"data": [], "message": "Client not found"}

    candidates = csp_solver.get_translators_with_fallback(task_requirements)
    if candidates.empty:
        candidates = csp_solver.split_task_across_days(task_requirements)
    if candidates.empty:
        candidates = csp_solver.split_task_across_translators(task_requirements, num_translators=2)
    if candidates.empty:
        return {"data": [], "message": "No eligible translators found"}

    ranked = rank_candidates_ml(candidates, task_requirements, get_ml_model())
    recommendations = format_recommendations(ranked, task_requirements, language_pair, top_n=top_n)

    return {
        "data": clean_json(recommendations.fillna("").to_dict(orient="records")),
        "task_requirements": clean_json(task_requirements),
        "model": "xgboost_ranker_full.pkl",
    }

@app.get("/translators")
def get_translators(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=200),
    sort_by: str = Query("index"),
    asc: bool = Query(True)
):
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cur = conn.cursor()

    # 1. Get total count
    cur.execute("SELECT COUNT(*) FROM 'TranslatorsCost+Pairs'")
    total = cur.fetchone()[0]

    asc_order = "ASC" if asc else "DESC"
    print(asc_order)

    # 2. Get paginated data
    query = f'''
    SELECT *
    FROM "TranslatorsCost+Pairs"
    ORDER BY "{sort_by}" {asc_order}
    LIMIT ? OFFSET ?
    '''
    cur.execute(
        query,
        (per_page, offset)
    )
    rows = cur.fetchall()

    conn.close()

    data = [dict(row) for row in rows]

    return {
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": (total + per_page - 1) // per_page,  # ceil
        "data": data
    }

@app.get("/schedules")
def get_schedules(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=200),
    sort_by: str = Query("index"),
    asc: bool = Query(True)
):
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cur = conn.cursor()

    # 1. Get total count
    cur.execute("SELECT COUNT(*) FROM 'Schedules'")
    total = cur.fetchone()[0]

    asc_order = "ASC" if asc else "DESC"
    print(asc_order)

    # 2. Get paginated data
    query = f'''
    SELECT *
    FROM "Schedules"
    ORDER BY "{sort_by}" {asc_order}
    LIMIT ? OFFSET ?
    '''
    cur.execute(
        query,
        (per_page, offset)
    )
    rows = cur.fetchall()

    conn.close()

    data = [dict(row) for row in rows]

    return {
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": (total + per_page - 1) // per_page,  # ceil
        "data": data
    }

@app.get("/clients")
def get_clients(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=200),
    sort_by: str = Query("index"),
    asc: bool = Query(True)
):
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cur = conn.cursor()

    # 1. Get total count
    cur.execute("SELECT COUNT(*) FROM 'Clients'")
    total = cur.fetchone()[0]

    asc_order = "ASC" if asc else "DESC"
    print(asc_order)

    # 2. Get paginated data
    query = f'''
    SELECT *
    FROM "Clients"
    ORDER BY "{sort_by}" {asc_order}
    LIMIT ? OFFSET ?
    '''
    cur.execute(
        query,
        (per_page, offset)
    )
    rows = cur.fetchall()

    conn.close()

    data = [dict(row) for row in rows]

    return {
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": (total + per_page - 1) // per_page,  # ceil
        "data": data
    }

@app.get("/tasks")
def get_tasks(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=200),
    sort_by: str = Query("index"),
    asc: bool = Query(True)
):
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cur = conn.cursor()

    # 1. Get total count
    cur.execute("SELECT COUNT(*) FROM 'Data'")
    total = cur.fetchone()[0]

    asc_order = "ASC" if asc else "DESC"
    print(asc_order)

    # 2. Get paginated data
    query = f'''
    SELECT *
    FROM "Data"
    ORDER BY "{sort_by}" {asc_order}
    LIMIT ? OFFSET ?
    '''
    cur.execute(
        query,
        (per_page, offset)
    )
    rows = cur.fetchall()

    conn.close()

    data = [dict(row) for row in rows]

    return {
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": (total + per_page - 1) // per_page,  # ceil
        "data": data
    }
