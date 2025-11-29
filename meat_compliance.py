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

    def suggest_improvements(self, soap_note: str, condition: str, validation_result: Dict) -> List[str]:
        """
        Generate AI-powered suggestions to improve M.E.A.T. compliance.
        
        Args:
            soap_note: The clinical note text
            condition: The condition being documented
            validation_result: Output from validate() method
            
        Returns:
            List of suggested phrases to add for missing M.E.A.T. elements
        """
        suggestions = []
        missing = validation_result.get('missing', [])
        
        # Template suggestions for each missing element
        suggestion_templates = {
            'Monitor': [
                f"Monitor {condition} progression and symptoms at next visit.",
                f"Continue to monitor for signs of {condition} complications.",
                f"Track {condition} status - currently stable/worsening/improving."
            ],
            'Evaluate': [
                f"Evaluated recent test results for {condition}.",
                f"Reviewed labs pertinent to {condition} management.",
                f"Physical exam findings consistent with controlled {condition}."
            ],
            'Assess': [
                f"Assessment: {condition} - current status addressed.",
                f"Discussed {condition} management plan with patient.",
                f"Plan to order additional testing if {condition} worsens."
            ],
            'Treat': [
                f"Continue current medications for {condition}.",
                f"Treatment for {condition}: maintain current regimen.",
                f"Referred to specialist for {condition} management."
            ]
        }
        
        for element in missing:
            if element in suggestion_templates:
                suggestions.append(f"Add for {element}: \"{suggestion_templates[element][0]}\"")
        
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
