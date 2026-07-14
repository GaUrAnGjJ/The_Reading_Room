# Book Recommender System

This module provides semantic search capabilities for the Book Finder application.
It uses `sentence-transformers` to generate dense vector embeddings for book descriptions and titles, enabling natural language search (e.g., "sad story about a robot").

## Setup

1. **Install Dependencies**:
   Ensure you have the required packages installed:
   ```bash
   pip install -r ../requirements.txt
   ```

2. **Generate Embeddings**:
   Before using the recommender, you must generate the embeddings file. This process reads books from `storage/library.db` and saves vectors to `recommender/embeddings.pkl`.
   ```bash
   python recommender/build_embeddings.py
   ```
   *Note: The first run downloads the model (~90MB). Processing 28k books may take 5-10 minutes depending on your CPU.*

## Usage

### Standalone Script
You can test the recommender in the terminal:
```bash
python recommender/recommender.py
```
(You can edit the query in the `__main__` block of `recommender.py`)

### API
The recommender is integrated into the main FastAPI application.
Endpoint: `GET /recommend?query=...`

Example:
```bash
curl "http://localhost:8000/recommend?query=space%20adventure"
```

## How it works
1. **Model**: Uses `all-MiniLM-L6-v2` (a lightweight, high-performance model).
2. **Text**: Combines `Title` and `Description`.
3. **Similarity**: Cosine similarity is calculated between the query vector and all book vectors.
