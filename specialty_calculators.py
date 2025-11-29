"""
Specialty Risk Calculators (v5.0)
Cardiology and Behavioral Health scoring engines.
"""

from typing import Dict

class CardioRiskCalculator:
    """Cardiology Risk Scores"""
    
    def calculate_ascvd(self, age: int, gender: str, total_chol: int, hdl: int, 
                       sbp: int, smoker: bool, diabetic: bool) -> float:
        """
        Calculate 10-year ASCVD Risk (Simplified Pooled Cohort Equation).
        Returns percentage risk (0-100).
        """
        # Simplified logic for demo purposes (real equation is complex log-linear)
        # Base risk
        risk = 2.0 
        
        if age > 40: risk += (age - 40) * 0.2
        if gender == 'M': risk *= 1.2
        if smoker: risk *= 1.5
        if diabetic: risk *= 1.6
        if sbp > 130: risk += (sbp - 130) * 0.1
        if total_chol > 200: risk += (total_chol - 200) * 0.05
        if hdl < 40: risk += 2.0
        
        return min(99.9, round(risk, 1))

    def calculate_cha2ds2_vasc(self, age: int, gender: str, chf: bool, htn: bool, 
                              stroke: bool, vascular: bool, diabetes: bool) -> int:
        """
        Calculate CHA2DS2-VASc Score for Atrial Fibrillation Stroke Risk.
        """
        score = 0
        if chf: score += 1
        if htn: score += 1
        if age >= 75: score += 2
        elif age >= 65: score += 1
        if diabetes: score += 1
        if stroke: score += 2
        if vascular: score += 1
        if gender == 'F': score += 1
        
        return score

class BehavioralHealthScorer:
    """Psychiatry Scoring Tools"""
    
    def score_phq9(self, answers: list[int]) -> Dict:
        """
        Score PHQ-9 Depression Scale.
        Args: answers: List of 9 integers (0-3)
        """
        total = sum(answers)
        severity = "None"
        if total >= 20: severity = "Severe"
        elif total >= 15: severity = "Moderately Severe"
        elif total >= 10: severity = "Moderate"
        elif total >= 5: severity = "Mild"
        
        return {'score': total, 'severity': severity}

    def score_gad7(self, answers: list[int]) -> Dict:
        """
        Score GAD-7 Anxiety Scale.
        Args: answers: List of 7 integers (0-3)
        """
        total = sum(answers)
        severity = "None"
        if total >= 15: severity = "Severe"
        elif total >= 10: severity = "Moderate"
        elif total >= 5: severity = "Mild"
        
        return {'score': total, 'severity': severity}
