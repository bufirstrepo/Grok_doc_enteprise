"""
Unified Patient Data Model

Normalizes patient data from different EHR systems (Epic, Cerner, etc.)
into a common format for the Kinetics engine.
"""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

from .base import PatientData, Observation, Medication, Condition


class DataSource(Enum):
    """Source of clinical data"""
    EPIC = "epic"
    CERNER = "cerner"
    MEDITECH = "meditech"
    ALLSCRIPTS = "allscripts"
    HL7V2 = "hl7v2"
    MANUAL = "manual"
    AI_ADAPTER = "ai_adapter"


@dataclass
class ClinicalInsight:
    """AI-generated insight from hospital tools"""
    source: str
    insight_type: str
    content: str
    confidence: float
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskScore:
    """Clinical risk score"""
    name: str
    value: float
    category: str
    source: str
    calculated_at: str
    factors: List[str] = field(default_factory=list)


@dataclass
class UnifiedPatientModel:
    """
    Unified patient model that aggregates data from multiple sources.
    
    This is the primary data structure consumed by the Kinetics engine.
    """
    patient_id: str
    mrn: str
    
    demographics: Dict[str, Any] = field(default_factory=dict)
    
    observations: List[Observation] = field(default_factory=list)
    medications: List[Medication] = field(default_factory=list)
    conditions: List[Condition] = field(default_factory=list)
    allergies: List[str] = field(default_factory=list)
    
    ai_insights: List[ClinicalInsight] = field(default_factory=list)
    risk_scores: List[RiskScore] = field(default_factory=list)
    
    imaging_results: List[Dict[str, Any]] = field(default_factory=list)
    genomic_data: Dict[str, Any] = field(default_factory=dict)
    
    sources: List[str] = field(default_factory=list)
    aggregated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    
    def add_from_ehr(self, patient_data: PatientData):
        """Add data from an EHR patient record"""
        if patient_data.source_system not in self.sources:
            self.sources.append(patient_data.source_system)
        
        self.demographics.update({
            'given_name': patient_data.given_name,
            'family_name': patient_data.family_name,
            'birth_date': patient_data.birth_date,
            'gender': patient_data.gender,
            'age': patient_data.get_age(),
            'address': patient_data.address,
            'phone': patient_data.phone,
            'email': patient_data.email
        })
        
        self.observations.extend(patient_data.observations)
        self.medications.extend(patient_data.medications)
        self.conditions.extend(patient_data.conditions)
        self.allergies.extend(patient_data.allergies)
        
        self._deduplicate()
    
    def add_ai_insight(
        self,
        source: str,
        insight_type: str,
        content: str,
        confidence: float,
        metadata: Optional[Dict] = None
    ):
        """Add an insight from a hospital AI tool"""
        if source not in self.sources:
            self.sources.append(f"ai:{source}")
        
        self.ai_insights.append(ClinicalInsight(
            source=source,
            insight_type=insight_type,
            content=content,
            confidence=confidence,
            timestamp=datetime.utcnow().isoformat() + "Z",
            metadata=metadata or {}
        ))
    
    def add_risk_score(
        self,
        name: str,
        value: float,
        category: str,
        source: str,
        factors: Optional[List[str]] = None
    ):
        """Add a clinical risk score"""
        self.risk_scores.append(RiskScore(
            name=name,
            value=value,
            category=category,
            source=source,
            calculated_at=datetime.utcnow().isoformat() + "Z",
            factors=factors or []
        ))
    
    def add_imaging_result(
        self,
        modality: str,
        body_part: str,
        findings: str,
        source: str,
        ai_analysis: Optional[Dict] = None
    ):
        """Add imaging study result"""
        self.imaging_results.append({
            'modality': modality,
            'body_part': body_part,
            'findings': findings,
            'source': source,
            'ai_analysis': ai_analysis,
            'recorded_at': datetime.utcnow().isoformat() + "Z"
        })
    
    def add_genomic_data(self, data_type: str, data: Dict[str, Any]):
        """Add genomic/molecular data"""
        if 'sources' not in self.genomic_data:
            self.genomic_data['sources'] = []
        self.genomic_data['sources'].append(data_type)
        self.genomic_data[data_type] = data
    
    def _deduplicate(self):
        """Remove duplicate entries based on IDs"""
        seen_obs = set()
        unique_obs = []
        for obs in self.observations:
            if obs.id not in seen_obs:
                seen_obs.add(obs.id)
                unique_obs.append(obs)
        self.observations = unique_obs
        
        seen_meds = set()
        unique_meds = []
        for med in self.medications:
            if med.id not in seen_meds:
                seen_meds.add(med.id)
                unique_meds.append(med)
        self.medications = unique_meds
        
        seen_cond = set()
        unique_cond = []
        for cond in self.conditions:
            if cond.id not in seen_cond:
                seen_cond.add(cond.id)
                unique_cond.append(cond)
        self.conditions = unique_cond
        
        self.allergies = list(set(self.allergies))
    
    def get_recent_labs(self, hours: int = 24) -> List[Observation]:
        """Get lab results from recent hours"""
        cutoff = datetime.utcnow()
        recent = []
        for obs in self.observations:
            if obs.category == "laboratory" and obs.effective_datetime:
                try:
                    obs_time = datetime.fromisoformat(
                        obs.effective_datetime.replace('Z', '+00:00')
                    )
                    if (cutoff - obs_time).total_seconds() < hours * 3600:
                        recent.append(obs)
                except:
                    recent.append(obs)
        return recent
    
    def get_abnormal_findings(self) -> Dict[str, List]:
        """Get all abnormal findings across categories"""
        return {
            'labs': [o for o in self.observations if o.is_abnormal()],
            'high_risk_scores': [r for r in self.risk_scores if r.value > 0.7],
            'critical_insights': [
                i for i in self.ai_insights 
                if 'critical' in i.insight_type.lower() or i.confidence > 0.9
            ]
        }
    
    def get_active_medications(self) -> List[Medication]:
        """Get currently active medications"""
        return [m for m in self.medications if m.status == "active"]
    
    def get_active_conditions(self) -> List[Condition]:
        """Get currently active conditions"""
        return [c for c in self.conditions if c.clinical_status == "active"]
    
    def get_insights_by_source(self, source: str) -> List[ClinicalInsight]:
        """Get AI insights from a specific source"""
        return [i for i in self.ai_insights if i.source == source]
    
    def to_kinetics_context(self) -> Dict[str, Any]:
        """
        Convert to context dict for Kinetics engine.
        
        Returns:
            Dict formatted for Kinetics LLM prompts
        """
        return {
            'patient_id': self.patient_id,
            'mrn': self.mrn,
            'age': self.demographics.get('age'),
            'gender': self.demographics.get('gender'),
            'active_conditions': [
                {'code': c.code, 'display': c.display}
                for c in self.get_active_conditions()
            ],
            'active_medications': [
                {'display': m.display, 'dose': f"{m.dose_value} {m.dose_unit}"}
                for m in self.get_active_medications()
            ],
            'recent_labs': [
                {
                    'name': o.display,
                    'value': o.value,
                    'unit': o.unit,
                    'abnormal': o.is_abnormal(),
                    'interpretation': o.interpretation
                }
                for o in self.get_recent_labs()
            ],
            'allergies': self.allergies,
            'ai_insights': [
                {
                    'source': i.source,
                    'type': i.insight_type,
                    'content': i.content,
                    'confidence': i.confidence
                }
                for i in self.ai_insights
            ],
            'risk_scores': [
                {
                    'name': r.name,
                    'value': r.value,
                    'category': r.category
                }
                for r in self.risk_scores
            ],
            'imaging_summary': [
                {
                    'modality': img['modality'],
                    'findings': img['findings'][:200]
                }
                for img in self.imaging_results
            ],
            'has_genomic_data': bool(self.genomic_data),
            'data_sources': self.sources
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'patient_id': self.patient_id,
            'mrn': self.mrn,
            'demographics': self.demographics,
            'observations': [asdict(o) for o in self.observations],
            'medications': [asdict(m) for m in self.medications],
            'conditions': [asdict(c) for c in self.conditions],
            'allergies': self.allergies,
            'ai_insights': [asdict(i) for i in self.ai_insights],
            'risk_scores': [asdict(r) for r in self.risk_scores],
            'imaging_results': self.imaging_results,
            'genomic_data': self.genomic_data,
            'sources': self.sources,
            'aggregated_at': self.aggregated_at
        }


