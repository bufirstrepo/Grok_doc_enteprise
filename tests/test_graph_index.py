import unittest
import sys
import os
import shutil

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ingestion.fhir_loader import FHIRLoader
from src.graph.overlap_graph import OverlapGraph
from src.graph.graph_index import GraphIndex

class TestGraphIndex(unittest.TestCase):
    def setUp(self):
        self.loader = FHIRLoader()
        self.loader.load_mock_data(num_doctors=10, num_patients=50, num_encounters=200)
        
    def test_graph_construction(self):
        """Verify graph builds correctly"""
        graph = OverlapGraph()
        graph.build_graph(self.loader.get_practitioners(), self.loader.get_encounters())
        
        # Check if we have nodes
        self.assertTrue(len(graph.graph) > 0)
        
        # Check metadata
        doc_id = self.loader.get_practitioners()[0].id
        self.assertIsNotNone(graph.get_metadata(doc_id))

    def test_faiss_indexing(self):
        """Verify FAISS indexing and search"""
        graph = OverlapGraph()
        graph.build_graph(self.loader.get_practitioners(), self.loader.get_encounters())
        
        index = GraphIndex(graph)
        index.build_index()
        
        # Search for a specialty
        results = index.search("Cardiology", k=3)
        self.assertTrue(len(results) > 0)
        
        # Verify results are doctors
        doc_id, score = results[0]
        self.assertTrue(doc_id.startswith("DOC-"))

if __name__ == '__main__':
    unittest.main()
