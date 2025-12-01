"""
Hospital Configuration System (v3.1)

Allows per-hospital customization of:
- EHR system (Epic, Cerner, etc.)
- Enabled AI tool adapters
- Network/compliance settings
- Feature flags
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "hospital_config.json")
AI_TOOLS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "ai_tools.yaml")

@dataclass
class EHRConfig:
    system: str
    fhir_url: str
    client_id: str
    client_secret: str = ""
    auth_flow: str = "client_credentials"

@dataclass
class AIAdapterConfig:
    backend: str
    enabled: bool = True
    api_key_env: str = ""
    model_path: str = ""
    max_tokens: int = 2048
    temperature: float = 0.0

@dataclass
class FeatureConfig:
    enable_hcc_scoring: bool = False
    enable_meat_compliance: bool = False
    enable_clinical_trials: bool = False
    enable_sepsis_prediction: bool = False
    enable_readmission_risk: bool = False
    enable_denial_prediction: bool = False
    enable_sdoh_screening: bool = False
    enable_peer_review: bool = False

@dataclass
class ComplianceConfig:
    require_wifi: bool = True
    wifi_keywords: List[str] = field(default_factory=list)
    audit_log_path: str = "audit.db"
    encryption_enabled: bool = True
    ldap_enabled: bool = False
    ldap_server: str = ""

@dataclass
class LLMConfig:
    default_model: str = "grok-beta"
    chain_mode_enabled: bool = True
    fast_mode_enabled: bool = True

@dataclass
class HospitalConfig:
    hospital_name: str
    site_id: str
    ehr: EHRConfig
    ai_tools: Dict[str, AIAdapterConfig]
    features: FeatureConfig
    compliance: ComplianceConfig
    llm_config: LLMConfig

    @classmethod
    def load(cls, path: Optional[str] = None) -> 'HospitalConfig':
        target_path = path if path else CONFIG_PATH
        if not os.path.exists(target_path):
            # Return default/empty config if file missing (or raise error depending on policy)
            # For now, let's raise to be safe, or return a default if that's expected behavior
            if not path: # If looking for default and missing
                 print(f"⚠️ Config not found at {target_path}, using defaults.")
                 return cls(
                     hospital_name="Default", site_id="DEF", 
                     ehr=EHRConfig("Other", "", ""), 
                     ai_tools={}, 
                     features=FeatureConfig(), 
                     compliance=ComplianceConfig(), 
                     llm_config=LLMConfig()
                 )
            raise FileNotFoundError(f"Config not found at {target_path}")

        with open(target_path, 'r') as f:
            data = json.load(f)

        # Load AI Tools from YAML if available, otherwise use JSON
        ai_tools_data = data.get("ai_tools", {})
        if os.path.exists(AI_TOOLS_PATH):
            try:
                with open(AI_TOOLS_PATH, 'r') as f:
                    yaml_data = yaml.safe_load(f)
                    if yaml_data and "ai_tools" in yaml_data:
                        ai_tools_data.update(yaml_data["ai_tools"])
            except Exception as e:
                print(f"⚠️ Warning: Failed to load ai_tools.yaml: {e}")

        return cls(
            hospital_name=data.get("hospital_name", "Unknown"),
            site_id=data.get("site_id", "Unknown"),
            ehr=EHRConfig(**data.get("ehr", {})),
            ai_tools={k: AIAdapterConfig(**v) for k, v in ai_tools_data.items()},
            features=FeatureConfig(**data.get("features", {})),
            compliance=ComplianceConfig(**data.get("compliance", {})),
            llm_config=LLMConfig(**data.get("llm_config", {}))
        )

# Global config instance
_current_config: Optional[HospitalConfig] = None

def load_hospital_config(config_path: Optional[str] = None) -> HospitalConfig:
    """
    Load hospital configuration from file or environment.
    """
    global _current_config
    
    if config_path is None:
        config_path = os.getenv('HOSPITAL_CONFIG_PATH')
    
    if config_path is None:
        # Check standard locations
        default_paths = [
            CONFIG_PATH,
            'config/hospital_config.json',
            'hospital_config.json'
        ]
        for path in default_paths:
            if Path(path).exists():
                config_path = path
                break
    
    _current_config = HospitalConfig.load(config_path)
    return _current_config

def get_current_config() -> HospitalConfig:
    """Get the current hospital configuration (loads if not already loaded)"""
    global _current_config
    if _current_config is None:
        return load_hospital_config()
    return _current_config

# Alias for compatibility
get_config = get_current_config
