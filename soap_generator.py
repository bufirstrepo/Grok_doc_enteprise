"""
SOAP Note Generator - Converts Multi-LLM Chain Output to Clinical Documentation

Transforms voice transcripts and chain reasoning into structured SOAP notes:
- Subjective: Patient's own words from transcript
- Objective: Labs, vitals, physical exam findings
- Assessment: Diagnosis/clinical reasoning from chain
- Plan: Treatment recommendations with safety scores
"""

from typing import Dict, List, Optional
from datetime import datetime
import re


class SOAPGenerator:
    """Generates SOAP notes from multi-LLM chain output"""

    def __init__(self):
        self.template_version = "2.0"

    def generate_soap(
        self,
        transcript: str,
        chain_result: Dict,
        patient_context: Optional[Dict] = None,
        include_citations: bool = True
    ) -> Dict:
        """
        Generate complete SOAP note from chain output

        Args:
            transcript: Voice transcript from physician
            chain_result: Output from run_multi_llm_decision()
            patient_context: Patient demographics, MRN, etc.
            include_citations: Include evidence citations

        Returns:
            {
                "soap_text": str,        # Formatted SOAP note
                "subjective": str,       # S section
                "objective": str,        # O section
                "assessment": str,       # A section
                "plan": str,            # P section
                "citations": List[str], # Evidence references
                "metadata": dict        # Billing codes, safety score, etc.
            }
        """
        # Extract components from transcript
        subjective = self._extract_subjective(transcript)
        objective = self._extract_objective(transcript)

        # Build assessment from chain reasoning
        assessment = self._build_assessment(chain_result, transcript)

        # Build plan from chain recommendation
        plan = self._build_plan(chain_result)

        # Extract citations
        citations = self._extract_citations(chain_result) if include_citations else []

        # Build metadata
        metadata = self._build_metadata(chain_result, patient_context)

        # Format complete SOAP note
        soap_text = self._format_soap(
            subjective, objective, assessment, plan,
            citations, metadata
        )

        return {
            "soap_text": soap_text,
            "subjective": subjective,
            "objective": objective,
            "assessment": assessment,
            "plan": plan,
            "citations": citations,
            "metadata": metadata
        }

    def _extract_subjective(self, transcript: str) -> str:
        """Extract subjective portion (patient's own words)"""
        # Look for chief complaint, HPI, symptoms
        subjective_keywords = [
            "patient reports", "patient states", "patient complains",
            "cc:", "chief complaint", "hpi:", "history of present illness",
            "symptoms", "pain", "fever", "nausea", "complains of"
        ]

        lines = transcript.split('\n')
        subjective_lines = []

        for line in lines:
            line_lower = line.lower()
            if any(kw in line_lower for kw in subjective_keywords):
                subjective_lines.append(line.strip())

        if subjective_lines:
            return "\n".join(subjective_lines)

        # Fallback: Use first part of transcript
        words = transcript.split()
        if len(words) > 50:
            return " ".join(words[:50]) + "..."
        return transcript

    def _extract_objective(self, transcript: str) -> str:
        """Extract objective findings (vitals, labs, exam)"""
        objective_keywords = [
            "vitals", "bp", "hr", "temp", "spo2", "rr",
            "labs", "cr", "wbc", "hgb", "plt",
            "physical exam", "pe:", "exam:", "auscultation",
            "palpation", "inspection", "percussion"
        ]

        lines = transcript.split('\n')
        objective_lines = []

        for line in lines:
            line_lower = line.lower()
            if any(kw in line_lower for kw in objective_keywords):
                objective_lines.append(line.strip())

        if objective_lines:
            return "\n".join(objective_lines)

        # Extract lab values with regex
        lab_pattern = r'([A-Z][a-z]+:?\s*[\d.]+)'
        labs = re.findall(lab_pattern, transcript)
        if labs:
            return "Labs: " + ", ".join(labs)

        return "No objective findings documented in transcript."

    def _build_assessment(self, chain_result: Dict, transcript: str) -> str:
        """Build assessment from chain reasoning"""
        assessment_parts = []

        # Add clinical reasoning from chain
        if 'chain_steps' in chain_result:
            for step in chain_result['chain_steps']:
                if step['step'] == 'Kinetics Model':
                    assessment_parts.append(f"**Pharmacokinetic Analysis:**\n{step['response']}")
                elif step['step'] == 'Adversarial Model':
                    assessment_parts.append(f"**Risk Assessment:**\n{step['response']}")
                elif step['step'] == 'Literature Model':
                    assessment_parts.append(f"**Evidence Review:**\n{step['response']}")

        # Add confidence score
        if 'final_confidence' in chain_result:
            confidence = chain_result['final_confidence']
            assessment_parts.append(
                f"\n**Clinical Decision Confidence:** {confidence:.1%}"
            )

        return "\n\n".join(assessment_parts) if assessment_parts else "Assessment pending."

    def _build_plan(self, chain_result: Dict) -> str:
        """Build plan from chain recommendation"""
        plan_parts = []

        # Main recommendation
        if 'final_recommendation' in chain_result:
            plan_parts.append(f"**Recommendation:**\n{chain_result['final_recommendation']}")

        # Safety monitoring
        if 'chain_steps' in chain_result:
            arbiter = next(
                (s for s in chain_result['chain_steps'] if s['step'] == 'Arbiter Model'),
                None
            )
            if arbiter:
                # Extract monitoring instructions
                response = arbiter['response']
                if 'monitor:' in response.lower():
                    monitor_match = re.search(r'monitor:\s*([^/]+)', response, re.IGNORECASE)
                    if monitor_match:
                        plan_parts.append(f"\n**Monitoring:**\n{monitor_match.group(1).strip()}")

        # Add follow-up
        plan_parts.append("\n**Follow-up:**\nReassess in 24-48 hours or PRN if symptoms worsen.")

        return "\n".join(plan_parts)

    def _extract_citations(self, chain_result: Dict) -> List[str]:
        """Extract evidence citations from chain"""
        citations = []

        if 'chain_steps' in chain_result:
            lit_model = next(
                (s for s in chain_result['chain_steps'] if s['step'] == 'Literature Model'),
                None
            )
            if lit_model:
                # Extract year patterns (e.g., "2024 IDSA guidelines", "CAMERA2 trial")
                response = lit_model['response']
                # Find guideline/trial references
                references = re.findall(
                    r'(\d{4}\s+[A-Z]{2,}\s+\w+|\w+\d+\s+trial|[A-Z]{2,}\d+\s+study)',
                    response
                )
                citations.extend(references)

        return list(set(citations))  # Unique citations

    def _build_metadata(self, chain_result: Dict, patient_context: Optional[Dict]) -> Dict:
        """Build metadata for billing/compliance"""
        metadata = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "template_version": self.template_version,
            "ai_assisted": True,
            "chain_mode": chain_result.get('total_steps', 0) > 1
        }

        # Add safety score
        if 'final_confidence' in chain_result:
            metadata['safety_score'] = chain_result['final_confidence']

        # Add chain verification status
        if 'chain_export' in chain_result:
            metadata['chain_verified'] = chain_result['chain_export'].get('chain_verified', False)

        # Add patient context
        if patient_context:
            metadata['mrn'] = patient_context.get('mrn')
            metadata['age'] = patient_context.get('age')
            metadata['gender'] = patient_context.get('gender')

        # Suggest billing codes (simplified - real system would be more sophisticated)
        metadata['suggested_codes'] = self._suggest_billing_codes(chain_result)

        return metadata

    def _suggest_billing_codes(self, chain_result: Dict) -> List[str]:
        """Suggest CPT/ICD codes based on complexity"""
        codes = []

        # E&M code based on complexity
        steps = chain_result.get('total_steps', 1)
        if steps >= 4:
            codes.append("99215")  # High complexity
        elif steps >= 2:
            codes.append("99214")  # Moderate complexity
        else:
            codes.append("99213")  # Low complexity

        return codes

    def _format_soap(
        self,
        subjective: str,
        objective: str,
        assessment: str,
        plan: str,
        citations: List[str],
        metadata: Dict
    ) -> str:
        """Format complete SOAP note"""
        sections = []

        # Header
        sections.append("=" * 60)
        sections.append("SOAP NOTE - AI-ASSISTED CLINICAL DOCUMENTATION")
        sections.append(f"Generated: {metadata['generated_at']}")
        if metadata.get('safety_score'):
            sections.append(f"Safety Score: {metadata['safety_score']:.1%}")
        if metadata.get('chain_verified'):
            sections.append("✓ Chain Integrity Verified")
        sections.append("=" * 60)
        sections.append("")

        # Subjective
        sections.append("SUBJECTIVE:")
        sections.append(subjective)
        sections.append("")

        # Objective
        sections.append("OBJECTIVE:")
        sections.append(objective)
        sections.append("")

        # Assessment
        sections.append("ASSESSMENT:")
        sections.append(assessment)
        sections.append("")

        # Plan
        sections.append("PLAN:")
        sections.append(plan)
        sections.append("")

        # Citations
        if citations:
            sections.append("EVIDENCE CITATIONS:")
            for i, citation in enumerate(citations, 1):
                sections.append(f"  {i}. {citation}")
            sections.append("")

        # Metadata footer
        sections.append("-" * 60)
        sections.append("BILLING/COMPLIANCE:")
        if metadata.get('suggested_codes'):
            sections.append(f"Suggested CPT: {', '.join(metadata['suggested_codes'])}")
        sections.append(f"AI Mode: {'Multi-LLM Chain' if metadata['chain_mode'] else 'Fast Mode'}")
        sections.append("⚠️ This is AI-assisted documentation requiring physician review and signature.")
        sections.append("-" * 60)

        return "\n".join(sections)


