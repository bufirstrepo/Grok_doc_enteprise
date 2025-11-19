#!/usr/bin/env python3
"""
Neo4j Knowledge Graph Tool for CrewAI
Wraps knowledge_graph.py for use by graph_agent
"""

from crewai.tools import BaseTool
from typing import Type, List
from pydantic import BaseModel, Field
import sys
import os

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.services.neo4j_validator import MedicalKnowledgeGraph


class Neo4jToolInput(BaseModel):
    """Input schema for Neo4j knowledge graph queries"""
    query_type: str = Field(..., description="Query type: 'validate_indication', 'check_interactions', 'find_alternatives'")
    drug: str = Field(..., description="Drug name")
    condition: str = Field(default="", description="Medical condition (for validation)")
    medications: List[str] = Field(default_factory=list, description="List of medications (for interactions)")


class Neo4jTool(BaseTool):
    """
    Medical Knowledge Graph Validator using Neo4j

    Validates clinical decisions against medical ontologies:
    - SNOMED CT (clinical terms)
    - LOINC (lab codes)
    - ICD-10 (diagnoses)
    - RxNorm (medications)
    - DrugBank (drug interactions)

    Used by: graph_agent (Knowledge Graph Agent), adversarial_agent
    """

    name: str = "Neo4j Medical Knowledge Graph"
    description: str = """Query medical knowledge graph for drug-condition validation, drug interactions,
    alternative therapies, and clinical decision support. Uses SNOMED/LOINC/ICD/RxNorm ontologies."""
    args_schema: Type[BaseModel] = Neo4jToolInput

    def _run(
        self,
        query_type: str,
        drug: str,
        condition: str = "",
        medications: List[str] = None
    ) -> str:
        """
        Query Neo4j knowledge graph

        Args:
            query_type: 'validate_indication', 'check_interactions', 'find_alternatives'
            drug: Drug name
            condition: Medical condition (for validation)
            medications: List of medications (for interaction checking)

        Returns:
            Knowledge graph query results for graph_agent
        """
        try:
            kg = MedicalKnowledgeGraph()

            if query_type == 'validate_indication':
                return self._validate_indication(kg, drug, condition)

            elif query_type == 'check_interactions':
                meds = medications or []
                if drug not in meds:
                    meds.append(drug)
                return self._check_interactions(kg, meds)

            elif query_type == 'find_alternatives':
                return self._find_alternatives(kg, drug, condition)

            else:
                return f"""=== KNOWLEDGE GRAPH ERROR ===
Unknown query type: '{query_type}'

Supported types:
  - validate_indication (check if drug is indicated for condition)
  - check_interactions (check drug-drug interactions)
  - find_alternatives (find alternative therapies)
"""

        except Exception as e:
            return f"""=== KNOWLEDGE GRAPH UNAVAILABLE ===
Error: {str(e)}

Recommendation: Use clinical judgment and manual references.
Neo4j database may not be configured or populated.
"""

    def _validate_indication(self, kg: MedicalKnowledgeGraph, drug: str, condition: str) -> str:
        """Validate drug-condition indication"""
        validation = kg.validate_indication(drug, condition)

        if validation.get('is_indicated'):
            guidelines = validation.get('guidelines', [])
            evidence_level = validation.get('evidence_level', 'Unknown')

            return f"""=== INDICATION VALIDATION ===

Drug:      {drug}
Condition: {condition}
Status:    ✓ VALIDATED

Evidence Level: {evidence_level}
Guidelines: {', '.join(guidelines) if guidelines else 'None on file'}

SNOMED Code: {validation.get('snomed_code', 'N/A')}
ICD-10 Code: {validation.get('icd_code', 'N/A')}

Recommendation: Indication is supported by medical ontologies.
"""
        else:
            return f"""=== INDICATION VALIDATION ===

Drug:      {drug}
Condition: {condition}
Status:    ✗ NOT VALIDATED

Knowledge graph does not show {drug} as indicated for {condition}.

Recommendation: Consider:
  1. Off-label use with strong clinical justification
  2. Alternative evidence-based therapy
  3. Specialist consultation
"""

    def _check_interactions(self, kg: MedicalKnowledgeGraph, medications: List[str]) -> str:
        """Check drug-drug interactions"""
        interactions = kg.check_drug_interactions(medications)

        if not interactions:
            return f"""=== DRUG INTERACTION CHECK ===

Medications: {', '.join(medications)}

Result: ✓ No major interactions detected

Recommendation: Safe to proceed. Monitor as per standard protocols.
"""

        # Sort by severity
        major = [i for i in interactions if i['severity'].lower() == 'major']
        moderate = [i for i in interactions if i['severity'].lower() == 'moderate']
        minor = [i for i in interactions if i['severity'].lower() == 'minor']

        output = f"""=== DRUG INTERACTION CHECK ===

Medications: {', '.join(medications)}

"""
        if major:
            output += f"⚠️ MAJOR INTERACTIONS ({len(major)}):\n"
            for interaction in major:
                output += f"""
  {interaction['drug1']} + {interaction['drug2']}
  Mechanism: {interaction['mechanism']}
  Effect: {interaction['clinical_effect']}
  Management: {interaction.get('management', 'Avoid combination or monitor closely')}
"""

        if moderate:
            output += f"\n⚠ Moderate Interactions ({len(moderate)}):\n"
            for interaction in moderate[:3]:  # Show top 3
                output += f"  - {interaction['drug1']} + {interaction['drug2']}: {interaction['clinical_effect']}\n"

        if minor:
            output += f"\nMinor Interactions: {len(minor)} detected\n"

        output += f"\nRecommendation: "
        if major:
            output += "MAJOR INTERACTIONS DETECTED. Consider alternative therapy or intensive monitoring."
        elif moderate:
            output += "Monitor for interaction effects. Dose adjustment may be needed."
        else:
            output += "Minor interactions only. Routine monitoring."

        return output

    def _find_alternatives(self, kg: MedicalKnowledgeGraph, drug: str, condition: str) -> str:
        """Find alternative therapies"""
        alternatives = kg.find_alternative_therapies(drug, condition)

        if not alternatives:
            return f"""=== ALTERNATIVE THERAPIES ===

Current: {drug} for {condition}

Result: No alternatives found in knowledge graph.

Recommendation: Consult clinical guidelines or specialist for alternatives.
"""

        output = f"""=== ALTERNATIVE THERAPIES ===

Current: {drug} for {condition}

Alternatives:
"""
        for alt in alternatives[:5]:  # Top 5
            output += f"""
  {alt['drug_name']}
    Evidence Level: {alt.get('evidence_level', 'Unknown')}
    Efficacy: {alt.get('efficacy_vs_standard', 'Comparable')}
    Safety Profile: {alt.get('safety_profile', 'Similar')}
"""

        return output


# Export
__all__ = ['Neo4jTool']


if __name__ == "__main__":
    print("Neo4j Tool - Medical Knowledge Graph")
    print("=" * 50)

    tool = Neo4jTool()
    print(f"Tool Name: {tool.name}")
    print(f"Description: {tool.description}")
    print("\nQuery types: validate_indication, check_interactions, find_alternatives")
