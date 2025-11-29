import unittest
import time
from ai_tools_adapters import get_ai_tool
from hl7_transport import HL7MessageBuilder
from peer_review import PeerReviewSystem
from hcc_scoring import HCCEngine

class TestV30Features(unittest.TestCase):
    
    def test_ai_tools_factory(self):
        # Test factory creation and config
        config = {'enabled': True, 'api_key': '123', 'endpoint': 'https://api.aidoc.com'}
        adapter = get_ai_tool("Aidoc", config)
        self.assertIsNotNone(adapter)
        self.assertTrue(adapter.enabled)
        self.assertEqual(adapter.api_key, '123')
        
        # Test disabled state
        config['enabled'] = False
        adapter = get_ai_tool("Aidoc", config)
        res = adapter.analyze("path/to/file")
        self.assertEqual(res['error'], 'Disabled')

    def test_hl7_parsing(self):
        # Test ADT message parsing
        raw_msg = "MSH|^~\\&|Sender|Fac|Grok|Fac|20251128||ADT^A01|MSG001|P|2.5\rPID|||12345||Doe^John||19800101|M\r"
        parsed = HL7MessageBuilder.parse_message(raw_msg)
        self.assertEqual(parsed['type'], 'ADT^A01')
        self.assertEqual(parsed['mrn'], '12345')
        self.assertEqual(parsed['name'], 'Doe^John')
        
        # Test ACK generation
        ack = HL7MessageBuilder.create_ack(raw_msg)
        self.assertIn("MSA|AA|MSG001", ack)

    def test_peer_review_workflow(self):
        system = PeerReviewSystem()
        
        # Submit
        rid = system.submit_for_review({'mrn': '123'}, priority="High")
        self.assertEqual(len(system.queue), 1)
        self.assertEqual(system.queue[0]['priority'], 'High')
        
        # Approve
        success = system.approve_case(rid, "Dr. Test", "LGTM")
        self.assertTrue(success)
        self.assertEqual(len(system.queue), 0)
        self.assertEqual(len(system.history), 1)
        self.assertEqual(system.history[0]['status'], 'Approved')

    def test_hcc_expansion(self):
        engine = HCCEngine()
        # Check if simulated expansion worked (should have > 3000 codes)
        self.assertGreater(len(engine.icd_map), 3000)
        
        # Check specific generated code
        self.assertIn('E11.05', engine.icd_map) # Generated diabetes code
        self.assertIn('C99.9', engine.icd_map)  # Generated cancer code

if __name__ == '__main__':
    unittest.main()
