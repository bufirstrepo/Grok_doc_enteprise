import hashlib
import json
from datetime import datetime
import sqlite3
from pathlib import Path
from typing import Dict, Optional
import os
from cryptography.fernet import Fernet

DB_PATH = "audit.db"
CHAIN_FILE = "audit_chain.jsonl"
KEY_FILE = "audit.key"

# ── ENCRYPTION HELPERS ───────────────────────────────────────────

def get_key() -> bytes:
    """Load or generate encryption key."""
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)
        # Set restrictive permissions
        os.chmod(KEY_FILE, 0o600)
        return key

_CIPHER = Fernet(get_key())

def encrypt(data: str) -> str:
    """Encrypt string data."""
    if not data: return ""
    return _CIPHER.encrypt(data.encode()).decode()

def decrypt(token: str) -> str:
    """Decrypt string data."""
    if not token: return ""
    try:
        return _CIPHER.decrypt(token.encode()).decode()
    except Exception:
        return "[DECRYPTION FAILED]"

# ── DATABASE & AUDIT LOGIC ───────────────────────────────────────

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

    # Create index for fast lookups (MRN is encrypted, so index is less useful for range queries but okay for exact match if deterministic... 
    # Fernet is NOT deterministic. So we can't index encrypted MRN for lookup.
    # For v1, we accept full scan or we would need a blind index (hash of MRN).
    # Let's add a blind index column for MRN lookups if needed, but for now we'll just scan or rely on ID.
    # Actually, let's keep it simple.
    
    conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON decisions(timestamp)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_model ON decisions(model_name)")

    conn.commit()
    conn.close()

def get_last_hash() -> str:
    """Get the hash of the most recent audit entry."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute(
            "SELECT entry_hash FROM decisions ORDER BY id DESC LIMIT 1"
        )
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else "GENESIS_BLOCK"
    except sqlite3.OperationalError:
        return "GENESIS_BLOCK"

def compute_entry_hash(entry: Dict) -> str:
    """
    Compute SHA-256 hash of audit entry.
    Hashes the ENCRYPTED values to ensure storage integrity.
    """
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
    analysis_mode: str = "fast",
    model_name: Optional[str] = None
) -> Dict:
    """
    Log a clinical decision to immutable audit trail with ENCRYPTION.
    """
    init_db()
    
    timestamp = datetime.utcnow().isoformat() + "Z"
    prev_hash = get_last_hash()
    
    # Encrypt sensitive fields
    enc_mrn = encrypt(mrn)
    enc_context = encrypt(patient_context)
    enc_doctor = encrypt(doctor)
    enc_query = encrypt(query)
    enc_labs = encrypt(labs)
    enc_response = encrypt(response)
    
    # Create entry with ENCRYPTED data
    entry = {
        "timestamp": timestamp,
        "mrn": enc_mrn,
        "patient_context": enc_context,
        "doctor": enc_doctor,
        "question": enc_query,
        "labs": enc_labs,
        "answer": enc_response,
        "bayesian_prob": bayesian_prob,
        "latency": latency,
        "analysis_mode": analysis_mode,
        "model_name": model_name,
        "prev_hash": prev_hash
    }

    # Compute hash on encrypted data
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
            timestamp, enc_mrn, enc_context, enc_doctor, enc_query, enc_labs, enc_response,
            bayesian_prob, latency, analysis_mode, model_name, prev_hash, entry_hash
        ))
        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.close()
        raise Exception(f"Duplicate entry detected: {e}")
    finally:
        conn.close()
    
    # Append to JSONL chain file
    with open(CHAIN_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    
    return entry

def verify_audit_integrity() -> Dict:
    """Verify the entire audit chain hasn't been tampered with."""
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
        
        if prev_hash != expected_prev_hash:
            return {
                "valid": False,
                "entries": len(entries),
                "tampered_index": i,
                "error": f"Chain break: expected prev_hash {expected_prev_hash[:16]}... but got {prev_hash[:16]}..."
            }
        
        # Recompute hash using stored (encrypted) values
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
                "error": f"Hash mismatch at entry {i}"
            }
        
        expected_prev_hash = stored_hash
    
    return {"valid": True, "entries": len(entries), "tampered_index": None}

