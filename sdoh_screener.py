"""
SDOH Screener (v5.0)
Social Determinants of Health Analysis Module.
Identifies social needs (Housing, Food, Transport) from clinical text.
"""

from typing import Dict, List

class SDOHAnalyzer:
    """
    Analyzes text for Social Determinants of Health (SDOH).
    Maps findings to ICD-10 Z-codes.
    """
    
    def __init__(self):
        self.categories = {
            'Housing': {
                'keywords': ['homeless', 'shelter', 'eviction', 'couch surfing', 'unstable housing'],
                'code': 'Z59.0'
            },
            'Food Insecurity': {
                'keywords': ['food bank', 'hunger', 'no food', 'can\'t afford food', 'food stamps'],
                'code': 'Z59.4'
            },
            'Transportation': {
                'keywords': ['no car', 'bus trouble', 'missed ride', 'transportation issues'],
                'code': 'Z59.82'
            },
            'Financial': {
                'keywords': ['can\'t afford meds', 'bankruptcy', 'poverty', 'financial strain'],
                'code': 'Z59.7'
            },
            'Social Isolation': {
                'keywords': ['lives alone', 'no family', 'lonely', 'socially isolated'],
                'code': 'Z60.2'
            }
        }

    def analyze(self, text: str) -> Dict:
        """
        Scan text for SDOH factors.
        """
        findings = {}
        text_lower = text.lower()
        
        for category, data in self.categories.items():
            for kw in data['keywords']:
                if kw in text_lower:
                    findings[category] = {
                        'code': data['code'],
                        'trigger': kw
                    }
                    break # Found one trigger for this category
                    
        return findings

if __name__ == "__main__":
    analyzer = SDOHAnalyzer()
    text = "Patient lives alone and has trouble affording medications. Uses food bank occasionally."
    print(analyzer.analyze(text))