# Helper function for quick SOAP generation
def generate_soap_from_voice(
    transcript: str,
    chain_result: Dict,
    patient_context: Optional[Dict] = None
) -> str:
    """
    Quick SOAP generation (returns formatted text only)

    Args:
        transcript: Voice transcript
        chain_result: Multi-LLM chain output
        patient_context: Patient info

    Returns:
        Formatted SOAP note text
    """
    generator = SOAPGenerator()
    result = generator.generate_soap(transcript, chain_result, patient_context)
    return result['soap_text']


# Example usage
if __name__ == "__main__":
    # Mock data for testing
    mock_transcript = """
    Patient reports severe headache, 8/10 pain, started 2 hours ago.
    Associated with nausea and photophobia. No recent trauma.

    Vitals: BP 145/92, HR 88, Temp 98.6F, SpO2 99%

    Physical exam: Alert and oriented x3. PERRL. No focal neurological deficits.
    Neck supple, no meningismus.
    """

    mock_chain = {
        'final_recommendation': 'Migraine with aura. Recommend sumatriptan 100mg PO now.',
        'final_confidence': 0.89,
        'total_steps': 4,
        'chain_steps': [
            {
                'step': 'Kinetics Model',
                'response': 'Sumatriptan clearance normal for age/weight. Standard 100mg dose appropriate.'
            },
            {
                'step': 'Adversarial Model',
                'response': 'Risk: Check for contraindications - CAD, uncontrolled HTN (BP slightly elevated). Consider cardiac history.'
            },
            {
                'step': 'Literature Model',
                'response': '2024 AAN guidelines support triptans as first-line for moderate-severe migraine. CAMERA2 trial showed efficacy in 75% of patients.'
            },
            {
                'step': 'Arbiter Model',
                'response': 'Recommendation: Sumatriptan 100mg PO / Safety: 89% / Rationale: Classic migraine presentation, no cardiac contraindications / Monitor: BP, headache severity at 2hr'
            }
        ],
        'chain_export': {'chain_verified': True}
    }

    mock_patient = {
        'mrn': 'TEST12345',
        'age': 42,
        'gender': 'Female'
    }

    # Generate SOAP note
    soap = generate_soap_from_voice(mock_transcript, mock_chain, mock_patient)
    print(soap)
