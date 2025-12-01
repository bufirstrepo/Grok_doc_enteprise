import unittest
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ingestion.fhir_loader import FHIRLoader
from src.graph.overlap_graph import OverlapGraph
from src.services.consult_predictor import ConsultPredictor

class TestConsultPredictor(unittest.TestCase):
    def setUp(self):
        self.loader = FHIRLoader()
        self.loader.load_mock_data(num_doctors=10, num_patients=50, num_encounters=200)
        
        self.graph = OverlapGraph()
        self.graph.build_graph(self.loader.get_practitioners(), self.loader.get_encounters())
        
        self.predictor = ConsultPredictor(self.loader, self.graph)

    def test_admin_mapping(self):
        """Verify admin is mapped to a doctor"""
        self.assertIn('admin', self.predictor.doc_mapping)
        
    def test_prediction_structure(self):
        """Verify prediction returns correct structure and masked PHI"""
        prediction = self.predictor.predict_next_consult('admin')
        
        if prediction: # Might be None if no overlap in random data
            self.assertIsNotNone(prediction.patient_id)
            self.assertIsNotNone(prediction.patient_name_masked)
            
            # Verify masking (should not contain full name parts if they are long)
            # Our mock names are "Patient XXXXXX", masked is "P. X."
            self.assertTrue("." in prediction.patient_name_masked)
            self.assertFalse("Patient" in prediction.patient_name_masked)
            
            self.assertTrue(len(prediction.shared_with) > 0)

if __name__ == '__main__':
    unittest.main()
