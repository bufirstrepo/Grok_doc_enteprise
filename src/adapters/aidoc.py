"""
Aidoc Adapter

Integrates with Aidoc's radiology AI platform for:
- CT scan analysis (PE, ICH, C-spine fractures)
- X-ray analysis
- Real-time radiology workflow prioritization
"""

from typing import Dict, List, Optional, Any
from .base import AIToolAdapter, AdapterResult, InsightCategory, AdapterStatus


class AidocAdapter(AIToolAdapter):
    """
    Adapter for Aidoc radiology AI platform.
    
    Aidoc provides AI-powered detection for:
    - Pulmonary embolism (PE)
    - Intracranial hemorrhage (ICH)
    - Cervical spine fractures
    - Aortic emergencies
    - And more
    """
    
    @property
    def adapter_name(self) -> str:
        return "aidoc"
    
    @property
    def supported_categories(self) -> List[InsightCategory]:
        return [
            InsightCategory.IMAGING_FINDING,
            InsightCategory.DIAGNOSIS,
            InsightCategory.RISK_PREDICTION
        ]
    
    def authenticate(self) -> bool:
        """Authenticate with Aidoc API"""
        if not self.api_key:
            self._status = AdapterStatus.ERROR
            return False
        
        try:
            response = self._make_request('GET', 'auth/verify')
            self._status = AdapterStatus.READY
            return response.get('authenticated', False)
        except Exception as e:
            print(f"Aidoc authentication failed: {e}")
            self._status = AdapterStatus.ERROR
            return False
    
    def analyze(
        self,
        patient_data: Dict[str, Any],
        analysis_type: Optional[str] = None
    ) -> AdapterResult:
        """
        Analyze imaging studies for the patient.
        
        Args:
            patient_data: Unified patient data with imaging references
            analysis_type: Specific study type (ct, xray, etc.)
        """
        if not self.enabled:
            return AdapterResult(
                success=False,
                adapter_name=self.adapter_name,
                category="imaging_finding",
                content="",
                error_message="Adapter disabled"
            )
        
        try:
            imaging_refs = patient_data.get('imaging_studies', [])
            if not imaging_refs:
                return AdapterResult(
                    success=True,
                    adapter_name=self.adapter_name,
                    category="imaging_finding",
                    content="No imaging studies available for analysis",
                    confidence=1.0
                )
            
            request_data = {
                'patient_id': patient_data.get('patient_id'),
                'studies': imaging_refs,
                'analysis_type': analysis_type or 'all'
            }
            
            response = self._make_request('POST', 'analyze', data=request_data)
            
            findings = response.get('findings', [])
            
            if findings:
                primary_finding = findings[0]
                content = self._format_finding(primary_finding)
                confidence = primary_finding.get('confidence', 0.0)
            else:
                content = "No significant findings detected"
                confidence = 0.95
            
            return AdapterResult(
                success=True,
                adapter_name=self.adapter_name,
                category="imaging_finding",
                content=content,
                confidence=confidence,
                raw_response=response,
                metadata={
                    'study_count': len(imaging_refs),
                    'finding_count': len(findings),
                    'analysis_type': analysis_type
                },
                latency_ms=response.get('_latency_ms', 0)
            )
            
        except Exception as e:
            return AdapterResult(
                success=False,
                adapter_name=self.adapter_name,
                category="imaging_finding",
                content="",
                error_message=str(e)
            )
    
    def get_insights(
        self,
        patient_id: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> List[AdapterResult]:
        """Retrieve existing Aidoc insights for a patient"""
        if not self.enabled:
            return []
        
        try:
            params = {'patient_id': patient_id}
            if from_date:
                params['from_date'] = from_date
            if to_date:
                params['to_date'] = to_date
            
            response = self._make_request('GET', 'insights', params=params)
            
            results = []
            for insight in response.get('insights', []):
                results.append(AdapterResult(
                    success=True,
                    adapter_name=self.adapter_name,
                    category=insight.get('category', 'imaging_finding'),
                    content=insight.get('description', ''),
                    confidence=insight.get('confidence', 0.0),
                    metadata={
                        'study_id': insight.get('study_id'),
                        'modality': insight.get('modality'),
                        'body_part': insight.get('body_part')
                    },
                    timestamp=insight.get('timestamp')
                ))
            
            return results
            
        except Exception as e:
            print(f"Failed to get Aidoc insights: {e}")
            return []
    
    def _format_finding(self, finding: Dict) -> str:
        """Format a finding into readable text"""
        finding_type = finding.get('type', 'Unknown')
        location = finding.get('location', '')
        severity = finding.get('severity', '')
        details = finding.get('details', '')
        
        parts = [f"[{finding_type}]"]
        if location:
            parts.append(f"Location: {location}")
        if severity:
            parts.append(f"Severity: {severity}")
        if details:
            parts.append(details)
        
        return " - ".join(parts)
    
    def analyze_ct(
        self,
        study_id: str,
        body_region: str = "chest"
    ) -> AdapterResult:
        """Analyze a specific CT study"""
        return self.analyze(
            patient_data={'imaging_studies': [{'id': study_id, 'modality': 'CT', 'body_region': body_region}]},
            analysis_type='ct'
        )
    
    def analyze_xray(
        self,
        study_id: str,
        body_region: str = "chest"
    ) -> AdapterResult:
        """Analyze a specific X-ray study"""
        return self.analyze(
            patient_data={'imaging_studies': [{'id': study_id, 'modality': 'XR', 'body_region': body_region}]},
            analysis_type='xray'
        )
