#!/usr/bin/env python3
"""
scispaCy Medical NLP for Grok Doc v2.0
Extract medical entities from clinical text

Capabilities:
- Named entity recognition (diseases, drugs, procedures)
- UMLS entity linking
- Negation detection
- Abbreviation expansion
- Section detection in clinical notes
"""

from typing import Dict, List, Optional, Tuple
import json

# scispaCy for medical NLP
try:
    import spacy
    from scispacy.linking import EntityLinker
    from scispacy.abbreviation import AbbreviationDetector
    SCISPACY_AVAILABLE = True
except ImportError:
    SCISPACY_AVAILABLE = False
    print("WARNING: scispaCy not installed. Run: pip install scispacy")
    print("Then download model: pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.3/en_core_sci_sm-0.5.3.tar.gz")


class MedicalNLPProcessor:
    """
    Medical NLP using scispaCy

    Models available:
    - en_core_sci_sm: Small general-purpose biomedical model
    - en_core_sci_md: Medium model with more vocab
    - en_ner_bc5cdr_md: Disease & chemical NER
    - en_ner_bionlp13cg_md: Cancer genetics NER
    """

    def __init__(self, model_name: str = "en_core_sci_sm"):
        """
        Initialize scispaCy NLP

        Args:
            model_name: scispaCy model to load
        """
        if not SCISPACY_AVAILABLE:
            raise ImportError("scispaCy required. Install with: pip install scispacy")

        try:
            self.nlp = spacy.load(model_name)

            # Add abbreviation detector
            self.nlp.add_pipe("abbreviation_detector")

            # Add entity linker (links to UMLS)
            self.nlp.add_pipe(
                "scispacy_linker",
                config={"resolve_abbreviations": True, "linker_name": "umls"}
            )

            print(f"Loaded scispaCy model: {model_name}")

        except OSError:
            print(f"Model {model_name} not found. Install with:")
            print(f"  pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.3/{model_name}-0.5.3.tar.gz")
            raise

    def extract_entities(self, text: str) -> Dict:
        """
        Extract medical entities from clinical text

        Args:
            text: Clinical note or report text

        Returns:
            {
                'diseases': List[Dict],
                'drugs': List[Dict],
                'procedures': List[Dict],
                'anatomy': List[Dict],
                'abbreviations': List[Dict],
                'all_entities': List[Dict]
            }
        """

        doc = self.nlp(text)

        entities = {
            'diseases': [],
            'drugs': [],
            'procedures': [],
            'anatomy': [],
            'abbreviations': [],
            'all_entities': []
        }

        # Extract named entities
        for ent in doc.ents:
            entity_info = {
                'text': ent.text,
                'label': ent.label_,
                'start': ent.start_char,
                'end': ent.end_char,
                'umls_codes': []
            }

            # Get UMLS codes
            if ent._.kb_ents:
                entity_info['umls_codes'] = [
                    {
                        'cui': cui,
                        'score': score,
                        'name': self.nlp.get_pipe("scispacy_linker").kb.cui_to_entity[cui].canonical_name
                    }
                    for cui, score in ent._.kb_ents[:3]  # Top 3 matches
                ]

            # Categorize by type
            if ent.label_ in ['DISEASE', 'SYMPTOM']:
                entities['diseases'].append(entity_info)
            elif ent.label_ in ['CHEMICAL', 'DRUG']:
                entities['drugs'].append(entity_info)
            elif ent.label_ == 'PROCEDURE':
                entities['procedures'].append(entity_info)
            elif ent.label_ in ['ANATOMY', 'ORGAN']:
                entities['anatomy'].append(entity_info)

            entities['all_entities'].append(entity_info)

        # Extract abbreviations
        for abrv in doc._.abbreviations:
            entities['abbreviations'].append({
                'abbreviation': abrv.text,
                'expansion': abrv._.long_form.text,
                'start': abrv.start_char,
                'end': abrv.end_char
            })

        return entities

    def detect_negation(self, text: str, target_entity: str) -> bool:
        """
        Detect if entity is negated

        Args:
            text: Clinical text
            target_entity: Entity to check (e.g., "pneumonia")

        Returns:
            True if negated, False otherwise
        """

        # Negation keywords
        negation_terms = [
            'no ', 'not ', 'without ', 'denies ', 'negative for ',
            'rules out ', 'ruled out ', 'absence of ', 'free of '
        ]

        # Simple window-based negation detection
        text_lower = text.lower()
        target_lower = target_entity.lower()

        # Find entity position
        entity_pos = text_lower.find(target_lower)
        if entity_pos == -1:
            return False

        # Check 50 characters before entity
        window_start = max(0, entity_pos - 50)
        window_text = text_lower[window_start:entity_pos]

        # Check for negation terms
        for neg_term in negation_terms:
            if neg_term in window_text:
                return True

        return False

    def extract_vitals(self, text: str) -> Dict:
        """
        Extract vital signs from clinical text

        Args:
            text: Clinical note

        Returns:
            Dict of vital signs
        """

        import re

        vitals = {}

        # Blood pressure
        bp_match = re.search(r'BP[:\s]+(\d+)/(\d+)', text, re.IGNORECASE)
        if bp_match:
            vitals['sbp'] = int(bp_match.group(1))
            vitals['dbp'] = int(bp_match.group(2))

        # Heart rate
        hr_match = re.search(r'HR[:\s]+(\d+)', text, re.IGNORECASE)
        if hr_match:
            vitals['hr'] = int(hr_match.group(1))

        # Temperature
        temp_match = re.search(r'(?:Temp|Temperature)[:\s]+(\d+\.?\d*)', text, re.IGNORECASE)
        if temp_match:
            vitals['temp'] = float(temp_match.group(1))

        # Respiratory rate
        rr_match = re.search(r'RR[:\s]+(\d+)', text, re.IGNORECASE)
        if rr_match:
            vitals['rr'] = int(rr_match.group(1))

        # SpO2
        spo2_match = re.search(r'(?:SpO2|O2 sat)[:\s]+(\d+)%?', text, re.IGNORECASE)
        if spo2_match:
            vitals['spo2'] = int(spo2_match.group(1))

        return vitals

    def extract_labs(self, text: str) -> Dict:
        """
        Extract lab values from clinical text

        Args:
            text: Clinical note or lab report

        Returns:
            Dict of lab values
        """

        import re

        labs = {}

        # Creatinine
        cr_match = re.search(r'(?:Cr|Creatinine)[:\s]+(\d+\.?\d*)', text, re.IGNORECASE)
        if cr_match:
            labs['creatinine'] = float(cr_match.group(1))

        # BUN
        bun_match = re.search(r'BUN[:\s]+(\d+)', text, re.IGNORECASE)
        if bun_match:
            labs['bun'] = int(bun_match.group(1))

        # WBC
        wbc_match = re.search(r'WBC[:\s]+(\d+\.?\d*)', text, re.IGNORECASE)
        if wbc_match:
            labs['wbc'] = float(wbc_match.group(1))

        # Hemoglobin
        hgb_match = re.search(r'(?:Hgb|Hemoglobin)[:\s]+(\d+\.?\d*)', text, re.IGNORECASE)
        if hgb_match:
            labs['hemoglobin'] = float(hgb_match.group(1))

        # Sodium
        na_match = re.search(r'(?:Na|Sodium)[:\s]+(\d+)', text, re.IGNORECASE)
        if na_match:
            labs['sodium'] = int(na_match.group(1))

        # Potassium
        k_match = re.search(r'(?:K|Potassium)[:\s]+(\d+\.?\d*)', text, re.IGNORECASE)
        if k_match:
            labs['potassium'] = float(k_match.group(1))

        return labs

    def structure_clinical_note(self, text: str) -> Dict:
        """
        Parse clinical note into structured sections

        Args:
            text: Full clinical note

        Returns:
            {
                'chief_complaint': str,
                'history_present_illness': str,
                'past_medical_history': str,
                'medications': List[str],
                'allergies': List[str],
                'physical_exam': str,
                'assessment_plan': str
            }
        """

        import re

        sections = {}

        # Chief Complaint
        cc_match = re.search(r'(?:Chief Complaint|CC)[:\s]+(.*?)(?=\n\n|\nHistory)', text, re.DOTALL | re.IGNORECASE)
        if cc_match:
            sections['chief_complaint'] = cc_match.group(1).strip()

        # HPI
        hpi_match = re.search(r'(?:History of Present Illness|HPI)[:\s]+(.*?)(?=\n\n|Past Medical)', text, re.DOTALL | re.IGNORECASE)
        if hpi_match:
            sections['history_present_illness'] = hpi_match.group(1).strip()

        # PMH
        pmh_match = re.search(r'(?:Past Medical History|PMH)[:\s]+(.*?)(?=\n\n|Medications)', text, re.DOTALL | re.IGNORECASE)
        if pmh_match:
            sections['past_medical_history'] = pmh_match.group(1).strip()

        # Medications
        meds_match = re.search(r'Medications[:\s]+(.*?)(?=\n\n|Allergies)', text, re.DOTALL | re.IGNORECASE)
        if meds_match:
            meds_text = meds_match.group(1).strip()
            sections['medications'] = [m.strip() for m in re.split(r'\n|,', meds_text) if m.strip()]

        # Allergies
        allergies_match = re.search(r'Allergies[:\s]+(.*?)(?=\n\n|Physical)', text, re.DOTALL | re.IGNORECASE)
        if allergies_match:
            allergies_text = allergies_match.group(1).strip()
            if 'nkda' in allergies_text.lower():
                sections['allergies'] = []
            else:
                sections['allergies'] = [a.strip() for a in re.split(r'\n|,', allergies_text) if a.strip()]

        # Physical Exam
        pe_match = re.search(r'(?:Physical Exam|PE)[:\s]+(.*?)(?=\n\n|Assessment)', text, re.DOTALL | re.IGNORECASE)
        if pe_match:
            sections['physical_exam'] = pe_match.group(1).strip()

        # Assessment & Plan
        ap_match = re.search(r'(?:Assessment and Plan|A/P|Assessment)[:\s]+(.*)', text, re.DOTALL | re.IGNORECASE)
        if ap_match:
            sections['assessment_plan'] = ap_match.group(1).strip()

        return sections


