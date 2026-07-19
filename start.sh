#!/bin/sh
echo "=== The Reading Room Startup ==="
echo "Working directory: $(pwd)"

PORT="${PORT:-8000}"
EMBEDDINGS_PATH="recommender/embeddings.pkl"
DB_PATH="storage/library.db"

<<<<<<< Updated upstream
# ── Download large files from GitHub Releases if not present ──────────────────
# These files are too large to commit to GitHub (>50 MB).
# They are hosted as assets on the GitHub Release tagged v1.0.

RELEASE_BASE="https://github.com/GaUrAnGjJ/The_Reading_Room/releases/download/v1.0"

if [ ! -f "$EMBEDDINGS_PATH" ]; then
    echo "Downloading embeddings.pkl (~80 MB)..."
    mkdir -p recommender
    wget -q -O "$EMBEDDINGS_PATH" "$RELEASE_BASE/embeddings.pkl" \
        || { echo "ERROR: Failed to download embeddings.pkl. Check the release URL."; exit 1; }
    echo "embeddings.pkl downloaded successfully."
fi

if [ ! -f "$DB_PATH" ]; then
    echo "Downloading library.db (~45 MB)..."
    mkdir -p storage
    wget -q -O "$DB_PATH" "$RELEASE_BASE/library.db" \
        || { echo "ERROR: Failed to download library.db. Check the release URL."; exit 1; }
    echo "library.db downloaded successfully."
=======
# Minimum valid file sizes (anything smaller is a Git LFS pointer or empty)
MIN_DB_SIZE=1000000        # 1 MB  — real DB is ~45 MB
MIN_EMBEDDINGS_SIZE=1000000 # 1 MB  — real pkl is ~80 MB

RELEASE_BASE="https://github.com/GaUrAnGjJ/The_Reading_Room/releases/download/v1.0"

# ── library.db ─────────────────────────────────────────────────────────────────
DB_SIZE=0
if [ -f "$DB_PATH" ]; then
    DB_SIZE=$(wc -c < "$DB_PATH" 2>/dev/null || echo 0)
fi

if [ "$DB_SIZE" -lt "$MIN_DB_SIZE" ]; then
    echo "Downloading library.db (~45 MB)..."
    mkdir -p storage
    wget -q -O "$DB_PATH" "$RELEASE_BASE/library.db" \
        || { echo "ERROR: Failed to download library.db. Check the GitHub Release."; exit 1; }
    echo "library.db downloaded ($(wc -c < "$DB_PATH") bytes)."
else
    echo "library.db already present (${DB_SIZE} bytes)."
fi

# ── embeddings.pkl ─────────────────────────────────────────────────────────────
EMB_SIZE=0
if [ -f "$EMBEDDINGS_PATH" ]; then
    EMB_SIZE=$(wc -c < "$EMBEDDINGS_PATH" 2>/dev/null || echo 0)
fi

if [ "$EMB_SIZE" -lt "$MIN_EMBEDDINGS_SIZE" ]; then
    echo "Downloading embeddings.pkl (~80 MB)..."
    mkdir -p recommender
    wget -q -O "$EMBEDDINGS_PATH" "$RELEASE_BASE/embeddings.pkl" \
        || { echo "ERROR: Failed to download embeddings.pkl. Check the GitHub Release."; exit 1; }
    echo "embeddings.pkl downloaded ($(wc -c < "$EMBEDDINGS_PATH") bytes)."
else
    echo "embeddings.pkl already present (${EMB_SIZE} bytes)."
>>>>>>> Stashed changes
fi

echo "Starting Uvicorn on port $PORT..."
exec uvicorn API.main:app --host 0.0.0.0 --port $PORT
