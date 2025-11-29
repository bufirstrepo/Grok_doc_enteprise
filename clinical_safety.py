"""
Clinical Safety Engine (v4.0)
Provides real-time safety checks including Drug-Drug Interactions (DDI).
"""

from typing import List, Dict, Tuple

class DrugInteractionChecker:
    """
    Checks medication lists for potential adverse interactions.
    Uses a local database of interaction pairs (simulated for v4.0).
    """
    
    def __init__(self):
        # Simulated Interaction Database (RxNorm-style pairs)
        # Format: frozenset({drug1, drug2}): (Severity, Description)
        self.interactions = {
            frozenset({'warfarin', 'aspirin'}): ('Major', 'Increased risk of bleeding.'),
            frozenset({'warfarin', 'ibuprofen'}): ('Major', 'Increased risk of GI bleeding.'),
            frozenset({'lisinopril', 'potassium'}): ('Moderate', 'Risk of hyperkalemia.'),
            frozenset({'simvastatin', 'amiodarone'}): ('Major', 'Increased risk of myopathy/rhabdomyolysis.'),
            frozenset({'sildenafil', 'nitroglycerin'}): ('Critical', 'Risk of severe hypotension.'),
            frozenset({'ciprofloxacin', 'tizanidine'}): ('Major', 'Hypotension and sedation risk.'),
            frozenset({'fluoxetine', 'phenelzine'}): ('Critical', 'Serotonin syndrome risk (allow washout).')
        }

    def check_interactions(self, medications: List[str]) -> List[Dict]:
        """
        Identify interactions in a list of medications.
        
        Args:
            medications: List of drug names (e.g., ['Aspirin', 'Warfarin'])
            
        Returns:
            List of interaction alerts.
        """
        alerts = []
        # Normalize inputs
        meds_norm = [m.lower().strip() for m in medications]
        
        # Check all pairs
        for i in range(len(meds_norm)):
            for j in range(i + 1, len(meds_norm)):
                pair = frozenset({meds_norm[i], meds_norm[j]})
                
                if pair in self.interactions:
                    severity, desc = self.interactions[pair]
                    alerts.append({
                        'pair': list(pair),
                        'severity': severity,
                        'description': desc
                    })
                    
        return alerts

    def get_severity_badge(self, severity: str) -> str:
        if severity == 'Critical': return '🔴'
        if severity == 'Major': return '🟠'
        if severity == 'Moderate': return '🟡'
        return '⚪'

if __name__ == "__main__":
    checker = DrugInteractionChecker()
    meds = ["Warfarin", "Aspirin", "Lisinopril"]
    alerts = checker.check_interactions(meds)
    
    for alert in alerts:
        print(f"{checker.get_severity_badge(alert['severity'])} {alert['severity']}: {alert['description']}")
