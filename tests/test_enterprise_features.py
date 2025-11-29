import unittest
import sys
import os

# Add parent directory to path to allow importing modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json
from llm_chain import MultiLLMChain, ChainStep, run_multi_llm_decision

# v2.5 Imports
from hcc_scoring import HCCEngine
from disease_discovery import DiseaseDiscoveryEngine
from meat_compliance import MEATValidator
from ehr_adapters import get_ehr_adapter

# v3.0 Imports
from ai_tools_adapters import get_ai_tool
from hl7_transport import HL7MessageBuilder
from peer_review import PeerReviewSystem

# v4.0 Imports
from clinical_safety import DrugInteractionChecker
from security_utils import PHIMasker

# v5.0 Imports
from specialty_calculators import CardioRiskCalculator, BehavioralHealthScorer
from rcm_engine import DenialPredictor
from sdoh_screener import SDOHAnalyzer

# v6.0 Imports
from advanced_analytics import SepsisPredictor, ReadmissionRiskScorer
from research_module import ClinicalTrialMatcher
from ai_governance import BiasDetector


class TestHCCAndRiskAdjustment(unittest.TestCase):
    """v2.5 & v6.5: HCC Scoring, Disease Discovery, M.E.A.T."""
    
    def test_hcc_scoring(self):
        """Test RAF score calculation"""
        engine = HCCEngine()
        result = engine.calculate_raf(72, 'M', ['E11.9', 'I50.9'])
        self.assertAlmostEqual(result['raf_score'], 0.778, places=3)
        self.assertTrue(result['revenue_impact'] > 8000)
    
    def test_hcc_expansion(self):
        """Test expanded ICD-10 mappings (~4,200 codes)"""
        engine = HCCEngine()
        self.assertGreater(len(engine.icd_map), 3000)
        self.assertIn('E11.05', engine.icd_map)
        self.assertIn('C99.9', engine.icd_map)
    
    def test_batch_raf_scoring(self):
        """v6.5: Test batch processing"""
        engine = HCCEngine()
        patients = [
            {'mrn': 'P001', 'age': 72, 'gender': 'M', 'icd_codes': ['E11.9', 'I50.9']},
            {'mrn': 'P002', 'age': 68, 'gender': 'F', 'icd_codes': ['C34.90']}
        ]
        results = engine.batch_calculate(patients)
        self.assertEqual(len(results), 2)
        self.assertTrue(all('raf_score' in r for r in results))
    
    def test_disease_discovery(self):
        """Test AI-powered condition identification"""
        engine = DiseaseDiscoveryEngine()
        text = "Patient has history of hypertension and morbid obesity. Denies diabetes."
        results = engine.analyze(text, [], {})
        self.assertIn('Hypertension', results)
        self.assertIn('Obesity', results)
        self.assertNotIn('Diabetes', results)
    
    def test_meat_compliance(self):
        """Test M.E.A.T. documentation validation"""
        validator = MEATValidator()
        note = "Diabetes is stable. A1c 7.2. Continue metformin."
        res = validator.validate(note, "Diabetes")
        self.assertEqual(res['score'], 0.75)
        self.assertIn('Assess', res['missing'])
    
    def test_meat_ai_suggestions(self):
        """v6.5: Test AI-powered M.E.A.T. suggestions"""
        validator = MEATValidator()
        note = "Diabetes mentioned"
        res = validator.validate(note, "Diabetes")
        suggestions = validator.suggest_improvements(note, "Diabetes", res)
        self.assertTrue(len(suggestions) > 0)
        self.assertTrue(any('Monitor' in s or 'Evaluate' in s for s in suggestions))


