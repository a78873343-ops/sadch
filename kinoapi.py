from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import sqlite3
from typing import Optional
import datetime

app = FastAPI(title="Кинохранилище")

DB_PATH = "cinema_storage.db"

# =========================
# ГЛАВНАЯ СТРАНИЦА (САЙТ)
# =========================

@app.get("/", response_class=HTMLResponse)
def home():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
        SELECT c.title, c.year, s.name as status
        FROM cassettes c
        JOIN statuses s ON c.status_id = s.id_status
        WHERE c.is_deleted = 0
        """)

        cassettes = cursor.fetchall()

    rows = ""
    for cassette in cassettes:
        rows += f"""
        <tr>
            <td>{cassette['title']}</td>
            <td>{cassette['year']}</td>
            <td>{cassette['status']}</td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Кинохранилище</title>
        <style>
            body {{
                font-family: Arial;
                background: #f4f4f4;
                padding: 40px;
            }}
            h1 {{
                color: #333;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                background: white;
            }}
            th, td {{
                padding: 10px;
                border: 1px solid #ddd;
            }}
            th {{
                background: #222;
                color: white;
            }}
            a {{
                display: inline-block;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>

        <h1>🎬 Кинохранилище</h1>

        <table>
            <tr>
                <th>Название</th>
                <th>Год</th>
                <th>Статус</th>
            </tr>
            {rows}
        </table>

        <a href="/docs">Перейти к API документации</a>

    </body>
    </html>
    """

    return HTMLResponse(content=html_content)

# =========================
# API МОДЕЛЬ
# =========================

class CassetteCreate(BaseModel):
    cabinet_id: int
    shelf_id: int
    genre_id: int
    title: str
    director: Optional[str] = None
    year: int
    status_id: int

# =========================
# API ДОБАВЛЕНИЯ
# =========================

@app.post("/cassettes")
def create_cassette(cassette: CassetteCreate):
    current_year = datetime.datetime.now().year
    if cassette.year > current_year:
        raise HTTPException(400, "Год больше текущего")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO cassettes
            (cabinet_id, shelf_id, genre_id, title, director, year, status_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            cassette.cabinet_id,
            cassette.shelf_id,
            cassette.genre_id,
            cassette.title,
            cassette.director,
            cassette.year,
            cassette.status_id
        ))

        conn.commit()

    return {"message": "Кассета добавлена"}

# =========================
# INIT DB
# =========================

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS statuses (
                id_status INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cassettes (
                cassette_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cabinet_id INTEGER,
                shelf_id INTEGER,
                genre_id INTEGER,
                title TEXT NOT NULL,
                director TEXT,
                year INTEGER,
                status_id INTEGER,
                is_deleted BOOLEAN DEFAULT 0,
                FOREIGN KEY (status_id) REFERENCES statuses(id_status)
            )
        """)

        cursor.execute("SELECT COUNT(*) FROM statuses")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO statuses (name) VALUES ('в наличии')")
            cursor.execute("INSERT INTO statuses (name) VALUES ('нет в наличии')")

        cursor.execute("SELECT COUNT(*) FROM cassettes")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO cassettes 
                (cabinet_id, shelf_id, genre_id, title, director, year, status_id)
                VALUES (1,1,1,'Интерстеллар','Кристофер Нолан',2014,1)
            """)

        conn.commit()

@app.on_event("startup")
def startup():
    init_db()
