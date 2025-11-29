import unittest
from advanced_analytics import SepsisPredictor, ReadmissionRiskScorer
from research_module import ClinicalTrialMatcher
from ai_governance import BiasDetector

class TestV60Features(unittest.TestCase):
    
    def test_sepsis_predictor(self):
        sepsis = SepsisPredictor()
        # High Risk: SBP 90 (1), RR 24 (1), GCS 14 (1) = 3
        res = sepsis.calculate_qsofa(90, 24, 14)
        self.assertEqual(res['score'], 3)
        self.assertIn("High", res['risk'])
        
        # Low Risk
        res = sepsis.calculate_qsofa(120, 16, 15)
        self.assertEqual(res['score'], 0)

    def test_readmission_scorer(self):
        lace = ReadmissionRiskScorer()
        # High Risk: LOS 7 (4) + Acuity (3) + Comorb 3 (3) + ED 1 (1) = 11
        res = lace.calculate_lace(7, True, 3, 1)
        self.assertGreaterEqual(res['score'], 10)
        self.assertEqual(res['risk'], "High")

    def test_trial_matcher(self):
        matcher = ClinicalTrialMatcher()
        # Match
        matches = matcher.find_trials("Lung Cancer", 60, "Male")
        self.assertTrue(len(matches) > 0)
        self.assertEqual(matches[0]['condition'], 'Lung Cancer')
        
        # No Match (Age)
        matches = matcher.find_trials("Lung Cancer", 10, "Male")
        self.assertEqual(len(matches), 0)

    def test_bias_detector(self):
        detector = BiasDetector()
        # Bias Flag
        text = "Patient is on Medicaid and is non-compliant."
        audit = detector.audit_recommendation(text)
        self.assertEqual(audit['risk_level'], "High")
        self.assertIn("medicaid", audit['flags'][0])
        
        # No Bias
        text = "Patient is adherent to medication."
        audit = detector.audit_recommendation(text)
        self.assertEqual(audit['risk_level'], "Low")

if __name__ == '__main__':
    unittest.main()