class TestIntegrationsAndMessaging(unittest.TestCase):
    """v2.5 & v3.0: EHR, AI Tools, HL7"""
    
    def test_ehr_adapters(self):
        """Test EHR factory and connection"""
        adapter = get_ehr_adapter("Epic", {
            'url': 'http://test', 
            'client_id': '1', 
            'client_secret': '2'
        })
        self.assertIsNotNone(adapter)
        success = adapter.connect()
        self.assertTrue(success)
    
    def test_ai_tools_factory(self):
        """v3.0: Test AI tool adapter factory"""
        config = {'enabled': True, 'api_key': '123', 'endpoint': 'https://api.aidoc.com'}
        adapter = get_ai_tool("Aidoc", config)
        self.assertIsNotNone(adapter)
        self.assertTrue(adapter.enabled)
        
        # Test disabled state
        config['enabled'] = False
        adapter = get_ai_tool("Aidoc", config)
        res = adapter.analyze("path/to/file")
        self.assertEqual(res['error'], 'Disabled')
    
    def test_hl7_parsing(self):
        """v3.0: Test HL7 v2 message parsing"""
        raw_msg = "MSH|^~\\&|Sender|Fac|Grok|Fac|20251128||ADT^A01|MSG001|P|2.5\rPID|||12345||Doe^John||19800101|M\r"
        parsed = HL7MessageBuilder.parse_message(raw_msg)
        self.assertEqual(parsed['type'], 'ADT^A01')
        self.assertEqual(parsed['mrn'], '12345')
        self.assertEqual(parsed['name'], 'Doe^John')
        
        ack = HL7MessageBuilder.create_ack(raw_msg)
        self.assertIn("MSA|AA|MSG001", ack)


class TestPeerReviewAndWorkflow(unittest.TestCase):
    """v3.0: Peer Review System"""
    
    def test_peer_review_workflow(self):
        """Test complete peer review lifecycle"""
        system = PeerReviewSystem()
        
        rid = system.submit_for_review({'mrn': '123'}, priority="High")
        self.assertEqual(len(system.queue), 1)
        self.assertEqual(system.queue[0]['priority'], 'High')
        
        success = system.approve_case(rid, "Dr. Test", "LGTM")
        self.assertTrue(success)
        self.assertEqual(len(system.queue), 0)
        self.assertEqual(len(system.history), 1)
        self.assertEqual(system.history[0]['status'], 'Approved')


class TestSafetyAndSecurity(unittest.TestCase):
    """v4.0: Clinical Safety & PHI Protection"""
    
    def test_ddi_checker(self):
        """Test drug interaction detection"""
        checker = DrugInteractionChecker()
        
        # Major interaction
        alerts = checker.check_interactions(["Warfarin", "Aspirin"])
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['severity'], 'Major')
        
        # No interaction
        alerts = checker.check_interactions(["Tylenol", "Vitamin C"])
        self.assertEqual(len(alerts), 0)
        
        # Multiple interactions
        alerts = checker.check_interactions(["Warfarin", "Aspirin", "Ibuprofen"])
        self.assertEqual(len(alerts), 2)
    
    def test_phi_masker(self):
        """Test PHI redaction"""
        masker = PHIMasker()
        
        text = "Patient MRN: 123456"
        masked = masker.mask_text(text)
        self.assertIn("[MRN-REDACTED]", masked)
        
        text = "SSN: 123-45-6789"
        masked = masker.mask_text(text)
        self.assertIn("[SSN-REDACTED]", masked)


class TestSpecialtyCalculators(unittest.TestCase):
    """v5.0: Cardiology & Behavioral Health"""
    
    def test_cardio_risk(self):
        """Test ASCVD and CHA2DS2-VASc"""
        calc = CardioRiskCalculator()
        
        risk = calc.calculate_ascvd(50, 'M', 220, 35, 140, True, True)
        self.assertGreater(risk, 5.0)
        
        score = calc.calculate_cha2ds2_vasc(75, 'M', False, False, True, False, False)
        self.assertEqual(score, 4)
    
    def test_behavioral_health(self):
        """Test PHQ-9 depression scoring"""
        scorer = BehavioralHealthScorer()
        res = scorer.score_phq9([3,3,3,3,3,3,3,0,0])
        self.assertEqual(res['severity'], 'Severe')


class TestRCMAndSDOH(unittest.TestCase):
    """v5.0: Revenue Cycle & Social Determinants"""
    
    def test_denial_predictor(self):
        """Test claims denial prediction"""
        predictor = DenialPredictor()
        
        res = predictor.predict_denial("Patient requests cosmetic procedure not medically necessary")
        self.assertEqual(res['probability'], 'High')
        
        res = predictor.predict_denial("Detailed history and exam performed.")
        self.assertEqual(res['probability'], 'Low')
    
    def test_sdoh_screener(self):
        """Test social determinants screening"""
        analyzer = SDOHAnalyzer()
        
        res = analyzer.analyze("Patient is currently homeless and staying in a shelter.")
        self.assertIn('Housing', res)
        self.assertEqual(res['Housing']['code'], 'Z59.0')
        
        res = analyzer.analyze("Complains of hunger and has no food at home.")
        self.assertIn('Food Insecurity', res)


