"""RAG chatbot module for The Reading Room.

Orchestration pipeline:
    user message + history
        → rewrite_query()       : resolve follow-ups into standalone query
        → recommender.recommend(): semantic + keyword retrieval
        → build_context()       : format books into LLM-readable text block
        → generate_response()   : Groq LLM call with grounding constraints
        → {reply, books, search_query}
"""

import os
import logging
from groq import Groq

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_DESC_CHARS = 400       # Truncate long descriptions in context block
MAX_HISTORY_TURNS = 6      # Keep last N role/content pairs to stay within token limit
TOP_K_BOOKS = 6            # Number of books to retrieve per query


# ── 1. Context Builder ─────────────────────────────────────────────────────────

def build_context(books: list[dict]) -> str:
    """Format a list of retrieved book dicts into a numbered text block.

    Each entry includes title, author, year, and a truncated description.
    This block is injected verbatim into the LLM system prompt.

    Args:
        books: List of book metadata dicts from the recommender.

    Returns:
        A formatted multi-line string, or a fallback message if empty.
    """
    if not books:
        return "No books were found matching the query."

    lines = []
    for i, book in enumerate(books, start=1):
        title = book.get("title", "Unknown Title")
        author = book.get("author", "Unknown Author")
        year = book.get("year", "")
        description = book.get("description") or ""

        # Truncate long descriptions to keep context window manageable
        if len(description) > MAX_DESC_CHARS:
            description = description[:MAX_DESC_CHARS].rsplit(" ", 1)[0] + "..."

        year_str = f" ({year})" if year else ""
        lines.append(
            f"[{i}] \"{title}\" by {author}{year_str}\n"
            f"    Description: {description}"
        )

    return "\n\n".join(lines)


# ── 2. Query Rewriter ──────────────────────────────────────────────────────────

def rewrite_query(history: list[dict], message: str) -> str:
    """Resolve a follow-up message into a self-contained search query.

    On the first turn (empty history), the message is returned as-is.
    On subsequent turns, an LLM call resolves pronouns and references
    (e.g. "something shorter than that" → "short sci-fi robot story").

    Args:
        history: List of prior {"role": ..., "content": ...} dicts.
        message: The current user message.

    Returns:
        A standalone search query string safe to pass to the retriever.
    """
    # Turn 1 — no prior context, skip LLM call
    if not history:
        return message

    client = Groq(api_key=_get_api_key())

    system_prompt = (
        "You are a search query rewriter for a book recommendation system. "
        "Given the conversation history and a new user message, rewrite the message "
        "into a single, self-contained search query. Output ONLY the query. No explanation."
    )

    trimmed_history = _trim(history)

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(trimmed_history)
    messages.append({"role": "user", "content": f"Rewrite as a standalone query: {message}"})

    response = client.chat.completions.create(
        model=GROQ_MODEL, messages=messages, temperature=0.2, max_tokens=80,
    )
    rewritten = response.choices[0].message.content.strip()
    logger.info("Query rewritten: '%s' -> '%s'", message, rewritten)
    return rewritten


# ── 3. Response Generator ──────────────────────────────────────────────────────

def generate_response(message: str, history: list[dict], books: list[dict]) -> str:
    """Call the Groq LLM to generate a grounded book recommendation response.

    The system prompt hard-constrains the model to only recommend titles
    that appear in the retrieved context block. If no match exists, the
    model must say so rather than invent titles.

    Args:
        message: The current user query (may be rewritten).
        history: Prior conversation turns for multi-turn context.
        books: Retrieved books list — used to build the grounding context.

    Returns:
        The assistant's natural language reply as a string.
    """
    context_block = build_context(books)
    client = Groq(api_key=_get_api_key())

    system_prompt = (
        "You are a knowledgeable book recommender assistant for The Reading Room. "
        "Recommend books from the BOOK CATALOG below only.\n\n"
        "STRICT RULES:\n"
        "1. You may ONLY recommend books that appear in the BOOK CATALOG below.\n"
        "2. Never invent, hallucinate, or suggest titles not present in the catalog.\n"
        "3. For each recommendation, briefly explain WHY it fits the user's request "
        "   using only information from the catalog description — do not add invented plot details.\n"
        "4. If none of the catalog books match the user's request, say so honestly.\n"
        "5. Be conversational, warm, and concise. Aim for 3–5 sentences per recommendation.\n\n"
        f"BOOK CATALOG:\n{context_block}"
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(_trim(history))
    messages.append({"role": "user", "content": message})

    response = client.chat.completions.create(
        model=GROQ_MODEL, messages=messages, temperature=0.5, max_tokens=600,
    )
    return response.choices[0].message.content.strip()


# ── 4. Main Orchestrator ───────────────────────────────────────────────────────

def chat(message: str, history: list[dict], recommender) -> dict:
    """Orchestrate the full RAG pipeline for a single chat turn.

    Pipeline:
        rewrite_query → recommend → build_context → generate_response

    Args:
        message:     Raw user message from the frontend.
        history:     List of prior {"role": ..., "content": ...} dicts.
        recommender: A loaded BookRecommender instance (reused from API).

    Returns:
        dict with keys:
            reply        (str)  — LLM-generated natural language response
            books        (list) — Retrieved book metadata dicts
            search_query (str)  — The (possibly rewritten) query used for retrieval
    """
    # Step 1 — Resolve follow-ups into a standalone query
    search_query = rewrite_query(history, message)

    books = recommender.recommend(search_query, top_k=5)
    reply = generate_response(message, history, books)

    return {
        "reply": reply,
        "books": books,
        "search_query": search_query,
    }


# ── Internal helpers ───────────────────────────────────────────────────────────

def _trim(history: list[dict]) -> list[dict]:
    """Return the last MAX_HISTORY_TURNS entries to stay within token limits."""
    return history[-MAX_HISTORY_TURNS:]


def _get_api_key() -> str:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise EnvironmentError(
            "GROQ_API_KEY is not set. Add it to .env and restart the server."
        )
    return key
