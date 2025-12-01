"""
Security Utilities (v4.0)
Helper functions for data privacy, PHI masking, and security hardening.
"""

import re
import re
from typing import List

class PHIMasker:
    """
    Redacts Protected Health Information (PHI) from text.
    Used for 'Demo Mode' or training data generation.
    """
    
    def __init__(self):
        # Regex patterns for common PHI
        self.patterns = {
            'MRN': r'\bMRN[-: ]*\d+\b', # Allow optional spaces/colons
            'SSN': r'\b\d{3}-\d{2}-\d{4}\b',
            'Phone': r'\b(\+\d{1,2}\s)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b',
            'Date': r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            'Name': r'\b[A-Z][a-z]+ [A-Z][a-z]+\b' # Simple name detector (capitalized pairs)
        }

    def mask_text(self, text: str) -> str:
        """
        Replace PHI with [REDACTED] placeholders.
        """
        masked_text = text
        
        # 1. Mask MRNs specifically first
        masked_text = re.sub(self.patterns['MRN'], "[MRN-REDACTED]", masked_text, flags=re.IGNORECASE)
        
        # 2. Mask SSNs
        masked_text = re.sub(self.patterns['SSN'], "[SSN-REDACTED]", masked_text)
        
        # 3. Mask Dates (simple approximation)
        masked_text = re.sub(self.patterns['Date'], "[DATE-REDACTED]", masked_text)
        
        # 4. Mask Names (Context-aware would be better, using simple regex for v4.0)
        # We avoid masking common medical terms by only masking if it looks strictly like a name
        # This is a heuristic and not perfect.
        # masked_text = re.sub(self.patterns['Name'], "[NAME-REDACTED]", masked_text) 
        
        return masked_text

    def is_demo_mode(self, session_state) -> bool:
        """Check if Demo Mode is active in session state"""
        return session_state.get('demo_mode', False)


class LDAPAuthenticator:
    """
    Enterprise LDAP/Active Directory Authentication.
    """
    def __init__(self, server_uri: str = "ldap://localhost", bind_dn: str = "", bind_password: str = ""):
        self.server_uri = server_uri
        self.bind_dn = bind_dn
        self.bind_password = bind_password

    def authenticate(self, username: str, password: str) -> bool:
        """
        Authenticate user against LDAP server.
        In production, this would use `ldap3` library.
        For now, we mock it or check against a secure hash if local.
        """
        # MOCK IMPLEMENTATION for v3.1 prototype
        # Real implementation would be:
        # server = Server(self.server_uri)
        # conn = Connection(server, user=f"uid={username},{self.bind_dn}", password=password)
        # return conn.bind()
        
        if username == "admin" and password == "grok_admin_2025":
            return True
        if username == "doctor" and password == "hippocratic":
            return True
            
        return False

if __name__ == "__main__":
    masker = PHIMasker()
    text = "Patient John Doe (MRN: 12345) admitted on 11/28/2025."
    # print(f"Original: {text}") # Commented out to prevent log leakage
    print(f"Masked:   {masker.mask_text(text)}")

