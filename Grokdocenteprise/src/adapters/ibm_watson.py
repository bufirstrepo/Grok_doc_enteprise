"""
IBM Watson Health Adapter

Integrates with IBM Watson Health for clinical decision support.
"""

from typing import Dict, List, Optional, Any
from .base import AIToolAdapter, AdapterResult, InsightCategory, AdapterStatus


class IBMWatsonAdapter(AIToolAdapter):
    """Adapter for IBM Watson Health clinical decision support"""
    
    @property
    def adapter_name(self) -> str:
        return "ibm_watson"
    
    @property
    def supported_categories(self) -> List[InsightCategory]:
        return [
            InsightCategory.DIAGNOSIS,
            InsightCategory.TREATMENT_RECOMMENDATION,
            InsightCategory.DRUG_INTERACTION
        ]
    
    def authenticate(self) -> bool:
        if not self.api_key:
            self._status = AdapterStatus.ERROR
            return False
        try:
            response = self._make_request('GET', 'v1/status')
            self._status = AdapterStatus.READY
            return response.get('status') == 'active'
        except:
            self._status = AdapterStatus.ERROR
            return False
    
    def analyze(self, patient_data: Dict[str, Any], analysis_type: Optional[str] = None) -> AdapterResult:
        if not self.enabled:
            return AdapterResult(success=False, adapter_name=self.adapter_name, category="diagnosis", content="", error_message="Disabled")
        
        try:
            response = self._make_request('POST', 'v1/clinical-insights', data={
                'patient_data': patient_data,
                'analysis_type': analysis_type or 'comprehensive'
            })
            return AdapterResult(
                success=True,
                adapter_name=self.adapter_name,
                category="diagnosis",
                content=response.get('insights', 'No insights'),
                confidence=response.get('confidence', 0.0),
                raw_response=response
            )
        except Exception as e:
            return AdapterResult(success=False, adapter_name=self.adapter_name, category="diagnosis", content="", error_message=str(e))
    
    def get_insights(self, patient_id: str, from_date: Optional[str] = None, to_date: Optional[str] = None) -> List[AdapterResult]:
        return []
