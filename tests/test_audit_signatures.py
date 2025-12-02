import sys
import os
import unittest
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import shutil
from ecdsa import VerifyingKey, SECP256k1
from audit_log import log_decision, verify_audit_integrity, get_signing_key, SIGNING_KEY_FILE, DB_PATH, CHAIN_FILE

class TestAuditSignatures(unittest.TestCase):
    def setUp(self):
        # Clean up previous test artifacts
        if os.path.exists(DB_PATH): os.remove(DB_PATH)
        if os.path.exists(CHAIN_FILE): os.remove(CHAIN_FILE)
        # Do NOT remove signing key, as audit_log module has it cached in memory
        # if os.path.exists(SIGNING_KEY_FILE): os.remove(SIGNING_KEY_FILE)
        
    def tearDown(self):
        # Clean up
        if os.path.exists(DB_PATH): os.remove(DB_PATH)
        if os.path.exists(CHAIN_FILE): os.remove(CHAIN_FILE)
        # Do NOT remove signing key
        # if os.path.exists(SIGNING_KEY_FILE): os.remove(SIGNING_KEY_FILE)

    def test_signature_generation_and_verification(self):
        # 1. Generate a log entry
        entry = log_decision(
            mrn="TEST_MRN",
            patient_context="Test Context",
            query="Test Query",
            labs="Test Labs",
            response="Test Response",
            doctor="Dr. Test",
            bayesian_prob=0.95,
            latency=0.1
        )
        
        # 2. Verify signature exists
        self.assertIn("signature", entry)
        signature_hex = entry["signature"]
        self.assertTrue(len(signature_hex) > 0)
        
        # 3. Verify signature using public key
        sk = get_signing_key()
        vk = sk.get_verifying_key()
        
        entry_hash = entry["hash"]
        try:
            vk.verify(bytes.fromhex(signature_hex), entry_hash.encode())
            verified = True
        except Exception:
            verified = False
            
        self.assertTrue(verified, "Signature verification failed")
        
    def test_chain_integrity_with_signatures(self):
        # 1. Log multiple entries
        log_decision("MRN1", "C1", "Q1", "L1", "A1", "D1", 0.9, 0.1)
        log_decision("MRN2", "C2", "Q2", "L2", "A2", "D2", 0.8, 0.2)
        
        # 2. Verify integrity
        result = verify_audit_integrity()
        self.assertTrue(result["valid"])
        self.assertEqual(result["entries"], 2)

if __name__ == "__main__":
    unittest.main()
