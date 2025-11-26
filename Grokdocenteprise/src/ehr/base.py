"""
Base EHR Client Interface

Abstract base class for EHR system integrations.
Implementations: EpicFHIRClient, CernerFHIRClient
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class ObservationCategory(Enum):
    """Categories of clinical observations"""
    VITAL_SIGNS = "vital-signs"
    LABORATORY = "laboratory"
    IMAGING = "imaging"
    PROCEDURE = "procedure"
    SURVEY = "survey"
    EXAM = "exam"
    THERAPY = "therapy"
    ACTIVITY = "activity"


@dataclass
class Observation:
    """Clinical observation (lab result, vital sign, etc.)"""
    id: str
    code: str
    code_system: str
    display: str
    value: Optional[Any] = None
    unit: Optional[str] = None
    reference_range_low: Optional[float] = None
    reference_range_high: Optional[float] = None
    interpretation: Optional[str] = None  # H, L, N, A, etc.
    category: Optional[str] = None
    effective_datetime: Optional[str] = None
    issued: Optional[str] = None
    status: str = "final"
    
    def is_abnormal(self) -> bool:
        """Check if observation is outside normal range"""
        if self.interpretation:
            return self.interpretation.upper() in ['H', 'L', 'HH', 'LL', 'A', 'AA']
        if self.value is not None and isinstance(self.value, (int, float)):
            if self.reference_range_low and self.value < self.reference_range_low:
                return True
            if self.reference_range_high and self.value > self.reference_range_high:
                return True
        return False


@dataclass
class Medication:
    """Medication prescription/administration"""
    id: str
    code: str
    code_system: str
    display: str
    dose_value: Optional[float] = None
    dose_unit: Optional[str] = None
    route: Optional[str] = None
    frequency: Optional[str] = None
    status: str = "active"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    prescriber: Optional[str] = None
    instructions: Optional[str] = None


@dataclass
class Condition:
    """Clinical condition/diagnosis"""
    id: str
    code: str
    code_system: str
    display: str
    clinical_status: str = "active"  # active, recurrence, relapse, inactive, remission, resolved
    verification_status: str = "confirmed"  # unconfirmed, provisional, differential, confirmed, refuted
    severity: Optional[str] = None
    onset_datetime: Optional[str] = None
    abatement_datetime: Optional[str] = None
    category: Optional[str] = None  # problem-list-item, encounter-diagnosis


@dataclass
class Encounter:
    """Clinical encounter/visit"""
    id: str
    type: str
    status: str
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None
    reason: Optional[str] = None
    location: Optional[str] = None
    practitioner: Optional[str] = None


@dataclass
class PatientData:
    """Patient demographic and clinical data"""
    id: str
    mrn: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    birth_date: Optional[str] = None
    gender: Optional[str] = None
    deceased: bool = False
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    
    observations: List[Observation] = field(default_factory=list)
    medications: List[Medication] = field(default_factory=list)
    conditions: List[Condition] = field(default_factory=list)
    encounters: List[Encounter] = field(default_factory=list)
    
    allergies: List[str] = field(default_factory=list)
    
    source_system: str = "unknown"
    retrieved_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    
    def get_age(self) -> Optional[int]:
        """Calculate patient age from birth date"""
        if not self.birth_date:
            return None
        try:
            birth = datetime.fromisoformat(self.birth_date.replace('Z', '+00:00'))
            today = datetime.now()
            age = today.year - birth.year
            if (today.month, today.day) < (birth.month, birth.day):
                age -= 1
            return age
        except:
            return None
    
    def get_active_medications(self) -> List[Medication]:
        """Get currently active medications"""
        return [m for m in self.medications if m.status == "active"]
    
    def get_active_conditions(self) -> List[Condition]:
        """Get currently active conditions"""
        return [c for c in self.conditions if c.clinical_status == "active"]
    
    def get_recent_labs(self, hours: int = 24) -> List[Observation]:
        """Get lab results from the last N hours"""
        cutoff = datetime.utcnow()
        recent = []
        for obs in self.observations:
            if obs.category == ObservationCategory.LABORATORY.value:
                if obs.effective_datetime:
                    try:
                        obs_time = datetime.fromisoformat(obs.effective_datetime.replace('Z', '+00:00'))
                        if (cutoff - obs_time).total_seconds() < hours * 3600:
                            recent.append(obs)
                    except:
                        recent.append(obs)
        return recent
    
    def get_abnormal_observations(self) -> List[Observation]:
        """Get all abnormal observations"""
        return [o for o in self.observations if o.is_abnormal()]


class EHRClient(ABC):
    """
    Abstract base class for EHR system clients.
    
    Implementations must provide:
    - FHIR R4 patient data retrieval
    - OAuth2 authentication
    - Error handling and retry logic
    """
    
    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with the EHR system.
        
        Returns:
            True if authentication successful
        """
        pass
    
    @abstractmethod
    def get_patient(self, patient_id: str) -> Optional[PatientData]:
        """
        Get patient demographic data.
        
        Args:
            patient_id: Patient FHIR ID or MRN
            
        Returns:
            PatientData or None if not found
        """
        pass
    
    @abstractmethod
    def get_observations(
        self,
        patient_id: str,
        category: Optional[str] = None,
        code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Observation]:
        """
        Get patient observations (labs, vitals, etc.)
        
        Args:
            patient_id: Patient FHIR ID
            category: Filter by category (vital-signs, laboratory, etc.)
            code: Filter by LOINC code
            start_date: Filter by date range start
            end_date: Filter by date range end
            
        Returns:
            List of Observation objects
        """
        pass
    
    @abstractmethod
    def get_medications(
        self,
        patient_id: str,
        status: Optional[str] = None
    ) -> List[Medication]:
        """
        Get patient medications.
        
        Args:
            patient_id: Patient FHIR ID
            status: Filter by status (active, completed, etc.)
            
        Returns:
            List of Medication objects
        """
        pass
    
    @abstractmethod
    def get_conditions(
        self,
        patient_id: str,
        clinical_status: Optional[str] = None
    ) -> List[Condition]:
        """
        Get patient conditions/diagnoses.
        
        Args:
            patient_id: Patient FHIR ID
            clinical_status: Filter by status (active, resolved, etc.)
            
        Returns:
            List of Condition objects
        """
        pass
    
    @abstractmethod
    def get_full_patient_context(self, patient_id: str) -> PatientData:
        """
        Get complete patient context including all clinical data.
        
        Args:
            patient_id: Patient FHIR ID or MRN
            
        Returns:
            PatientData with all observations, medications, conditions
        """
        pass
    
    @abstractmethod
    def search_patients(
        self,
        name: Optional[str] = None,
        mrn: Optional[str] = None,
        birth_date: Optional[str] = None
    ) -> List[PatientData]:
        """
        Search for patients by criteria.
        
        Args:
            name: Patient name (partial match)
            mrn: Medical Record Number
            birth_date: Date of birth (YYYY-MM-DD)
            
        Returns:
            List of matching PatientData objects
        """
        pass
    
    @property
    @abstractmethod
    def is_authenticated(self) -> bool:
        """Check if client is currently authenticated"""
        pass
    
    @property
    @abstractmethod
    def ehr_type(self) -> str:
        """Return EHR system type (epic, cerner, etc.)"""
        pass
