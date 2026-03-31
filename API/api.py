from fastapi import FastAPI, Query
import sqlite3

app = FastAPI()

def get_db_connection():
    conn = sqlite3.connect(".data/database.db")
    conn.row_factory = sqlite3.Row  # returns dict-like rows
    return conn

@app.get("/")
def read_root():
    return {"Hello": "World!!"}

@app.get("/translators")
def get_translators(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
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
