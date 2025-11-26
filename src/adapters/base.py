"""
Base AI Tool Adapter Interface

Abstract base class for hospital AI tool integrations.
All adapters must implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class AdapterStatus(Enum):
    """Adapter operational status"""
    READY = "ready"
    AUTHENTICATING = "authenticating"
    ERROR = "error"
    DISABLED = "disabled"
    RATE_LIMITED = "rate_limited"


class InsightCategory(Enum):
    """Categories of clinical insights"""
    DIAGNOSIS = "diagnosis"
    RISK_PREDICTION = "risk_prediction"
    IMAGING_FINDING = "imaging_finding"
    PATHOLOGY_FINDING = "pathology_finding"
    GENOMIC_FINDING = "genomic_finding"
    TREATMENT_RECOMMENDATION = "treatment_recommendation"
    DRUG_INTERACTION = "drug_interaction"
    WORKFLOW_ALERT = "workflow_alert"
    QUALITY_MEASURE = "quality_measure"


@dataclass
class AdapterResult:
    """Result from an AI tool adapter"""
    success: bool
    adapter_name: str
    category: str
    content: str
    confidence: float = 0.0
    raw_response: Optional[Dict] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    latency_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    
    def to_insight(self) -> Dict[str, Any]:
        """Convert to insight format for unified model"""
        return {
            'source': self.adapter_name,
            'type': self.category,
            'content': self.content,
            'confidence': self.confidence,
            'metadata': self.metadata
        }


class AIToolAdapter(ABC):
    """
    Abstract base class for hospital AI tool adapters.
    
    Each adapter connects to a specific hospital AI tool
    (Aidoc, PathAI, Tempus, etc.) and normalizes its output.
    """
    
    def __init__(
        self,
        api_endpoint: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
        enabled: bool = True
    ):
        self.api_endpoint = api_endpoint.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.enabled = enabled
        self._status = AdapterStatus.DISABLED if not enabled else AdapterStatus.READY
        self._session = None
    
    @property
    @abstractmethod
    def adapter_name(self) -> str:
        """Return adapter identifier"""
        pass
    
    @property
    @abstractmethod
    def supported_categories(self) -> List[InsightCategory]:
        """Return list of supported insight categories"""
        pass
    
    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with the AI tool's API.
        
        Returns:
            True if authentication successful
        """
        pass
    
    @abstractmethod
    def analyze(
        self,
        patient_data: Dict[str, Any],
        analysis_type: Optional[str] = None
    ) -> AdapterResult:
        """
        Perform analysis on patient data.
        
        Args:
            patient_data: Unified patient data context
            analysis_type: Specific analysis to perform
            
        Returns:
            AdapterResult with analysis output
        """
        pass
    
    @abstractmethod
    def get_insights(
        self,
        patient_id: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> List[AdapterResult]:
        """
        Retrieve existing insights for a patient.
        
        Args:
            patient_id: Patient identifier
            from_date: Start date filter
            to_date: End date filter
            
        Returns:
            List of AdapterResult objects
        """
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get adapter status"""
        return {
            'name': self.adapter_name,
            'status': self._status.value,
            'enabled': self.enabled,
            'endpoint': self.api_endpoint,
            'has_api_key': self.api_key is not None
        }
    
    def _get_session(self):
        """Get or create HTTP session"""
        if self._session is None:
            try:
                import requests
                self._session = requests.Session()
                self._session.headers.update({
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                })
                if self.api_key:
                    self._session.headers['Authorization'] = f'Bearer {self.api_key}'
            except ImportError:
                raise RuntimeError("requests library required")
        return self._session
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict:
        """Make API request"""
        import time
        start_time = time.time()
        
        session = self._get_session()
        url = f"{self.api_endpoint}/{endpoint}"
        
        try:
            response = session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            latency = (time.time() - start_time) * 1000
            result = response.json()
            result['_latency_ms'] = latency
            
            return result
            
        except Exception as e:
            self._status = AdapterStatus.ERROR
            raise RuntimeError(f"{self.adapter_name} API error: {e}")