# Global NLP processor
_nlp_processor = None

def get_nlp_processor() -> MedicalNLPProcessor:
    """Get global NLP processor"""
    global _nlp_processor
    if _nlp_processor is None:
        _nlp_processor = MedicalNLPProcessor()
    return _nlp_processor


if __name__ == "__main__":
    print("scispaCy Medical NLP Processor")
    print(f"scispaCy available: {SCISPACY_AVAILABLE}")

    if SCISPACY_AVAILABLE:
        # Test with sample clinical text
        sample_text = """
        Patient is a 68-year-old male with history of COPD and hypertension who
        presents with shortness of breath and fever. Vitals: BP 145/92, HR 110,
        Temp 101.5F, SpO2 88% on room air. Labs: WBC 15.2, Cr 1.3, Na 138, K 4.2.
        CXR shows right lower lobe consolidation consistent with pneumonia.
        Assessment: Community-acquired pneumonia. Plan: Start ceftriaxone 1g IV daily
        and azithromycin 500mg PO daily.
        """

        processor = get_nlp_processor()

        print("\nExtracting entities...")
        entities = processor.extract_entities(sample_text)

        print(f"\nDiseases found: {len(entities['diseases'])}")
        for disease in entities['diseases']:
            print(f"  - {disease['text']} ({disease['label']})")

        print(f"\nDrugs found: {len(entities['drugs'])}")
        for drug in entities['drugs']:
            print(f"  - {drug['text']}")

        print("\nExtracted vitals:")
        vitals = processor.extract_vitals(sample_text)
        print(json.dumps(vitals, indent=2))

        print("\nExtracted labs:")
        labs = processor.extract_labs(sample_text)
        print(json.dumps(labs, indent=2))

        # Test negation
        is_negated = processor.detect_negation(sample_text, "pneumothorax")
        print(f"\nPneumothorax negated: {is_negated}")

    else:
        print("\nInstall scispaCy:")
        print("  pip install scispacy")
        print("  pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.3/en_core_sci_sm-0.5.3.tar.gz")
