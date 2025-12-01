#!/usr/bin/env python3
"""
Neo4j Medical Knowledge Graph for Grok Doc v2.0
Cross-verification engine using SNOMED CT, LOINC, ICD-10, RxNorm

Validates LLM recommendations against authoritative medical ontologies:
- Drug-condition indications
- Drug-drug interactions
- Contraindications
- ICD-10 code validation
- LOINC lab code standardization
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json

# Neo4j driver
try:
    from neo4j import GraphDatabase, Driver, Session
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    print("WARNING: neo4j driver not installed. Run: pip install neo4j")


class MedicalKnowledgeGraph:
    """
    Medical knowledge graph using Neo4j

    Schema:
    - (Drug)-[:INDICATED_FOR]->(Condition)
    - (Drug)-[:CONTRAINDICATED]->(Condition)
    - (Drug)-[:INTERACTS_WITH]->(Drug)
    - (Diagnosis)-[:MAPS_TO]->(ICD10Code)
    - (LabTest)-[:MAPS_TO]->(LOINCCode)
    """

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        username: str = "neo4j",
        password: str = "password"
    ):
        """
        Initialize Neo4j connection

        Args:
            uri: Neo4j bolt URI
            username: Database username
            password: Database password
        """
        if not NEO4J_AVAILABLE:
            raise ImportError("neo4j required. Install with: pip install neo4j")

        self.driver: Driver = GraphDatabase.driver(uri, auth=(username, password))
        print(f"Connected to Neo4j at {uri}")

    def close(self):
        """Close database connection"""
        if self.driver:
            self.driver.close()

    def validate_indication(self, drug: str, condition: str) -> Dict:
        """
        Check if drug is indicated for condition

        Args:
            drug: Drug name (e.g., "vancomycin")
            condition: Condition (e.g., "MRSA bacteremia")

        Returns:
            {
                'is_indicated': bool,
                'evidence': List[str],
                'guidelines': List[str]
            }
        """

        query = """
        MATCH (d:Drug {name: $drug})-[r:INDICATED_FOR]->(c:Condition {name: $condition})
        RETURN r.evidence AS evidence, r.guidelines AS guidelines
        """

        with self.driver.session() as session:
            result = session.run(query, drug=drug.lower(), condition=condition.lower())
            record = result.single()

            if record:
                return {
                    'is_indicated': True,
                    'evidence': record['evidence'] or [],
                    'guidelines': record['guidelines'] or []
                }
            else:
                return {
                    'is_indicated': False,
                    'evidence': [],
                    'guidelines': []
                }

    def check_contraindications(self, drug: str, patient_conditions: List[str]) -> List[Dict]:
        """
        Check for contraindications

        Args:
            drug: Drug name
            patient_conditions: List of patient conditions

        Returns:
            List of contraindications with severity
        """

        query = """
        MATCH (d:Drug {name: $drug})-[r:CONTRAINDICATED]->(c:Condition)
        WHERE c.name IN $conditions
        RETURN c.name AS condition, r.severity AS severity, r.rationale AS rationale
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                drug=drug.lower(),
                conditions=[c.lower() for c in patient_conditions]
            )

            contraindications = []
            for record in result:
                contraindications.append({
                    'condition': record['condition'],
                    'severity': record['severity'],  # absolute, relative
                    'rationale': record['rationale']
                })

            return contraindications

    def check_drug_interactions(self, drugs: List[str]) -> List[Dict]:
        """
        Check for drug-drug interactions

        Args:
            drugs: List of drug names

        Returns:
            List of interactions with severity
        """

        query = """
        MATCH (d1:Drug)-[r:INTERACTS_WITH]->(d2:Drug)
        WHERE d1.name IN $drugs AND d2.name IN $drugs
        RETURN d1.name AS drug1, d2.name AS drug2,
               r.severity AS severity, r.mechanism AS mechanism,
               r.clinical_effect AS effect
        """

        with self.driver.session() as session:
            result = session.run(query, drugs=[d.lower() for d in drugs])

            interactions = []
            for record in result:
                interactions.append({
                    'drug1': record['drug1'],
                    'drug2': record['drug2'],
                    'severity': record['severity'],  # major, moderate, minor
                    'mechanism': record['mechanism'],
                    'clinical_effect': record['effect']
                })

            return interactions

    def validate_icd10(self, diagnosis: str) -> Optional[str]:
        """
        Validate diagnosis and return ICD-10 code

        Args:
            diagnosis: Diagnosis description

        Returns:
            ICD-10 code if valid, None otherwise
        """

        query = """
        MATCH (diag:Diagnosis)-[:MAPS_TO]->(icd:ICD10Code)
        WHERE diag.name =~ $pattern OR icd.description =~ $pattern
        RETURN icd.code AS code, icd.description AS description
        LIMIT 1
        """

        pattern = f"(?i).*{diagnosis}.*"  # Case-insensitive partial match

        with self.driver.session() as session:
            result = session.run(query, pattern=pattern)
            record = result.single()

            if record:
                return record['code']
            else:
                return None

    def get_loinc_code(self, lab_test: str) -> Optional[str]:
        """
        Get LOINC code for lab test

        Args:
            lab_test: Lab test name (e.g., "creatinine")

        Returns:
            LOINC code if found
        """

        query = """
        MATCH (lab:LabTest)-[:MAPS_TO]->(loinc:LOINCCode)
        WHERE lab.name =~ $pattern
        RETURN loinc.code AS code, loinc.description AS description
        LIMIT 1
        """

        pattern = f"(?i).*{lab_test}.*"

        with self.driver.session() as session:
            result = session.run(query, pattern=pattern)
            record = result.single()

            if record:
                return record['code']
            else:
                return None

    def validate_recommendation(
        self,
        drug: str,
        diagnosis: str,
        patient_conditions: List[str],
        concurrent_medications: List[str]
    ) -> Dict:
        """
        Complete validation of LLM recommendation

        Args:
            drug: Recommended drug
            diagnosis: Primary diagnosis
            patient_conditions: All patient conditions
            concurrent_medications: Other medications patient is taking

        Returns:
            {
                'is_valid': bool,
                'indication_check': Dict,
                'contraindications': List[Dict],
                'drug_interactions': List[Dict],
                'icd10_code': str,
                'warnings': List[str]
            }
        """

        # Check indication
        indication = self.validate_indication(drug, diagnosis)

        # Check contraindications
        contraindications = self.check_contraindications(drug, patient_conditions)

        # Check drug interactions
        all_drugs = [drug] + concurrent_medications
        interactions = self.check_drug_interactions(all_drugs)

        # Validate ICD-10
        icd10 = self.validate_icd10(diagnosis)

        # Generate warnings
        warnings = []
        if not indication['is_indicated']:
            warnings.append(f"{drug} not indicated for {diagnosis} per knowledge graph")

        for contra in contraindications:
            if contra['severity'] == 'absolute':
                warnings.append(f"ABSOLUTE CONTRAINDICATION: {contra['condition']} - {contra['rationale']}")
            else:
                warnings.append(f"Relative contraindication: {contra['condition']}")

        for interaction in interactions:
            if interaction['severity'] == 'major':
                warnings.append(f"MAJOR INTERACTION: {interaction['drug1']} + {interaction['drug2']} - {interaction['clinical_effect']}")

        # Overall validity
        is_valid = (
            indication['is_indicated'] and
            not any(c['severity'] == 'absolute' for c in contraindications) and
            not any(i['severity'] == 'major' for i in interactions)
        )

        return {
            'is_valid': is_valid,
            'indication_check': indication,
            'contraindications': contraindications,
            'drug_interactions': interactions,
            'icd10_code': icd10,
            'warnings': warnings,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }


