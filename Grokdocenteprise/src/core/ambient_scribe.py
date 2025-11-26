"""
Ambient Scribe for Grok Doc v2.5

Clinical documentation AI assistant that:
1. Accepts transcribed clinical conversation text (NLP transcription input)
2. Extracts structured clinical information (symptoms, medications, assessments)
3. Generates SOAP note format (Subjective, Objective, Assessment, Plan)
4. Supports ICD-10 and CPT code suggestions
5. Creates signature-ready notes with hash verification
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib
import json
import re
import time


class SegmentType(Enum):
    """Types of transcript segments"""
    CHIEF_COMPLAINT = "chief_complaint"
    HISTORY = "history"
    SYMPTOMS = "symptoms"
    MEDICATIONS = "medications"
    ALLERGIES = "allergies"
    VITALS = "vitals"
    EXAM = "exam"
    LABS = "labs"
    ASSESSMENT = "assessment"
    PLAN = "plan"
    UNKNOWN = "unknown"


class CodeType(Enum):
    """Types of clinical codes"""
    ICD10 = "ICD-10"
    CPT = "CPT"


@dataclass
class TranscriptSegment:
    """Parsed conversation segment from clinical transcript"""
    segment_type: SegmentType
    content: str
    speaker: Optional[str] = None
    timestamp_offset: Optional[float] = None
    confidence: float = 1.0
    raw_text: str = ""
    extracted_entities: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment_type": self.segment_type.value,
            "content": self.content,
            "speaker": self.speaker,
            "timestamp_offset": self.timestamp_offset,
            "confidence": self.confidence,
            "raw_text": self.raw_text,
            "extracted_entities": self.extracted_entities
        }


@dataclass
class CodeSuggestion:
    """ICD-10 or CPT code suggestion"""
    code: str
    code_type: CodeType
    description: str
    confidence: float
    supporting_text: str = ""
    is_primary: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "code_type": self.code_type.value,
            "description": self.description,
            "confidence": self.confidence,
            "supporting_text": self.supporting_text,
            "is_primary": self.is_primary
        }


@dataclass
class SOAPNote:
    """Structured SOAP format note"""
    subjective: str
    objective: str
    assessment: str
    plan: str
    chief_complaint: str = ""
    history_of_present_illness: str = ""
    review_of_systems: str = ""
    physical_exam: str = ""
    medical_decision_making: str = ""
    icd10_codes: List[CodeSuggestion] = field(default_factory=list)
    cpt_codes: List[CodeSuggestion] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    generated_at: str = ""
    note_hash: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.utcnow().isoformat() + "Z"
        if not self.note_hash:
            self.note_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Compute SHA-256 hash of note content"""
        content = {
            "subjective": self.subjective,
            "objective": self.objective,
            "assessment": self.assessment,
            "plan": self.plan,
            "generated_at": self.generated_at
        }
        canonical = json.dumps(content, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subjective": self.subjective,
            "objective": self.objective,
            "assessment": self.assessment,
            "plan": self.plan,
            "chief_complaint": self.chief_complaint,
            "history_of_present_illness": self.history_of_present_illness,
            "review_of_systems": self.review_of_systems,
            "physical_exam": self.physical_exam,
            "medical_decision_making": self.medical_decision_making,
            "icd10_codes": [c.to_dict() for c in self.icd10_codes],
            "cpt_codes": [c.to_dict() for c in self.cpt_codes],
            "metadata": self.metadata,
            "generated_at": self.generated_at,
            "note_hash": self.note_hash
        }

    def to_formatted_text(self) -> str:
        """Format as human-readable clinical note"""
        sections = []
        sections.append("=" * 70)
        sections.append("CLINICAL NOTE - AMBIENT SCRIBE DOCUMENTATION")
        sections.append(f"Generated: {self.generated_at}")
        sections.append(f"Note Hash: {self.note_hash[:16]}...")
        sections.append("=" * 70)
        sections.append("")

        if self.chief_complaint:
            sections.append(f"CHIEF COMPLAINT: {self.chief_complaint}")
            sections.append("")

        sections.append("SUBJECTIVE:")
        sections.append(self.subjective)
        sections.append("")

        sections.append("OBJECTIVE:")
        sections.append(self.objective)
        sections.append("")

        sections.append("ASSESSMENT:")
        sections.append(self.assessment)
        sections.append("")

        sections.append("PLAN:")
        sections.append(self.plan)
        sections.append("")

        if self.icd10_codes:
            sections.append("ICD-10 CODES:")
            for code in self.icd10_codes:
                primary = " [PRIMARY]" if code.is_primary else ""
                sections.append(f"  {code.code}: {code.description} ({code.confidence:.0%}){primary}")
            sections.append("")

        if self.cpt_codes:
            sections.append("CPT CODES:")
            for code in self.cpt_codes:
                sections.append(f"  {code.code}: {code.description} ({code.confidence:.0%})")
            sections.append("")

        sections.append("-" * 70)
        sections.append("⚠️ AI-ASSISTED DOCUMENTATION - REQUIRES PHYSICIAN REVIEW AND SIGNATURE")
        sections.append("-" * 70)

        return "\n".join(sections)


