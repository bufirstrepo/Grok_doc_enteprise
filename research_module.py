"""
Research & Development Module (v6.0)
Clinical Trial Eligibility Matching Engine.
"""

from typing import List, Dict

class ClinicalTrialMatcher:
    """
    Matches patients to active clinical trials based on diagnosis and demographics.
    """
    
    def __init__(self):
        # Mock Database of Active Trials
        self.trials = [
            {
                'id': 'NCT01234567',
                'title': 'Immunotherapy for Stage IV Lung Cancer',
                'condition': 'Lung Cancer',
                'min_age': 18,
                'max_age': 75,
                'gender': 'Any',
                'phase': 'Phase 3'
            },
            {
                'id': 'NCT09876543',
                'title': 'Novel Statin for High Cholesterol',
                'condition': 'Hyperlipidemia',
                'min_age': 40,
                'max_age': 80,
                'gender': 'Any',
                'phase': 'Phase 2'
            },
            {
                'id': 'NCT05555555',
                'title': 'Hormone Therapy for Breast Cancer',
                'condition': 'Breast Cancer',
                'min_age': 18,
                'max_age': 99,
                'gender': 'Female',
                'phase': 'Phase 4'
            }
        ]

    def find_trials(self, diagnosis: str, age: int, gender: str) -> List[Dict]:
        """
        Find matching trials.
        """
        matches = []
        diag_lower = diagnosis.lower()
        
        for trial in self.trials:
            # 1. Condition Match (Simple string check)
            if trial['condition'].lower() not in diag_lower:
                continue
                
            # 2. Age Match
            if not (trial['min_age'] <= age <= trial['max_age']):
                continue
                
            # 3. Gender Match
            if trial['gender'] != 'Any' and trial['gender'] != gender:
                continue
                
            matches.append(trial)
            
        return matches

if __name__ == "__main__":
    matcher = ClinicalTrialMatcher()
    print(matcher.find_trials("Stage IV Lung Cancer", 65, "Male"))
