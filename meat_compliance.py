"""
M.E.A.T. Compliance Checker
Validates clinical documentation for CMS Risk Adjustment compliance.
Checks for: Monitor, Evaluate, Assess/Address, Treat.
"""

import re
from typing import Dict, List, Tuple

class MEATValidator:
    """
    Analyzes SOAP notes to ensure conditions are properly documented 
    according to M.E.A.T. criteria.
    """
    
    def __init__(self):
        # Keywords/Patterns for each M.E.A.T. component
        self.criteria = {
            'Monitor': [
                r'\bsigns\b', r'\bsymptoms\b', r'\bdisease progression\b', 
                r'\bregression\b', r'\bstable\b', r'\bworsening\b', r'\bimproving\b'
            ],
            'Evaluate': [
                r'\btest results\b', r'\bmedication effectiveness\b', 
                r'\bresponse to treatment\b', r'\bphysical exam findings\b',
                r'\breviewed labs\b', r'\breviewed imaging\b',
                r'\ba1c\b', r'\bbp\b', r'\blabs\b', r'\bimaging\b' # Added specific lab keywords
            ],
            'Assess': [
                r'\bordering tests\b', r'\bdiscussion\b', r'\brecords review\b',
                r'\bcounseling\b', r'\baddressing\b', r'\bplan to\b',
                r'\bassessment\b'
            ],
            'Treat': [
                r'\bmedications\b', r'\btherapies\b', r'\bprocedures\b',
                r'\bprescribed\b', r'\bcontinued\b', r'\bincreased dose\b',
                r'\bdecreased dose\b', r'\breferral\b',
                r'\bcontinue\b', r'\bstart\b', r'\bstop\b' # Added simple action verbs
            ]
        }

    def validate(self, soap_note: str, condition: str) -> Dict:
        """
        Check if a specific condition is documented with M.E.A.T. criteria.
        
        Args:
            soap_note: Full text of the clinical note
            condition: The condition to check (e.g., "Diabetes")
            
        Returns:
            Dict with score, missing elements, and evidence
        """
        # In a real system, we would segment the note to find the section 
        # discussing this specific condition. For v2.5, we check the whole note 
        # but look for proximity or general presence if condition is mentioned.
        
        # Simple proximity check: Look for condition mention and context
        note_lower = soap_note.lower()
        cond_lower = condition.lower()
        
        if cond_lower not in note_lower:
            return {
                'score': 0.0,
                'status': 'Not Mentioned',
                'missing': ['Monitor', 'Evaluate', 'Assess', 'Treat'],
                'evidence': {}
            }
            
        findings = {}
        missing = []
        
        for category, patterns in self.criteria.items():
            found = False
            for pattern in patterns:
                if re.search(pattern, note_lower):
                    findings[category] = pattern.replace(r'\b', '')
                    found = True
                    break
            if not found:
                missing.append(category)
                
        # Calculate score (0-100%)
        score = (4 - len(missing)) / 4.0
        
        return {
            'score': score,
            'status': 'Compliant' if score == 1.0 else 'Partial' if score > 0 else 'Non-Compliant',
            'missing': missing,
            'evidence': findings
        }

    def get_compliance_badge(self, score: float) -> str:
        if score == 1.0: return "✅ M.E.A.T. Compliant"
        if score >= 0.5: return "⚠️ Partial Documentation"
        return "❌ Non-Compliant"
    
    # ─── v6.5 ENTERPRISE: AI-Powered Suggestions ─────────────────────
    
    def suggest_improvements(self, soap_note: str, condition: str, validation_result: Dict) -> List[str]:
        """
        Generate AI-powered suggestions for missing M.E.A.T. elements.
        
        Args:
            soap_note: Full text of the clinical note
            condition: The condition being validated
            validation_result: Output from validate() method
            
        Returns:
            List of actionable suggestions
        """
        suggestions = []
        missing = validation_result.get('missing', [])
        
        if not missing:
            return ["✅ Documentation is M.E.A.T. compliant!"]
        
        # Template-based suggestions (In production, use LLM for context-aware hints)
        templates = {
            'Monitor': [
                f"Add monitoring statement: \"Monitored {condition} - currently stable/worsening/improving\"",
                f"Document disease progression: \"{condition} shows regression/stability/progression\"",
                f"Include symptom tracking for {condition}"
            ],
            'Evaluate': [
                f"Reference test results: \"Reviewed labs/imaging for {condition}\"",
                f"Document response to treatment: \"{condition} response to [medication]\"",
                f"Include objective findings from physical exam related to {condition}"
            ],
            'Assess': [
                f"Add assessment statement: \"Assessed {condition} severity and impact\"",
                f"Document treatment plan: \"Plan to adjust therapy for {condition}\"",
                f"Include counseling note: \"Discussed {condition} management with patient\""
            ],
            'Treat': [
                f"Document treatment: \"Prescribed/Continued [medication] for {condition}\"",
                f"List therapies: \"Patient on [treatment regimen] for {condition}\"",
                f"Note interventions: \"Referral to specialist for {condition} management\""
            ]
        }
        
        for element in missing:
            if element in templates:
                # Pick first suggestion from template
                suggestions.append(f"**{element}**: {templates[element][0]}")
        
        return suggestions

if __name__ == "__main__":
    validator = MEATValidator()
    
    note = """
    Assessment:
    1. Type 2 Diabetes: Stable on current Metformin. A1c reviewed, 7.2. 
    Continue current dose. Monitor for hypoglycemia.
    """
    
    result = validator.validate(note, "Diabetes")
    print(f"Condition: Diabetes")
    print(f"Score: {result['score']:.0%}")
    print(f"Status: {result['status']}")
    print(f"Missing: {result['missing']}")
    print(f"Evidence: {result['evidence']}")
    
    # Test AI suggestions
    if result['missing']:
        suggestions = validator.suggest_improvements(note, "Diabetes", result)
        print("\nAI-Powered Suggestions:")
        for s in suggestions:
            print(f"  - {s}")
