"""
Adverse Event Logging for FDA MDR Compliance (21 CFR Part 803)
Tracks misdiagnoses, software failures, and patient safety events
"""

import sqlite3
from datetime import datetime
from typing import Dict, Optional

DB_PATH = "adverse_events.db"

def init_adverse_event_db():
    """Initialize adverse event tracking database"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS adverse_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_date TEXT NOT NULL,
            report_date TEXT NOT NULL,
            severity TEXT NOT NULL,  -- 'Death', 'Serious Injury', 'Malfunction'
            event_description TEXT NOT NULL,
            patient_outcome TEXT,
            grok_recommendation TEXT,
            actual_diagnosis TEXT,
            reporter_name TEXT NOT NULL,
            mdr_reportable BOOLEAN DEFAULT 0,  -- FDA 30-day report required?
            mdr_report_number TEXT,
            corrective_action TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_adverse_event(
    event_description: str,
    severity: str,  # 'Death', 'Serious Injury', 'Malfunction'
    grok_recommendation: str,
    actual_diagnosis: str,
    reporter_name: str,
    patient_outcome: Optional[str] = None
) -> Dict:
    """
    Log adverse event per FDA MDR requirements
    
    Returns event ID and whether 30-day FDA report required
    """
    init_adverse_event_db()
    
    event_date = datetime.utcnow().isoformat() + "Z"
    
    # Determine if FDA MDR report required
    mdr_reportable = severity in ["Death", "Serious Injury"]
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("""
        INSERT INTO adverse_events
        (event_date, report_date, severity, event_description, 
         patient_outcome, grok_recommendation, actual_diagnosis, 
         reporter_name, mdr_reportable)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        event_date, event_date, severity, event_description,
        patient_outcome, grok_recommendation, actual_diagnosis,
        reporter_name, mdr_reportable
    ))
    
    event_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    if mdr_reportable:
        print(f"🔴 ALERT: FDA MDR Report Required within 30 days for Event #{event_id}")
    
    return {
        "event_id": event_id,
        "mdr_reportable": mdr_reportable,
        "report_deadline": "30 days from event" if mdr_reportable else None
    }

if __name__ == "__main__":
    # Example: log a software malfunction
    log_adverse_event(
        event_description="Grok recommended apixaban for patient with active GI bleed",
        severity="Serious Injury",
        grok_recommendation="Apixaban 5mg BID",
        actual_diagnosis="Contraindicated - active bleeding",
        reporter_name="Dr. Smith",
        patient_outcome="Patient required transfusion"
    )