def populate_sample_knowledge_graph(kg: MedicalKnowledgeGraph):
    """Populate Neo4j with sample medical knowledge (for testing)"""

    with kg.driver.session() as session:
        # Create sample drugs
        session.run("""
        CREATE (v:Drug {name: 'vancomycin'})
        CREATE (w:Drug {name: 'warfarin'})
        CREATE (c:Drug {name: 'ciprofloxacin'})
        """)

        # Create sample conditions
        session.run("""
        CREATE (mrsa:Condition {name: 'mrsa bacteremia'})
        CREATE (aki:Condition {name: 'acute kidney injury'})
        CREATE (pregnancy:Condition {name: 'pregnancy'})
        """)

        # Create indications
        session.run("""
        MATCH (v:Drug {name: 'vancomycin'}), (mrsa:Condition {name: 'mrsa bacteremia'})
        CREATE (v)-[:INDICATED_FOR {
            evidence: ['2024 IDSA Guidelines'],
            guidelines: ['IDSA MRSA 2024', 'Sanford Guide']
        }]->(mrsa)
        """)

        # Create contraindications
        session.run("""
        MATCH (v:Drug {name: 'vancomycin'}), (aki:Condition {name: 'acute kidney injury'})
        CREATE (v)-[:CONTRAINDICATED {
            severity: 'relative',
            rationale: 'Nephrotoxic - use with caution and dose-adjust'
        }]->(aki)
        """)

        # Create drug interactions
        session.run("""
        MATCH (w:Drug {name: 'warfarin'}), (c:Drug {name: 'ciprofloxacin'})
        CREATE (w)-[:INTERACTS_WITH {
            severity: 'major',
            mechanism: 'CYP450 inhibition',
            clinical_effect: 'Increased INR, bleeding risk'
        }]->(c)
        """)

        # Create ICD-10 mappings
        session.run("""
        CREATE (diag:Diagnosis {name: 'MRSA bacteremia'})
        CREATE (icd:ICD10Code {code: 'A49.02', description: 'Methicillin resistant Staphylococcus aureus infection'})
        CREATE (diag)-[:MAPS_TO]->(icd)
        """)

        # Create LOINC mappings
        session.run("""
        CREATE (lab:LabTest {name: 'creatinine'})
        CREATE (loinc:LOINCCode {code: '2160-0', description: 'Creatinine [Mass/volume] in Serum or Plasma'})
        CREATE (lab)-[:MAPS_TO]->(loinc)
        """)

    print("Sample knowledge graph populated")


if __name__ == "__main__":
    print("Medical Knowledge Graph Validator")
    print(f"Neo4j available: {NEO4J_AVAILABLE}")

    if NEO4J_AVAILABLE:
        # Test with sample data
        kg = MedicalKnowledgeGraph(
            uri="bolt://localhost:7687",
            username="neo4j",
            password="password"
        )

        try:
            # Populate sample data
            print("\nPopulating sample knowledge graph...")
            populate_sample_knowledge_graph(kg)

            # Test validation
            print("\nTesting validation...")
            result = kg.validate_recommendation(
                drug="vancomycin",
                diagnosis="MRSA bacteremia",
                patient_conditions=["acute kidney injury"],
                concurrent_medications=[]
            )

            print(json.dumps(result, indent=2))

        finally:
            kg.close()

    else:
        print("\nInstall Neo4j driver:")
        print("  pip install neo4j")
        print("\nInstall Neo4j database:")
        print("  https://neo4j.com/download/")
