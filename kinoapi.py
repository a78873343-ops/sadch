from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from fastapi.responses import FileResponse
import sqlite3
from typing import Optional
import datetime

app = FastAPI(title="Кинохранилище API")

DB_PATH = "cinema_storage.db"

@app.get("/", response_class=HTMLResponse)
@app.get("/", response_class=HTMLResponse)
@app.get("/")
def home():
    return FileResponse("index.html")

# =======================
# MODELS
# =======================

class CabinetCreate(BaseModel):
    letter: str

class GenreCreate(BaseModel):
    name: str

class CassetteCreate(BaseModel):
    cabinet_id: int
    shelf_id: int
    genre_id: int
    title: str
    director: Optional[str] = None
    year: int
    status_id: int

class CassetteStatusUpdate(BaseModel):
    status_id: int

# =======================
# CABINETS
# =======================

@app.post("/cabinets")
def create_cabinet(cabinet: CabinetCreate):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO cabinets (letter) VALUES (?)",
                (cabinet.letter.upper(),)
            )
            cabinet_id = cursor.lastrowid

            for i in range(1, 5):
                cursor.execute(
                    "INSERT INTO shelves (cabinet_id, shelf_number) VALUES (?, ?)",
                    (cabinet_id, i)
                )

            conn.commit()
            return {"cabinet_id": cabinet_id}

    except sqlite3.IntegrityError:
        raise HTTPException(400, "Шкаф с такой буквой уже существует")

@app.get("/cabinets")
def get_cabinets():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM cabinets")
        cabinets = []

        for cab in cursor.fetchall():
            cabinet_dict = dict(cab)

            cursor.execute(
                "SELECT * FROM shelves WHERE cabinet_id = ? ORDER BY shelf_number",
                (cab["id_cabinet"],)
            )
            cabinet_dict["shelves"] = [dict(s) for s in cursor.fetchall()]
            cabinets.append(cabinet_dict)

        return {"cabinets": cabinets}

# =======================
# GENRES
# =======================

@app.post("/genres")
def create_genre(genre: GenreCreate):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO genres (name) VALUES (?)",
                (genre.name,)
            )
            conn.commit()
            return {"genre_id": cursor.lastrowid}

    except sqlite3.IntegrityError:
        raise HTTPException(400, "Жанр уже существует")

@app.get("/genres")
def get_genres():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM genres")
        return {"genres": [dict(row) for row in cursor.fetchall()]}

# =======================
# CASSETTES
# =======================

@app.post("/cassettes")
def create_cassette(cassette: CassetteCreate):
    current_year = datetime.datetime.now().year

    if cassette.year > current_year:
        raise HTTPException(400, "Год больше текущего")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM statuses WHERE id_status = ?", (cassette.status_id,))
        if not cursor.fetchone():
            raise HTTPException(404, "Статус не найден")

        cursor.execute("SELECT 1 FROM cabinets WHERE id_cabinet = ?", (cassette.cabinet_id,))
        if not cursor.fetchone():
            raise HTTPException(404, "Шкаф не найден")

        cursor.execute(
            "SELECT 1 FROM shelves WHERE id_shelf = ? AND cabinet_id = ?",
            (cassette.shelf_id, cassette.cabinet_id)
        )
        if not cursor.fetchone():
            raise HTTPException(404, "Полка не найдена")

        cursor.execute("SELECT 1 FROM genres WHERE id_genre = ?", (cassette.genre_id,))
        if not cursor.fetchone():
            raise HTTPException(404, "Жанр не найден")

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
        return {"cassette_id": cursor.lastrowid}

@app.get("/cassettes")
def get_cassettes(year: Optional[int] = None):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = """
        SELECT c.*, s.name as status_name
        FROM cassettes c
        JOIN statuses s ON c.status_id = s.id_status
        WHERE c.is_deleted = 0
        """
        params = []

        if year:
            query += " AND c.year = ?"
            params.append(year)

        cursor.execute(query, params)
        return {"cassettes": [dict(row) for row in cursor.fetchall()]}

