from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
import sqlite3

app = FastAPI(title="Books API")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

DB_PATH = "storage/library.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row 
    return conn

@app.get("/api/health")
def health_check():
    return {"status": "API is running"}

## Find Book By ISBN

@app.get("/books/{isbn}")
def get_book_by_isbn(isbn: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM books WHERE isbn = ?",
        (isbn,)
    )
    book = cursor.fetchone()
    conn.close()

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    return dict(book)

## Search by author or book name

@app.get("/search")
def search_books(q: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM books
        WHERE title LIKE ? OR author LIKE ?
        LIMIT 20
    """, (f"%{q}%", f"%{q}%"))

    results = cursor.fetchall()
    conn.close()

    return [dict(r) for r in results]

@app.get("/random-books")
def get_random_books():
    """Fetch 10 random books from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM books ORDER BY RANDOM() LIMIT 10")
        results = cursor.fetchall()
        return [dict(r) for r in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

## Recommendation System

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))
from recommender.recommender import BookRecommender

recommender_engine = BookRecommender()

@app.on_event("startup")
def load_recommender():
    """Load recommender model on startup to reduce latency for first request."""
    # We wrap in try-except in case embeddings aren't built yet
    try:
        recommender_engine.load()
        print("Recommender model loaded successfully.")
    except Exception as e:
        print(f"Warning: Could not load recommender model: {e}")

@app.get("/recommend")
def recommend_books(query: str):
    """Get book recommendations based on semantic search."""
    try:
        results = recommender_engine.recommend(query)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {str(e)}")

# Serve static files from the frontend directory
# This must be the last route to allow other API routes to take precedence
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
