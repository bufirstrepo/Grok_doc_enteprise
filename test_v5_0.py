import unittest
from specialty_calculators import CardioRiskCalculator, BehavioralHealthScorer
from rcm_engine import DenialPredictor
from sdoh_screener import SDOHAnalyzer

class TestV50Features(unittest.TestCase):
    
    def test_cardio_risk(self):
        calc = CardioRiskCalculator()
        # Test ASCVD: 50yo Male, Smoker, Diabetic, High BP/Chol should be high risk
        risk = calc.calculate_ascvd(50, 'M', 220, 35, 140, True, True)
        self.assertGreater(risk, 5.0)
        
        # Test CHA2DS2-VASc: Age 75 (2) + Stroke (2) = 4
        score = calc.calculate_cha2ds2_vasc(75, 'M', False, False, True, False, False)
        self.assertEqual(score, 4)

    def test_behavioral_health(self):
        scorer = BehavioralHealthScorer()
        # PHQ-9 Severe: 3,3,3,3,3,3,3,0,0 = 21
        res = scorer.score_phq9([3,3,3,3,3,3,3,0,0])
        self.assertEqual(res['severity'], 'Severe')

    def test_denial_predictor(self):
        predictor = DenialPredictor()
        # Test High Risk
        res = predictor.predict_denial("Patient requests cosmetic procedure not medically necessary")
        self.assertEqual(res['probability'], 'High')
        self.assertIn("cosmetic", res['reasons'][0])
        
        # Test Low Risk
        res = predictor.predict_denial("Detailed history and exam performed. Decision made to treat.")
        self.assertEqual(res['probability'], 'Low')

    def test_sdoh_screener(self):
        analyzer = SDOHAnalyzer()
        # Test Housing
        res = analyzer.analyze("Patient is currently homeless and staying in a shelter.")
        self.assertIn('Housing', res)
        self.assertEqual(res['Housing']['code'], 'Z59.0')
        
        # Test Food
        res = analyzer.analyze("Complains of hunger and has no food at home.")
        self.assertIn('Food Insecurity', res)

if __name__ == '__main__':
    unittest.main()
