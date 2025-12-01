"""
Adversarial Reasoning Stage for Grok Doc v2.5

Performs "red-team" testing of clinical recommendations by:
1. Generating counter-arguments and alternative diagnoses
2. Identifying potential risks and edge cases
3. Challenging the primary recommendation with devil's advocate reasoning
4. Scoring the robustness of the original recommendation
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json


@dataclass
class AdversarialInput:
    """Input for adversarial analysis"""
    primary_recommendation: str
    patient_context: Dict[str, Any]
    clinical_question: str
    original_confidence: float = 0.8
    bayesian_result: Optional[Dict] = None
    metadata: Optional[Dict] = None


@dataclass
class CounterArgument:
    """A structured counter-argument against the primary recommendation"""
    category: str  # "drug_interaction", "alternative_diagnosis", "edge_case", "contraindication"
    argument: str
    severity: str  # "low", "medium", "high", "critical"
    evidence_basis: str  # "clinical_guideline", "case_report", "theoretical", "patient_specific"
    mitigation: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'category': self.category,
            'argument': self.argument,
            'severity': self.severity,
            'evidence_basis': self.evidence_basis,
            'mitigation': self.mitigation
        }


@dataclass
class AdversarialResult:
    """Result from adversarial analysis"""
    original_recommendation: str
    counter_arguments: List[CounterArgument]
    alternative_diagnoses: List[str]
    identified_risks: List[str]
    edge_cases: List[str]
    robustness_score: float  # 0.0 to 1.0
    adjusted_confidence: float
    adversarial_summary: str
    recommendation_status: str  # "upheld", "modified", "requires_review", "rejected"
    timestamp: str
    hash: str
    model_used: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'original_recommendation': self.original_recommendation,
            'counter_arguments': [ca.to_dict() for ca in self.counter_arguments],
            'alternative_diagnoses': self.alternative_diagnoses,
            'identified_risks': self.identified_risks,
            'edge_cases': self.edge_cases,
            'robustness_score': self.robustness_score,
            'adjusted_confidence': self.adjusted_confidence,
            'adversarial_summary': self.adversarial_summary,
            'recommendation_status': self.recommendation_status,
            'timestamp': self.timestamp,
            'hash': self.hash,
            'model_used': self.model_used
        }


class AdversarialStage:
    """
    Adversarial reasoning stage that performs red-team testing
    of clinical recommendations.
    
    This stage acts as a "devil's advocate" to challenge primary
    recommendations, identify risks, and ensure robustness before
    final clinical decisions are made.
    """
    
    RISK_CATEGORIES = [
        "drug_interaction",
        "contraindication", 
        "dosing_error",
        "allergic_reaction",
        "renal_adjustment",
        "hepatic_adjustment",
        "age_related",
        "pregnancy_lactation",
        "alternative_diagnosis"
    ]
    
    SEVERITY_WEIGHTS = {
        "critical": 1.0,
        "high": 0.7,
        "medium": 0.4,
        "low": 0.2
    }
    
    def __init__(
        self,
        use_llm: bool = True,
        model_name: Optional[str] = None,
        min_counter_arguments: int = 3,
        risk_threshold: float = 0.3
    ):
        """
        Initialize Adversarial Stage.
        
        Args:
            use_llm: Whether to use LLM for analysis (if False, uses rule-based fallback)
            model_name: Specific model to use (if None, uses default)
            min_counter_arguments: Minimum counter-arguments to generate
            risk_threshold: Threshold above which to flag for review
        """
        self.use_llm = use_llm
        self.model_name = model_name
        self.min_counter_arguments = min_counter_arguments
        self.risk_threshold = risk_threshold
    
    def analyze(self, input_data: AdversarialInput) -> AdversarialResult:
        """
        Perform adversarial analysis on a primary recommendation.
        
        Args:
            input_data: AdversarialInput with recommendation and context
            
        Returns:
            AdversarialResult with counter-arguments and robustness assessment
        """
        if self.use_llm:
            try:
                return self._analyze_with_llm(input_data)
            except Exception as e:
                return self._analyze_fallback(input_data, fallback_reason=str(e))
        else:
            return self._analyze_fallback(input_data)
    
    def _analyze_with_llm(self, input_data: AdversarialInput) -> AdversarialResult:
        """Perform LLM-based adversarial analysis"""
        try:
            from local_inference import grok_query
        except ImportError:
            return self._analyze_fallback(input_data, fallback_reason="local_inference not available")
        
        prompt = self._build_adversarial_prompt(input_data)
        
        response = grok_query(
            prompt,
            temperature=0.1,
            max_tokens=1500,
            model_name=self.model_name
        )
        
        parsed = self._parse_llm_response(response, input_data)
        
        counter_arguments = parsed.get('counter_arguments', [])
        alternative_diagnoses = parsed.get('alternative_diagnoses', [])
        identified_risks = parsed.get('identified_risks', [])
        edge_cases = parsed.get('edge_cases', [])
        
        robustness_score = self._calculate_robustness_score(
            counter_arguments,
            input_data.original_confidence
        )
        
        adjusted_confidence = self._calculate_adjusted_confidence(
            input_data.original_confidence,
            robustness_score,
            counter_arguments
        )
        
        recommendation_status = self._determine_recommendation_status(
            robustness_score,
            adjusted_confidence,
            counter_arguments
        )
        
        adversarial_summary = self._generate_summary(
            counter_arguments,
            identified_risks,
            recommendation_status
        )
        
        result_hash = self._compute_hash(input_data, adversarial_summary)
        
        return AdversarialResult(
            original_recommendation=input_data.primary_recommendation,
            counter_arguments=counter_arguments,
            alternative_diagnoses=alternative_diagnoses,
            identified_risks=identified_risks,
            edge_cases=edge_cases,
            robustness_score=robustness_score,
            adjusted_confidence=adjusted_confidence,
            adversarial_summary=adversarial_summary,
            recommendation_status=recommendation_status,
            timestamp=datetime.utcnow().isoformat() + "Z",
            hash=result_hash,
            model_used=self.model_name or "default"
        )
    
    def _analyze_fallback(
        self,
        input_data: AdversarialInput,
        fallback_reason: Optional[str] = None
    ) -> AdversarialResult:
        """
        Rule-based fallback analysis when LLM is unavailable.
        
        Generates structured counter-arguments based on patient context
        and known clinical rules.
        """
        counter_arguments = []
        identified_risks = []
        edge_cases = []
        alternative_diagnoses = []
        
        patient = input_data.patient_context
        recommendation = input_data.primary_recommendation.lower()
        
        age = patient.get('age')
        if age is not None:
            if age >= 65:
                counter_arguments.append(CounterArgument(
                    category="age_related",
                    argument="Patient is elderly (≥65). Consider reduced dosing and increased monitoring for drug accumulation, falls risk, and cognitive effects.",
                    severity="medium",
                    evidence_basis="clinical_guideline",
                    mitigation="Start low, go slow. Monitor renal function and cognitive status."
                ))
                identified_risks.append("Elderly patient - increased sensitivity to medications")
                edge_cases.append("Age-related pharmacokinetic changes may affect drug clearance")
            elif age < 18:
                counter_arguments.append(CounterArgument(
                    category="age_related",
                    argument="Pediatric patient. Dosing may need weight-based adjustment. Some medications have different safety profiles in children.",
                    severity="medium",
                    evidence_basis="clinical_guideline",
                    mitigation="Verify weight-based dosing. Consult pediatric guidelines."
                ))
                identified_risks.append("Pediatric dosing considerations required")
        
        labs = patient.get('labs', {})
        
        creatinine = labs.get('creatinine') or labs.get('serum_creatinine')
        gfr = labs.get('gfr') or labs.get('egfr')
        
        if creatinine and isinstance(creatinine, (int, float)) and creatinine > 1.5:
            counter_arguments.append(CounterArgument(
                category="renal_adjustment",
                argument=f"Elevated creatinine ({creatinine}). Renally-cleared medications may accumulate. Dose adjustment required.",
                severity="high",
                evidence_basis="patient_specific",
                mitigation="Calculate CrCl/GFR and adjust renally-cleared drugs accordingly."
            ))
            identified_risks.append("Renal impairment - drug accumulation risk")
        
        if gfr and isinstance(gfr, (int, float)) and gfr < 60:
            severity = "critical" if gfr < 30 else "high"
            counter_arguments.append(CounterArgument(
                category="renal_adjustment",
                argument=f"Reduced GFR ({gfr}). Many medications require dose adjustment or are contraindicated.",
                severity=severity,
                evidence_basis="patient_specific",
                mitigation="Review all medications for renal dosing. Consider nephrology consultation."
            ))
            identified_risks.append(f"GFR {gfr} - significant renal impairment")
        
        alt = labs.get('alt') or labs.get('sgpt')
        ast = labs.get('ast') or labs.get('sgot')
        
        if alt and isinstance(alt, (int, float)) and alt > 80:
            counter_arguments.append(CounterArgument(
                category="hepatic_adjustment",
                argument=f"Elevated ALT ({alt}). Hepatically-metabolized drugs may have altered clearance.",
                severity="medium",
                evidence_basis="patient_specific",
                mitigation="Consider hepatic dosing adjustments. Monitor liver function."
            ))
            identified_risks.append("Elevated liver enzymes - hepatotoxicity risk")
        
        allergies = patient.get('allergies', [])
        if allergies:
            for allergy in allergies:
                if isinstance(allergy, str) and allergy.lower() in recommendation:
                    counter_arguments.append(CounterArgument(
                        category="allergic_reaction",
                        argument=f"ALERT: Patient has documented allergy to {allergy}. Recommendation may contain allergen.",
                        severity="critical",
                        evidence_basis="patient_specific",
                        mitigation="Verify no cross-reactivity. Consider alternative agent."
                    ))
                    identified_risks.append(f"Potential allergen exposure: {allergy}")
        
        medications = patient.get('medications', []) or patient.get('active_medications', [])
        if medications:
            high_risk_combos = [
                ('warfarin', 'nsaid', 'Warfarin + NSAID increases bleeding risk'),
                ('ace', 'potassium', 'ACE inhibitor + potassium may cause hyperkalemia'),
                ('metformin', 'contrast', 'Metformin + contrast may cause lactic acidosis'),
                ('ssri', 'maoi', 'SSRI + MAOI risk of serotonin syndrome'),
                ('opioid', 'benzodiazepine', 'Opioid + benzodiazepine increases respiratory depression risk'),
            ]
            
            med_str = ' '.join([str(m).lower() for m in medications])
            for drug1, drug2, warning in high_risk_combos:
                if drug1 in med_str or drug1 in recommendation:
                    if drug2 in med_str or drug2 in recommendation:
                        counter_arguments.append(CounterArgument(
                            category="drug_interaction",
                            argument=warning,
                            severity="high",
                            evidence_basis="clinical_guideline",
                            mitigation="Consider alternative therapy or enhanced monitoring."
                        ))
                        identified_risks.append(warning)
        
        counter_arguments.append(CounterArgument(
            category="alternative_diagnosis",
            argument="Consider whether the presenting symptoms could represent a different underlying condition that would change management.",
            severity="medium",
            evidence_basis="theoretical",
            mitigation="Review differential diagnosis before finalizing treatment."
        ))
        alternative_diagnoses.append("Consider broader differential diagnosis")
        
        edge_cases.append("Atypical presentation may mask underlying condition")
        edge_cases.append("Drug-drug interactions not captured in current medication list")
        edge_cases.append("Recent OTC or supplement use not documented")
        
        if fallback_reason:
            edge_cases.append(f"Analysis performed using rule-based fallback: {fallback_reason}")
        
        robustness_score = self._calculate_robustness_score(
            counter_arguments,
            input_data.original_confidence
        )
        
        adjusted_confidence = self._calculate_adjusted_confidence(
            input_data.original_confidence,
            robustness_score,
            counter_arguments
        )
        
        recommendation_status = self._determine_recommendation_status(
            robustness_score,
            adjusted_confidence,
            counter_arguments
        )
        
        adversarial_summary = self._generate_summary(
            counter_arguments,
            identified_risks,
            recommendation_status
        )
        
        result_hash = self._compute_hash(input_data, adversarial_summary)
        
        return AdversarialResult(
            original_recommendation=input_data.primary_recommendation,
            counter_arguments=counter_arguments,
            alternative_diagnoses=alternative_diagnoses,
            identified_risks=identified_risks,
            edge_cases=edge_cases,
            robustness_score=robustness_score,
            adjusted_confidence=adjusted_confidence,
            adversarial_summary=adversarial_summary,
            recommendation_status=recommendation_status,
            timestamp=datetime.utcnow().isoformat() + "Z",
            hash=result_hash,
            model_used="rule_based_fallback"
        )
    
    def _build_adversarial_prompt(self, input_data: AdversarialInput) -> str:
        """Build the adversarial analysis prompt for LLM"""
        patient = input_data.patient_context
        
        context_parts = []
        if patient.get('age'):
            context_parts.append(f"Age: {patient['age']}")
        if patient.get('gender'):
            context_parts.append(f"Gender: {patient['gender']}")
        if patient.get('weight'):
            context_parts.append(f"Weight: {patient['weight']} kg")
        if patient.get('labs'):
            labs_str = ", ".join([f"{k}: {v}" for k, v in patient['labs'].items()])
            context_parts.append(f"Labs: {labs_str}")
        if patient.get('allergies'):
            context_parts.append(f"Allergies: {', '.join(patient['allergies'])}")
        if patient.get('medications'):
            meds = patient['medications']
            if isinstance(meds, list):
                context_parts.append(f"Current Medications: {', '.join(str(m) for m in meds[:10])}")
        if patient.get('conditions') or patient.get('diagnoses'):
            conditions = patient.get('conditions') or patient.get('diagnoses', [])
            if isinstance(conditions, list):
                context_parts.append(f"Conditions: {', '.join(str(c) for c in conditions[:10])}")
        
        patient_context_str = "\n".join(context_parts) if context_parts else "Limited patient data available"
        
        bayesian_info = ""
        if input_data.bayesian_result:
            bayesian_info = f"""