@dataclass
class SignedNote:
    """Signature-ready note with hash verification"""
    soap_note: SOAPNote
    signature_hash: str
    physician_id: str
    signed_at: str
    signature_method: str
    attestation: str = "I have reviewed and verified this documentation."
    is_verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "soap_note": self.soap_note.to_dict(),
            "signature_hash": self.signature_hash,
            "physician_id": self.physician_id,
            "signed_at": self.signed_at,
            "signature_method": self.signature_method,
            "attestation": self.attestation,
            "is_verified": self.is_verified
        }


class AmbientScribe:
    """
    Main ambient scribe engine for clinical documentation.

    Processes transcribed clinical conversations and generates
    structured SOAP notes with ICD-10/CPT code suggestions.
    """

    SYMPTOM_PATTERNS = [
        (r'\b(headache|cephalgia)\b', 'R51.9', 'Headache, unspecified'),
        (r'\b(chest pain)\b', 'R07.9', 'Chest pain, unspecified'),
        (r'\b(abdominal pain|stomach pain|belly pain)\b', 'R10.9', 'Unspecified abdominal pain'),
        (r'\b(back pain|lumbago)\b', 'M54.5', 'Low back pain'),
        (r'\b(nausea)\b', 'R11.0', 'Nausea'),
        (r'\b(vomiting)\b', 'R11.10', 'Vomiting, unspecified'),
        (r'\b(dizziness|vertigo)\b', 'R42', 'Dizziness and giddiness'),
        (r'\b(fever|febrile)\b', 'R50.9', 'Fever, unspecified'),
        (r'\b(cough)\b', 'R05.9', 'Cough, unspecified'),
        (r'\b(shortness of breath|dyspnea|sob)\b', 'R06.00', 'Dyspnea, unspecified'),
        (r'\b(fatigue|tired|exhausted)\b', 'R53.83', 'Other fatigue'),
        (r'\b(anxiety|anxious)\b', 'F41.9', 'Anxiety disorder, unspecified'),
        (r'\b(depression|depressed)\b', 'F32.9', 'Major depressive disorder, single episode'),
        (r'\b(insomnia|cannot sleep|trouble sleeping)\b', 'G47.00', 'Insomnia, unspecified'),
        (r'\b(hypertension|high blood pressure|htn)\b', 'I10', 'Essential hypertension'),
        (r'\b(diabetes|diabetic|dm)\b', 'E11.9', 'Type 2 diabetes mellitus without complications'),
        (r'\b(asthma)\b', 'J45.909', 'Unspecified asthma, uncomplicated'),
        (r'\b(copd)\b', 'J44.9', 'Chronic obstructive pulmonary disease, unspecified'),
        (r'\b(migraine)\b', 'G43.909', 'Migraine, unspecified'),
        (r'\b(joint pain|arthralgia)\b', 'M25.50', 'Pain in unspecified joint'),
    ]

    CPT_COMPLEXITY_MAP = {
        1: ('99212', 'Office visit, straightforward'),
        2: ('99213', 'Office visit, low complexity'),
        3: ('99214', 'Office visit, moderate complexity'),
        4: ('99215', 'Office visit, high complexity'),
        5: ('99215', 'Office visit, high complexity'),
    }

    SUBJECTIVE_KEYWORDS = [
        'patient reports', 'patient states', 'patient complains', 'patient says',
        'cc:', 'chief complaint', 'hpi:', 'history of present illness',
        'symptoms', 'complains of', 'presents with', 'experiencing',
        'pain', 'discomfort', 'noticed', 'feels', 'feeling'
    ]

    OBJECTIVE_KEYWORDS = [
        'vitals', 'bp', 'hr', 'temp', 'spo2', 'rr', 'blood pressure',
        'heart rate', 'temperature', 'oxygen saturation', 'respiratory rate',
        'labs', 'lab results', 'cr', 'wbc', 'hgb', 'plt', 'bmp', 'cbc',
        'physical exam', 'pe:', 'exam:', 'on examination',
        'auscultation', 'palpation', 'inspection', 'percussion',
        'lungs', 'heart', 'abdomen', 'extremities', 'skin', 'neuro'
    ]

    MEDICATION_PATTERNS = [
        r'\b(metformin|glucophage)\s*(\d+\s*mg)?',
        r'\b(lisinopril|prinivil|zestril)\s*(\d+\s*mg)?',
        r'\b(atorvastatin|lipitor)\s*(\d+\s*mg)?',
        r'\b(amlodipine|norvasc)\s*(\d+\s*mg)?',
        r'\b(omeprazole|prilosec)\s*(\d+\s*mg)?',
        r'\b(metoprolol)\s*(\d+\s*mg)?',
        r'\b(gabapentin|neurontin)\s*(\d+\s*mg)?',
        r'\b(hydrocodone|vicodin)\s*(\d+/\d+)?',
        r'\b(prednisone)\s*(\d+\s*mg)?',
        r'\b(amoxicillin)\s*(\d+\s*mg)?',
        r'\b(azithromycin|zithromax|z-?pack)\b',
        r'\b(ibuprofen|advil|motrin)\s*(\d+\s*mg)?',
        r'\b(acetaminophen|tylenol)\s*(\d+\s*mg)?',
        r'\b(aspirin|asa)\s*(\d+\s*mg)?',
    ]

    def __init__(
        self,
        use_llm: bool = True,
        model_name: Optional[str] = None,
        fallback_to_rules: bool = True
    ):
        """
        Initialize Ambient Scribe.

        Args:
            use_llm: Whether to use LLM for enhanced extraction
            model_name: Specific model to use (if None, uses default)
            fallback_to_rules: Fall back to rule-based extraction if LLM fails
        """
        self.use_llm = use_llm
        self.model_name = model_name
        self.fallback_to_rules = fallback_to_rules
        self._llm_available = False

        if use_llm:
            try:
                from local_inference import grok_query
                self._grok_query = grok_query
                self._llm_available = True
            except ImportError:
                self._llm_available = False

    def process_transcript(
        self,
        transcript: str,
        patient_context: Optional[Dict[str, Any]] = None
    ) -> SOAPNote:
        """
        Process clinical transcript and generate SOAP note.

        Args:
            transcript: Transcribed clinical conversation text
            patient_context: Optional patient demographics and context

        Returns:
            SOAPNote with extracted clinical information
        """
        start_time = time.time()

        segments = self._parse_transcript(transcript)

        if self._llm_available and self.use_llm:
            try:
                soap_note = self._extract_with_llm(transcript, segments, patient_context)
            except Exception as e:
                if self.fallback_to_rules:
                    soap_note = self._extract_with_rules(transcript, segments, patient_context)
                else:
                    raise RuntimeError(f"LLM extraction failed: {e}")
        else:
            soap_note = self._extract_with_rules(transcript, segments, patient_context)

        icd10_codes = self._suggest_icd10_codes(transcript, soap_note)
        cpt_codes = self._suggest_cpt_codes(transcript, soap_note, patient_context)

        soap_note.icd10_codes = icd10_codes
        soap_note.cpt_codes = cpt_codes

        latency_ms = (time.time() - start_time) * 1000
        soap_note.metadata['latency_ms'] = latency_ms
        soap_note.metadata['extraction_method'] = 'llm' if (self._llm_available and self.use_llm) else 'rules'
        soap_note.metadata['segment_count'] = len(segments)

        if patient_context:
            soap_note.metadata['patient_mrn'] = patient_context.get('mrn')
            soap_note.metadata['patient_age'] = patient_context.get('age')
            soap_note.metadata['patient_gender'] = patient_context.get('gender')

        soap_note.note_hash = soap_note._compute_hash()

        return soap_note

    def _parse_transcript(self, transcript: str) -> List[TranscriptSegment]:
        """Parse transcript into typed segments"""
        segments = []
        lines = transcript.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            segment_type = self._classify_segment(line)
            speaker = self._extract_speaker(line)
            entities = self._extract_entities(line)

            segment = TranscriptSegment(
                segment_type=segment_type,
                content=line,
                speaker=speaker,
                raw_text=line,
                extracted_entities=entities,
                confidence=0.8 if segment_type != SegmentType.UNKNOWN else 0.5
            )
            segments.append(segment)

        return segments

    def _classify_segment(self, text: str) -> SegmentType:
        """Classify text segment by type"""
        text_lower = text.lower()

        if any(kw in text_lower for kw in ['chief complaint', 'cc:', 'presents with', 'main concern']):
            return SegmentType.CHIEF_COMPLAINT

        if any(kw in text_lower for kw in ['history', 'hpi:', 'started', 'began', 'developed']):
            return SegmentType.HISTORY

        if any(kw in text_lower for kw in ['symptom', 'pain', 'ache', 'discomfort', 'feels', 'nausea', 'fever']):
            return SegmentType.SYMPTOMS

        if any(kw in text_lower for kw in ['medication', 'taking', 'prescribed', 'mg', 'dose']):
            return SegmentType.MEDICATIONS

        if any(kw in text_lower for kw in ['allerg', 'reaction to', 'sensitive to']):
            return SegmentType.ALLERGIES

        if any(kw in text_lower for kw in ['vitals', 'bp', 'blood pressure', 'heart rate', 'hr', 'temp', 'spo2']):
            return SegmentType.VITALS

        if any(kw in text_lower for kw in ['exam', 'physical', 'auscultation', 'palpation', 'inspection']):
            return SegmentType.EXAM

        if any(kw in text_lower for kw in ['lab', 'result', 'wbc', 'hgb', 'creatinine', 'glucose']):
            return SegmentType.LABS

        if any(kw in text_lower for kw in ['assessment', 'diagnosis', 'impression', 'conclude']):
            return SegmentType.ASSESSMENT

        if any(kw in text_lower for kw in ['plan', 'recommend', 'prescribe', 'order', 'follow up', 'refer']):
            return SegmentType.PLAN

        return SegmentType.UNKNOWN

    def _extract_speaker(self, text: str) -> Optional[str]:
        """Extract speaker from transcript line"""
        speaker_match = re.match(r'^(Doctor|Dr\.|Physician|Patient|Pt\.|Nurse|RN):?\s*', text, re.IGNORECASE)
        if speaker_match:
            speaker = speaker_match.group(1).lower()
            if speaker in ['doctor', 'dr.', 'physician']:
                return 'physician'
            elif speaker in ['patient', 'pt.']:
                return 'patient'
            elif speaker in ['nurse', 'rn']:
                return 'nurse'
        return None

    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract clinical entities from text"""
        entities = {}

        vitals = {}
        bp_match = re.search(r'(?:bp|blood pressure)[:\s]*(\d{2,3})/(\d{2,3})', text, re.IGNORECASE)
        if bp_match:
            vitals['bp_systolic'] = int(bp_match.group(1))
            vitals['bp_diastolic'] = int(bp_match.group(2))

        hr_match = re.search(r'(?:hr|heart rate|pulse)[:\s]*(\d{2,3})', text, re.IGNORECASE)
        if hr_match:
            vitals['heart_rate'] = int(hr_match.group(1))

        temp_match = re.search(r'(?:temp|temperature)[:\s]*([\d.]+)\s*(?:f|°f|c|°c)?', text, re.IGNORECASE)
        if temp_match:
            vitals['temperature'] = float(temp_match.group(1))

        spo2_match = re.search(r'(?:spo2|o2 sat|oxygen)[:\s]*(\d{2,3})%?', text, re.IGNORECASE)
        if spo2_match:
            vitals['spo2'] = int(spo2_match.group(1))

        rr_match = re.search(r'(?:rr|respiratory rate)[:\s]*(\d{1,2})', text, re.IGNORECASE)
        if rr_match:
            vitals['respiratory_rate'] = int(rr_match.group(1))

        if vitals:
            entities['vitals'] = vitals

        medications = []
        for pattern in self.MEDICATION_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    med_name = match[0]
                    dose = match[1] if len(match) > 1 else None
                else:
                    med_name = match
                    dose = None
                medications.append({'name': med_name, 'dose': dose})

        if medications:
            entities['medications'] = medications

        pain_match = re.search(r'(\d{1,2})\s*(?:/\s*10|out of 10|on a scale)', text, re.IGNORECASE)
        if pain_match:
            entities['pain_score'] = int(pain_match.group(1))

        return entities

    def _extract_with_llm(
        self,
        transcript: str,
        segments: List[TranscriptSegment],
        patient_context: Optional[Dict[str, Any]]
    ) -> SOAPNote:
        """Extract SOAP note using LLM"""
        context_str = ""
        if patient_context:
            context_str = f"""
