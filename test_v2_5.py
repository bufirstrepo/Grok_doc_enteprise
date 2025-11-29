import unittest
from hcc_scoring import HCCEngine
from disease_discovery import DiseaseDiscoveryEngine
from meat_compliance import MEATValidator
from ehr_adapters import get_ehr_adapter

class TestV25Features(unittest.TestCase):
    
    def test_hcc_scoring(self):
        engine = HCCEngine()
        # Test Case: 72M with Diabetes (E11.9) and CHF (I50.9)
        # Demo factors: M 70-74 (0.35) + Diabetes (0.105) + CHF (0.323) = 0.778
        result = engine.calculate_raf(72, 'M', ['E11.9', 'I50.9'])
        self.assertAlmostEqual(result['raf_score'], 0.778, places=3)
        self.assertTrue(result['revenue_impact'] > 8000)

    def test_disease_discovery(self):
        engine = DiseaseDiscoveryEngine()
        text = "Patient has history of hypertension and morbid obesity. Denies diabetes."
        # Should find Hypertension and Obesity. Should NOT find Diabetes (negated).
        results = engine.analyze(text, [], {})
        self.assertIn('Hypertension', results)
        self.assertIn('Obesity', results)
        self.assertNotIn('Diabetes', results)

    def test_meat_compliance(self):
        validator = MEATValidator()
        # Note has Monitor (stable), Evaluate (A1c), Treat (continue dose)
        # Missing Assess (plan/discussion)
        note = "Diabetes is stable. A1c 7.2. Continue metformin."
        res = validator.validate(note, "Diabetes")
        self.assertEqual(res['score'], 0.75) # 3/4
        self.assertIn('Assess', res['missing'])

    def test_ehr_adapters(self):
        # Test factory
        adapter = get_ehr_adapter("Epic", {'url': 'http://test', 'client_id': '1', 'client_secret': '2'})
        self.assertIsNotNone(adapter)
        self.assertFalse(adapter.connected)
        
        # Test connect
        success = adapter.connect()
        self.assertTrue(success)
        self.assertTrue(adapter.connected)

if __name__ == '__main__':
    unittest.main()
