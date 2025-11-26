"""EHR Integration Layer - Epic, Cerner, and unified data model"""
from .base import EHRClient, PatientData, Observation, Medication, Condition
from .epic_fhir import EpicFHIRClient
from .cerner_fhir import CernerFHIRClient
from .unified_model import UnifiedPatientModel, normalize_patient_data

__all__ = [
    'EHRClient',
    'PatientData',
    'Observation', 
    'Medication',
    'Condition',
    'EpicFHIRClient',
    'CernerFHIRClient',
    'UnifiedPatientModel',
    'normalize_patient_data'
]
