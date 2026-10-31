"""
The Reading Room — Streamlit Application with Full Visual Styling and Book Covers.

Reuses the existing backend modules directly (in-process, no HTTP layer):
    - recommender.recommender.BookRecommender  → semantic search / recommend
    - storage/library.db (sqlite3)              → keyword search + random shelf
    - chat.chatbot.chat                          → RAG chatbot (Groq)
"""

import html
import os
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

# ── Path setup so local package imports (recommender, chat) resolve ──────────
ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "storage" / "library.db"

from recommender.recommender import BookRecommender
from chat.chatbot import chat as rag_chat

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="The Reading Room — Intelligent Book Discovery",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Inject Fonts and Custom Styling matching the original design ────────────
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Crimson+Text:ital,wght@0,400;0,600;0,700;1,400&family=Playfair+Display:ital,wght@0,500;0,700;0,900;1,400&display=swap');

:root {
    --bg-color: #fdfbf7;
    --paper-color: #f4ecd8;
    --card-bg: #ffffff;
    --text-primary: #2c1810;
    --text-secondary: #5d4037;
    --accent: #8b4513;
    --accent-light: #d7ccc8;
    --gold: #d4af37;
    --font-heading: 'Playfair Display', Georgia, serif;
    --font-body: 'Crimson Text', Garamond, Georgia, serif;
}

/* App Background & Typography */
.stApp {
    background-color: var(--bg-color);
    color: var(--text-primary);
    font-family: var(--font-body);
}

/* Header Banner */
.reading-header {
    text-align: center;
    padding: 2.5rem 1rem 1.8rem;
    margin-bottom: 2rem;
    border-bottom: 2px solid var(--accent-light);
    position: relative;
}

.reading-header::after {
    content: "❧";
    font-size: 1.8rem;
    color: var(--accent);
    position: absolute;
    bottom: -1.3rem;
    left: 50%;
    transform: translateX(-50%);
    background: var(--bg-color);
    padding: 0 1rem;
}

.reading-title {
    font-family: var(--font-heading);
    font-size: 3.2rem;
    font-weight: 900;
    color: var(--text-primary);
    letter-spacing: -0.5px;
    margin-bottom: 0.3rem;
}

.reading-subtitle {
    font-family: var(--font-body);
    font-style: italic;
    font-size: 1.25rem;
    color: var(--text-secondary);
}

/* Tab Styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 1.5rem;
    justify-content: center;
    border-bottom: 2px solid var(--accent-light);
    margin-bottom: 2rem;
}

.stTabs [data-baseweb="tab"] {
    font-family: var(--font-heading);
    font-weight: 700;
    font-size: 1.05rem;
    color: var(--text-secondary);
    padding: 0.75rem 1.5rem;
    border: none !important;
}

.stTabs [aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom: 3px solid var(--accent) !important;
}

/* Book Card Styling */
.book-card {
    background: var(--card-bg);
    border: 1px solid #e2d7cb;
    border-radius: 4px;
    margin-bottom: 1.8rem;
    display: flex;
    flex-direction: column;
    box-shadow: 2px 2px 0 #d9cdbd, 4px 4px 0 #ece4d8;
    transition: transform 0.25s ease, box-shadow 0.25s ease;
    overflow: hidden;
    height: 100%;
    min-height: 520px;
}

.book-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 12px 22px rgba(44, 24, 16, 0.15);
}

.book-poster-container {
    width: 100%;
    height: 250px;
    background: var(--paper-color);
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    position: relative;
    border-bottom: 1px solid #e8dec8;
}

.book-poster {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 0.4s ease;
}

.book-card:hover .book-poster {
    transform: scale(1.04);
}

.book-info {
    padding: 1.25rem;
    display: flex;
    flex-direction: column;
    flex-grow: 1;
}

.book-title {
    font-family: var(--font-heading);
    font-size: 1.2rem;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1.3;
    margin-bottom: 0.35rem;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    min-height: 3.1rem;
}

.book-author {
    color: var(--accent);
    font-family: var(--font-heading);
    font-style: italic;
    font-size: 0.95rem;
    margin-bottom: 0.5rem;
    padding-bottom: 0.35rem;
    border-bottom: 1px solid var(--accent-light);
}

.book-meta {
    font-size: 0.82rem;
    color: var(--text-secondary);
    margin-bottom: 0.75rem;
}

