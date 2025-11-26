"""
Caption Health Adapter

Integrates with Caption Health's cardiac ultrasound AI platform.
"""

from typing import Dict, List, Optional, Any
from .base import AIToolAdapter, AdapterResult, InsightCategory, AdapterStatus


class CaptionHealthAdapter(AIToolAdapter):
    """Adapter for Caption Health AI-guided cardiac ultrasound"""
    
    @property
    def adapter_name(self) -> str:
        return "caption_health"
    
    @property
    def supported_categories(self) -> List[InsightCategory]:
        return [
            InsightCategory.IMAGING_FINDING,
            InsightCategory.DIAGNOSIS,
            InsightCategory.RISK_PREDICTION
        ]
    
    def authenticate(self) -> bool:
        if not self.api_key:
            self._status = AdapterStatus.ERROR
            return False
        try:
            response = self._make_request('GET', 'api/auth/verify')
            self._status = AdapterStatus.READY
            return response.get('valid', False)
        except:
            self._status = AdapterStatus.ERROR
            return False
    
    def analyze(self, patient_data: Dict[str, Any], analysis_type: Optional[str] = None) -> AdapterResult:
        if not self.enabled:
            return AdapterResult(success=False, adapter_name=self.adapter_name, category="imaging_finding", content="", error_message="Disabled")
        
        try:
            response = self._make_request('POST', 'api/cardiac/analyze', data={'patient_id': patient_data.get('patient_id')})
            ef = response.get('ejection_fraction')
            content = f"Ejection Fraction: {ef}%" if ef else response.get('summary', 'Analysis complete')
            return AdapterResult(
                success=True,
                adapter_name=self.adapter_name,
                category="imaging_finding",
                content=content,
                confidence=response.get('confidence', 0.0),
                raw_response=response,
                metadata={'ejection_fraction': ef}
            )
        except Exception as e:
            return AdapterResult(success=False, adapter_name=self.adapter_name, category="imaging_finding", content="", error_message=str(e))
    
    def get_insights(self, patient_id: str, from_date: Optional[str] = None, to_date: Optional[str] = None) -> List[AdapterResult]:
        return []
