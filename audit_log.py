import hashlib
import json
from datetime import datetime
import sqlite3
from pathlib import Path
from typing import Dict, Optional

DB_PATH = "audit.db"
CHAIN_FILE = "audit_chain.jsonl"  # JSONL for proper data structure

def init_db():
    """Initialize SQLite database with proper schema."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            mrn TEXT NOT NULL,
            patient_context TEXT,
            doctor TEXT NOT NULL,
            question TEXT NOT NULL,
            labs TEXT,
            answer TEXT NOT NULL,
            bayesian_prob REAL,
            latency REAL,
            analysis_mode TEXT DEFAULT 'fast',
            model_name TEXT,
            prev_hash TEXT NOT NULL,
            entry_hash TEXT NOT NULL,
            UNIQUE(entry_hash)
        )
    """)

    # Create fallback events table for model routing audit
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fallback_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            primary_model TEXT NOT NULL,
            fallback_model TEXT,
            exception_msg TEXT,
            success BOOLEAN
        )
    """)

    # Create index for fast MRN lookups
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mrn ON decisions(mrn)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON decisions(timestamp)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_model ON decisions(model_name)")

    conn.commit()
    conn.close()

def get_last_hash() -> str:
    """
    Get the hash of the most recent audit entry.
    This creates the blockchain-style chain.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute(
            "SELECT entry_hash FROM decisions ORDER BY id DESC LIMIT 1"
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        else:
            return "GENESIS_BLOCK"  # First entry in chain
    except sqlite3.OperationalError:
        return "GENESIS_BLOCK"

def compute_entry_hash(entry: Dict) -> str:
    """
    Compute SHA-256 hash of audit entry.
    Hash includes previous hash to create blockchain-style chain.
    """
    # Canonical ordering ensures consistent hashes
    hash_data = {
        "timestamp": entry["timestamp"],
        "mrn": entry["mrn"],
        "doctor": entry["doctor"],
        "question": entry["question"],
        "answer": entry["answer"],
        "prev_hash": entry["prev_hash"]
    }
    
    canonical_json = json.dumps(hash_data, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()

def log_decision(
    mrn: str,
    patient_context: str,
    query: str,
    labs: str,
    response: str,
    doctor: str,
    bayesian_prob: float,
    latency: float,
    analysis_mode: str = "fast",  # NEW in v2.0: "fast" or "chain"
    model_name: Optional[str] = None  # NEW: Track which model was used
) -> Dict:
    """
    Log a clinical decision to immutable audit trail.
    
    Returns:
        Dict containing the logged entry with hash
    """
    init_db()
    
    timestamp = datetime.utcnow().isoformat() + "Z"
    prev_hash = get_last_hash()
    
    # Create entry
    entry = {
        "timestamp": timestamp,
        "mrn": mrn,
        "patient_context": patient_context,
        "doctor": doctor,
        "question": query,
        "labs": labs,
        "answer": response,
        "bayesian_prob": bayesian_prob,
        "latency": latency,
        "analysis_mode": analysis_mode,  # NEW in v2.0
        "model_name": model_name,  # NEW: Model tracking
        "prev_hash": prev_hash
    }

    # Compute hash (includes prev_hash for chain integrity)
    entry_hash = compute_entry_hash(entry)
    entry["hash"] = entry_hash

    # Write to SQLite
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            INSERT INTO decisions
            (timestamp, mrn, patient_context, doctor, question, labs, answer,
             bayesian_prob, latency, analysis_mode, model_name, prev_hash, entry_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp, mrn, patient_context, doctor, query, labs, response,
            bayesian_prob, latency, analysis_mode, model_name, prev_hash, entry_hash
        ))
        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.close()
        raise Exception(f"Duplicate entry detected: {e}")
    finally:
        conn.close()
    
    # Append to JSONL chain file (append-only, human-readable backup)
    with open(CHAIN_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    
    return entry

def verify_audit_integrity() -> Dict:
    """
    Verify the entire audit chain hasn't been tampered with.
    
    Returns:
        Dict with 'valid' (bool), 'entries' (int), 'tampered_index' (int or None)
    """
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("""
        SELECT id, timestamp, mrn, patient_context, doctor, question, labs, 
               answer, bayesian_prob, latency, prev_hash, entry_hash
        FROM decisions
        ORDER BY id ASC
    """)
    
    entries = cursor.fetchall()
    conn.close()
    
    if not entries:
        return {"valid": True, "entries": 0, "tampered_index": None}
    
    expected_prev_hash = "GENESIS_BLOCK"
    
    for i, row in enumerate(entries):
        (entry_id, timestamp, mrn, patient_context, doctor, question, labs, 
         answer, bayesian_prob, latency, prev_hash, stored_hash) = row
        
        # Check chain link
        if prev_hash != expected_prev_hash:
            return {
                "valid": False,
                "entries": len(entries),
                "tampered_index": i,
                "error": f"Chain break: expected prev_hash {expected_prev_hash[:16]}... but got {prev_hash[:16]}..."
            }
        
        # Recompute hash
        entry = {
            "timestamp": timestamp,
            "mrn": mrn,
            "doctor": doctor,
            "question": question,
            "answer": answer,
            "prev_hash": prev_hash
        }
        
        computed_hash = compute_entry_hash(entry)
        
        if computed_hash != stored_hash:
            return {
                "valid": False,
                "entries": len(entries),
                "tampered_index": i,
                "error": f"Hash mismatch at entry {i}: data has been modified"
            }
        
        expected_prev_hash = stored_hash
    
    return {
        "valid": True,
        "entries": len(entries),
        "tampered_index": None
    }

def get_patient_history(mrn: str, limit: int = 50) -> list:
    """
    Retrieve audit history for a specific patient.
    
    Args:
        mrn: Medical Record Number
        limit: Maximum number of entries to return
    
    Returns:
        List of audit entries for the patient
    """
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("""
        SELECT timestamp, doctor, question, answer, bayesian_prob, entry_hash
        FROM decisions
        WHERE mrn = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (mrn, limit))
    
    results = cursor.fetchall()
    conn.close()
    
    return [
        {
            "timestamp": row[0],
            "doctor": row[1],
            "question": row[2],
            "answer": row[3],
            "bayesian_prob": row[4],
            "hash": row[5]
        }
        for row in results
    ]

def export_audit_trail(output_path: str = "audit_export.json"):
    """
    Export entire audit trail for regulatory compliance.
    Includes integrity verification.
    """
    integrity = verify_audit_integrity()
    
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("""
        SELECT timestamp, mrn, patient_context, doctor, question, labs, 
               answer, bayesian_prob, latency, prev_hash, entry_hash
        FROM decisions
        ORDER BY id ASC
    """)
    
    entries = [
        {
            "timestamp": row[0],
            "mrn": row[1],
            "patient_context": row[2],
            "doctor": row[3],
            "question": row[4],
            "labs": row[5],
            "answer": row[6],
            "bayesian_prob": row[7],
            "latency": row[8],
            "prev_hash": row[9],
            "hash": row[10]
        }
        for row in cursor.fetchall()
    ]
    conn.close()
    
    export_data = {
        "export_timestamp": datetime.utcnow().isoformat() + "Z",
        "integrity_check": integrity,
        "total_entries": len(entries),
        "entries": entries
    }
    
    with open(output_path, "w") as f:
        json.dump(export_data, f, indent=2)
    
    return export_data

def sign_note(note_text: str, physician_id: str, signature_method: str = "PIN") -> Dict:
    """
    Create cryptographic signature for a clinical note (for mobile co-pilot)

    Args:
        note_text: The clinical note text (SOAP note, etc.)
        physician_id: Physician identifier
        signature_method: "PIN", "biometric", or "certificate"

    Returns:
        {
            "signature_hash": str,     # SHA-256 of note + physician + timestamp
            "physician_id": str,
            "signed_at": str,          # ISO timestamp
            "note_hash": str,          # Hash of note content only
            "signature_method": str
        }
    """
    timestamp = datetime.utcnow().isoformat() + "Z"

    # Hash the note content
    note_hash = hashlib.sha256(note_text.encode('utf-8')).hexdigest()

    # Create signature data
    signature_data = {
        "note_hash": note_hash,
        "physician_id": physician_id,
        "signed_at": timestamp,
        "signature_method": signature_method
    }

    # Compute signature hash
    canonical = json.dumps(signature_data, sort_keys=True, separators=(',', ':'))
    signature_hash = hashlib.sha256(canonical.encode('utf-8')).hexdigest()

    return {
        "signature_hash": signature_hash,
        "physician_id": physician_id,
        "signed_at": timestamp,
        "note_hash": note_hash,
        "signature_method": signature_method
    }

def verify_note_signature(note_text: str, signature: Dict) -> bool:
    """
    Verify a note signature hasn't been tampered with

    Args:
        note_text: The clinical note text
        signature: Signature dict from sign_note()

    Returns:
        True if signature is valid, False otherwise
    """
    # Recompute note hash
    note_hash = hashlib.sha256(note_text.encode('utf-8')).hexdigest()

    # Check if note hash matches signature
    if note_hash != signature['note_hash']:
        return False

    # Recompute signature hash
    signature_data = {
        "note_hash": signature['note_hash'],
        "physician_id": signature['physician_id'],
        "signed_at": signature['signed_at'],
        "signature_method": signature['signature_method']
    }

    canonical = json.dumps(signature_data, sort_keys=True, separators=(',', ':'))
    expected_hash = hashlib.sha256(canonical.encode('utf-8')).hexdigest()

    return expected_hash == signature['signature_hash']

def log_fallback_event(
    primary_model: str,
    exception_msg: str,
    fallback_model: Optional[str] = "llama-3.1-70b",
    success: bool = False
) -> Dict:
    """
    Log a model fallback event for tribunal experiments.

    Args:
        primary_model: The model that failed
        exception_msg: The exception message
        fallback_model: The fallback model used (if any)
        success: Whether fallback succeeded

    Returns:
        dict: Logged event details
    """
    init_db()

    timestamp = datetime.utcnow().isoformat() + "Z"

    event = {
        "timestamp": timestamp,
        "primary_model": primary_model,
        "fallback_model": fallback_model,
        "exception_msg": exception_msg,
        "success": success
    }

    # Write to SQLite
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            INSERT INTO fallback_events
            (timestamp, primary_model, fallback_model, exception_msg, success)
            VALUES (?, ?, ?, ?, ?)
        """, (
            timestamp, primary_model, fallback_model, exception_msg, success
        ))
        conn.commit()
    finally:
        conn.close()

    print(f"⚠️  Fallback event logged: {primary_model} → {fallback_model}")

    return event


def get_fallback_statistics() -> Dict:
    """
    Get statistics on model fallback events.

    Returns:
        dict: Fallback statistics by model
    """
    init_db()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("""
        SELECT primary_model, COUNT(*) as fallback_count,
               SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count
        FROM fallback_events
        GROUP BY primary_model
    """)

    stats = {}
    for row in cursor.fetchall():
        model, total, successes = row
        stats[model] = {
            "total_fallbacks": total,
            "successful_fallbacks": successes,
            "failed_fallbacks": total - successes
        }

    conn.close()

    return stats


# Initialize DB on import
init_db()