BAYESIAN ANALYSIS:
- Safety Probability: {input_data.bayesian_result.get('prob_safe', 0):.1%}
- Based on {input_data.bayesian_result.get('n_cases', 0)} similar cases
"""
        
        return f"""You are a PARANOID clinical safety reviewer performing adversarial "red-team" analysis. 
Your job is to find EVERY possible reason why the proposed recommendation could be WRONG or HARMFUL.

PATIENT CONTEXT:
{patient_context_str}
{bayesian_info}
CLINICAL QUESTION:
{input_data.clinical_question}

PRIMARY RECOMMENDATION (Original Confidence: {input_data.original_confidence:.0%}):
{input_data.primary_recommendation}

TASK: Perform rigorous adversarial analysis. You MUST identify:

1. COUNTER-ARGUMENTS: At least 3 reasons this recommendation could be wrong or suboptimal
   - Drug interactions
   - Contraindications based on patient factors
   - Dosing concerns
   - Alternative interpretations

2. ALTERNATIVE DIAGNOSES: What else could explain the clinical picture?

3. RISKS: What are the specific risks if this recommendation is followed?

4. EDGE CASES: What unusual scenarios could make this recommendation dangerous?

FORMAT YOUR RESPONSE AS:

COUNTER-ARGUMENTS:
- [Category: drug_interaction/contraindication/dosing_error/alternative_diagnosis] [Severity: low/medium/high/critical] [Argument text]

