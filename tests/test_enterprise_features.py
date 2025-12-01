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
    
        # BLAKE3 hex digest is 64 characters (256 bits)
        self.assertEqual(len(hash1), 64)
        
        # Deterministic check
        hash2 = chain._compute_step_hash(
            "Test Step",
            "Test prompt",
            "Test response",
            "prev_hash_123",
            timestamp
        )
        self.assertEqual(hash1, hash2)
        
        # Avalanche effect check
        hash3 = chain._compute_step_hash(
            "Test Step",
            "Test prompt",
            "Test response changed",
            "prev_hash_123",
            timestamp
        )
        self.assertNotEqual(hash1, hash3)

    @patch('llm_chain.ModelRouter')
    def test_full_chain_execution(self, MockRouter):
        # Setup mock router instance
        mock_router_instance = MockRouter.return_value
        
        # Mock responses for the 6 stages
        # Scribe, Kinetics, Blue Team, Red Team, Literature, Arbiter
        mock_responses = [
            # Scribe (JSON)
            '{"subjective": ["Patient is 72M"], "plan": ["Monitor"]}',
            # Kinetics
            "Calculated dose: 1000mg. Math: ...",
            # Blue Team
            "AUDIT_PASS",
            # Red Team
            "NO LETHAL FLAW",
            # Literature
            "EVIDENCE_GRADE: A",
            # Arbiter
            "Final Decision: APPROVED. Risks low."
        ]
        mock_router_instance.route_request.side_effect = mock_responses
    
        # Mock personas to have only 1 per stage to match mock_responses count
        mock_personas = {
            "scribe": ["Scribe Persona"],
            "kinetics": ["Kinetics Persona"],
            "adversarial": ["Adversarial Persona"],
            "red_team": ["Red Team Persona"],
            "literature": ["Literature Persona"],
            "arbiter": ["Arbiter Persona"]
        }
        
        chain = MultiLLMChain(personas=mock_personas)
        result = chain.run_chain(
            self.patient_context,
            self.query,
            self.retrieved_cases,
            self.bayesian_result
        )
    
        # Check result structure
        print(f"DEBUG RESULT: {result}")
        self.assertIn('chain_export', result)
        self.assertIn('final_decision', result)
        self.assertIn('confidence', result)
    
        # Check 6 steps executed
        self.assertEqual(len(result['chain_export']['steps']), 6)
        self.assertTrue(result['chain_export']['verified'])
        self.assertEqual(result['final_decision'], "APPROVED")

    @patch('llm_chain.ModelRouter')
    def test_chain_verification(self, MockRouter):
        """Test chain integrity verification"""
        mock_router_instance = MockRouter.return_value
        
        # Mock responses for 6 steps
        mock_responses = [
            '{"json": "data"}', # Scribe
            "Kinetics Response",
            "Blue Team Response",
            "Red Team Response",
            "Literature Response",
            "Arbiter Response"
        ]
        mock_router_instance.route_request.side_effect = mock_responses
        
        # Mock personas to have only 1 per stage to match mock_responses count
        mock_personas = {
            "scribe": ["Scribe Persona"],
            "kinetics": ["Kinetics Persona"],
            "adversarial": ["Adversarial Persona"],
            "red_team": ["Red Team Persona"],
            "literature": ["Literature Persona"],
            "arbiter": ["Arbiter Persona"]
        }
        
        chain = MultiLLMChain(personas=mock_personas)
        result = chain.run_chain(self.patient_context, self.query, [], {})
        
        # Verify valid chain
        self.assertTrue(chain.verify_chain())
        
        # Tamper with chain
        # Since ChainStep is frozen, we can't modify it directly.
        # We have to replace an item in the list with a tampered one.
        original_step = chain.chain_history[1]
        
        # Create a tampered step. We have to compute a valid hash for the *tampered* content 
        # to pass __post_init__, but it won't match the *chain* integrity (next step's prev_hash).
        # Actually, verify_chain checks if re-computing hash matches stored hash.
        # If we create a new step with modified response but OLD hash, __post_init__ will fail.
        # So we can't easily create an "invalid" step object in v10.1 because of the strict check!
        # This is a feature, not a bug.
        # To test verification failure, we can manually append a step that doesn't link correctly
        # or use `object.__setattr__` to bypass frozen check if we really want to simulate corruption.
        
        object.__setattr__(original_step, 'response', "TAMPERED_RESPONSE")
        
        # Now verify should fail because re-computed hash won't match stored hash
        self.assertFalse(chain.verify_chain())

class TestChainStepDataclass(unittest.TestCase):
    def test_chain_step_creation(self):
        """Test ChainStep can be created with all fields"""
        # In v10.1, we must provide the CORRECT hash
        from llm_chain import blake3_hash
        
        step_name = "Test Model"
        prompt = "Test prompt"
        response = "Test response"
        timestamp = "2025-11-18T12:00:00Z"
        prev_hash = "abc1234567890abcdef1234567890abcdef" # Arbitrary
        
        # Compute valid hash
        content = f"{prev_hash}|{step_name}|{prompt}|{response}|{timestamp}"
        valid_hash = blake3_hash(content)
        
        step = ChainStep(
            step_name=step_name,
            prompt=prompt,
            response=response,
            timestamp=timestamp,
            prev_hash=prev_hash,
            step_hash=valid_hash,
            confidence=1.0 # Default is 1.0 now
        )
        
        self.assertEqual(step.step_name, step_name)
        self.assertEqual(step.confidence, 1.0)


if __name__ == '__main__':
    # Run all tests
    unittest.main(verbosity=2)
