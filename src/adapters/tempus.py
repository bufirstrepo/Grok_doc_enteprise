"""
Tempus Adapter

Integrates with Tempus precision medicine platform for:
- Genomic profiling
- Molecular diagnostics
- AI-driven treatment recommendations
"""

from typing import Dict, List, Optional, Any
from .base import AIToolAdapter, AdapterResult, InsightCategory, AdapterStatus


class TempusAdapter(AIToolAdapter):
    """
    Adapter for Tempus precision medicine platform.
    
    Tempus provides:
    - Comprehensive genomic profiling
    - RNA expression analysis
    - Molecular tumor boards
    - Clinical trial matching
    - AI-driven treatment recommendations
    """
    
    @property
    def adapter_name(self) -> str:
        return "tempus"
    
    @property
    def supported_categories(self) -> List[InsightCategory]:
        return [
            InsightCategory.GENOMIC_FINDING,
            InsightCategory.TREATMENT_RECOMMENDATION,
            InsightCategory.DIAGNOSIS
        ]
    
    def authenticate(self) -> bool:
        """Authenticate with Tempus API"""
        if not self.api_key:
            self._status = AdapterStatus.ERROR
            return False
        
        try:
            response = self._make_request('GET', 'api/v1/auth/verify')
            self._status = AdapterStatus.READY
            return response.get('valid', False)
        except Exception as e:
            print(f"Tempus authentication failed: {e}")
            self._status = AdapterStatus.ERROR
            return False
    
    def analyze(
        self,
        patient_data: Dict[str, Any],
        analysis_type: Optional[str] = None
    ) -> AdapterResult:
        """
        Retrieve or trigger genomic analysis.
        
        Args:
            patient_data: Patient data with genomic sample info
            analysis_type: genomic, rna, treatment_match
        """
        if not self.enabled:
            return AdapterResult(
                success=False,
                adapter_name=self.adapter_name,
                category="genomic_finding",
                content="",
                error_message="Adapter disabled"
            )
        
        try:
            patient_id = patient_data.get('patient_id')
            
            response = self._make_request(
                'GET', 
                f'api/v1/patients/{patient_id}/genomic-profile'
            )
            
            if response.get('status') == 'completed':
                content = self._format_genomic_profile(response)
                confidence = 0.95
            elif response.get('status') == 'pending':
                content = "Genomic analysis in progress"
                confidence = 0.0
            else:
                content = "No genomic data available"
                confidence = 1.0
            
            return AdapterResult(
                success=True,
                adapter_name=self.adapter_name,
                category="genomic_finding",
                content=content,
                confidence=confidence,
                raw_response=response,
                metadata={
                    'status': response.get('status'),
                    'mutations': response.get('mutations', []),
                    'trial_matches': len(response.get('clinical_trials', [])),
                    'therapy_options': len(response.get('therapies', []))
                },
                latency_ms=response.get('_latency_ms', 0)
            )
            
        except Exception as e:
            return AdapterResult(
                success=False,
                adapter_name=self.adapter_name,
                category="genomic_finding",
                content="",
                error_message=str(e)
            )
    
    def get_insights(
        self,
        patient_id: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> List[AdapterResult]:
        """Retrieve Tempus genomic insights for a patient"""
        if not self.enabled:
            return []
        
        try:
            response = self._make_request(
                'GET',
                f'api/v1/patients/{patient_id}/insights'
            )
            
            results = []
            for insight in response.get('insights', []):
                results.append(AdapterResult(
                    success=True,
                    adapter_name=self.adapter_name,
                    category=insight.get('category', 'genomic_finding'),
                    content=insight.get('description', ''),
                    confidence=insight.get('confidence', 0.0),
                    metadata={
                        'gene': insight.get('gene'),
                        'variant': insight.get('variant'),
                        'clinical_significance': insight.get('clinical_significance')
                    },
                    timestamp=insight.get('timestamp')
                ))
            
            return results
            
        except Exception as e:
            print(f"Failed to get Tempus insights: {e}")
            return []
    
    def _format_genomic_profile(self, profile: Dict) -> str:
        """Format genomic profile into readable text"""
        parts = []
        
        mutations = profile.get('mutations', [])
        if mutations:
            actionable = [m for m in mutations if m.get('actionable')]
            parts.append(f"Mutations detected: {len(mutations)} ({len(actionable)} actionable)")
            
            for m in actionable[:3]:
                parts.append(f"  - {m.get('gene')}: {m.get('variant')} ({m.get('significance')})")
        
        therapies = profile.get('therapies', [])
        if therapies:
            parts.append(f"Therapy options: {len(therapies)} identified")
            for t in therapies[:2]:
                parts.append(f"  - {t.get('name')}: {t.get('evidence_level')}")
        
        trials = profile.get('clinical_trials', [])
        if trials:
            parts.append(f"Clinical trial matches: {len(trials)}")
        
        return "\n".join(parts) if parts else "No significant genomic findings"
    
    def get_treatment_recommendations(
        self,
        patient_id: str,
        cancer_type: Optional[str] = None
    ) -> AdapterResult:
        """Get AI-driven treatment recommendations"""
        try:
            params = {'patient_id': patient_id}
            if cancer_type:
                params['cancer_type'] = cancer_type
            
            response = self._make_request(
                'GET',
                'api/v1/treatment-recommendations',
                params=params
            )
            
            recommendations = response.get('recommendations', [])
            
            if recommendations:
                content = "\n".join([
                    f"- {r.get('therapy')}: {r.get('rationale')}"
                    for r in recommendations[:5]
                ])
            else:
                content = "No specific treatment recommendations available"
            
            return AdapterResult(
                success=True,
                adapter_name=self.adapter_name,
                category="treatment_recommendation",
                content=content,
                confidence=response.get('confidence', 0.0),
                raw_response=response
            )
            
        except Exception as e:
            return AdapterResult(
                success=False,
                adapter_name=self.adapter_name,
                category="treatment_recommendation",
                content="",
                error_message=str(e)
            )
