import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import pickle
import uuid
from typing import List, Optional

# Define the directory for the vector index and map
DEFAULT_DATA_DIR = "backend/data"
DEFAULT_VECTOR_INDEX_FILE = "vector_index.faiss"
DEFAULT_ID_MAP_FILE = "vector_id_map.pkl"

DEFAULT_VECTOR_INDEX_PATH = os.path.join(DEFAULT_DATA_DIR, DEFAULT_VECTOR_INDEX_FILE)
DEFAULT_ID_MAP_PATH = os.path.join(DEFAULT_DATA_DIR, DEFAULT_ID_MAP_FILE)

# Ensure the default data directory exists
os.makedirs(DEFAULT_DATA_DIR, exist_ok=True)

class VectorDB:
    def __init__(
        self, 
        model_name="intfloat/e5-small-v2",
        index_file_path: Optional[str] = None,
        id_map_file_path: Optional[str] = None
    ):
        self.model_name = model_name
        self.index_path = index_file_path or DEFAULT_VECTOR_INDEX_PATH
        self.id_to_content_map_path = id_map_file_path or DEFAULT_ID_MAP_PATH
        
        # Ensure directory for custom paths exists if provided
        if index_file_path:
            os.makedirs(os.path.dirname(index_file_path), exist_ok=True)
        if id_map_file_path:
            os.makedirs(os.path.dirname(id_map_file_path), exist_ok=True)

        self.model = SentenceTransformer(self.model_name)
        # Get embedding dimension from the model
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        
        self.load_or_create_index()

    def load_or_create_index(self):
        if os.path.exists(self.index_path) and os.path.exists(self.id_to_content_map_path):
            print(f"Loading existing FAISS index from {self.index_path}")
            self.index = faiss.read_index(self.index_path)
            with open(self.id_to_content_map_path, 'rb') as f:
                self.internal_idx_to_content_id_map = pickle.load(f)
            print(f"Loaded index with {self.index.ntotal} vectors.")
        else:
            print(f"Creating new FAISS index (dim: {self.embedding_dim}) at {self.index_path}")
            self.index = faiss.IndexFlatL2(self.embedding_dim)
            # self.index = faiss.IndexIDMap(faiss.IndexFlatL2(self.embedding_dim)) # If using FAISS internal IDs directly
            self.internal_idx_to_content_id_map = {}
            self.save_index() # Save the empty index and map

    def add_text_embedding(self, content_item_id: uuid.UUID, text_content: str):
        if not isinstance(content_item_id, uuid.UUID):
            raise ValueError("content_item_id must be a UUID")

        embedding = self.model.encode([text_content], convert_to_tensor=False, normalize_embeddings=True)
        embedding_np = np.array(embedding, dtype=np.float32)
        
        # FAISS typically uses sequential integer IDs. We map these internal FAISS IDs to our UUIDs.
        internal_idx = self.index.ntotal
        self.index.add(embedding_np)
        self.internal_idx_to_content_id_map[internal_idx] = str(content_item_id) # Store UUID as string
        
        print(f"Added embedding for {content_item_id}. Index size: {self.index.ntotal}")
        self.save_index()
        return internal_idx

    def search_similar(self, query_text: str, k: int = 5) -> List[dict]:
        if self.index.ntotal == 0:
            return []
            
        query_embedding = self.model.encode([query_text], convert_to_tensor=False, normalize_embeddings=True)
        query_embedding_np = np.array(query_embedding, dtype=np.float32)
        
        distances, internal_indices = self.index.search(query_embedding_np, k)
        
        results = []
        for i in range(len(internal_indices[0])):
            internal_idx = internal_indices[0][i]
            if internal_idx != -1: # FAISS returns -1 if fewer than k results are found
                content_id_str = self.internal_idx_to_content_id_map.get(internal_idx)
                if content_id_str:
                    results.append({
                        "content_item_id": uuid.UUID(content_id_str),
                        "score": float(distances[0][i]) # L2 distance, smaller is better
                    })
        return results

    def save_index(self):
        print(f"Saving FAISS index to {self.index_path} ({self.index.ntotal} vectors)")
        faiss.write_index(self.index, self.index_path)
        with open(self.id_to_content_map_path, 'wb') as f:
            pickle.dump(self.internal_idx_to_content_id_map, f)
        print("Index saved.")

    def get_vector_count(self):
        return self.index.ntotal

# Example usage (for testing)
if __name__ == '__main__':
    vector_db_instance = VectorDB()
    print(f"Initial vector count: {vector_db_instance.get_vector_count()}")

    # Test adding some items
    test_id_1 = uuid.uuid4()
    test_id_2 = uuid.uuid4()
    vector_db_instance.add_text_embedding(test_id_1, "This is a test document about apples.")
    vector_db_instance.add_text_embedding(test_id_2, "Another document, this one is about bananas.")
    print(f"Vector count after additions: {vector_db_instance.get_vector_count()}")

    # Test search
    search_results = vector_db_instance.search_similar("fruits like apples", k=1)
    print("Search results for 'fruits like apples':")
    for res in search_results:
        print(f"  Content ID: {res['content_item_id']}, Score: {res['score']}")
        assert res['content_item_id'] == test_id_1

    search_results_banana = vector_db_instance.search_similar("yellow fruits", k=1)
    print("Search results for 'yellow fruits':")
    for res in search_results_banana:
        print(f"  Content ID: {res['content_item_id']}, Score: {res['score']}")
        assert res['content_item_id'] == test_id_2
    
    # Test reloading
    del vector_db_instance
    print("Reloading VectorDB...")
    reloaded_vector_db = VectorDB()
    print(f"Reloaded vector count: {reloaded_vector_db.get_vector_count()}")
    assert reloaded_vector_db.get_vector_count() == 2
    reloaded_search = reloaded_vector_db.search_similar("apples document", k=1)
    print(f"Search result from reloaded: {reloaded_search}")
    assert reloaded_search[0]['content_item_id'] == test_id_1

    print("VectorDB test completed.") 