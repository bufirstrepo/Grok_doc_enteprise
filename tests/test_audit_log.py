# Create tests directory
mkdir -p tests

# Create test file
cat > tests/test_audit_log.py << 'EOF'
"""
Basic tests for audit logging functionality
"""

import os
import tempfile
from audit_log import log_decision, verify_audit_integrity

def test_audit_logging():
    """Test basic audit log creation and verification"""
    
    # Create temporary database
    import audit_log
    audit_log.DB_PATH = tempfile.mktemp(suffix=".db")
    audit_log.CHAIN_FILE = tempfile.mktemp(suffix=".jsonl")
    
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
    
    assert entry["mrn"] == "TEST123"
    assert "hash" in entry
    assert entry["prev_hash"] == "GENESIS_BLOCK"
    
    # Verify integrity
    result = verify_audit_integrity()
    assert result["valid"] == True
    assert result["entries"] == 1
    
    # Clean up
    os.remove(audit_log.DB_PATH)
    os.remove(audit_log.CHAIN_FILE)
    
    print("✓ Audit log tests passed")

if __name__ == "__main__":
    test_audit_logging()
EOF