.book-description {
    font-family: var(--font-body);
    font-size: 0.98rem;
    line-height: 1.5;
    color: var(--text-secondary);
    margin-bottom: 1rem;
    display: -webkit-box;
    -webkit-line-clamp: 4;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.card-footer {
    margin-top: auto;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 0.75rem;
    border-top: 1px dashed var(--accent-light);
}

.book-score {
    font-size: 0.85rem;
    color: var(--text-primary);
    font-weight: 700;
}

.more-details-btn {
    display: inline-block;
    background: transparent;
    border: 1px solid var(--text-primary);
    color: var(--text-primary) !important;
    font-family: var(--font-body);
    font-weight: 600;
    font-size: 0.8rem;
    padding: 0.35rem 0.75rem;
    text-decoration: none !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-radius: 2px;
    transition: all 0.2s ease;
}

.more-details-btn:hover {
    background: var(--text-primary);
    color: #fffefb !important;
}

/* Input Fields & Buttons */
.stTextInput > div > div > input {
    font-family: var(--font-body);
    font-size: 1.15rem;
    background-color: #ffffff;
    border: 1.5px solid var(--accent-light);
    border-radius: 4px;
    color: var(--text-primary);
}

.stButton > button {
    font-family: var(--font-heading);
    font-weight: 700;
    background-color: var(--accent);
    color: #ffffff !important;
    border: none;
    border-radius: 3px;
    padding: 0.5rem 1.25rem;
}

.stButton > button:hover {
    background-color: var(--text-primary);
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ── GROQ_API_KEY: prefer Streamlit secrets in deployment, fall back to env ──
try:
    if "GROQ_API_KEY" in st.secrets:
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
except FileNotFoundError:
    pass


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


def random_books(limit: int = 9) -> list[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM books ORDER BY RANDOM() LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def render_book_card(book: dict):
    title = html.escape(str(book.get("title") or "Unknown Title"))
    author = html.escape(str(book.get("author") or "Unknown Author"))
    year = book.get("year")
    
    # Format year safely
    if isinstance(year, (int, float)) and not (pd.isna(year) or np.isnan(year)) and year > 0:
        year_str = str(int(year))
    elif year:
        year_str = str(year)
    else:
        year_str = "Unknown Year"

    isbn = html.escape(str(book.get("isbn") or ""))
    desc = html.escape(str(book.get("description") or "No description available."))
    short_desc = desc[:280] + ("..." if len(desc) > 280 else "")
    score = book.get("score")
    poster_url = book.get("poster_url")
    book_url = book.get("book_url")

    # High quality fallback book cover if poster_url is empty or missing
    fallback_img = "https://images.unsplash.com/photo-1543002588-bfa74002ed7e?w=350&auto=format&fit=crop&q=80"
    img_src = poster_url.strip() if poster_url and str(poster_url).strip() else fallback_img

    score_badge = ""
    if score is not None:
        try:
            score_pct = int(float(score) * 100)
            score_badge = f'<div class="book-score">★ Match: {score_pct}%</div>'
        except Exception:
            score_badge = f'<div class="book-score">★ Score: {score:.2f}</div>'

    more_link = ""
    if book_url:
        more_link = f'<a href="{book_url}" target="_blank" rel="noopener noreferrer" class="more-details-btn">Details ↗</a>'

    card_html = f"""
    <div class="book-card">
        <div class="book-poster-container">
            <img src="{img_src}" alt="{title}" class="book-poster" onerror="this.onerror=null; this.src='{fallback_img}';">
        </div>
        <div class="book-info">
            <div class="book-title" title="{title}">{title}</div>
            <div class="book-author">by {author}</div>
            <div class="book-meta">{year_str}{f' • ISBN: {isbn}' if isbn else ''}</div>
            <div class="book-description">{short_desc}</div>
            <div class="card-footer">
                {score_badge}
                {more_link}
            </div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


# ── Header Banner ────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="reading-header">
        <div class="reading-title">📚 The Reading Room</div>
        <div class="reading-subtitle">Your intelligent literary assistant & curated library</div>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_recommend, tab_search, tab_shelves, tab_chat = st.tabs(
    ["✨ Describe your Book", "🔎 Keyword Search", "🎲 From the Shelves", "💬 Chat with Assistant"]
)

# ── Tab 1: Semantic recommend ───────────────────────────────────────────
with tab_recommend:
    st.markdown("##### Describe what you feel like reading (mood, theme, plot, or atmosphere)")
    query = st.text_input(
        "Search prompt",
        placeholder="e.g. 'a melancholy sci-fi story about conscious robots', 'love story between couple in rain'",
        label_visibility="collapsed",
        key="recommend_query",
    )
    if query:
        with st.spinner("Finding books that match your description..."):
            rec = get_recommender()
            results = rec.recommend(query, top_k=6)
        if not results:
            st.info("No books found matching your description. Try different keywords.")
        else:
            cols = st.columns(3)
            for i, book in enumerate(results):
                with cols[i % 3]:
                    render_book_card(book)

# ── Tab 2: Keyword search ───────────────────────────────────────────────
with tab_search:
    st.markdown("##### Search directly by title or author name")
    q = st.text_input(
        "Keyword prompt",
        placeholder="e.g. 'Dune', 'Isaac Asimov', 'Frank Herbert'",
        label_visibility="collapsed",
        key="keyword_query",
    )
    if q:
        results = keyword_search(q, limit=12)
        if not results:
            st.info("No books found. Try a different search.")
        else:
            cols = st.columns(3)
            for i, book in enumerate(results):
                with cols[i % 3]:
                    render_book_card(book)

# ── Tab 3: Random shelf ─────────────────────────────────────────────────
with tab_shelves:
    col_btn, _ = st.columns([2, 8])
    with col_btn:
        if st.button("🎲 Shuffle the Shelves"):
            st.session_state["shelf_books"] = random_books(limit=9)

    if "shelf_books" not in st.session_state:
        st.session_state["shelf_books"] = random_books(limit=9)

    cols = st.columns(3)
    for i, book in enumerate(st.session_state["shelf_books"]):
        with cols[i % 3]:
            render_book_card(book)

# ── Tab 4: RAG Chat ─────────────────────────────────────────────────────
with tab_chat:
    st.markdown("##### Chat directly with The Reading Room assistant")
    st.caption("Ask questions about books, recommendations, or themes strictly grounded in our catalog.")

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_msg = st.chat_input("Ask for a book recommendation or inquire about titles...")
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
                with st.spinner("Consulting the library catalog..."):
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
                            with st.expander("📚 Books referenced from catalog"):
                                exp_cols = st.columns(min(3, len(result["books"])))
                                for idx, b in enumerate(result["books"][:6]):
                                    with exp_cols[idx % 3]:
                                        render_book_card(b)
                    except Exception as e:
                        reply_text = f"Something went wrong: {e}"
                        st.error(reply_text)

        st.session_state["chat_history"].append(
            {"role": "assistant", "content": reply_text}
        )