class TestAnalyticsAndResearch(unittest.TestCase):
    """v6.0: Predictive Analytics & Clinical Trials"""
    
    def test_sepsis_predictor(self):
        """Test qSOFA sepsis risk"""
        sepsis = SepsisPredictor()
        
        res = sepsis.calculate_qsofa(90, 24, 14)
        self.assertEqual(res['score'], 3)
        self.assertIn("High", res['risk'])
        
        res = sepsis.calculate_qsofa(120, 16, 15)
        self.assertEqual(res['score'], 0)
    
    def test_readmission_scorer(self):
        """Test LACE readmission risk"""
        lace = ReadmissionRiskScorer()
        res = lace.calculate_lace(7, True, 3, 1)
        self.assertGreaterEqual(res['score'], 10)
        self.assertEqual(res['risk'], "High")
    
    def test_trial_matcher(self):
        """Test clinical trial matching"""
        matcher = ClinicalTrialMatcher()
        
        matches = matcher.find_trials("Lung Cancer", 60, "Male")
        self.assertTrue(len(matches) > 0)
        self.assertEqual(matches[0]['condition'], 'Lung Cancer')
        
        matches = matcher.find_trials("Lung Cancer", 10, "Male")
        self.assertEqual(len(matches), 0)
    
    def test_bias_detector(self):
        """Test AI bias detection"""
        detector = BiasDetector()
        
        audit = detector.audit_recommendation("Patient is on Medicaid and is non-compliant.")
        self.assertEqual(audit['risk_level'], "High")
        
        audit = detector.audit_recommendation("Patient is adherent to medication.")
        self.assertEqual(audit['risk_level'], "Low")


