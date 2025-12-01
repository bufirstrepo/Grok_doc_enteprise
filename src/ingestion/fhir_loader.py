"""
FHIR Data Loader
Simulates bulk export from Epic/Cerner for graph construction.
"""

from typing import List, Dict, Any
from dataclasses import dataclass
import random
import uuid

@dataclass
class Practitioner:
    id: str
    name: str
    specialty: str
    department: str

@dataclass
class Patient:
    id: str
    name: str
    conditions: List[str]

@dataclass
class Encounter:
    id: str
    patient_id: str
    practitioner_id: str
    date: str
    type: str

class FHIRLoader:
    """
    Simulates loading data from a FHIR Bulk Export or HL7 feed.
    In a real scenario, this would parse NDJSON files from an S3 bucket or local directory.
    """

    def __init__(self):
        self.practitioners: Dict[str, Practitioner] = {}
        self.patients: Dict[str, Patient] = {}
        self.encounters: List[Encounter] = []

    def load_mock_data(self, num_doctors=50, num_patients=500, num_encounters=2000):
        """Generates synthetic data for testing the graph index."""
        
        specialties = [
            "Cardiology", "Oncology", "Internal Medicine", "Neurology", 
            "Emergency", "Critical Care", "Infectious Disease", "Nephrology"
        ]
        
        # Generate Doctors
        for i in range(num_doctors):
            doc_id = f"DOC-{i:03d}"
            spec = random.choice(specialties)
            self.practitioners[doc_id] = Practitioner(
                id=doc_id,
                name=f"Dr. {uuid.uuid4().hex[:6]}",
                specialty=spec,
                department=f"{spec} Dept"
            )

        # Generate Patients
        for i in range(num_patients):
            pat_id = f"PAT-{i:04d}"
            self.patients[pat_id] = Patient(
                id=pat_id,
                name=f"Patient {uuid.uuid4().hex[:6]}",
                conditions=["Hypertension", "Diabetes"] # Simplified
            )

        # Generate Encounters (Edges)
        doc_ids = list(self.practitioners.keys())
        pat_ids = list(self.patients.keys())
        
        for i in range(num_encounters):
            self.encounters.append(Encounter(
                id=f"ENC-{i:05d}",
                patient_id=random.choice(pat_ids),
                practitioner_id=random.choice(doc_ids),
                date="2025-01-01",
                type="Inpatient"
            ))
            
        print(f"Loaded {len(self.practitioners)} doctors, {len(self.patients)} patients, {len(self.encounters)} encounters.")

    def get_practitioners(self) -> List[Practitioner]:
        return list(self.practitioners.values())

    def get_patients(self) -> List[Patient]:
        return list(self.patients.values())

    def get_encounters(self) -> List[Encounter]:
        return self.encounters
