"""
AI Governance & Ethics Module (v6.0)
Bias Detection and Fairness Auditing tools.
"""

from typing import Dict, List

class BiasDetector:
    """
    Analyzes AI outputs for potential demographic bias.
    """
    
    def __init__(self):
        self.sensitive_terms = [
            "race", "ethnicity", "gender", "age", "socioeconomic", 
            "insurance", "medicaid", "uninsured"
        ]
        
        self.negative_outcomes = [
            "non-compliant", "drug seeking", "aggressive", "difficult", 
            "refused", "denied"
        ]

    def audit_recommendation(self, text: str) -> Dict:
        """
        Scan text for sensitive terms appearing near negative outcomes.
        """
        text_lower = text.lower()
        flags = []
        
        # Simple proximity check (if both sensitive term and negative outcome exist)
        # In a real system, this would use dependency parsing or sentiment analysis.
        
        found_sensitive = [t for t in self.sensitive_terms if t in text_lower]
        found_negative = [t for t in self.negative_outcomes if t in text_lower]
        
        risk_level = "Low"
        
        if found_sensitive and found_negative:
            risk_level = "High"
            flags.append(f"Potential Bias: Sensitive terms {found_sensitive} found with negative terms {found_negative}")
        elif found_sensitive:
            risk_level = "Medium"
            flags.append(f"Note: Recommendation contains sensitive demographic terms: {found_sensitive}")
            
        return {
            'risk_level': risk_level,
            'flags': flags
        }

if __name__ == "__main__":
    detector = BiasDetector()
    text = "Patient is a 45yo male on Medicaid who is non-compliant with meds."
    print(detector.audit_recommendation(text))
