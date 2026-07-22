"""
The Reading Room — single-file Streamlit port.

Reuses the existing backend modules directly (in-process, no HTTP layer):
    - recommender.recommender.BookRecommender  → semantic search / recommend
    - storage/library.db (sqlite3)              → keyword search + random shelf
    - chat.chatbot.chat                          → RAG chatbot (Groq)

Run locally:
    streamlit run streamlit_app.py

Deploy: push to GitHub, deploy on share.streamlit.io pointing at this file,
and set GROQ_API_KEY in the app's Secrets (see README section below).
"""

import os
import sqlite3
from pathlib import Path

import streamlit as st

# ── Path setup so local package imports (recommender, chat) resolve ──────────
ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "storage" / "library.db"

from recommender.recommender import BookRecommender
from chat.chatbot import chat as rag_chat

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="The Reading Room",
    page_icon="📚",
    layout="wide",
)

# ── GROQ_API_KEY: prefer Streamlit secrets in deployment, fall back to env ──
# st.secrets raises if no secrets.toml exists at all (e.g. running locally
# with only a .env file), so this must be wrapped rather than checked with `in`.
try:
    if "GROQ_API_KEY" in st.secrets:
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
except FileNotFoundError:
    pass  # No secrets.toml — fine locally if GROQ_API_KEY is set via .env / env var


# ── Cached resources (loaded once per session/process, not per rerun) ──────
@st.cache_resource(show_spinner="Loading recommender model...")
def get_recommender() -> BookRecommender:
    rec = BookRecommender()
    rec.load()
    return rec


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def keyword_search(query: str, limit: int = 20) -> list[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM books WHERE title LIKE ? OR author LIKE ? LIMIT ?",
            (f"%{query}%", f"%{query}%", limit),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def random_books(limit: int = 10) -> list[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM books ORDER BY RANDOM() LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def render_book_card(book: dict):
    title = book.get("title", "Unknown Title")
    author = book.get("author", "Unknown Author")
    year = book.get("year", "")
    desc = book.get("description") or "No description available."
    score = book.get("score")

    with st.container(border=True):
        st.markdown(f"**{title}**")
        meta = author + (f" · {year}" if year else "")
        st.caption(meta)
        st.write(desc[:300] + ("..." if len(desc) > 300 else ""))
        if score is not None:
            st.caption(f"match score: {score:.3f}")


# ── Sidebar navigation ───────────────────────────────────────────────────
st.title("📚 The Reading Room")
st.caption("Your intelligent literary assistant")

tab_recommend, tab_search, tab_shelves, tab_chat = st.tabs(
    ["✨ Describe your Book", "🔎 Keyword Search", "🎲 From the Shelves", "💬 Chat"]
)

# ── Tab 1: Semantic recommend ───────────────────────────────────────────
with tab_recommend:
    query = st.text_input(
        "Describe the book you're looking for",
        placeholder="e.g. 'space opera with robots'",
        key="recommend_query",
    )
    if query:
        with st.spinner("Searching..."):
            rec = get_recommender()
            results = rec.recommend(query)
        if not results:
            st.info("No books found. Try a different description.")
        else:
            cols = st.columns(3)
            for i, book in enumerate(results):
                with cols[i % 3]:
                    render_book_card(book)

# ── Tab 2: Keyword search ───────────────────────────────────────────────
with tab_search:
    q = st.text_input(
        "Search by title or author",
        placeholder="e.g. 'Game of Thrones'",
        key="keyword_query",
    )
    if q:
        results = keyword_search(q)
        if not results:
            st.info("No books found. Try a different search.")
        else:
            cols = st.columns(3)
            for i, book in enumerate(results):
                with cols[i % 3]:
                    render_book_card(book)

# ── Tab 3: Random shelf ─────────────────────────────────────────────────
with tab_shelves:
    if st.button("Shuffle shelf"):
        st.session_state["shelf_books"] = random_books()
    if "shelf_books" not in st.session_state:
        st.session_state["shelf_books"] = random_books()
    cols = st.columns(3)
    for i, book in enumerate(st.session_state["shelf_books"]):
        with cols[i % 3]:
            render_book_card(book)

# ── Tab 4: RAG Chat ─────────────────────────────────────────────────────
with tab_chat:
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []  # list of {"role", "content"}

    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_msg = st.chat_input("Ask for a book recommendation...")
    if user_msg:
        st.session_state["chat_history"].append({"role": "user", "content": user_msg})
        with st.chat_message("user"):
            st.write(user_msg)

        with st.chat_message("assistant"):
            if not os.getenv("GROQ_API_KEY"):
                reply_text = (
                    "GROQ_API_KEY is not set. Add it to `.env` locally, "
                    "or to this app's Secrets when deployed."
                )
                st.error(reply_text)
            else:
                with st.spinner("Thinking..."):
                    try:
                        rec = get_recommender()
                        result = rag_chat(
                            message=user_msg,
                            history=st.session_state["chat_history"][:-1],
                            recommender=rec,
                        )
                        reply_text = result["reply"]
                        st.write(reply_text)
                        if result.get("books"):
                            with st.expander("Books referenced"):
                                for b in result["books"]:
                                    render_book_card(b)
                    except Exception as e:
                        reply_text = f"Something went wrong: {e}"
                        st.error(reply_text)

        st.session_state["chat_history"].append(
            {"role": "assistant", "content": reply_text}
        )