class TestMultiLLMChainLogic(unittest.TestCase):
    """v2.0: Multi-LLM reasoning chain logic"""

    def setUp(self):
        """Set up test fixtures"""
        self.patient_context = {
            'age': 72,
            'gender': 'Male',
            'labs': 'Cr: 1.8, WBC: 14.2'
        }
        self.query = "Safe vancomycin dose for septic shock?"
        self.retrieved_cases = [
            {'summary': 'Case 1: Vancomycin in elderly male with AKI'},
            {'summary': 'Case 2: Septic shock management guidelines'}
        ]
        self.bayesian_result = {
            'prob_safe': 0.85,
            'n_cases': 150,
            'ci_low': 0.78,
            'ci_high': 0.91
        }

    def test_chain_initialization(self):
        """Test chain initializes correctly"""
        chain = MultiLLMChain()
        self.assertEqual(chain.genesis_hash, "GENESIS_CHAIN")
        self.assertEqual(len(chain.chain_history), 0)

    def test_hash_computation(self):
        """Test cryptographic hash computation"""
        chain = MultiLLMChain()
        timestamp = "2025-01-01T00:00:00Z"
        hash1 = chain._compute_step_hash(
            "Test Step",
            "Test prompt",
            "Test response",
            "prev_hash_123",
            timestamp
        )

        # BLAKE2b hex digest is 128 characters
        self.assertEqual(len(hash1), 128)

        # Same inputs should produce same hash
        hash2 = chain._compute_step_hash(
            "Test Step",
            "Test prompt",
            "Test response",
            "prev_hash_123",
            timestamp
        )
        self.assertEqual(hash1, hash2)

        # Different inputs should produce different hash
        hash3 = chain._compute_step_hash(
            "Test Step",
            "Different prompt",
            "Test response",
            "prev_hash_123",
            timestamp
        )
        self.assertNotEqual(hash1, hash3)

    @patch('llm_chain.grok_query')
    def test_full_chain_execution(self, mock_grok):
        """Test full 4-stage chain execution"""
        # Mock responses must be dicts because safe_grok_query expects resp["text"]
        mock_responses = [
            {"text": "Perspective strength: [8]\nCredence: >75%\nKey PK uncertainty: None\n\nKinetics: 1000mg q12h"},
            {"text": "Perspective strength: [9]\nCredence: >75%\nKey coding uncertainty: None\n\nAdversarial: Risk of nephrotoxicity\nFINAL CODING SCORE: [0.9]"},
            {"text": "Perspective strength: [7]\nCredence: 25-75%\nKey safety uncertainty: Renal function\n\nRed Team: Monitor renal function\nFINAL SAFETY SCORE: [0.85]"},
            {"text": "Perspective strength: [8]\nCredence: >75%\nKey evidence uncertainty: None\n\nLiterature: 2024 IDSA guidelines support AUC-based dosing\nEVIDENCE STRENGTH: [0.9]"},
            # Arbiter returns JSON string in "text" or directly? 
            # safe_grok_query returns resp["text"]. _run_arbiter_model parses that text as JSON.
            {"text": json.dumps({
                "decision": "APPROVED",
                "action": "1000mg q12h",
                "safety_score": 0.94,
                "confidence_interval": "0.94 [0.89-0.99]",
                "data_sufficiency": 0.92,
                "regulatory_check": "Compliant",
                "guideline": "IDSA 2025",
                "risk_analysis": "None",
                "evidence_table": {},
                "bias_check": "None"
            })}
        ]
        mock_grok.side_effect = mock_responses

        chain = MultiLLMChain()
        result = chain.run_chain(
            self.patient_context,
            self.query,
            self.retrieved_cases,
            self.bayesian_result
        )

        # Check result structure
        print(f"DEBUG RESULT: {result}")
        self.assertIn('chain_steps', result)
        self.assertIn('final_recommendation', result)
        self.assertIn('final_confidence', result)
        self.assertIn('chain_hash', result)
        self.assertIn('total_steps', result)

        # Check 5 steps executed (Kinetics, Blue, Red, Lit, Arbiter)
        self.assertEqual(result['total_steps'], 5)
        self.assertEqual(len(result['chain_steps']), 5)

    @patch('llm_chain.grok_query')
    def test_chain_verification(self, mock_grok):
        """Test hash chain integrity verification"""
        # Mock generic response
        mock_grok.return_value = {"text": "Perspective strength: [8]\nCredence: >75%\nKey uncertainty: None\n\nTest response"}
        # Note: run_chain calls grok_query 5 times. return_value handles all calls.
        # But Arbiter expects JSON. So we need side_effect or a smart return_value.
        # Let's use side_effect for the 5 calls.
        
        arbiter_json = json.dumps({
            "decision": "APPROVED",
            "action": "Test Action",
            "safety_score": 0.9,
            "confidence_interval": "0.9 [0.8-1.0]",
            "data_sufficiency": 0.9,
            "regulatory_check": "Compliant",
            "guideline": "N/A",
            "risk_analysis": "None",
            "evidence_table": {},
            "bias_check": "None"
        })
        
        mock_grok.side_effect = [
            {"text": "Perspective strength: [8]\nCredence: >75%\nKey uncertainty: None\n\nResponse 1"},
            {"text": "Perspective strength: [8]\nCredence: >75%\nKey uncertainty: None\n\nResponse 2"},
            {"text": "Perspective strength: [8]\nCredence: >75%\nKey uncertainty: None\n\nResponse 3"},
            {"text": "Perspective strength: [8]\nCredence: >75%\nKey uncertainty: None\n\nResponse 4"},
            {"text": arbiter_json}
        ]

        chain = MultiLLMChain()
        chain.run_chain(
            self.patient_context,
            self.query,
            self.retrieved_cases,
            self.bayesian_result
        )

        # Chain should be valid
        self.assertTrue(chain.verify_chain())

        # Tamper with a step
        if len(chain.chain_history) > 0:
            chain.chain_history[1].response = "TAMPERED RESPONSE"

        # Chain should now be invalid
        self.assertFalse(chain.verify_chain())


class TestChainStepDataclass(unittest.TestCase):
    """Test ChainStep dataclass"""

    def test_chain_step_creation(self):
        """Test ChainStep can be created with all fields"""
        step = ChainStep(
            step_name="Test Model",
            prompt="Test prompt",
            response="Test response",
            timestamp="2025-11-18T12:00:00Z",
            prev_hash="abc123",
            step_hash="def456",
            confidence=0.85
        )

        self.assertEqual(step.step_name, "Test Model")
        self.assertEqual(step.confidence, 0.85)


if __name__ == '__main__':
    # Run all tests
    unittest.main(verbosity=2)
