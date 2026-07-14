import sqlite3
import pandas as pd
import pickle
import logging
from pathlib import Path
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Paths
ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "storage" / "library.db"
EMBEDDINGS_PATH = ROOT / "recommender" / "embeddings.pkl"

def load_data():
    """Load books from SQLite database."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}")
    
    logging.info("Connecting to database...")
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT isbn, title, author, description, year, poster_url, book_url
        FROM books 
        WHERE description IS NOT NULL AND description != ''
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    logging.info(f"Loaded {len(df)} records from database.")
    return df

def create_embeddings():
    """Generate and save embeddings."""
    df = load_data()
    
    # Prepare text for embedding
    # We combine title and description for better context
    logging.info("Preprocessing text...")
    df['text_to_embed'] = df['title'].fillna('') + ": " + df['description'].fillna('')
    texts = df['text_to_embed'].tolist()
    
    # Initialize model
    model_name = 'all-MiniLM-L6-v2'
    logging.info(f"Loading SentenceTransformer model: {model_name}...")
    model = SentenceTransformer(model_name)
    
    # Generate embeddings
    logging.info("Generating embeddings (this may take a while)...")
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    
    # Save to file
    data_to_save = {
        'ids': df['isbn'].tolist(),
        'metadatas': df[['isbn', 'title', 'author', 'year', 'poster_url', 'book_url', 'description']].to_dict('records'),
        'embeddings': embeddings,
        'model_name': model_name
    }
    
    EMBEDDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(EMBEDDINGS_PATH, 'wb') as f:
        pickle.dump(data_to_save, f)
        
    logging.info(f"Embeddings saved to {EMBEDDINGS_PATH}")
    logging.info(f"Shape: {embeddings.shape}")

if __name__ == "__main__":
    create_embeddings()