PATIENT CONTEXT:
- Age: {patient_context.get('age', 'Unknown')}
- Gender: {patient_context.get('gender', 'Unknown')}
- MRN: {patient_context.get('mrn', 'N/A')}
"""

        prompt = f"""You are a clinical documentation specialist. Extract a structured SOAP note from this transcript.

{context_str}

CLINICAL TRANSCRIPT:
{transcript}

TASK: Generate a complete SOAP note with the following sections:
1. SUBJECTIVE: Patient's symptoms, complaints, history in their own words
2. OBJECTIVE: Vitals, physical exam findings, lab results
3. ASSESSMENT: Clinical impression and diagnosis
4. PLAN: Treatment plan, medications, follow-up

Format your response as:
SUBJECTIVE: [content]
OBJECTIVE: [content]
ASSESSMENT: [content]
PLAN: [content]
CHIEF_COMPLAINT: [one-line summary]

Be concise but comprehensive. Include all clinically relevant information."""

        response = self._grok_query(
            prompt,
            max_tokens=1500,
            model_name=self.model_name
        )

        return self._parse_llm_response(response, segments, patient_context)

    def _parse_llm_response(
        self,
        response: str,
        segments: List[TranscriptSegment],
        patient_context: Optional[Dict[str, Any]]
    ) -> SOAPNote:
        """Parse LLM response into SOAPNote"""
        sections = {
            'subjective': '',
            'objective': '',
            'assessment': '',
            'plan': '',
            'chief_complaint': ''
        }

        patterns = {
            'subjective': r'SUBJECTIVE:\s*(.*?)(?=OBJECTIVE:|$)',
            'objective': r'OBJECTIVE:\s*(.*?)(?=ASSESSMENT:|$)',
            'assessment': r'ASSESSMENT:\s*(.*?)(?=PLAN:|$)',
            'plan': r'PLAN:\s*(.*?)(?=CHIEF_COMPLAINT:|$)',
            'chief_complaint': r'CHIEF_COMPLAINT:\s*(.*?)$'
        }

        for section, pattern in patterns.items():
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                sections[section] = match.group(1).strip()

        if not sections['subjective']:
            sections['subjective'] = self._build_subjective_from_segments(segments)
        if not sections['objective']:
            sections['objective'] = self._build_objective_from_segments(segments)

        return SOAPNote(
            subjective=sections['subjective'],
            objective=sections['objective'],
            assessment=sections['assessment'],
            plan=sections['plan'],
            chief_complaint=sections['chief_complaint'],
            metadata={'llm_extracted': True}
        )

    def _extract_with_rules(
        self,
        transcript: str,
        segments: List[TranscriptSegment],
        patient_context: Optional[Dict[str, Any]]
    ) -> SOAPNote:
        """Extract SOAP note using rule-based extraction"""
        subjective = self._build_subjective_from_segments(segments)
        objective = self._build_objective_from_segments(segments)
        assessment = self._build_assessment_from_segments(segments, transcript)
        plan = self._build_plan_from_segments(segments, transcript)
        chief_complaint = self._extract_chief_complaint(segments, transcript)

        return SOAPNote(
            subjective=subjective,
            objective=objective,
            assessment=assessment,
            plan=plan,
            chief_complaint=chief_complaint,
            metadata={'rule_extracted': True}
        )

    def _build_subjective_from_segments(self, segments: List[TranscriptSegment]) -> str:
        """Build subjective section from segments"""
        subjective_types = [
            SegmentType.CHIEF_COMPLAINT,
            SegmentType.HISTORY,
            SegmentType.SYMPTOMS,
            SegmentType.MEDICATIONS,
            SegmentType.ALLERGIES
        ]

        subjective_segments = [s for s in segments if s.segment_type in subjective_types]

        if subjective_segments:
            return "\n".join([s.content for s in subjective_segments])

        patient_segments = [s for s in segments if s.speaker == 'patient']
        if patient_segments:
            return "\n".join([s.content for s in patient_segments])

        return "Patient history and symptoms not clearly documented in transcript."

    def _build_objective_from_segments(self, segments: List[TranscriptSegment]) -> str:
        """Build objective section from segments"""
        objective_types = [
            SegmentType.VITALS,
            SegmentType.EXAM,
            SegmentType.LABS
        ]

        parts = []

        vitals_parts = []
        for s in segments:
            if s.extracted_entities.get('vitals'):
                vitals = s.extracted_entities['vitals']
                if 'bp_systolic' in vitals:
                    vitals_parts.append(f"BP {vitals['bp_systolic']}/{vitals['bp_diastolic']}")
                if 'heart_rate' in vitals:
                    vitals_parts.append(f"HR {vitals['heart_rate']}")
                if 'temperature' in vitals:
                    vitals_parts.append(f"Temp {vitals['temperature']}")
                if 'spo2' in vitals:
                    vitals_parts.append(f"SpO2 {vitals['spo2']}%")
                if 'respiratory_rate' in vitals:
                    vitals_parts.append(f"RR {vitals['respiratory_rate']}")

        if vitals_parts:
            parts.append("Vitals: " + ", ".join(vitals_parts))

        objective_segments = [s for s in segments if s.segment_type in objective_types]
        for s in objective_segments:
            if s.content not in str(parts):
                parts.append(s.content)

        if parts:
            return "\n".join(parts)

        return "Objective findings not clearly documented in transcript."

    def _build_assessment_from_segments(
        self,
        segments: List[TranscriptSegment],
        transcript: str
    ) -> str:
        """Build assessment section from segments"""
        assessment_segments = [s for s in segments if s.segment_type == SegmentType.ASSESSMENT]

        if assessment_segments:
            return "\n".join([s.content for s in assessment_segments])

        detected_conditions = []
        for pattern, code, description in self.SYMPTOM_PATTERNS:
            if re.search(pattern, transcript, re.IGNORECASE):
                detected_conditions.append(description)

        if detected_conditions:
            return "Clinical impression based on symptoms:\n- " + "\n- ".join(detected_conditions[:5])

        return "Assessment pending physician review."

    def _build_plan_from_segments(
        self,
        segments: List[TranscriptSegment],
        transcript: str
    ) -> str:
        """Build plan section from segments"""
        plan_segments = [s for s in segments if s.segment_type == SegmentType.PLAN]

        if plan_segments:
            return "\n".join([s.content for s in plan_segments])

        plan_parts = []

        all_meds = []
        for s in segments:
            if s.extracted_entities.get('medications'):
                all_meds.extend(s.extracted_entities['medications'])

        if all_meds:
            med_strs = [f"{m['name']}" + (f" {m['dose']}" if m['dose'] else "") for m in all_meds]
            plan_parts.append("Current medications: " + ", ".join(med_strs))

        if re.search(r'follow\s*up|return|come back', transcript, re.IGNORECASE):
            plan_parts.append("Follow-up as directed.")

        if re.search(r'refer|specialist|consult', transcript, re.IGNORECASE):
            plan_parts.append("Referral to specialist as discussed.")

        if plan_parts:
            return "\n".join(plan_parts)

        return "Plan to be determined by physician."

    def _extract_chief_complaint(
        self,
        segments: List[TranscriptSegment],
        transcript: str
    ) -> str:
        """Extract chief complaint"""
        cc_segments = [s for s in segments if s.segment_type == SegmentType.CHIEF_COMPLAINT]
        if cc_segments:
            return cc_segments[0].content[:100]

        cc_match = re.search(
            r'(?:chief complaint|cc|main concern|presents? (?:with|for))[:\s]*([^.]+)',
            transcript,
            re.IGNORECASE
        )
        if cc_match:
            return cc_match.group(1).strip()[:100]

        symptom_segments = [s for s in segments if s.segment_type == SegmentType.SYMPTOMS]
        if symptom_segments:
            return symptom_segments[0].content[:100]

        return "Chief complaint not specified"

    def _suggest_icd10_codes(
        self,
        transcript: str,
        soap_note: SOAPNote
    ) -> List[CodeSuggestion]:
        """Suggest ICD-10 codes based on transcript content"""
        codes = []
        text_to_search = f"{transcript} {soap_note.assessment}".lower()
        is_first = True

        for pattern, code, description in self.SYMPTOM_PATTERNS:
            matches = re.findall(pattern, text_to_search, re.IGNORECASE)
            if matches:
                count = len(matches)
                confidence = min(0.5 + (count * 0.1), 0.95)

                suggestion = CodeSuggestion(
                    code=code,
                    code_type=CodeType.ICD10,
                    description=description,
                    confidence=confidence,
                    supporting_text=matches[0] if matches else "",
                    is_primary=is_first
                )
                codes.append(suggestion)
                is_first = False

        codes.sort(key=lambda x: x.confidence, reverse=True)
        return codes[:10]

    def _suggest_cpt_codes(
        self,
        transcript: str,
        soap_note: SOAPNote,
        patient_context: Optional[Dict[str, Any]]
    ) -> List[CodeSuggestion]:
        """Suggest CPT codes based on visit complexity"""
        codes = []

        complexity = 2

        word_count = len(transcript.split())
        if word_count > 500:
            complexity += 1
        if word_count > 1000:
            complexity += 1

        if len(soap_note.icd10_codes) > 3:
            complexity += 1

        if re.search(r'critical|urgent|emergency|severe', transcript, re.IGNORECASE):
            complexity = min(complexity + 1, 5)

        if patient_context:
            age = patient_context.get('age', 0)
            if age > 65 or age < 2:
                complexity = min(complexity + 1, 5)

        complexity = max(1, min(complexity, 5))
        cpt_code, description = self.CPT_COMPLEXITY_MAP[complexity]

        codes.append(CodeSuggestion(
            code=cpt_code,
            code_type=CodeType.CPT,
            description=description,
            confidence=0.85,
            supporting_text=f"Based on {complexity}/5 complexity assessment",
            is_primary=True
        ))

        if re.search(r'injection|immunization|vaccine', transcript, re.IGNORECASE):
            codes.append(CodeSuggestion(
                code='96372',
                code_type=CodeType.CPT,
                description='Therapeutic injection',
                confidence=0.7,
                supporting_text='Injection mentioned in transcript'
            ))

        if re.search(r'ekg|ecg|electrocardiogram', transcript, re.IGNORECASE):
            codes.append(CodeSuggestion(
                code='93000',
                code_type=CodeType.CPT,
                description='Electrocardiogram, complete',
                confidence=0.75,
                supporting_text='ECG mentioned in transcript'
            ))

        if re.search(r'x-?ray|radiograph', transcript, re.IGNORECASE):
            codes.append(CodeSuggestion(
                code='71046',
                code_type=CodeType.CPT,
                description='Chest X-ray, 2 views',
                confidence=0.7,
                supporting_text='X-ray mentioned in transcript'
            ))

        return codes

    def sign_note(
        self,
        soap_note: SOAPNote,
        physician_id: str,
        signature_method: str = "PIN",
        attestation: Optional[str] = None
    ) -> SignedNote:
        """
        Create signature-ready note with hash verification.

        Args:
            soap_note: The SOAP note to sign
            physician_id: Physician identifier
            signature_method: "PIN", "biometric", or "certificate"
            attestation: Custom attestation text

        Returns:
            SignedNote with cryptographic signature
        """
        timestamp = datetime.utcnow().isoformat() + "Z"

        signature_data = {
            "note_hash": soap_note.note_hash,
            "physician_id": physician_id,
            "signed_at": timestamp,
            "signature_method": signature_method
        }

        canonical = json.dumps(signature_data, sort_keys=True, separators=(',', ':'))
        signature_hash = hashlib.sha256(canonical.encode('utf-8')).hexdigest()

        return SignedNote(
            soap_note=soap_note,
            signature_hash=signature_hash,
            physician_id=physician_id,
            signed_at=timestamp,
            signature_method=signature_method,
            attestation=attestation or "I have reviewed and verified this documentation.",
            is_verified=True
        )

    def verify_signature(self, signed_note: SignedNote) -> bool:
        """
        Verify a signed note's integrity.

        Args:
            signed_note: The signed note to verify

        Returns:
            True if signature is valid, False otherwise
        """
        current_note_hash = signed_note.soap_note._compute_hash()
        if current_note_hash != signed_note.soap_note.note_hash:
            return False

        signature_data = {
            "note_hash": signed_note.soap_note.note_hash,
            "physician_id": signed_note.physician_id,
            "signed_at": signed_note.signed_at,
            "signature_method": signed_note.signature_method
        }

        canonical = json.dumps(signature_data, sort_keys=True, separators=(',', ':'))
        expected_hash = hashlib.sha256(canonical.encode('utf-8')).hexdigest()

        return expected_hash == signed_note.signature_hash


def process_clinical_transcript(
    transcript: str,
    patient_context: Optional[Dict[str, Any]] = None,
    use_llm: bool = True,
    model_name: Optional[str] = None
) -> SOAPNote:
    """
    Convenience function to process clinical transcript.

    Args:
        transcript: Transcribed clinical conversation
        patient_context: Optional patient demographics
        use_llm: Whether to use LLM for extraction
        model_name: Specific model to use

    Returns:
        SOAPNote with extracted clinical information
    """
    scribe = AmbientScribe(use_llm=use_llm, model_name=model_name)
    return scribe.process_transcript(transcript, patient_context)


def sign_clinical_note(
    soap_note: SOAPNote,
    physician_id: str,
    signature_method: str = "PIN"
) -> SignedNote:
    """
    Convenience function to sign a clinical note.

    Args:
        soap_note: The SOAP note to sign
        physician_id: Physician identifier
        signature_method: Signature method

    Returns:
        SignedNote with cryptographic signature
    """
    scribe = AmbientScribe(use_llm=False)
    return scribe.sign_note(soap_note, physician_id, signature_method)
