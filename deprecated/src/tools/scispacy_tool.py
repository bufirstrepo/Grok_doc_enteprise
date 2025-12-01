#!/usr/bin/env python3
"""
sciSpaCy Medical NLP Tool for CrewAI
Wraps medical_nlp.py for use by nlp_agent
"""

from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import sys
import os

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

# Import from root (medical_nlp is still there)
from medical_nlp import get_nlp_pipeline, extract_clinical_entities


class ScispacyToolInput(BaseModel):
    """Input schema for sciSpaCy NLP analysis"""
    clinical_text: str = Field(..., description="Clinical text to analyze (note, transcript, report)")
    extract_type: str = Field(default="all", description="Entity type: 'all', 'medications', 'diagnoses', 'procedures', 'labs'")


class ScispacyTool(BaseTool):
    """
    Medical NLP using sciSpaCy

    Extracts clinical entities from unstructured text:
    - Medications (with dosages)
    - Diagnoses and conditions
    - Procedures and treatments
    - Lab values and vital signs
    - Anatomical terms
    - UMLS concept linking

    Used by: nlp_agent (NLP Agent), for processing clinical notes
    """

    name: str = "sciSpaCy Medical NLP"
    description: str = """Extract medical entities from clinical text using sciSpaCy NLP.
    Identifies medications, diagnoses, procedures, labs, and links to UMLS concepts.
    Processes physician notes, transcripts, and clinical documentation."""
    args_schema: Type[BaseModel] = ScispacyToolInput

    def _run(self, clinical_text: str, extract_type: str = "all") -> str:
        """
        Extract clinical entities using sciSpaCy

        Args:
            clinical_text: Clinical text (note, transcript, report)
            extract_type: 'all', 'medications', 'diagnoses', 'procedures', 'labs'

        Returns:
            Structured entity extraction report for nlp_agent
        """
        try:
            nlp = get_nlp_pipeline()
            entities = extract_clinical_entities(clinical_text, nlp)

            if extract_type == "all":
                return self._format_all_entities(entities, clinical_text)
            elif extract_type == "medications":
                return self._format_medications(entities)
            elif extract_type == "diagnoses":
                return self._format_diagnoses(entities)
            elif extract_type == "procedures":
                return self._format_procedures(entities)
            elif extract_type == "labs":
                return self._format_labs(entities)
            else:
                return f"Unknown extract_type: '{extract_type}'. Use 'all', 'medications', 'diagnoses', 'procedures', or 'labs'."

        except Exception as e:
            return f"""=== NLP EXTRACTION FAILED ===
Error: {str(e)}

Recommendation: Process clinical text manually.
sciSpaCy models may not be installed (run: pip install scispacy en_core_sci_md)
"""

    def _format_all_entities(self, entities: dict, text: str) -> str:
        """Format all extracted entities"""
        meds = entities.get('medications', [])
        diagnoses = entities.get('diagnoses', [])
        procedures = entities.get('procedures', [])
        labs = entities.get('lab_values', [])
        umls = entities.get('umls_concepts', [])

        output = f"""=== CLINICAL NLP EXTRACTION ===

Text Length: {len(text)} characters

MEDICATIONS ({len(meds)}):
{self._format_list(meds)}

DIAGNOSES ({len(diagnoses)}):
{self._format_list(diagnoses)}

PROCEDURES ({len(procedures)}):
{self._format_list(procedures)}

LAB VALUES ({len(labs)}):
{self._format_list(labs)}

UMLS CONCEPTS ({len(umls)}):
{self._format_umls(umls)}

Recommendation: Review extracted entities for accuracy.
"""
        return output

    def _format_medications(self, entities: dict) -> str:
        """Format medication entities"""
        meds = entities.get('medications', [])

        output = f"""=== MEDICATION EXTRACTION ===

Total Medications: {len(meds)}

"""
        for med in meds:
            output += f"""  • {med['text']}
    Dose: {med.get('dose', 'Not specified')}
    Route: {med.get('route', 'Not specified')}
    Frequency: {med.get('frequency', 'Not specified')}
    UMLS CUI: {med.get('cui', 'N/A')}

"""
        if not meds:
            output += "  No medications detected.\n"

        return output

    def _format_diagnoses(self, entities: dict) -> str:
        """Format diagnosis entities"""
        diagnoses = entities.get('diagnoses', [])

        output = f"""=== DIAGNOSIS EXTRACTION ===

Total Diagnoses: {len(diagnoses)}

"""
        for dx in diagnoses:
            output += f"  • {dx['text']} (ICD-10: {dx.get('icd_code', 'N/A')})\n"

        if not diagnoses:
            output += "  No diagnoses detected.\n"

        return output

    def _format_procedures(self, entities: dict) -> str:
        """Format procedure entities"""
        procedures = entities.get('procedures', [])

        output = f"""=== PROCEDURE EXTRACTION ===

Total Procedures: {len(procedures)}

"""
        for proc in procedures:
            output += f"  • {proc['text']} (CPT: {proc.get('cpt_code', 'N/A')})\n"

        if not procedures:
            output += "  No procedures detected.\n"

        return output

    def _format_labs(self, entities: dict) -> str:
        """Format lab value entities"""
        labs = entities.get('lab_values', [])

        output = f"""=== LAB VALUE EXTRACTION ===

Total Lab Values: {len(labs)}

"""
        for lab in labs:
            output += f"""  • {lab['test']}: {lab['value']} {lab.get('unit', '')}
    LOINC: {lab.get('loinc_code', 'N/A')}
    Reference Range: {lab.get('reference_range', 'N/A')}

"""
        if not labs:
            output += "  No lab values detected.\n"

        return output

    def _format_list(self, items: list, max_items: int = 5) -> str:
        """Format list of items"""
        if not items:
            return "  None detected"

        output = ""
        for i, item in enumerate(items[:max_items], 1):
            if isinstance(item, dict):
                output += f"  {i}. {item.get('text', str(item))}\n"
            else:
                output += f"  {i}. {item}\n"

        if len(items) > max_items:
            output += f"  ... and {len(items) - max_items} more\n"

        return output

    def _format_umls(self, concepts: list, max_concepts: int = 5) -> str:
        """Format UMLS concept list"""
        if not concepts:
            return "  None detected"

        output = ""
        for concept in concepts[:max_concepts]:
            cui = concept.get('cui', 'N/A')
            name = concept.get('name', 'Unknown')
            semantic_type = concept.get('semantic_type', 'N/A')
            output += f"  {cui}: {name} ({semantic_type})\n"

        if len(concepts) > max_concepts:
            output += f"  ... and {len(concepts) - max_concepts} more\n"

        return output


# Export
__all__ = ['ScispacyTool']


if __name__ == "__main__":
    print("sciSpaCy Tool - Medical NLP")
    print("=" * 50)

    tool = ScispacyTool()
    print(f"Tool Name: {tool.name}")
    print(f"Description: {tool.description}")
    print("\nExtraction types: all, medications, diagnoses, procedures, labs")
