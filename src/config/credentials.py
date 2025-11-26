"""
Credential Manager for Hospital AI Integrations

Securely manages API keys and secrets for:
- EHR systems (Epic, Cerner)
- Hospital AI tools (Aidoc, PathAI, etc.)
- LLM APIs (Grok with BAA)

All credentials are stored as environment variables, never in code.
"""

import os
from typing import Dict, Optional, List
from dataclasses import dataclass


@dataclass
class CredentialStatus:
    """Status of a credential"""
    name: str
    env_var: str
    is_set: bool
    required: bool
    description: str


class CredentialManager:
    """
    Manages credentials for hospital AI integrations.
    Credentials are stored in environment variables for security.
    """
    
    REQUIRED_CREDENTIALS = {
        'EPIC_CLIENT_SECRET': 'Epic FHIR API client secret',
        'CERNER_CLIENT_SECRET': 'Cerner FHIR API client secret',
    }
    
    OPTIONAL_CREDENTIALS = {
        'GROK_API_KEY': 'xAI Grok API key (requires BAA for HIPAA)',
        'AIDOC_API_KEY': 'Aidoc radiology AI API key',
        'PATHOLOGY_API_KEY': 'PathAI pathology analysis API key',
        'TEMPUS_API_KEY': 'Tempus genomics/oncology API key',
        'BUTTERFLY_API_KEY': 'Butterfly iQ ultrasound AI API key',
        'CAPTION_HEALTH_API_KEY': 'Caption Health cardiac AI API key',
        'IBM_WATSON_API_KEY': 'IBM Watson Health API key',
        'DEEPMIND_API_KEY': 'DeepMind Health API key',
        'KERAGON_API_KEY': 'Keragon workflow automation API key',
        'NUANCE_DAX_API_KEY': 'Nuance DAX ambient scribe API key',
        'PUBMED_API_KEY': 'PubMed/NCBI E-utilities API key',
        'DRUGBANK_API_KEY': 'DrugBank drug interaction API key',
    }
    
    def __init__(self):
        self._cached_credentials: Dict[str, str] = {}
    
    def get_credential(self, env_var: str, required: bool = False) -> Optional[str]:
        """
        Get a credential from environment variables.
        
        Args:
            env_var: Name of the environment variable
            required: If True, raises error when not found
            
        Returns:
            Credential value or None
            
        Raises:
            ValueError: If required credential is not set
        """
        if env_var in self._cached_credentials:
            return self._cached_credentials[env_var]
        
        value = os.getenv(env_var)
        
        if value:
            self._cached_credentials[env_var] = value
            return value
        
        if required:
            raise ValueError(
                f"Required credential not set: {env_var}\n"
                f"Set it with: export {env_var}=your_secret_value"
            )
        
        return None
    
    def is_set(self, env_var: str) -> bool:
        """Check if a credential is set"""
        return os.getenv(env_var) is not None
    
    def get_status(self) -> List[CredentialStatus]:
        """Get status of all known credentials"""
        statuses = []
        
        for env_var, description in self.REQUIRED_CREDENTIALS.items():
            statuses.append(CredentialStatus(
                name=env_var.replace('_', ' ').title(),
                env_var=env_var,
                is_set=self.is_set(env_var),
                required=True,
                description=description
            ))
        
        for env_var, description in self.OPTIONAL_CREDENTIALS.items():
            statuses.append(CredentialStatus(
                name=env_var.replace('_', ' ').title(),
                env_var=env_var,
                is_set=self.is_set(env_var),
                required=False,
                description=description
            ))
        
        return statuses
    
    def get_configured_adapters(self) -> List[str]:
        """Get list of adapters that have credentials configured"""
        adapter_creds = {
            'aidoc': 'AIDOC_API_KEY',
            'pathAI': 'PATHOLOGY_API_KEY',
            'tempus': 'TEMPUS_API_KEY',
            'butterfly_iq': 'BUTTERFLY_API_KEY',
            'caption_health': 'CAPTION_HEALTH_API_KEY',
            'ibm_watson': 'IBM_WATSON_API_KEY',
            'deepmind_health': 'DEEPMIND_API_KEY',
            'keragon': 'KERAGON_API_KEY',
            'nuance_dax': 'NUANCE_DAX_API_KEY',
        }
        
        return [
            adapter for adapter, env_var in adapter_creds.items()
            if self.is_set(env_var)
        ]
    
    def validate_ehr_credentials(self, ehr_type: str) -> bool:
        """Validate that required EHR credentials are set"""
        if ehr_type == 'epic':
            return self.is_set('EPIC_CLIENT_SECRET')
        elif ehr_type == 'cerner':
            return self.is_set('CERNER_CLIENT_SECRET')
        return False
    
    def validate_grok_for_hipaa(self) -> Dict[str, bool]:
        """
        Check if Grok is properly configured for HIPAA compliance.
        
        Returns:
            Dict with validation results
        """
        has_key = self.is_set('GROK_API_KEY')
        has_baa = os.getenv('GROK_HAS_BAA', 'false').lower() == 'true'
        
        return {
            'api_key_set': has_key,
            'baa_confirmed': has_baa,
            'hipaa_compliant': has_key and has_baa,
            'message': (
                "✓ Grok ready for HIPAA use" if (has_key and has_baa)
                else "⚠️ Grok NOT ready: " + (
                    "Missing API key" if not has_key
                    else "BAA not confirmed (set GROK_HAS_BAA=true after signing)"
                )
            )
        }
    
    def print_status(self):
        """Print credential status to console"""
        print("\n" + "="*60)
        print("CREDENTIAL STATUS")
        print("="*60)
        
        statuses = self.get_status()
        
        required = [s for s in statuses if s.required]
        optional = [s for s in statuses if not s.required]
        
        print("\nREQUIRED CREDENTIALS:")
        for s in required:
            status = "✓ SET" if s.is_set else "✗ MISSING"
            print(f"  {status}: {s.env_var}")
            print(f"         {s.description}")
        
        print("\nOPTIONAL CREDENTIALS:")
        for s in optional:
            if s.is_set:
                print(f"  ✓ SET: {s.env_var}")
        
        configured = self.get_configured_adapters()
        print(f"\nCONFIGURED ADAPTERS: {len(configured)}")
        for adapter in configured:
            print(f"  - {adapter}")
        
        grok_status = self.validate_grok_for_hipaa()
        print(f"\nGROK HIPAA STATUS: {grok_status['message']}")
        
        print("="*60 + "\n")


# Global instance
_credential_manager: Optional[CredentialManager] = None


def get_credential_manager() -> CredentialManager:
    """Get the global credential manager instance"""
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = CredentialManager()
    return _credential_manager