@app.patch("/cassettes/{cassette_id}")
def update_status(cassette_id: int, update: CassetteStatusUpdate):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM statuses WHERE id_status = ?", (update.status_id,))
        if not cursor.fetchone():
            raise HTTPException(404, "Статус не найден")

        cursor.execute("""
            UPDATE cassettes
            SET status_id = ?
            WHERE cassette_id = ? AND is_deleted = 0
        """, (update.status_id, cassette_id))

        if cursor.rowcount == 0:
            raise HTTPException(404, "Кассета не найдена")

        conn.commit()
        return {"status": "обновлено"}

@app.patch("/cassettes/{cassette_id}/delete")
def logical_delete(cassette_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE cassettes SET is_deleted = 1 WHERE cassette_id = ?",
            (cassette_id,)
        )

        if cursor.rowcount == 0:
            raise HTTPException(404, "Кассета не найдена")

        conn.commit()
        return {"status": "удалено логически"}

# =======================
# INIT DB
# =======================

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cabinets (
                id_cabinet INTEGER PRIMARY KEY AUTOINCREMENT,
                letter TEXT UNIQUE NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shelves (
                id_shelf INTEGER PRIMARY KEY AUTOINCREMENT,
                cabinet_id INTEGER NOT NULL,
                shelf_number INTEGER NOT NULL CHECK (shelf_number BETWEEN 1 AND 4),
                FOREIGN KEY (cabinet_id) REFERENCES cabinets(id_cabinet),
                UNIQUE(cabinet_id, shelf_number)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS genres (
                id_genre INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS statuses (
                id_status INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cassettes (
                cassette_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cabinet_id INTEGER NOT NULL,
                shelf_id INTEGER NOT NULL,
                genre_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                director TEXT,
                year INTEGER CHECK (year >= 1888),
                status_id INTEGER NOT NULL,
                is_deleted BOOLEAN DEFAULT 0,
                FOREIGN KEY (cabinet_id) REFERENCES cabinets(id_cabinet),
                FOREIGN KEY (shelf_id) REFERENCES shelves(id_shelf),
                FOREIGN KEY (genre_id) REFERENCES genres(id_genre),
                FOREIGN KEY (status_id) REFERENCES statuses(id_status)
            )
        """)

        cursor.execute("SELECT COUNT(*) FROM statuses")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO statuses (name) VALUES ('в наличии')")
            cursor.execute("INSERT INTO statuses (name) VALUES ('нет в наличии')")

        seed_data(cursor)
        conn.commit()

def seed_data(cursor):
    cursor.execute("SELECT COUNT(*) FROM cabinets")
    if cursor.fetchone()[0] > 0:
        return

    cursor.execute("INSERT INTO cabinets (letter) VALUES ('A')")
    cabinet_id = cursor.lastrowid

    for i in range(1, 5):
        cursor.execute(
            "INSERT INTO shelves (cabinet_id, shelf_number) VALUES (?, ?)",
            (cabinet_id, i)
        )

    cursor.execute("INSERT INTO genres (name) VALUES ('Драма')")
    genre1 = cursor.lastrowid

    cursor.execute("INSERT INTO genres (name) VALUES ('Комедия')")
    genre2 = cursor.lastrowid

    cursor.execute("SELECT id_status FROM statuses WHERE name = 'в наличии'")
    status_available = cursor.fetchone()[0]

    cursor.execute("SELECT id_status FROM statuses WHERE name = 'нет в наличии'")
    status_unavailable = cursor.fetchone()[0]

    cassettes = [
        (cabinet_id, 1, genre1, "Фильм 1", "Иванов", 2001, status_available),
        (cabinet_id, 1, genre2, "Фильм 2", "Петров", 2005, status_available),
        (cabinet_id, 2, genre1, "Фильм 3", None, 2010, status_unavailable),
        (cabinet_id, 3, genre2, "Фильм 4", "Сидоров", 2015, status_available),
        (cabinet_id, 4, genre1, "Фильм 5", None, 2020, status_available),
    ]

    for cassette in cassettes:
        cursor.execute("""
            INSERT INTO cassettes
            (cabinet_id, shelf_id, genre_id, title, director, year, status_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, cassette)

@app.on_event("startup")
def startup():
    init_db()
