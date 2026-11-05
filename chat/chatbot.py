"""RAG chatbot module for Vertex Valet.

Orchestration pipeline:
    user message + history
        → guardrail check       : reject math / off-topic calculations
        → rewrite_query()       : resolve follow-ups into standalone query
        → recommender.recommend(): semantic + keyword retrieval
        → build_context()       : format books into LLM-readable text block
        → generate_response()   : Groq LLM call with strict grounding constraints
        → {reply, books, search_query}
"""

import os
import re
import logging
from groq import Groq

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
GROQ_MODEL = "openai/gpt-oss-20b"
MAX_DESC_CHARS = 400       # Truncate long descriptions in context block
MAX_HISTORY_TURNS = 6      # Keep last N role/content pairs to stay within token limit
TOP_K_BOOKS = 6            # Number of books to retrieve per query

OFF_TOPIC_REPLY = (
    "I do not contain this information. I am a specialized book assistant and "
    "can only answer questions or provide recommendations based on the books in our library catalog."
)


# ── Guardrails ─────────────────────────────────────────────────────────────────

def is_math_or_calculation(text: str) -> bool:
    """Detect if user input is a math question or numerical calculation."""
    clean = text.strip().lower()

    # If the user is specifically looking for books or reading material, do not block
    book_intent_words = [
        "book", "books", "read", "reading", "novel", "author", "recommend",
        "literature", "textbook", "story", "stories", "library"
    ]
    if any(w in clean for w in book_intent_words):
        return False

    # Explicit math / calculate / solve keywords
    if re.search(r"\b(calculate|compute|solve|math|maths|equation|arithmetic|integral|derivative|algebra)\b", clean):
        return True

    # Standard arithmetic expressions (e.g., '2 + 2', '15 * 84', '100 / 4', '50 - 20')
    has_operator = bool(re.search(r"[\+\*\/\=\^\%]|\bplus\b|\bminus\b|\btimes\b|\bdivided\b", clean))
    has_digit = bool(re.search(r"\d+", clean))
    if has_operator and (has_digit or len(clean.split()) <= 6):
        return True

    return False


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
    On subsequent turns, checks for pronouns/references or falls back to message.
    """
    clean_msg = message.strip()
    if not history or not clean_msg:
        return clean_msg

    # Check if message already looks like a complete standalone query
    # (does not contain conversational follow-up words)
    follow_up_indicators = ["it", "that", "this", "those", "them", "another", "shorter", "longer", "more like", "instead", "else"]
    words = clean_msg.lower().split()
    has_indicator = any(ind in words for ind in follow_up_indicators)

    # If the message is already specific and has no follow-up pronoun, use it directly
    if not has_indicator and len(words) >= 4:
        return clean_msg

    try:
        client = Groq(api_key=_get_api_key())
        system_prompt = (
            "You are a search query rewriter for a book recommendation system. "
            "Given the conversation history and a new user message, rewrite the message "
            "into a single, self-contained search query. Output ONLY the query. No explanation."
        )

        trimmed_history = _trim(history)
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(trimmed_history)
        messages.append({"role": "user", "content": f"Rewrite as a standalone query: {clean_msg}"})

        response = client.chat.completions.create(
            model=GROQ_MODEL, messages=messages, temperature=0.2, max_tokens=80,
        )
        rewritten = (response.choices[0].message.content or "").strip()
        
        # If the LLM returned empty or whitespace, fall back safely to original message
        if not rewritten or len(rewritten) < 3:
            logger.warning("Query rewrite returned empty string; falling back to original message.")
            return clean_msg

        logger.info("Query rewritten: '%s' -> '%s'", clean_msg, rewritten)
        return rewritten
    except Exception as e:
        logger.warning("Query rewrite failed (%s); using original message.", e)
        return clean_msg


# ── 3. Response Generator ──────────────────────────────────────────────────────

def generate_response(message: str, history: list[dict], books: list[dict]) -> str:
    """Call the Groq LLM to generate a grounded book recommendation response.

    The system prompt strictly constrains the model to only recommend titles
    that appear in the retrieved context block, and strictly refuses any
    math calculations, general knowledge questions, or queries outside the book catalog.

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
        "You are a dedicated, knowledgeable book assistant for The Reading Room.\n"
        "Your ONLY function is to assist users with book recommendations and inquiries based strictly on the BOOK CATALOG provided below.\n\n"
        "STRICT BOUNDARIES AND GROUNDING RULES:\n"
        "1. You must ONLY recommend books that appear in the provided BOOK CATALOG below. Never invent, hallucinate, or suggest external books.\n"
        "2. For each recommendation, explain why it fits using details from its catalog description.\n"
        "3. If a request involves multiple genres or themes (e.g. sci-fi and romance), recommend the closest relevant books from the catalog, clearly explaining which aspects they satisfy (for example, suggesting available science-fiction stories and romance titles from the catalog).\n"
        "4. NEVER answer math calculations (e.g. '2 + 2', equations, arithmetic), general knowledge trivia, coding, weather, or random questions outside of books and literature.\n"
        "5. If the user asks for a math calculation or any question outside of books and literature, you MUST refuse and respond with:\n"
        "   \"I do not contain this information. I am a specialized book assistant and can only answer questions or provide recommendations based on the books in our library catalog.\"\n"
        "6. Only if the retrieved catalog is completely empty or completely irrelevant to the user's book inquiry, state:\n"
        "   \"I could not find any books matching your request in our catalog.\"\n"
        "7. For polite greetings (e.g. 'hello', 'hi'), greet warmly and invite the user to ask for book recommendations.\n\n"
        f"BOOK CATALOG:\n{context_block}"
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(_trim(history))
    messages.append({"role": "user", "content": message})

    response = client.chat.completions.create(
        model=GROQ_MODEL, messages=messages, temperature=0.3, max_tokens=600,
    )
    return response.choices[0].message.content.strip()


# ── 4. Main Orchestrator ───────────────────────────────────────────────────────

def chat(message: str, history: list[dict], recommender) -> dict:
    """Orchestrate the full RAG pipeline for a single chat turn.

    Pipeline:
        check domain guardrail → rewrite_query → recommend → build_context → generate_response

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
    # Guardrail: check for math or calculation queries
    if is_math_or_calculation(message):
        logger.info("Math/calculation query blocked: '%s'", message)
        return {
            "reply": OFF_TOPIC_REPLY,
            "books": [],
            "search_query": message,
        }

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
