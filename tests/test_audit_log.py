"""
Basic tests for audit logging functionality with Encryption
"""

import os
import tempfile
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from audit_log import log_decision, verify_audit_integrity, get_patient_history

def test_audit_logging():
    """Test basic audit log creation and verification"""
    
    # Create temporary database
    import audit_log
    audit_log.DB_PATH = tempfile.mktemp(suffix=".db")
    audit_log.CHAIN_FILE = tempfile.mktemp(suffix=".jsonl")
    audit_log.KEY_FILE = tempfile.mktemp(suffix=".key")
    
    # Log a decision
    entry = log_decision(
        mrn="TEST123",
        patient_context="Test patient",
        query="Test query",
        labs="Test labs",
        response="Test response",
        doctor="Dr. Test",
        bayesian_prob=0.95,
        latency=2.1
    )
    
    # Verify Encryption: Stored fields should NOT match plaintext
    assert entry["mrn"] != "TEST123"
    assert entry["doctor"] != "Dr. Test"
    assert "hash" in entry
    assert entry["prev_hash"] == "GENESIS_BLOCK"
    
    # Verify Integrity (should pass on encrypted data)
    result = verify_audit_integrity()
    assert result["valid"] == True
    assert result["entries"] == 1
    
    # Verify Decryption via History Lookup
    history = get_patient_history("TEST123")
    assert len(history) == 1
    assert history[0]["doctor"] == "Dr. Test"
    assert history[0]["question"] == "Test query"
    
    # Clean up
    if os.path.exists(audit_log.DB_PATH): os.remove(audit_log.DB_PATH)
    if os.path.exists(audit_log.CHAIN_FILE): os.remove(audit_log.CHAIN_FILE)
    if os.path.exists(audit_log.KEY_FILE): os.remove(audit_log.KEY_FILE)
    
    print("✓ Audit log tests passed (Encryption Verified)")

if __name__ == "__main__":
    test_audit_logging()
