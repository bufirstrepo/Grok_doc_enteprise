"""
RCM / Denial Prediction Engine (v5.0)
Predicts likelihood of claim denial based on documentation and coding.
"""

from typing import Dict, List

class DenialPredictor:
    """
    Rule-based engine to predict claim denials.
    """
    
    def __init__(self):
        self.high_risk_keywords = [
            "experimental", "investigational", "cosmetic", "not medically necessary",
            "patient request", "routine screening"
        ]
        
        self.required_elements = {
            '99213': ['history', 'exam', 'decision'],
            '99214': ['detailed history', 'detailed exam', 'moderate decision']
        }

    def predict_denial(self, text: str, cpt_code: str = '99213') -> Dict:
        """
        Analyze documentation for denial risk.
        """
        risk_score = 0
        reasons = []
        text_lower = text.lower()
        
        # 1. Check for "Not Medically Necessary" triggers
        for kw in self.high_risk_keywords:
            if kw in text_lower:
                risk_score += 30
                reasons.append(f"Found high-risk term: '{kw}'")
                
        # 2. Check for missing auth (mock logic)
        if "authorization" not in text_lower and "referral" not in text_lower:
            risk_score += 10
            reasons.append("Potential missing prior authorization")
            
        # 3. Coding specificity (Mock)
        if "unspecified" in text_lower:
            risk_score += 15
            reasons.append("Use of unspecified diagnosis codes")
            
        # Determine Probability
        prob = "Low"
        if risk_score >= 50: prob = "High"
        elif risk_score >= 20: prob = "Medium"
        
        return {
            'probability': prob,
            'risk_score': risk_score,
            'reasons': reasons
        }