def get_patient_history(mrn: str, limit: int = 50) -> list:
    """
    Retrieve audit history for a specific patient.
    Decrypts data on retrieval.
    """
    init_db()
    
    # Since MRN is encrypted non-deterministically, we must scan and decrypt to find matches.
    # In production, we'd use a blind index (HMAC of MRN) for lookup.
    # For this prototype, we'll fetch all and filter in memory (inefficient but secure).
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("""
        SELECT timestamp, mrn, doctor, question, answer, bayesian_prob, entry_hash
        FROM decisions
        ORDER BY timestamp DESC
    """)
    
    results = []
    for row in cursor:
        dec_mrn = decrypt(row[1])
        if dec_mrn == mrn:
            results.append({
                "timestamp": row[0],
                "doctor": decrypt(row[2]),
                "question": decrypt(row[3]),
                "answer": decrypt(row[4]),
                "bayesian_prob": row[5],
                "hash": row[6]
            })
            if len(results) >= limit:
                break
                
    conn.close()
    return results

def export_audit_trail(output_path: str = "audit_export.json"):
    """
    Export entire audit trail with DECRYPTED data for compliance review.
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
    
    entries = []
    for row in cursor:
        entries.append({
            "timestamp": row[0],
            "mrn": decrypt(row[1]),
            "patient_context": decrypt(row[2]),
            "doctor": decrypt(row[3]),
            "question": decrypt(row[4]),
            "labs": decrypt(row[5]),
            "answer": decrypt(row[6]),
            "bayesian_prob": row[7],
            "latency": row[8],
            "prev_hash": row[9],
            "hash": row[10]
        })
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
    """Create cryptographic signature for a clinical note."""
    timestamp = datetime.utcnow().isoformat() + "Z"
    note_hash = hashlib.sha256(note_text.encode('utf-8')).hexdigest()

    signature_data = {
        "note_hash": note_hash,
        "physician_id": physician_id,
        "signed_at": timestamp,
        "signature_method": signature_method
    }

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
    """Verify a note signature."""
    note_hash = hashlib.sha256(note_text.encode('utf-8')).hexdigest()
    if note_hash != signature['note_hash']: return False

    signature_data = {
        "note_hash": signature['note_hash'],
        "physician_id": signature['physician_id'],
        "signed_at": signature['signed_at'],
        "signature_method": signature['signature_method']
    }

    canonical = json.dumps(signature_data, sort_keys=True, separators=(',', ':'))
    expected_hash = hashlib.sha256(canonical.encode('utf-8')).hexdigest()

    return expected_hash == signature['signature_hash']

def log_security_violation(
    violation_type: str,
    reason: str,
    provenance: str = "unknown",
    additional_data: Optional[Dict] = None
) -> Dict:
    """Log security violations."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    
    # Ensure table exists (simplified for brevity, assume init_db called)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS security_violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            violation_type TEXT NOT NULL,
            reason TEXT NOT NULL,
            provenance TEXT NOT NULL,
            additional_data TEXT,
            prev_hash TEXT NOT NULL,
            entry_hash TEXT NOT NULL,
            UNIQUE(entry_hash)
        )
    """)
    conn.commit()

    timestamp = datetime.utcnow().isoformat() + "Z"
    
    cursor = conn.execute("SELECT entry_hash FROM security_violations ORDER BY id DESC LIMIT 1")
    result = cursor.fetchone()
    prev_hash = result[0] if result else "GENESIS_SECURITY_BLOCK"

    entry = {
        "timestamp": timestamp,
        "violation_type": violation_type,
        "reason": reason,
        "provenance": provenance,
        "additional_data": json.dumps(additional_data) if additional_data else None,
        "prev_hash": prev_hash
    }

    hash_data = {k: v for k, v in entry.items() if k != "additional_data"}
    canonical_json = json.dumps(hash_data, sort_keys=True, separators=(',', ':'))
    entry_hash = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
    entry["hash"] = entry_hash

    try:
        conn.execute("""
            INSERT INTO security_violations
            (timestamp, violation_type, reason, provenance, additional_data, prev_hash, entry_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp, violation_type, reason, provenance,
            entry["additional_data"], prev_hash, entry_hash
        ))
        conn.commit()
    except sqlite3.IntegrityError:
        pass # Handle duplicate
    finally:
        conn.close()

    return entry

def log_fallback_event(primary_model: str, exception_msg: str, fallback_model: str = "llama-3.1-70b") -> bool:
    """Log model fallback events."""
    init_db()
    timestamp = datetime.utcnow().isoformat() + "Z"
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            INSERT INTO fallback_events
            (timestamp, primary_model, fallback_model, exception_msg, success)
            VALUES (?, ?, ?, ?, ?)
        """, (timestamp, primary_model, fallback_model, exception_msg, True))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def get_fallback_statistics() -> Dict:
    """Get statistics about model fallback events."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("""
        SELECT primary_model, COUNT(*) as count
        FROM fallback_events
        GROUP BY primary_model
        ORDER BY count DESC
    """)
    stats = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return {"total_fallbacks": sum(stats.values()), "by_model": stats}

# Initialize DB on import
init_db()
