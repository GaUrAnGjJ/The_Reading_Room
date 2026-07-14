import pickle
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ROOT = Path(__file__).resolve().parent.parent
EMBEDDINGS_PATH = ROOT / "recommender" / "embeddings.pkl"

class BookRecommender:
    def __init__(self):
        self.model = None
        self.embeddings = None
        self.metadatas = None
        self.ids = None
        self.loaded = False
        
    def load(self):
        """Load model and embeddings."""
        if not EMBEDDINGS_PATH.exists():
            raise FileNotFoundError(f"Embeddings file not found at {EMBEDDINGS_PATH}. Run build_embeddings.py first.")
            
        logging.info(f"Loading embeddings from {EMBEDDINGS_PATH}...")
        with open(EMBEDDINGS_PATH, 'rb') as f:
            data = pickle.load(f)
            
        self.embeddings = data['embeddings']
        self.metadatas = data['metadatas']
        self.ids = data['ids']
        model_name = data.get('model_name', 'all-MiniLM-L6-v2')
        
        logging.info(f"Loading model {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.loaded = True
        logging.info("Recommender ready.")

    def recommend(self, query: str, top_k: int = 6):
        """Recommend books based on query string."""
        if not self.loaded:
            self.load()
            
        # 1. Semantic Search
        query_vec = self.model.encode([query])
        scores = cosine_similarity(query_vec, self.embeddings).flatten()
        
        # Sanitize scores to avoid JSON errors
        scores = np.nan_to_num(scores, nan=0.0, posinf=1.0, neginf=0.0)
        
        # Get top semantic results (fetch more candidates to blend)
        top_n = min(len(scores), 50)
        top_indices = scores.argsort()[-top_n:][::-1]
        
        semantic_results = []
        seen_isbns = set()
        
        for idx in top_indices:
            score = float(scores[idx])
            meta = self.metadatas[idx]
            if meta['isbn'] not in seen_isbns:
                semantic_results.append({**meta, "score": score})
                seen_isbns.add(meta['isbn'])
            
        # 2. Keyword Search (Boost Author matches)
        # This allows "searching by author" within the recommendation engine
        query_lower = query.lower().strip()
        author_matches = []
        
        # Only scan if query is meaningful (avoid short purely numeric queries potentially)
        if len(query_lower) > 2:
            for meta in self.metadatas:
                # Check for author match
                if meta.get('author') and query_lower in meta['author'].lower():
                    if meta['isbn'] not in seen_isbns:
                        # Give a boosted score (above 1.0) so they appear first
                        author_matches.append({**meta, "score": 2.0})
                        seen_isbns.add(meta['isbn'])
        
        # 3. Combine Results
        # Author matches first, then semantic matches
        final_results = author_matches + semantic_results
        
        # Sort by score descending
        final_results.sort(key=lambda x: x['score'], reverse=True)
        
        return final_results[:top_k]

if __name__ == "__main__":
    rec = BookRecommender()
    print(rec.recommend("space robot"))
