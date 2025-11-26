"""
Keragon Adapter

Integrates with Keragon healthcare workflow automation platform.
"""

from typing import Dict, List, Optional, Any
from .base import AIToolAdapter, AdapterResult, InsightCategory, AdapterStatus


class KeragonAdapter(AIToolAdapter):
    """Adapter for Keragon healthcare workflow automation"""
    
    @property
    def adapter_name(self) -> str:
        return "keragon"
    
    @property
    def supported_categories(self) -> List[InsightCategory]:
        return [
            InsightCategory.WORKFLOW_ALERT,
            InsightCategory.QUALITY_MEASURE
        ]
    
    def authenticate(self) -> bool:
        if not self.api_key:
            self._status = AdapterStatus.ERROR
            return False
        try:
            response = self._make_request('GET', 'api/v1/auth/verify')
            self._status = AdapterStatus.READY
            return response.get('authenticated', False)
        except:
            self._status = AdapterStatus.ERROR
            return False
    
    def analyze(self, patient_data: Dict[str, Any], analysis_type: Optional[str] = None) -> AdapterResult:
        if not self.enabled:
            return AdapterResult(success=False, adapter_name=self.adapter_name, category="workflow_alert", content="", error_message="Disabled")
        
        try:
            response = self._make_request('POST', 'api/v1/workflows/trigger', data={
                'patient_id': patient_data.get('patient_id'),
                'workflow_type': analysis_type or 'clinical_review'
            })
            return AdapterResult(
                success=True,
                adapter_name=self.adapter_name,
                category="workflow_alert",
                content=response.get('message', 'Workflow triggered'),
                confidence=1.0,
                raw_response=response
            )
        except Exception as e:
            return AdapterResult(success=False, adapter_name=self.adapter_name, category="workflow_alert", content="", error_message=str(e))
    
    def get_insights(self, patient_id: str, from_date: Optional[str] = None, to_date: Optional[str] = None) -> List[AdapterResult]:
        return []
