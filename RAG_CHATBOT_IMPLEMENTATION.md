# Reading Room — RAG Chatbot Implementation Plan

Status legend: `[x]` done · `[ ]` to do

---

## Phase 0 — Prerequisites (already in place)

- [x] `recommender/recommender.py` — semantic + author-boosted retrieval over `embeddings.pkl`
- [x] `storage/library.db` — SQLite `books` table (title, author, description, year, poster_url, book_url)
- [x] `API/main.py` — FastAPI app with `/recommend`, `/search`, `/books/{isbn}`
- [x] Groq account + API key (reused from Vertex Valet's LLM generation layer)

---

## Phase 1 — Backend RAG module

**Goal:** retrieval-grounded chat, no hallucinated titles.

- [x] Create `chat/chatbot.py`
  - [x] `rewrite_query(history, message)` — resolves follow-ups ("something shorter than that") into a standalone search query. Skips the LLM call on turn 1.
  - [x] `build_context(books)` — formats retrieved metadata into a numbered block, truncates long descriptions (~400 chars)
  - [x] `generate_response(message, history, books)` — Groq call (`llama-3.3-70b-versatile`), system prompt hard-constrains recommendations to titles present in context
  - [x] `chat(message, history, recommender)` — orchestrates rewrite → retrieve → generate
- [x] Add `groq` to `requirements.txt`

**Files touched:** `chat/chatbot.py` (new)

---

## Phase 2 — API endpoint

- [x] Add `ChatMessage` / `ChatRequest` pydantic models to `API/main.py`
- [x] Add `POST /chat` — reuses the already-loaded `recommender_engine` singleton (no duplicate model loading)
  - Returns `{reply, books, search_query}`
  - `503` if recommender isn't loaded yet, `502` if Groq fails

**Files touched:** `API/main.py`

---

## Phase 3 — Environment setup

- [ ] Create `.env` (gitignored) with:
  ```
  GROQ_API_KEY=your_key_here
  ```
- [ ] Add `python-dotenv` to `requirements.txt` and load it at the top of `API/main.py`:
  ```python
  from dotenv import load_dotenv
  load_dotenv()
  ```
- [ ] Confirm `.env` is in `.gitignore` (check — repo may not have one yet)
- [ ] For deployment (Docker/HF Spaces): set `GROQ_API_KEY` as a secret/env var, not baked into the image

---

## Phase 4 — Local testing

- [ ] Start the server: `python pipeline.py --api`
- [ ] Smoke test with curl:
  ```bash
  curl -X POST http://localhost:8000/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "something like a sad robot story", "history": []}'
  ```
- [ ] Test multi-turn follow-up (pass the prior turn back in `history`):
  ```bash
  curl -X POST http://localhost:8000/chat \
    -H "Content-Type: application/json" \
    -d '{
      "message": "something shorter than that",
      "history": [
        {"role": "user", "content": "something like a sad robot story"},
        {"role": "assistant", "content": "<previous reply>"}
      ]
    }'
  ```
- [ ] Test an out-of-catalog query (e.g. a genre with zero matches) — verify the model says so instead of inventing a title
- [ ] Spot-check 10–15 queries manually: does every book named in the reply actually appear in `books` from the response?

---

## Phase 5 — Groundedness evaluation (reuse Vertex Valet's LLM-as-judge harness)

- [ ] Port the judge prompt/harness from Vertex Valet's phase-4 eval work into `chat/eval.py`
- [ ] Judge checks, per response:
  - Every book title mentioned in `reply` exists in the `books` list returned
  - The reasoning given for each recommendation is consistent with that book's actual description (not contradicted or fabricated)
- [ ] Run against a fixed test set of ~30–50 queries, log a groundedness % and consistency %
- [ ] Decide threshold: log-only vs. block-and-retry on failure
- [ ] **Do this after Phase 4 manual testing**, not before — no point automating evaluation of a pipeline you haven't sanity-checked by hand yet

---

## Phase 6 — Frontend chat UI

- [ ] Decide placement: modal, side panel, or dedicated `/chat` page (your call — affects `index.html` structure)
- [ ] Extend `frontend/index.html` with a chat container + input box
- [ ] Extend `frontend/app.js`:
  - [ ] Maintain `history` array client-side (role/content pairs)
  - [ ] POST to `/chat` on submit, append user + assistant turns to the UI
  - [ ] Render `books` from the response using your existing book-card component (reuse, don't rebuild)
  - [ ] Loading state while waiting on the Groq round-trip
  - [ ] Error state for `502`/`503` responses
- [ ] Extend `frontend/styles.css` for the chat bubbles/panel

---

## Phase 7 — Hardening (optional, do if you see real issues in Phase 4/5)

- [ ] Retry logic around Groq calls for daily quota limits (same pattern as Vertex Valet)
- [ ] Rate-limit `/chat` per session/IP if deploying publicly
- [ ] Trim `history` sent to the client to avoid unbounded payload growth on long conversations
- [ ] Cache `rewrite_query` output for identical `(history, message)` pairs if you see repeated latency in testing

---

## Phase 8 — Deployment

- [ ] Update `Dockerfile` / `docker-compose.yml` if new env vars or dependencies need to be declared
- [ ] Set `GROQ_API_KEY` as a secret on your hosting platform (Railway/HF Spaces)
- [ ] Update `README.md`: new `/chat` endpoint, setup step for `GROQ_API_KEY`
- [ ] Re-verify cold-start behavior — recommender model load + first Groq call latency on a fresh container

---

## Open decisions (need your call, not mine)

1. **Chat placement in UI** — modal vs. panel vs. separate page?
2. **Groundedness enforcement** — log-only, or block a response and retry if the judge flags it?
3. **History storage** — client-side only (simplest, resets on refresh) or server-side session (survives refresh, more infra)?
