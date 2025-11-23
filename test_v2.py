"""
Test Suite for Grok Doc v2.0 Multi-LLM Chain

Tests cover:
- Multi-LLM chain execution
- Hash chain integrity verification
- Confidence score calculation
- Audit log integration
- Error handling
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json

from llm_chain import MultiLLMChain, ChainStep, run_multi_llm_decision


class TestMultiLLMChain(unittest.TestCase):
    """Test cases for the Multi-LLM reasoning chain"""

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
        hash1 = chain._compute_step_hash(
            "Test Step",
            "Test prompt",
            "Test response",
            "prev_hash_123"
        )

        # Same inputs should produce same hash
        hash2 = chain._compute_step_hash(
            "Test Step",
            "Test prompt",
            "Test response",
            "prev_hash_123"
        )
        self.assertEqual(hash1, hash2)

        # Different inputs should produce different hash
        hash3 = chain._compute_step_hash(
            "Test Step",
            "Different prompt",
            "Test response",
            "prev_hash_123"
        )
        self.assertNotEqual(hash1, hash3)

    @patch('llm_chain.grok_query')
    def test_kinetics_model(self, mock_grok):
        """Test Kinetics Model execution"""
        mock_grok.return_value = "Recommend 1000mg q12h based on CrCl 45 mL/min"

        chain = MultiLLMChain()
        result = chain._run_kinetics_model(
            self.patient_context,
            self.query,
            self.retrieved_cases,
            self.bayesian_result
        )

        self.assertEqual(result.step_name, "Kinetics Model")
        self.assertEqual(result.confidence, 0.85)  # Uses bayesian prob_safe
        self.assertIsNotNone(result.step_hash)
        self.assertEqual(result.prev_hash, "GENESIS_CHAIN")

    @patch('llm_chain.grok_query')
    def test_adversarial_model(self, mock_grok):
        """Test Adversarial Model execution"""
        mock_grok.return_value = "Risk of accumulation if renal function declines"

        chain = MultiLLMChain()
        # First run kinetics to establish chain
        with patch('llm_chain.grok_query', return_value="Kinetics response"):
            kinetics_step = chain._run_kinetics_model(
                self.patient_context, self.query,
                self.retrieved_cases, self.bayesian_result
            )

        # Now run adversarial
        mock_grok.return_value = "Risk of accumulation"
        adversarial_step = chain._run_adversarial_model(
            self.patient_context, self.query, kinetics_step
        )

        self.assertEqual(adversarial_step.step_name, "Adversarial Model")
        self.assertIsNone(adversarial_step.confidence)  # No confidence for risk analysis
        self.assertEqual(adversarial_step.prev_hash, kinetics_step.step_hash)

    @patch('llm_chain.grok_query')
    def test_full_chain_execution(self, mock_grok):
        """Test full 4-stage chain execution"""
        mock_responses = [
            "Kinetics: 1000mg q12h",
            "Adversarial: Risk of nephrotoxicity",
            "Literature: 2024 IDSA guidelines support AUC-based dosing",
            "Arbiter: Recommendation: 1000mg q12h / Safety: 85% / Rationale: Balanced approach"
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
        self.assertIn('chain_steps', result)
        self.assertIn('final_recommendation', result)
        self.assertIn('final_confidence', result)
        self.assertIn('chain_hash', result)
        self.assertIn('total_steps', result)

        # Check 4 steps executed
        self.assertEqual(result['total_steps'], 4)
        self.assertEqual(len(result['chain_steps']), 4)

        # Check step names
        step_names = [s['step'] for s in result['chain_steps']]
        self.assertIn('Kinetics Model', step_names)
        self.assertIn('Adversarial Model', step_names)
        self.assertIn('Literature Model', step_names)
        self.assertIn('Arbiter Model', step_names)

    @patch('llm_chain.grok_query')
    def test_chain_verification(self, mock_grok):
        """Test hash chain integrity verification"""
        mock_grok.return_value = "Test response"

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

    @patch('llm_chain.grok_query')
    def test_confidence_calculation(self, mock_grok):
        """Test final confidence score calculation"""
        mock_grok.return_value = "Test"

        chain = MultiLLMChain()
        result = chain.run_chain(
            self.patient_context,
            self.query,
            self.retrieved_cases,
            self.bayesian_result
        )

        # Confidence should be weighted average:
        # 30% kinetics (0.85) + 20% baseline (0.85) + 50% literature (0.90)
        expected = 0.85 * 0.30 + 0.85 * 0.20 + 0.90 * 0.50
        self.assertAlmostEqual(result['final_confidence'], expected, places=2)

    @patch('llm_chain.grok_query')
    def test_export_chain(self, mock_grok):
        """Test chain export for audit"""
        mock_grok.return_value = "Test"

        chain = MultiLLMChain()
        chain.run_chain(
            self.patient_context,
            self.query,
            self.retrieved_cases,
            self.bayesian_result
        )

        export = chain.export_chain()

        # Check export structure
        self.assertIn('chain_id', export)
        self.assertIn('genesis_hash', export)
        self.assertIn('steps', export)
        self.assertIn('total_steps', export)
        self.assertIn('chain_verified', export)

        # Check export data
        self.assertEqual(export['genesis_hash'], "GENESIS_CHAIN")
        self.assertEqual(export['total_steps'], 4)
        self.assertTrue(export['chain_verified'])

    @patch('llm_chain.grok_query')
    def test_run_multi_llm_decision_wrapper(self, mock_grok):
        """Test top-level wrapper function"""
        mock_grok.return_value = "Test response"

        result = run_multi_llm_decision(
            self.patient_context,
            self.query,
            self.retrieved_cases,
            self.bayesian_result
        )

        # Check wrapper adds chain_export
        self.assertIn('chain_export', result)
        self.assertIn('final_recommendation', result)
        self.assertIn('chain_steps', result)

    def test_empty_chain_verification(self):
        """Test verification of empty chain"""
        chain = MultiLLMChain()
        # Empty chain should be valid
        self.assertTrue(chain.verify_chain())

    @patch('llm_chain.grok_query')
    def test_hash_chain_linkage(self, mock_grok):
        """Test that each step links to previous hash"""
        mock_grok.return_value = "Test"

        chain = MultiLLMChain()
        chain.run_chain(
            self.patient_context,
            self.query,
            self.retrieved_cases,
            self.bayesian_result
        )

        # First step should link to genesis
        self.assertEqual(chain.chain_history[0].prev_hash, "GENESIS_CHAIN")

        # Each subsequent step should link to previous
        for i in range(1, len(chain.chain_history)):
            self.assertEqual(
                chain.chain_history[i].prev_hash,
                chain.chain_history[i-1].step_hash
            )


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

    def test_chain_step_optional_confidence(self):
        """Test ChainStep with None confidence"""
        step = ChainStep(
            step_name="Adversarial Model",
            prompt="Test",
            response="Test",
            timestamp="2025-11-18T12:00:00Z",
            prev_hash="abc",
            step_hash="def",
            confidence=None
        )

        self.assertIsNone(step.confidence)


class TestIntegration(unittest.TestCase):
    """Integration tests with mocked LLM"""

    @patch('llm_chain.grok_query')
    def test_realistic_clinical_scenario(self, mock_grok):
        """Test with realistic clinical data"""
        # Realistic responses from each model
        mock_grok.side_effect = [
            "Based on CrCl 45 mL/min, recommend vancomycin 1000mg q12h. Target trough 15-20 mcg/mL.",
            "Risk: Patient on lisinopril (ACE-I) increases AKI risk. Monitor Cr daily.",
            "2024 IDSA guidelines support AUC/MIC-based dosing. Consider AUC-guided dosing software.",
            "Recommendation: Vancomycin 1000mg q12h / Safety: 82% / Rationale: Balances efficacy with nephrotoxicity risk / Monitor: Trough in 48h, daily Cr"
        ]

        patient = {
            'age': 72,
            'gender': 'Male',
            'labs': 'Cr: 1.8 (was 2.9), WBC: 14.2, Temp: 38.9C'
        }
        query = "Safe vancomycin dose for septic shock with improving renal function?"

        cases = [
            {'summary': 'Elderly male with sepsis and AKI on vancomycin'},
            {'summary': 'Vancomycin dosing in reduced renal clearance'},
        ]

        bayesian = {
            'prob_safe': 0.82,
            'n_cases': 247,
            'ci_low': 0.75,
            'ci_high': 0.88
        }

        result = run_multi_llm_decision(patient, query, cases, bayesian)

        # Check all steps executed
        self.assertEqual(len(result['chain_steps']), 4)

        # Check final confidence is reasonable
        self.assertGreater(result['final_confidence'], 0.70)
        self.assertLess(result['final_confidence'], 0.95)

        # Check chain verified
        self.assertTrue(result['chain_export']['chain_verified'])


class TestHardenedChain(unittest.TestCase):
    """Test cases for hardened chain execution with timeouts and retries"""

    def setUp(self):
        """Set up test fixtures"""
        self.patient_context = {
            'age': 65,
            'gender': 'Female',
            'labs': 'Cr: 1.2, BUN: 22'
        }
        self.query = "Safe antibiotic for UTI?"
        self.retrieved_cases = [
            {'summary': 'UTI in elderly female'},
            {'summary': 'Antibiotic safety profile'}
        ]
        self.bayesian_result = {
            'prob_safe': 0.90,
            'n_cases': 200,
            'ci_low': 0.85,
            'ci_high': 0.94
        }

    @patch('llm_chain.grok_query')
    def test_stage_metadata_injection(self, mock_grok):
        """Test that stage metadata is properly injected"""
        mock_grok.return_value = "Test response"

        chain = MultiLLMChain()
        result = chain.run_chain(
            self.patient_context,
            self.query,
            self.retrieved_cases,
            self.bayesian_result
        )

        # Check that stage_metadata exists in result
        self.assertIn('stage_metadata', result)

        # Check metadata for all stages
        for stage_name in ['kinetics', 'adversarial', 'literature', 'arbiter']:
            self.assertIn(stage_name, result['stage_metadata'])
            metadata = result['stage_metadata'][stage_name]

            # Verify metadata structure
            self.assertIn('stage_name', metadata)
            self.assertIn('execution_time_ms', metadata)
            self.assertIn('retry_count', metadata)
            self.assertIn('timestamp', metadata)
            self.assertIn('timeout_configured', metadata)
            self.assertIn('max_retries_configured', metadata)

            # Verify metadata values
            self.assertEqual(metadata['stage_name'], stage_name)
            self.assertGreaterEqual(metadata['execution_time_ms'], 0)
            self.assertGreaterEqual(metadata['retry_count'], 0)

    @patch('llm_chain.grok_query')
    def test_performance_summary_in_export(self, mock_grok):
        """Test that chain export includes performance summary"""
        mock_grok.return_value = "Test response"

        chain = MultiLLMChain()
        chain.run_chain(
            self.patient_context,
            self.query,
            self.retrieved_cases,
            self.bayesian_result
        )

        export = chain.export_chain()

        # Check performance summary exists
        self.assertIn('performance_summary', export)
        perf = export['performance_summary']

        # Check performance summary structure
        self.assertIn('total_execution_time_ms', perf)
        self.assertIn('stage_timings', perf)
        self.assertIn('retries', perf)

        # Verify all stages are tracked
        for stage_name in ['kinetics', 'adversarial', 'literature', 'arbiter']:
            self.assertIn(stage_name, perf['stage_timings'])
            self.assertIn(stage_name, perf['retries'])

        # Total execution time should be sum of stage timings
        total = perf['total_execution_time_ms']
        stage_sum = sum(perf['stage_timings'].values())
        self.assertAlmostEqual(total, stage_sum, places=2)

    @patch('llm_chain.grok_query')
    def test_stage_results_with_contracts(self, mock_grok):
        """Test that stage results follow the StageResult contract"""
        mock_grok.return_value = "Test recommendation with risk of adverse events"

        chain = MultiLLMChain()
        chain.run_chain(
            self.patient_context,
            self.query,
            self.retrieved_cases,
            self.bayesian_result
        )

        # Check that stage_results are stored
        self.assertEqual(len(chain.stage_results), 4)

        # Verify each stage result follows the contract
        for stage_name, result in chain.stage_results.items():
            # Check all required fields exist
            self.assertIn('recommendation', result)
            self.assertIn('confidence', result)
            self.assertIn('reasoning', result)
            self.assertIn('contraindications', result)
            self.assertIn('timestamp', result)
            self.assertIn('stage_name', result)
            self.assertIn('_stage_metadata', result)

            # Verify field types
            self.assertIsInstance(result['recommendation'], str)
            self.assertIsInstance(result['confidence'], float)
            self.assertIsInstance(result['reasoning'], str)
            self.assertIsInstance(result['contraindications'], list)
            self.assertIsInstance(result['timestamp'], str)
            self.assertIsInstance(result['stage_name'], str)
            self.assertIsInstance(result['_stage_metadata'], dict)

            # Confidence should be between 0 and 1
            self.assertGreaterEqual(result['confidence'], 0.0)
            self.assertLessEqual(result['confidence'], 1.0)

    @patch('llm_chain.grok_query')
    def test_retry_logic_on_failure(self, mock_grok):
        """Test that stages retry on failure"""
        # First call fails, second succeeds
        mock_grok.side_effect = [
            Exception("Temporary failure"),
            "Success response",  # Kinetics retry
            "Adversarial response",
            "Literature response",
            "Arbiter response"
        ]

        chain = MultiLLMChain()
        result = chain.run_chain(
            self.patient_context,
            self.query,
            self.retrieved_cases,
            self.bayesian_result
        )

        # Chain should complete successfully
        self.assertEqual(result['total_steps'], 4)

        # Kinetics should show 1 retry
        kinetics_metadata = result['stage_metadata']['kinetics']
        self.assertEqual(kinetics_metadata['retry_count'], 1)

    @patch('llm_chain.grok_query')
    def test_contraindications_parsing(self, mock_grok):
        """Test that contraindications are extracted from responses"""
        mock_grok.side_effect = [
            "Kinetics: Dose 500mg. Caution with renal impairment.",
            "Adversarial: Risk of QT prolongation. Avoid in cardiac patients.",
            "Literature: Warning about drug interactions with warfarin.",
            "Arbiter: Final recommendation. Monitor for contraindications."
        ]

        chain = MultiLLMChain()
        chain.run_chain(
            self.patient_context,
            self.query,
            self.retrieved_cases,
            self.bayesian_result
        )

        # Check that contraindications were extracted
        for stage_name in ['kinetics', 'adversarial', 'literature', 'arbiter']:
            result = chain.stage_results[stage_name]
            self.assertGreater(len(result['contraindications']), 0)

    @patch('llm_chain.grok_query')
    def test_weighted_confidence_calculation(self, mock_grok):
        """Test that arbiter uses weighted confidence from all stages"""
        mock_grok.return_value = "Test response"

        chain = MultiLLMChain()
        result = chain.run_chain(
            self.patient_context,
            self.query,
            self.retrieved_cases,
            self.bayesian_result
        )

        # Get individual stage confidences
        kinetics_conf = chain.stage_results['kinetics']['confidence']
        adversarial_conf = chain.stage_results['adversarial']['confidence']
        literature_conf = chain.stage_results['literature']['confidence']

        # Expected weighted average: 30% kinetics + 20% adversarial + 50% literature
        expected_confidence = (
            kinetics_conf * 0.3 +
            adversarial_conf * 0.2 +
            literature_conf * 0.5
        )

        # Check arbiter confidence matches
        arbiter_conf = chain.stage_results['arbiter']['confidence']
        self.assertAlmostEqual(arbiter_conf, expected_confidence, places=2)


if __name__ == '__main__':
    unittest.main()
