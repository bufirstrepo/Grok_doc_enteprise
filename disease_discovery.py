"""
Disease Discovery AI Engine
Uses NLP and inference rules to identify undocumented conditions from clinical notes, labs, and medications.
"""

import re
from typing import List, Dict

class DiseaseDiscoveryEngine:
    """
    Identifies potential conditions based on:
    1. Keyword/Regex matching in clinical notes (with negation detection)
    2. Medication inference (e.g., Insulin -> Diabetes)
    3. Lab value inference (e.g., A1c > 6.5 -> Diabetes)
    """
    
    def __init__(self):
        # Regex patterns for conditions
        self.patterns = {
            'Diabetes': [
                r'\bdiabetes\b', r'\bdm2\b', r'\btype 2 dm\b', r'\bhyperglycemia\b'
            ],
            'Hypertension': [
                r'\bhypertension\b', r'\bhtn\b', r'\belevated bp\b', r'\bhigh blood pressure\b'
            ],
            'CKD': [
                r'\bckd\b', r'\bchronic kidney disease\b', r'\brenal insufficiency\b', r'\brenal failure\b'
            ],
            'CHF': [
                r'\bchf\b', r'\bheart failure\b', r'\bcongestive heart failure\b', r'\bcardiomyopathy\b'
            ],
            'COPD': [
                r'\bcopd\b', r'\bemphysema\b', r'\bchronic bronchitis\b'
            ],
            'Obesity': [
                r'\bobesity\b', r'\bmorbid obesity\b', r'\bmi > 35\b', r'\bmi > 40\b'
            ]
        }
        
        # Medication inference rules
        self.med_rules = {
            'Diabetes': ['metformin', 'insulin', 'glipizide', 'jardiance', 'ozempic'],
            'Hypertension': ['lisinopril', 'amlodipine', 'metoprolol', 'losartan'],
            'CHF': ['lasix', 'furosemide', 'entresto', 'carvedilol'],
            'Afib': ['eliquis', 'xarelto', 'warfarin', 'amiodarone'],
            'Asthma/COPD': ['albuterol', 'symbicort', 'advair', 'spiriva']
        }
        
        # Lab inference rules (Condition: lambda labs: bool)
        self.lab_rules = {
            'Diabetes': lambda l: self._check_lab(l, 'a1c', 6.5, '>'),
            'CKD Stage 3+': lambda l: self._check_lab(l, 'gfr', 60, '<'),
            'Anemia': lambda l: self._check_lab(l, 'hgb', 12, '<'), # Simplified
            'Hyperkalemia': lambda l: self._check_lab(l, 'potassium', 5.5, '>')
        }

    def analyze(self, text: str, meds: List[str] = [], labs: Dict[str, float] = {}) -> Dict:
        """
        Analyze patient data to discover conditions.
        
        Args:
            text: Clinical note text
            meds: List of medication names
            labs: Dictionary of lab values (e.g., {'a1c': 7.2})
            
        Returns:
            Dict of discovered conditions with sources
        """
        discovered = {}
        
        # 1. Text Analysis (NLP)
        text_lower = text.lower()
        for condition, patterns in self.patterns.items():
            for pattern in patterns:
                # Check for match
                match = re.search(pattern, text_lower)
                if match:
                    # Simple negation check (look behind 3 words)
                    start = max(0, match.start() - 20)
                    context = text_lower[start:match.start()]
                    if not any(neg in context for neg in ['no ', 'not ', 'denies ', 'negative for ']):
                        self._add_finding(discovered, condition, 'NLP (Note)')
                        break # Found one pattern for this condition, move to next
        
        # 2. Medication Inference
        meds_lower = [m.lower() for m in meds]
        for condition, triggers in self.med_rules.items():
            found_meds = [m for m in meds_lower if any(t in m for t in triggers)]
            if found_meds:
                self._add_finding(discovered, condition, f'Inferred from Meds ({", ".join(found_meds)})')

        # 3. Lab Inference
        for condition, rule in self.lab_rules.items():
            if rule(labs):
                self._add_finding(discovered, condition, 'Inferred from Labs')
                
        return discovered

    def _add_finding(self, discovered: Dict, condition: str, source: str):
        if condition not in discovered:
            discovered[condition] = []
        discovered[condition].append(source)

    def _check_lab(self, labs: Dict, name: str, threshold: float, op: str) -> bool:
        # Normalize keys
        labs_norm = {k.lower(): v for k, v in labs.items()}
        
        # Find partial match for lab name
        val = None
        for k, v in labs_norm.items():
            if name in k:
                val = v
                break
        
        if val is None:
            return False
            
        if op == '>': return val > threshold
        if op == '<': return val < threshold
        return False

if __name__ == "__main__":
    engine = DiseaseDiscoveryEngine()
    
    notes = "Patient denies chest pain. History of hypertension and morbid obesity. No diabetes."
    meds = ["Lisinopril", "Metformin"]
    labs = {"HbA1c": 7.2, "Creatinine": 1.1}
    
    results = engine.analyze(notes, meds, labs)
    print("Discovered Conditions:")
    for cond, sources in results.items():
        print(f"- {cond}: {', '.join(sources)}")
