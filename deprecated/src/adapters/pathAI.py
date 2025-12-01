"""
PathAI Adapter

Integrates with PathAI's pathology AI platform for:
- Digital pathology analysis
- Cancer detection and grading
- Biomarker quantification
"""

from typing import Dict, List, Optional, Any
from .base import AIToolAdapter, AdapterResult, InsightCategory, AdapterStatus


class PathAIAdapter(AIToolAdapter):
    """
    Adapter for PathAI digital pathology platform.
    
    PathAI provides AI-powered analysis for:
    - Cancer detection in tissue slides
    - Tumor grading (Gleason, etc.)
    - Biomarker expression quantification
    - Therapy response prediction
    """
    
    @property
    def adapter_name(self) -> str:
        return "pathAI"
    
    @property
    def supported_categories(self) -> List[InsightCategory]:
        return [
            InsightCategory.PATHOLOGY_FINDING,
            InsightCategory.DIAGNOSIS,
            InsightCategory.TREATMENT_RECOMMENDATION
        ]
    
    def authenticate(self) -> bool:
        """Authenticate with PathAI API"""
        if not self.api_key:
            self._status = AdapterStatus.ERROR
            return False
        
        try:
            response = self._make_request('GET', 'v1/auth/status')
            self._status = AdapterStatus.READY
            return response.get('status') == 'active'
        except Exception as e:
            print(f"PathAI authentication failed: {e}")
            self._status = AdapterStatus.ERROR
            return False
    
    def analyze(
        self,
        patient_data: Dict[str, Any],
        analysis_type: Optional[str] = None
    ) -> AdapterResult:
        """
        Analyze pathology samples for the patient.
        
        Args:
            patient_data: Unified patient data with pathology references
            analysis_type: cancer_detection, grading, biomarkers
        """
        if not self.enabled:
            return AdapterResult(
                success=False,
                adapter_name=self.adapter_name,
                category="pathology_finding",
                content="",
                error_message="Adapter disabled"
            )
        
        try:
            pathology_samples = patient_data.get('pathology_samples', [])
            if not pathology_samples:
                return AdapterResult(
                    success=True,
                    adapter_name=self.adapter_name,
                    category="pathology_finding",
                    content="No pathology samples available for analysis",
                    confidence=1.0
                )
            
            request_data = {
                'patient_id': patient_data.get('patient_id'),
                'samples': pathology_samples,
                'analysis_type': analysis_type or 'comprehensive'
            }
            
            response = self._make_request('POST', 'v1/analyze', data=request_data)
            
            findings = response.get('results', {})
            
            content = self._format_pathology_result(findings)
            confidence = findings.get('confidence', 0.0)
            
            return AdapterResult(
                success=True,
                adapter_name=self.adapter_name,
                category="pathology_finding",
                content=content,
                confidence=confidence,
                raw_response=response,
                metadata={
                    'sample_count': len(pathology_samples),
                    'cancer_detected': findings.get('cancer_detected', False),
                    'grade': findings.get('grade'),
                    'biomarkers': findings.get('biomarkers', {})
                },
                latency_ms=response.get('_latency_ms', 0)
            )
            
        except Exception as e:
            return AdapterResult(
                success=False,
                adapter_name=self.adapter_name,
                category="pathology_finding",
                content="",
                error_message=str(e)
            )
    
    def get_insights(
        self,
        patient_id: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> List[AdapterResult]:
        """Retrieve existing PathAI insights for a patient"""
        if not self.enabled:
            return []
        
        try:
            params = {'patient_id': patient_id}
            if from_date:
                params['from_date'] = from_date
            if to_date:
                params['to_date'] = to_date
            
            response = self._make_request('GET', 'v1/results', params=params)
            
            results = []
            for result in response.get('results', []):
                results.append(AdapterResult(
                    success=True,
                    adapter_name=self.adapter_name,
                    category='pathology_finding',
                    content=self._format_pathology_result(result),
                    confidence=result.get('confidence', 0.0),
                    metadata={
                        'sample_id': result.get('sample_id'),
                        'tissue_type': result.get('tissue_type'),
                        'diagnosis': result.get('diagnosis')
                    },
                    timestamp=result.get('analyzed_at')
                ))
            
            return results
            
        except Exception as e:
            print(f"Failed to get PathAI insights: {e}")
            return []
    
    def _format_pathology_result(self, result: Dict) -> str:
        """Format pathology result into readable text"""
        parts = []
        
        if result.get('cancer_detected'):
            cancer_type = result.get('cancer_type', 'Malignancy')
            grade = result.get('grade', 'Unknown grade')
            parts.append(f"[POSITIVE] {cancer_type} detected - {grade}")
        else:
            parts.append("[NEGATIVE] No malignancy detected")
        
        if result.get('biomarkers'):
            biomarker_strs = []
            for marker, value in result['biomarkers'].items():
                biomarker_strs.append(f"{marker}: {value}")
            parts.append(f"Biomarkers: {', '.join(biomarker_strs)}")
        
        if result.get('recommendations'):
            parts.append(f"Recommendations: {result['recommendations']}")
        
        return " | ".join(parts)
