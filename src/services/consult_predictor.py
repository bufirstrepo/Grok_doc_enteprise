"""
Consult Predictor Service
Predicts the next likely consult based on doctor-patient overlap graph.
"""

import hashlib
from typing import Optional, Dict, List
from dataclasses import dataclass
from ..graph.overlap_graph import OverlapGraph
from ..ingestion.fhir_loader import FHIRLoader, Practitioner, Patient

@dataclass
class ConsultPrediction:
    patient_id: str
    patient_name_masked: str
    reason: str
    urgency: str
    shared_with: List[str]

class ConsultPredictor:
    def __init__(self, loader: FHIRLoader, graph: OverlapGraph):
        self.loader = loader
        self.graph = graph
        self.doc_mapping = self._map_users_to_docs()

    def _map_users_to_docs(self) -> Dict[str, str]:
        """
        Maps system usernames to FHIR Practitioner IDs.
        In production, this would use LDAP/Auth0 attributes.
        For now, we deterministically map 'admin' and others to mock doctors.
        """
        mapping = {}
        docs = self.loader.get_practitioners()
        if not docs:
            return {}
            
        # Deterministic mapping for demo
        # 'admin' -> First doctor
        mapping['admin'] = docs[0].id
        
        # Map other potential users
        for i, doc in enumerate(docs[1:], 1):
            mapping[f"user{i}"] = doc.id
            
        return mapping

    def predict_next_consult(self, username: str) -> Optional[ConsultPrediction]:
        """
        Predicts the most relevant next consult for the logged-in user.
        Strategy:
        1. Find the Practitioner ID for the user.
        2. Find 'closest' colleagues in the graph (highest overlap).
        3. Identify patients treated by colleagues but NOT yet by this user (referral candidates) 
           OR patients shared with colleagues that have recent activity.
        
        For this MVP, we'll simplify:
        - Find top neighbor (colleague).
        - Pick a random patient shared with that colleague.
        """
        doc_id = self.doc_mapping.get(username)
        if not doc_id:
            return None

        # Get neighbors (colleagues with shared patients)
        neighbors = self.graph.get_neighbors(doc_id)
        if not neighbors:
            return None

        # Top colleague
        colleague_id, weight = neighbors[0]
        colleague = self.graph.get_metadata(colleague_id)
        
        # Find shared patients
        # In a real graph, we'd query edges. Here we scan encounters (inefficient but fine for MVP).
        my_patients = set()
        colleague_patients = set()
        
        for enc in self.loader.get_encounters():
            if enc.practitioner_id == doc_id:
                my_patients.add(enc.patient_id)
            if enc.practitioner_id == colleague_id:
                colleague_patients.add(enc.patient_id)
                
        shared = list(my_patients.intersection(colleague_patients))
        
        if not shared:
            return None
            
        # Pick one (most recent in real app)
        target_pat_id = shared[0]
        patient = self.loader.patients.get(target_pat_id)
        
        if not patient:
            return None

        # Mask Name (PHI Protection)
        masked_name = f"{patient.name[0]}. {patient.name.split()[-1][0]}." 
        
        return ConsultPrediction(
            patient_id=target_pat_id,
            patient_name_masked=masked_name,
            reason=f"Shared care with Dr. {colleague.name.split()[-1]} ({colleague.specialty})",
            urgency="Routine",
            shared_with=[colleague.name]
        )
