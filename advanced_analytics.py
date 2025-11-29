"""
Advanced Analytics Engine (v6.0)
Predictive models for Sepsis (qSOFA) and Readmission Risk (LACE).
"""

from typing import Dict

class SepsisPredictor:
    """
    Sepsis Early Warning System using qSOFA score.
    """
    
    def calculate_qsofa(self, sbp: int, resp_rate: int, gcs: int) -> Dict:
        """
        Calculate qSOFA Score.
        Criteria:
        - SBP <= 100 mmHg (+1)
        - Resp Rate >= 22 (+1)
        - GCS < 15 (+1)
        """
        score = 0
        if sbp <= 100: score += 1
        if resp_rate >= 22: score += 1
        if gcs < 15: score += 1
        
        risk = "Low"
        if score >= 2: risk = "High (Sepsis Risk)"
        
        return {'score': score, 'risk': risk}

class ReadmissionRiskScorer:
    """
    Readmission Risk using LACE Index.
    """
    
    def calculate_lace(self, length_of_stay: int, acuity: bool, comorbidities: int, ed_visits: int) -> Dict:
        """
        Calculate LACE Index.
        L: Length of Stay (0-7 pts)
        A: Acuity (0 or 3 pts)
        C: Comorbidities (Charlson Score 0-5 pts)
        E: ED Visits in last 6mo (0-4 pts)
        """
        score = 0
        
        # L: Length of Stay
        if length_of_stay < 1: score += 0
        elif length_of_stay <= 2: score += 1 # 1-2 days (simplified)
        elif length_of_stay <= 4: score += 2 # 3-4 days
        elif length_of_stay <= 6: score += 3 # 5-6 days
        elif length_of_stay <= 13: score += 4 # 7-13 days
        else: score += 7 # >14 days (simplified cap)
        
        # A: Acuity (Emergent admission)
        if acuity: score += 3
        
        # C: Comorbidities (Charlson - simplified input)
        score += min(comorbidities, 5)
        
        # E: ED Visits
        score += min(ed_visits, 4)
        
        risk = "Low"
        if score >= 10: risk = "High"
        elif score >= 5: risk = "Moderate"
        
        return {'score': score, 'risk': risk}
