"""
Graph Index (FAISS)
Indexes doctor embeddings for fast similarity search.
For this MVP, we use a simple embedding strategy: One-Hot Encoding of Specialty + Graph Embeddings (Node2Vec style simplified).
"""

import numpy as np
import faiss
from typing import List, Dict, Tuple
from .overlap_graph import OverlapGraph

class GraphIndex:
    def __init__(self, graph: OverlapGraph):
        self.graph = graph
        self.index = None
        self.doc_ids: List[str] = [] # Map index ID to Doc ID
        self.dimension = 0

    def build_index(self):
        """
        Builds a FAISS index based on doctor specialties and graph connectivity.
        Vector representation:
        - Part 1: Specialty (One-hot)
        - Part 2: Connectivity (Adjacency vector simplified)
        """
        docs = list(self.graph.doc_metadata.values())
        if not docs:
            print("No doctors to index.")
            return

        self.doc_ids = [d.id for d in docs]
        
        # 1. Create Specialty Map
        specialties = sorted(list(set(d.specialty for d in docs)))
        spec_map = {s: i for i, s in enumerate(specialties)}
        spec_dim = len(specialties)

        # 2. Create Vectors
        # For simplicity, we'll just use specialty one-hot for now. 
        # In a real system, we'd add graph embeddings (Node2Vec).
        self.dimension = spec_dim
        
        vectors = np.zeros((len(docs), self.dimension), dtype='float32')
        
        for i, doc in enumerate(docs):
            if doc.specialty in spec_map:
                vectors[i, spec_map[doc.specialty]] = 1.0
            
            # Normalize
            faiss.normalize_L2(vectors[i:i+1])

        # 3. Index with FAISS
        self.index = faiss.IndexFlatIP(self.dimension) # Inner Product (Cosine Similarity since normalized)
        self.index.add(vectors)
        
        print(f"Indexed {len(docs)} doctors with dimension {self.dimension}.")

    def search(self, query_specialty: str, k: int = 5) -> List[Tuple[str, float]]:
        """Find doctors similar to the query specialty."""
        if not self.index:
            return []

        # Create query vector
        # We need to reconstruct the spec map or store it. 
        # For this MVP, we'll re-derive it (inefficient but fine for demo).
        docs = list(self.graph.doc_metadata.values())
        specialties = sorted(list(set(d.specialty for d in docs)))
        spec_map = {s: i for i, s in enumerate(specialties)}
        
        q_vec = np.zeros((1, self.dimension), dtype='float32')
        if query_specialty in spec_map:
            q_vec[0, spec_map[query_specialty]] = 1.0
        
        faiss.normalize_L2(q_vec)
        
        # Search
        distances, indices = self.index.search(q_vec, k)
        
        results = []
        for i in range(k):
            idx = indices[0][i]
            if idx != -1:
                doc_id = self.doc_ids[idx]
                score = float(distances[0][i])
                results.append((doc_id, score))
                
        return results
