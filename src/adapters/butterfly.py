"""
Butterfly iQ Adapter

Integrates with Butterfly Network's AI-powered ultrasound platform.
"""

from typing import Dict, List, Optional, Any
from .base import AIToolAdapter, AdapterResult, InsightCategory, AdapterStatus


class ButterflyAdapter(AIToolAdapter):
    """Adapter for Butterfly iQ portable ultrasound with AI guidance"""
    
    @property
    def adapter_name(self) -> str:
        return "butterfly_iq"
    
    @property
    def supported_categories(self) -> List[InsightCategory]:
        return [
            InsightCategory.IMAGING_FINDING,
            InsightCategory.DIAGNOSIS
        ]
    
    def authenticate(self) -> bool:
        if not self.api_key:
            self._status = AdapterStatus.ERROR
            return False
        try:
            response = self._make_request('GET', 'v1/auth/status')
            self._status = AdapterStatus.READY
            return response.get('authenticated', False)
        except:
            self._status = AdapterStatus.ERROR
            return False
    
    def analyze(self, patient_data: Dict[str, Any], analysis_type: Optional[str] = None) -> AdapterResult:
        if not self.enabled:
            return AdapterResult(success=False, adapter_name=self.adapter_name, category="imaging_finding", content="", error_message="Disabled")
        
        try:
            response = self._make_request('POST', 'v1/analyze', data={'patient_id': patient_data.get('patient_id')})
            return AdapterResult(
                success=True,
                adapter_name=self.adapter_name,
                category="imaging_finding",
                content=response.get('findings', 'No findings'),
                confidence=response.get('confidence', 0.0),
                raw_response=response
            )
        except Exception as e:
            return AdapterResult(success=False, adapter_name=self.adapter_name, category="imaging_finding", content="", error_message=str(e))
    
    def get_insights(self, patient_id: str, from_date: Optional[str] = None, to_date: Optional[str] = None) -> List[AdapterResult]:
        return []
