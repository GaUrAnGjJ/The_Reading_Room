# from dotenv import load_dotenv
# load_dotenv()  # Load GROQ_API_KEY from .env before anything else

# from fastapi import FastAPI, HTTPException
# from fastapi.staticfiles import StaticFiles
# from pydantic import BaseModel
# import sqlite3

# app = FastAPI(title="The Reading Room API")

# from fastapi.middleware.cors import CORSMiddleware

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Allows all origins
#     allow_credentials=True,
#     allow_methods=["*"],  # Allows all methods
#     allow_headers=["*"],  # Allows all headers
# )

# DB_PATH = "storage/library.db"

# def get_db_connection():
#     conn = sqlite3.connect(DB_PATH)
#     conn.row_factory = sqlite3.Row 
#     return conn

# @app.get("/api/health")
# def health_check():
#     return {"status": "API is running"}

# ## Find Book By ISBN

# @app.get("/books/{isbn}")
# def get_book_by_isbn(isbn: str):
#     conn = get_db_connection()
#     cursor = conn.cursor()

#     cursor.execute(
#         "SELECT * FROM books WHERE isbn = ?",
#         (isbn,)
#     )
#     book = cursor.fetchone()
#     conn.close()

#     if not book:
#         raise HTTPException(status_code=404, detail="Book not found")

#     return dict(book)

# ## Search by author or book name

# @app.get("/search")
# def search_books(q: str):
#     conn = get_db_connection()
#     cursor = conn.cursor()

#     cursor.execute("""
#         SELECT *
#         FROM books
#         WHERE title LIKE ? OR author LIKE ?
#         LIMIT 20
#     """, (f"%{q}%", f"%{q}%"))

#     results = cursor.fetchall()
#     conn.close()

#     return [dict(r) for r in results]

# @app.get("/random-books")
# def get_random_books():
#     """Fetch 10 random books from the database."""
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     try:
#         cursor.execute("SELECT * FROM books ORDER BY RANDOM() LIMIT 10")
#         results = cursor.fetchall()
#         return [dict(r) for r in results]
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#     finally:
#         conn.close()

# ## Recommendation System

# import sys
# from pathlib import Path
# ROOT = Path(__file__).resolve().parent.parent
# sys.path.append(str(ROOT))
# from recommender.recommender import BookRecommender

# recommender_engine = BookRecommender()

# @app.on_event("startup")
# def load_recommender():
#     """Load recommender model on startup to reduce latency for first request."""
#     # We wrap in try-except in case embeddings aren't built yet
#     try:
#         recommender_engine.load()
#         print("Recommender model loaded successfully.")
#     except Exception as e:
#         print(f"Warning: Could not load recommender model: {e}")

# @app.get("/recommend")
# def recommend_books(query: str):
#     """Get book recommendations based on semantic search."""
#     try:
#         results = recommender_engine.recommend(query)
#         return results
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Recommendation failed: {str(e)}")

# ## RAG Chat Endpoint

# from chat.chatbot import chat as rag_chat

# class ChatMessage(BaseModel):
#     role: str    # "user" or "assistant"
#     content: str

# class ChatRequest(BaseModel):
#     message: str
#     history: list[ChatMessage] = []

# @app.post("/chat")
# def chat_endpoint(request: ChatRequest):
#     """RAG chat endpoint.

#     Accepts a user message and prior conversation history.
#     Returns a grounded LLM reply, the retrieved books, and the search query used.

#     Returns:
#         200: {reply, books, search_query}
#         503: Recommender model not loaded yet
#         502: Groq API call failed
#     """
#     if not recommender_engine.loaded:
#         raise HTTPException(
#             status_code=503,
#             detail="Recommender model is not loaded yet. Try again in a moment."
#         )

#     # Convert Pydantic models to plain dicts for chatbot.py
#     history_dicts = [{"role": m.role, "content": m.content} for m in request.history]

#     try:
#         result = rag_chat(
#             message=request.message,
#             history=history_dicts,
#             recommender=recommender_engine,
#         )
#     except EnvironmentError as e:
#         # GROQ_API_KEY not set
#         raise HTTPException(status_code=503, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=502, detail=f"Groq API error: {str(e)}")

#     return result


# # Serve static files from the frontend directory
# # This must be the LAST route so API routes take precedence
# app.mount("/", StaticFiles(directory="frontend", html=True), name="static")



### New Code 

from dotenv import load_dotenv
load_dotenv()  # Load GROQ_API_KEY from .env before anything else

import os
import time
import logging

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sqlite3

logger = logging.getLogger(__name__)

app = FastAPI(title="Vertex Valet API")

# ── Eval platform integration ────────────────────────────────────────────────
# Uses eval_sdk (installed via:
#   pip install git+https://github.com/GaUrAnGjJ/AI-Evaluation-and-Obsevation.git#subdirectory=sdk)
# All three env vars go in .env — logging is skipped (not blocked) if unset,
# so the chatbot works fine even before this is configured.
EVAL_BASE_URL = os.getenv("EVAL_BASE_URL", "http://localhost:8000")
EVAL_PROJECT_ID = os.getenv("EVAL_PROJECT_ID")
EVAL_API_KEY = os.getenv("EVAL_API_KEY")

eval_client = None
if EVAL_PROJECT_ID and EVAL_API_KEY:
    try:
        from eval_sdk import EvalClient
        eval_client = EvalClient(
            base_url=EVAL_BASE_URL,
            project_id=EVAL_PROJECT_ID,
            api_key=EVAL_API_KEY,
        )
        print(f"[eval_sdk] Trace logging ENABLED (project={EVAL_PROJECT_ID})")
    except Exception as e:
        print(f"[eval_sdk] Failed to initialize, trace logging DISABLED: {e}")
else:
    print("[eval_sdk] EVAL_PROJECT_ID/EVAL_API_KEY not set — trace logging DISABLED")

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

## RAG Chat Endpoint

from chat.chatbot import chat as rag_chat

class ChatMessage(BaseModel):
    role: str    # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []

@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    """RAG chat endpoint.

    Accepts a user message and prior conversation history.
    Returns a grounded LLM reply, the retrieved books, and the search query used.

    Returns:
        200: {reply, books, search_query}
        503: Recommender model not loaded yet
        502: Groq API call failed
    """
    if not recommender_engine.loaded:
        raise HTTPException(
            status_code=503,
            detail="Recommender model is not loaded yet. Try again in a moment."
        )

    # Convert Pydantic models to plain dicts for chatbot.py
    history_dicts = [{"role": m.role, "content": m.content} for m in request.history]

    start = time.perf_counter()
    try:
        result = rag_chat(
            message=request.message,
            history=history_dicts,
            recommender=recommender_engine,
        )
    except EnvironmentError as e:
        # GROQ_API_KEY not set
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Groq API error: {str(e)}")

    latency_ms = (time.perf_counter() - start) * 1000

    if eval_client:
        eval_client.log_rag(
            query=request.message,
            response=result["reply"],
            retrieved_context=[b.get("description", "") for b in result["books"]],
            model="llama-3.3-70b-versatile",
            latency_ms=latency_ms,
            prompt_template="STRICT RULES: only recommend from BOOK CATALOG...",
            trace_metadata={"search_query": result["search_query"]},
        )

    return result


# Serve static files from the frontend directory
# This must be the LAST route so API routes take precedence
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")