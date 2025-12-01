"""
Enhanced Kinetics Engine

The core reasoning engine that:
1. Receives data from Epic/Cerner EHR
2. Aggregates insights from hospital AI tools
3. Performs unified clinical reasoning
4. Supports continuous learning from outcomes
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json
import hashlib

from ..ehr.unified_model import UnifiedPatientModel
from ..adapters.base import AdapterResult


@dataclass
class KineticsContext:
    """Complete context for Kinetics reasoning"""
    patient: UnifiedPatientModel
    clinical_question: str
    retrieved_cases: List[Dict] = field(default_factory=list)
    ai_adapter_results: List[AdapterResult] = field(default_factory=list)
    bayesian_result: Optional[Dict] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_prompt_context(self) -> str:
        """Convert to formatted context string for LLM prompt"""
        sections = []
        
        demographics = self.patient.demographics
        sections.append(f"""PATIENT DEMOGRAPHICS:
- Age: {demographics.get('age', 'Unknown')}
- Gender: {demographics.get('gender', 'Unknown')}
- MRN: {self.patient.mrn}""")
        
        active_conditions = self.patient.get_active_conditions()
        if active_conditions:
            cond_list = "\n".join([f"  - {c.display}" for c in active_conditions[:10]])
            sections.append(f"ACTIVE CONDITIONS:\n{cond_list}")
        
        active_meds = self.patient.get_active_medications()
        if active_meds:
            med_list = "\n".join([f"  - {m.display} ({m.dose_value} {m.dose_unit})" for m in active_meds[:10]])
            sections.append(f"ACTIVE MEDICATIONS:\n{med_list}")
        
        recent_labs = self.patient.get_recent_labs(24)
        if recent_labs:
            lab_list = "\n".join([
                f"  - {o.display}: {o.value} {o.unit or ''} {'[ABNORMAL]' if o.is_abnormal() else ''}"
                for o in recent_labs[:15]
            ])
            sections.append(f"RECENT LABS (24h):\n{lab_list}")
        
        if self.patient.allergies:
            sections.append(f"ALLERGIES: {', '.join(self.patient.allergies)}")
        
        if self.ai_adapter_results:
            insights = []
            for result in self.ai_adapter_results:
                if result.success and result.content:
                    insights.append(f"  [{result.adapter_name}] {result.content} (confidence: {result.confidence:.0%})")
            if insights:
                sections.append(f"AI TOOL INSIGHTS:\n" + "\n".join(insights))
        
        if self.bayesian_result:
            sections.append(f"""BAYESIAN ANALYSIS:
- Safety Probability: {self.bayesian_result.get('prob_safe', 0):.1%}
- 95% CI: [{self.bayesian_result.get('ci_low', 0):.1%}, {self.bayesian_result.get('ci_high', 0):.1%}]
- Based on {self.bayesian_result.get('n_cases', 0)} similar cases""")
        
        if self.retrieved_cases:
            case_summaries = "\n".join([
                f"  Case {i+1}: {case.get('summary', 'N/A')}"
                for i, case in enumerate(self.retrieved_cases[:10])
            ])
            sections.append(f"SIMILAR HISTORICAL CASES:\n{case_summaries}")
        
        return "\n\n".join(sections)


@dataclass
class KineticsResult:
    """Result from Kinetics engine analysis"""
    recommendation: str
    confidence: float
    reasoning_steps: List[Dict]
    data_sources: List[str]
    warnings: List[str]
    suggested_actions: List[str]
    hash: str
    timestamp: str
    latency_ms: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'recommendation': self.recommendation,
            'confidence': self.confidence,
            'reasoning_steps': self.reasoning_steps,
            'data_sources': self.data_sources,
            'warnings': self.warnings,
            'suggested_actions': self.suggested_actions,
            'hash': self.hash,
            'timestamp': self.timestamp,
            'latency_ms': self.latency_ms
        }


class EnhancedKineticsEngine:
    """
    Enhanced Kinetics reasoning engine.
    
    This engine:
    1. Aggregates data from EHR systems (Epic, Cerner)
    2. Collects insights from hospital AI tools
    3. Performs Bayesian safety analysis
    4. Generates unified clinical recommendations
    5. Tracks outcomes for continuous learning
    """
    
    def __init__(
        self,
        use_grok: bool = False,
        use_local_llm: bool = True,
        model_name: Optional[str] = None
    ):
        """
        Initialize Kinetics engine.
        
        Args:
            use_grok: Use Grok API (requires BAA)
            use_local_llm: Use local LLM backend
            model_name: Specific model to use
        """
        self.use_grok = use_grok
        self.use_local_llm = use_local_llm
        self.model_name = model_name
        self._outcomes_db: List[Dict] = []
    
    def analyze(
        self,
        context: KineticsContext
    ) -> KineticsResult:
        """
        Perform comprehensive clinical analysis.
        
        Args:
            context: Complete patient context
            
        Returns:
            KineticsResult with recommendation and reasoning
        """
        import time
        start_time = time.time()
        
        prompt = self._build_kinetics_prompt(context)
        
        try:
            if self.use_grok:
                response = self._query_grok(prompt)
            elif self.use_local_llm:
                response = self._query_local_llm(prompt)
            else:
                response = self._generate_fallback_response(context)
        except Exception as e:
            response = f"Analysis error: {str(e)}. Please review manually."
        
        latency_ms = (time.time() - start_time) * 1000
        
        confidence = self._calculate_confidence(context)
        warnings = self._generate_warnings(context)
        actions = self._generate_suggested_actions(context)
        
        result_hash = self._compute_hash(context, response)
        
        return KineticsResult(
            recommendation=response,
            confidence=confidence,
            reasoning_steps=self._extract_reasoning_steps(context),
            data_sources=context.patient.sources,
            warnings=warnings,
            suggested_actions=actions,
            hash=result_hash,
            timestamp=datetime.utcnow().isoformat() + "Z",
            latency_ms=latency_ms
        )
    
    def _build_kinetics_prompt(self, context: KineticsContext) -> str:
        """Build the Kinetics LLM prompt"""
        return f"""You are an expert clinical pharmacologist providing rapid clinical reasoning.