def normalize_patient_data(
    ehr_data: Optional[PatientData] = None,
    ai_insights: Optional[List[Dict]] = None,
    imaging_results: Optional[List[Dict]] = None,
    genomic_data: Optional[Dict] = None
) -> UnifiedPatientModel:
    """
    Normalize data from multiple sources into unified model.
    
    Args:
        ehr_data: Patient data from EHR system
        ai_insights: List of AI tool insights
        imaging_results: List of imaging study results
        genomic_data: Genomic/molecular data
        
    Returns:
        UnifiedPatientModel with all data aggregated
    """
    patient_id = ehr_data.id if ehr_data else "unknown"
    mrn = ehr_data.mrn if ehr_data else "unknown"
    
    model = UnifiedPatientModel(
        patient_id=patient_id,
        mrn=mrn
    )
    
    if ehr_data:
        model.add_from_ehr(ehr_data)
    
    if ai_insights:
        for insight in ai_insights:
            model.add_ai_insight(
                source=insight.get('source', 'unknown'),
                insight_type=insight.get('type', 'general'),
                content=insight.get('content', ''),
                confidence=insight.get('confidence', 0.5),
                metadata=insight.get('metadata')
            )
    
    if imaging_results:
        for img in imaging_results:
            model.add_imaging_result(
                modality=img.get('modality', 'unknown'),
                body_part=img.get('body_part', 'unknown'),
                findings=img.get('findings', ''),
                source=img.get('source', 'unknown'),
                ai_analysis=img.get('ai_analysis')
            )
    
    if genomic_data:
        for data_type, data in genomic_data.items():
            model.add_genomic_data(data_type, data)
    
    return model
