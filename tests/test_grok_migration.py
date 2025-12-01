import unittest
import os
import json
from unittest.mock import patch, MagicMock
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from local_inference import get_config, grok_query

class TestGrokMigration(unittest.TestCase):
    def setUp(self):
        self.config_path = os.path.join(os.path.dirname(__file__), '../config/hospital_config.json')
        with open(self.config_path, 'r') as f:
            self.config = json.load(f)

    def test_default_model_is_grok_beta(self):
        """Verify default model is grok-beta"""
        self.assertEqual(self.config['llm_config']['default_model'], 'grok-beta')

    def test_grok_beta_params(self):
        """Verify grok-beta parameters"""
        grok_config = self.config['ai_tools']['grok-beta']
        self.assertEqual(grok_config['max_tokens'], 8192)
        self.assertEqual(grok_config['temperature'], 0.0)
        self.assertEqual(grok_config['backend'], 'xai_api')

    def test_vllm_removed(self):
        """Verify vLLM backend is removed from local_inference.py"""
        # We can check this by trying to import vllm_engine and asserting ImportError
        with self.assertRaises(ImportError):
            import vllm_engine

    @patch('local_inference.get_llm')
    def test_query_grok_beta(self, mock_get_llm):
        """Verify grok_query calls xAI client for grok-beta"""
        mock_client = MagicMock()
        mock_get_llm.return_value = {"type": "xai_api", "name": "grok-beta", "engine": mock_client}
        
        # Mock response
        mock_client.query_xai.return_value = "Test response"

        response = grok_query("Test prompt", model_name="grok-beta")
        
        self.assertEqual(response, "Test response")
        mock_client.query_xai.assert_called_once()
        call_args = mock_client.query_xai.call_args[1]
        self.assertEqual(call_args['model'], 'grok-beta')
        self.assertEqual(call_args['max_tokens'], 8192)
        self.assertEqual(call_args['temperature'], 0.0)

if __name__ == '__main__':
    unittest.main()