ALTERNATIVE DIAGNOSES:
- [Diagnosis 1]
- [Diagnosis 2]

IDENTIFIED RISKS:
- [Risk 1]
- [Risk 2]

EDGE CASES:
- [Edge case 1]
- [Edge case 2]

OVERALL ASSESSMENT: [Brief summary of main concerns]"""
    
    def _parse_llm_response(
        self,
        response: str,
        input_data: AdversarialInput
    ) -> Dict[str, Any]:
        """Parse LLM response into structured components"""
        result = {
            'counter_arguments': [],
            'alternative_diagnoses': [],
            'identified_risks': [],
            'edge_cases': []
        }
        
        lines = response.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            line_lower = line.lower()
            if 'counter-argument' in line_lower or 'counter argument' in line_lower:
                current_section = 'counter_arguments'
                continue
            elif 'alternative diagnos' in line_lower:
                current_section = 'alternative_diagnoses'
                continue
            elif 'identified risk' in line_lower or 'risks:' in line_lower:
                current_section = 'identified_risks'
                continue
            elif 'edge case' in line_lower:
                current_section = 'edge_cases'
                continue
            elif 'overall assessment' in line_lower:
                current_section = None
                continue
            
            if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                content = line.lstrip('-•* ').strip()
                
                if current_section == 'counter_arguments' and content:
                    ca = self._parse_counter_argument(content)
                    if ca:
                        result['counter_arguments'].append(ca)
                elif current_section == 'alternative_diagnoses' and content:
                    result['alternative_diagnoses'].append(content)
                elif current_section == 'identified_risks' and content:
                    result['identified_risks'].append(content)
                elif current_section == 'edge_cases' and content:
                    result['edge_cases'].append(content)
        
        if len(result['counter_arguments']) < self.min_counter_arguments:
            fallback = self._analyze_fallback(input_data)
            for ca in fallback.counter_arguments:
                if len(result['counter_arguments']) < self.min_counter_arguments:
                    result['counter_arguments'].append(ca)
        
        return result
    
    def _parse_counter_argument(self, text: str) -> Optional[CounterArgument]:
        """Parse a single counter-argument from text"""
        category = "alternative_diagnosis"
        severity = "medium"
        
        text_lower = text.lower()
        
        for cat in self.RISK_CATEGORIES:
            if cat.replace('_', ' ') in text_lower or cat.replace('_', '-') in text_lower:
                category = cat
                break
        
        if 'drug' in text_lower and 'interact' in text_lower:
            category = "drug_interaction"
        elif 'contrain' in text_lower:
            category = "contraindication"
        elif 'dose' in text_lower or 'dosing' in text_lower:
            category = "dosing_error"
        elif 'allerg' in text_lower:
            category = "allergic_reaction"
        elif 'renal' in text_lower or 'kidney' in text_lower:
            category = "renal_adjustment"
        elif 'hepat' in text_lower or 'liver' in text_lower:
            category = "hepatic_adjustment"
        
        for sev in ['critical', 'high', 'medium', 'low']:
            if sev in text_lower:
                severity = sev
                break
        
        if 'fatal' in text_lower or 'death' in text_lower or 'lethal' in text_lower:
            severity = "critical"
        elif 'serious' in text_lower or 'severe' in text_lower:
            severity = "high"
        
        evidence_basis = "theoretical"
        if 'guideline' in text_lower or 'recommend' in text_lower:
            evidence_basis = "clinical_guideline"
        elif 'case' in text_lower or 'report' in text_lower:
            evidence_basis = "case_report"
        elif 'patient' in text_lower and ('specific' in text_lower or 'this' in text_lower):
            evidence_basis = "patient_specific"
        
        cleaned_text = text
        for marker in ['[critical]', '[high]', '[medium]', '[low]', 
                       '[drug_interaction]', '[contraindication]', '[dosing_error]',
                       '[alternative_diagnosis]', '[renal_adjustment]', '[hepatic_adjustment]']:
            cleaned_text = cleaned_text.replace(marker, '').replace(marker.upper(), '')
        cleaned_text = cleaned_text.strip()
        
        if len(cleaned_text) < 10:
            return None
        
        return CounterArgument(
            category=category,
            argument=cleaned_text,
            severity=severity,
            evidence_basis=evidence_basis,
            mitigation=None
        )
    
    def _calculate_robustness_score(
        self,
        counter_arguments: List[CounterArgument],
        original_confidence: float
    ) -> float:
        """
        Calculate robustness score based on counter-arguments.
        
        Higher score = recommendation is more robust (fewer/less severe issues)
        Lower score = recommendation has significant concerns
        """
        if not counter_arguments:
            return 0.9
        
        total_weight = 0.0
        for ca in counter_arguments:
            weight = self.SEVERITY_WEIGHTS.get(ca.severity, 0.3)
            if ca.category in ['contraindication', 'allergic_reaction']:
                weight *= 1.5
            total_weight += weight
        
        max_expected_weight = len(counter_arguments) * 0.7
        
        if max_expected_weight > 0:
            penalty = min(total_weight / max_expected_weight, 1.0) * 0.5
        else:
            penalty = 0.0
        
        robustness = max(0.1, min(0.95, original_confidence - penalty))
        
        return round(robustness, 3)
    
    def _calculate_adjusted_confidence(
        self,
        original_confidence: float,
        robustness_score: float,
        counter_arguments: List[CounterArgument]
    ) -> float:
        """Calculate adjusted confidence after adversarial testing"""
        critical_count = sum(1 for ca in counter_arguments if ca.severity == 'critical')
        high_count = sum(1 for ca in counter_arguments if ca.severity == 'high')
        
        if critical_count > 0:
            critical_penalty = 0.15 * critical_count
        else:
            critical_penalty = 0.0
        
        high_penalty = 0.08 * high_count
        
        adjusted = original_confidence * robustness_score - critical_penalty - high_penalty
        adjusted = max(0.05, min(0.95, adjusted))
        
        return round(adjusted, 3)
    
    def _determine_recommendation_status(
        self,
        robustness_score: float,
        adjusted_confidence: float,
        counter_arguments: List[CounterArgument]
    ) -> str:
        """Determine the status of the recommendation after adversarial review"""
        critical_count = sum(1 for ca in counter_arguments if ca.severity == 'critical')
        high_count = sum(1 for ca in counter_arguments if ca.severity == 'high')
        
        if critical_count > 0:
            return "requires_review"
        
        if high_count >= 3 or adjusted_confidence < 0.3:
            return "rejected"
        
        if high_count >= 1 or adjusted_confidence < 0.5:
            return "requires_review"
        
        if robustness_score >= 0.7 and adjusted_confidence >= 0.6:
            return "upheld"
        
        return "modified"
    
    def _generate_summary(
        self,
        counter_arguments: List[CounterArgument],
        identified_risks: List[str],
        recommendation_status: str
    ) -> str:
        """Generate a human-readable summary of the adversarial analysis"""
        status_descriptions = {
            "upheld": "Recommendation appears robust after adversarial review.",
            "modified": "Recommendation valid but modifications suggested.",
            "requires_review": "Significant concerns identified. Physician review required.",
            "rejected": "Multiple critical issues found. Recommendation not supported."
        }
        
        summary_parts = [status_descriptions.get(recommendation_status, "Analysis complete.")]
        
        critical = [ca for ca in counter_arguments if ca.severity == 'critical']
        high = [ca for ca in counter_arguments if ca.severity == 'high']
        
        if critical:
            summary_parts.append(f"CRITICAL ISSUES ({len(critical)}): {critical[0].argument[:100]}...")
        
        if high:
            summary_parts.append(f"High-severity concerns ({len(high)}): {high[0].argument[:80]}...")
        
        if identified_risks:
            summary_parts.append(f"Key risks: {'; '.join(identified_risks[:3])}")
        
        return " ".join(summary_parts)
    
    def _compute_hash(self, input_data: AdversarialInput, summary: str) -> str:
        """Compute hash for audit trail"""
        data = {
            'recommendation': input_data.primary_recommendation,
            'question': input_data.clinical_question,
            'summary': summary,
            'timestamp': datetime.utcnow().isoformat()
        }
        canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def run_adversarial_analysis(
    recommendation: str,
    patient_context: Dict[str, Any],
    clinical_question: str,
    original_confidence: float = 0.8,
    bayesian_result: Optional[Dict] = None,
    use_llm: bool = True,
    model_name: Optional[str] = None
) -> AdversarialResult:
    """
    Convenience function to run adversarial analysis.
    
    Args:
        recommendation: Primary clinical recommendation to challenge
        patient_context: Dict with patient data (age, gender, labs, medications, etc.)
        clinical_question: The original clinical question
        original_confidence: Confidence score of the primary recommendation
        bayesian_result: Optional Bayesian analysis results
        use_llm: Whether to use LLM (True) or rule-based fallback (False)
        model_name: Optional specific model to use
        
    Returns:
        AdversarialResult with counter-arguments and robustness assessment
    """
    stage = AdversarialStage(use_llm=use_llm, model_name=model_name)
    
    input_data = AdversarialInput(
        primary_recommendation=recommendation,
        patient_context=patient_context,
        clinical_question=clinical_question,
        original_confidence=original_confidence,
        bayesian_result=bayesian_result
    )
    
    return stage.analyze(input_data)
