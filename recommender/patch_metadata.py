import pickle
import sqlite3
import pandas as pd
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "storage" / "library.db"
EMBEDDINGS_PATH = ROOT / "recommender" / "embeddings.pkl"

def patch_embeddings():
    if not EMBEDDINGS_PATH.exists():
        logging.error("Embeddings file not found!")
        return

    logging.info("Loading existing embeddings...")
    with open(EMBEDDINGS_PATH, 'rb') as f:
        data = pickle.load(f)

    existing_ids = data['ids'] # List of ISBNs
    embeddings = data['embeddings']
    model_name = data.get('model_name', 'all-MiniLM-L6-v2')
    
    logging.info(f"Loaded {len(existing_ids)} embeddings.")

    logging.info("Connecting to database...")
    conn = sqlite3.connect(DB_PATH)
    
    # We fetch ALL books first, then map them locally to ensure we find everything
    query = """
        SELECT isbn, title, author, description, year, poster_url, book_url
        FROM books 
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Create a lookup dictionary by ISBN
    # We use string conversion for ISBN to be safe
    df['isbn'] = df['isbn'].astype(str)
    book_map = df.set_index('isbn').to_dict('index')
    
    new_metadatas = []
    
    logging.info("Reconstructing metadata...")
    missing_count = 0
    for isbn in existing_ids:
        isbn_str = str(isbn)
        if isbn_str in book_map:
            meta = book_map[isbn_str]
            # Ensure ISBN is included in the meta dict
            meta['isbn'] = isbn_str
            new_metadatas.append(meta)
        else:
            # Fallback - use existing metadata if DB lookup fails (unlikely)
            # Find the index in the original list? 
            # Actually data['metadatas'] matches data['ids'] by index
            # But let's hopw we don't hit this.
            logging.warning(f"ISBN {isbn} not found in current DB dump!")
            missing_count += 1
            # Try to recover from existing metadata if possible, but that doesn't have description
            # This shouldn't happen if the DB hasn't changed.
            
    if missing_count > 0:
        logging.error(f"Aborting! {missing_count} ISBNs from embeddings missing in DB.")
        return

    if len(new_metadatas) != len(existing_ids):
         logging.error("Mismatch in length!")
         return

    data_to_save = {
        'ids': existing_ids,
        'metadatas': new_metadatas,
        'embeddings': embeddings,
        'model_name': model_name
    }
    
    logging.info("Saving patched embeddings...")
    with open(EMBEDDINGS_PATH, 'wb') as f:
        pickle.dump(data_to_save, f)
        
    logging.info("Done!")

if __name__ == "__main__":
    patch_embeddings()
