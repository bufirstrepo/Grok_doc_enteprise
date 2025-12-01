"""
Overlap Graph Builder
Constructs a graph where nodes are doctors and edges represent shared patients.
"""

from typing import List, Dict, Tuple
from collections import defaultdict
from ..ingestion.fhir_loader import Practitioner, Patient, Encounter

class OverlapGraph:
    def __init__(self):
        # Adjacency list: doc_id -> {neighbor_doc_id: weight}
        self.graph: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.doc_metadata: Dict[str, Practitioner] = {}

    def build_graph(self, practitioners: List[Practitioner], encounters: List[Encounter]):
        """
        Builds the doctor-doctor overlap graph.
        Two doctors are connected if they have treated the same patient.
        Edge weight = number of shared patients.
        """
        # Store metadata
        for doc in practitioners:
            self.doc_metadata[doc.id] = doc

        # Map Patient -> List of Doctors
        patient_to_docs = defaultdict(set)
        for enc in encounters:
            patient_to_docs[enc.patient_id].add(enc.practitioner_id)

        # Build Graph
        for pat_id, doc_ids in patient_to_docs.items():
            doc_list = list(doc_ids)
            # Create edges for every pair of doctors treating this patient
            for i in range(len(doc_list)):
                for j in range(i + 1, len(doc_list)):
                    doc_a = doc_list[i]
                    doc_b = doc_list[j]
                    
                    # Undirected graph
                    self.graph[doc_a][doc_b] += 1
                    self.graph[doc_b][doc_a] += 1

        print(f"Graph built with {len(self.graph)} nodes.")

    def get_neighbors(self, doc_id: str) -> List[Tuple[str, int]]:
        """Returns list of (neighbor_id, weight) sorted by weight desc."""
        if doc_id not in self.graph:
            return []
        
        neighbors = list(self.graph[doc_id].items())
        neighbors.sort(key=lambda x: x[1], reverse=True)
        return neighbors

    def get_metadata(self, doc_id: str) -> Practitioner:
        return self.doc_metadata.get(doc_id)