{context.to_prompt_context()}

CLINICAL QUESTION:
{context.clinical_question}

TASK:
Provide a focused pharmacokinetic assessment and recommendation:
1. Direct answer to the clinical question
2. Key safety considerations based on patient factors
3. Specific dose/monitoring recommendations if applicable
4. Confidence level and rationale

Keep response concise (3-4 sentences for main recommendation).
"""
    
    def _query_grok(self, prompt: str) -> str:
        """Query Grok API"""
        from .grok_backend import get_grok_backend
        
        backend = get_grok_backend()
        if not backend.is_hipaa_ready():
            raise RuntimeError("Grok not configured for HIPAA use")
        
        response = backend.query(prompt, temperature=0.0, max_tokens=500)
        return response.content
    
    def _query_local_llm(self, prompt: str) -> str:
        """Query local LLM"""
        try:
            from local_inference import grok_query
            return grok_query(prompt, model_name=self.model_name)
        except Exception as e:
            return f"Local LLM unavailable: {e}"
    
    def _generate_fallback_response(self, context: KineticsContext) -> str:
        """Generate a structured fallback when LLM unavailable"""
        bayesian = context.bayesian_result or {}
        prob_safe = bayesian.get('prob_safe', 0.5)
        
        if prob_safe >= 0.85:
            safety_assessment = "Based on similar cases, this appears to be a LOW RISK scenario."
        elif prob_safe >= 0.70:
            safety_assessment = "Based on similar cases, this is a MODERATE RISK scenario requiring careful monitoring."
        else:
            safety_assessment = "Based on similar cases, this is a HIGHER RISK scenario. Consider alternatives."
        
        abnormal = context.patient.get_abnormal_findings()
        lab_alerts = [f"{o.display}: {o.value}" for o in abnormal.get('labs', [])[:3]]
        
        response_parts = [
            safety_assessment,
            f"Safety probability: {prob_safe:.0%} based on {bayesian.get('n_cases', 0)} similar cases."
        ]
        
        if lab_alerts:
            response_parts.append(f"Notable findings: {', '.join(lab_alerts)}")
        
        response_parts.append("Recommend physician review of complete clinical picture.")
        
        return " ".join(response_parts)
    
    def _calculate_confidence(self, context: KineticsContext) -> float:
        """Calculate overall confidence score"""
        base_confidence = 0.5
        
        if context.bayesian_result:
            bayesian_conf = context.bayesian_result.get('prob_safe', 0.5)
            base_confidence = (base_confidence + bayesian_conf) / 2
        
        n_sources = len(context.patient.sources)
        source_bonus = min(n_sources * 0.05, 0.2)
        
        n_cases = len(context.retrieved_cases)
        case_bonus = min(n_cases * 0.002, 0.1)
        
        adapter_confidences = [
            r.confidence for r in context.ai_adapter_results
            if r.success and r.confidence > 0
        ]
        if adapter_confidences:
            adapter_avg = sum(adapter_confidences) / len(adapter_confidences)
            base_confidence = (base_confidence + adapter_avg) / 2
        
        return min(base_confidence + source_bonus + case_bonus, 0.99)
    
    def _generate_warnings(self, context: KineticsContext) -> List[str]:
        """Generate safety warnings"""
        warnings = []
        
        abnormal = context.patient.get_abnormal_findings()
        if abnormal.get('labs'):
            warnings.append(f"Abnormal labs detected: {len(abnormal['labs'])} findings")
        
        if context.patient.allergies:
            warnings.append(f"Patient has {len(context.patient.allergies)} documented allergies")
        
        high_risk = abnormal.get('high_risk_scores', [])
        if high_risk:
            warnings.append(f"Elevated risk scores: {', '.join([r.name for r in high_risk])}")
        
        bayesian = context.bayesian_result or {}
        if bayesian.get('prob_safe', 1.0) < 0.7:
            warnings.append("Bayesian analysis suggests elevated risk profile")
        
        return warnings
    
    def _generate_suggested_actions(self, context: KineticsContext) -> List[str]:
        """Generate suggested follow-up actions"""
        actions = []
        
        bayesian = context.bayesian_result or {}
        if bayesian.get('prob_safe', 1.0) < 0.85:
            actions.append("Consider enhanced monitoring protocol")
        
        abnormal = context.patient.get_abnormal_findings()
        if abnormal.get('labs'):
            actions.append("Review abnormal laboratory values")
        
        if not context.patient.get_recent_labs(24):
            actions.append("Consider ordering updated labs")
        
        if context.ai_adapter_results:
            critical = [r for r in context.ai_adapter_results if 'critical' in r.category.lower()]
            if critical:
                actions.append("Review critical AI findings")
        
        return actions
    
    def _extract_reasoning_steps(self, context: KineticsContext) -> List[Dict]:
        """Extract reasoning chain steps"""
        steps = []
        
        steps.append({
            'step': 'Data Aggregation',
            'description': f'Collected data from {len(context.patient.sources)} sources',
            'sources': context.patient.sources
        })
        
        if context.retrieved_cases:
            steps.append({
                'step': 'Case Retrieval',
                'description': f'Retrieved {len(context.retrieved_cases)} similar historical cases',
                'sample_cases': [c.get('summary', '')[:100] for c in context.retrieved_cases[:3]]
            })
        
        if context.bayesian_result:
            steps.append({
                'step': 'Bayesian Analysis',
                'description': f"Safety probability: {context.bayesian_result.get('prob_safe', 0):.1%}",
                'result': context.bayesian_result
            })
        
        if context.ai_adapter_results:
            adapter_summary = [
                {'adapter': r.adapter_name, 'category': r.category, 'confidence': r.confidence}
                for r in context.ai_adapter_results if r.success
            ]
            steps.append({
                'step': 'AI Tool Synthesis',
                'description': f'Synthesized {len(adapter_summary)} AI tool insights',
                'adapters': adapter_summary
            })
        
        return steps
    
    def _compute_hash(self, context: KineticsContext, response: str) -> str:
        """Compute hash for audit trail"""
        data = {
            'patient_id': context.patient.patient_id,
            'question': context.clinical_question,
            'response': response,
            'timestamp': datetime.utcnow().isoformat()
        }
        canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode()).hexdigest()
    
    def record_outcome(
        self,
        result: KineticsResult,
        actual_outcome: str,
        outcome_positive: bool,
        notes: Optional[str] = None
    ):
        """
        Record actual outcome for continuous learning.
        
        Args:
            result: The original Kinetics result
            actual_outcome: What actually happened
            outcome_positive: Whether outcome was positive
            notes: Additional notes
        """
        self._outcomes_db.append({
            'result_hash': result.hash,
            'timestamp': result.timestamp,
            'confidence': result.confidence,
            'actual_outcome': actual_outcome,
            'outcome_positive': outcome_positive,
            'notes': notes,
            'recorded_at': datetime.utcnow().isoformat() + "Z"
        })
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """Get statistics for continuous learning"""
        if not self._outcomes_db:
            return {'total_outcomes': 0, 'accuracy': None}
        
        positive = sum(1 for o in self._outcomes_db if o['outcome_positive'])
        total = len(self._outcomes_db)
        
        return {
            'total_outcomes': total,
            'positive_outcomes': positive,
            'accuracy': positive / total if total > 0 else None,
            'avg_confidence': sum(o['confidence'] for o in self._outcomes_db) / total
        }
