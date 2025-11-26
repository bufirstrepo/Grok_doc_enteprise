"""
Hospital Configuration System

Allows per-hospital customization of:
- EHR system (Epic, Cerner, etc.)
- Enabled AI tool adapters
- Network/compliance settings
- Feature flags
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class EHRConfig:
    """EHR system configuration"""
    type: str = "epic"  # epic, cerner, meditech, allscripts
    fhir_endpoint: str = ""
    client_id: str = ""
    client_secret_env: str = ""  # Name of env var containing secret
    scopes: List[str] = field(default_factory=lambda: [
        "patient/*.read",
        "observation/*.read", 
        "condition/*.read",
        "medicationrequest/*.read"
    ])
    oauth_token_url: str = ""
    supports_bulk_export: bool = False
    hl7v2_enabled: bool = False
    hl7v2_port: int = 2575


@dataclass
class AIAdapterConfig:
    """Configuration for a hospital AI tool adapter"""
    enabled: bool = False
    api_endpoint: str = ""
    api_key_env: str = ""  # Name of env var containing API key
    timeout_seconds: int = 30
    priority: int = 1  # Lower = higher priority
    fallback_enabled: bool = True


@dataclass
class AIToolsConfig:
    """All hospital AI tool adapters"""
    aidoc: AIAdapterConfig = field(default_factory=AIAdapterConfig)
    pathAI: AIAdapterConfig = field(default_factory=AIAdapterConfig)
    tempus: AIAdapterConfig = field(default_factory=AIAdapterConfig)
    butterfly_iq: AIAdapterConfig = field(default_factory=AIAdapterConfig)
    caption_health: AIAdapterConfig = field(default_factory=AIAdapterConfig)
    ibm_watson: AIAdapterConfig = field(default_factory=AIAdapterConfig)
    deepmind_health: AIAdapterConfig = field(default_factory=AIAdapterConfig)
    keragon: AIAdapterConfig = field(default_factory=AIAdapterConfig)
    nuance_dax: AIAdapterConfig = field(default_factory=AIAdapterConfig)
    
    def get_enabled_adapters(self) -> Dict[str, AIAdapterConfig]:
        """Return only enabled adapters"""
        result = {}
        for name, config in asdict(self).items():
            if config.get('enabled', False):
                result[name] = AIAdapterConfig(**config)
        return result


@dataclass
class FeatureConfig:
    """Feature flags for hospital customization"""
    ambient_scribe: bool = True
    patient_messaging: bool = True
    discharge_summaries: bool = True
    risk_prediction: bool = True
    cds_hooks: bool = True
    multi_llm_chain: bool = True
    bayesian_analysis: bool = True
    continuous_learning: bool = True
    mobile_copilot: bool = False


@dataclass
class ComplianceConfig:
    """Compliance and security settings"""
    network_subnets: List[str] = field(default_factory=lambda: ["10.0.0.0/8"])
    require_wifi_check: bool = True
    audit_retention_days: int = 2555  # 7 years for HIPAA
    ssl_cert_pinning: bool = True
    hospital_internal_host: str = "internal-ehr.hospital.local"
    hospital_internal_port: int = 443
    expected_cert_sha256: str = ""
    ssid_keywords: List[str] = field(default_factory=lambda: ["Hospital-Secure", "HOSP-CLINICAL"])


@dataclass
class LLMConfig:
    """LLM and inference settings"""
    default_model: str = "llama-3.1-70b"
    grok_enabled: bool = False
    grok_api_key_env: str = "GROK_API_KEY"
    grok_has_baa: bool = False  # Must have BAA for HIPAA compliance
    temperature: float = 0.0
    max_tokens: int = 2048
    fallback_model: str = "llama-3.1-70b"


@dataclass
class HospitalConfig:
    """Complete hospital configuration"""
    hospital_id: str = "default"
    hospital_name: str = "Default Hospital"
    ehr: EHRConfig = field(default_factory=EHRConfig)
    ai_tools: AIToolsConfig = field(default_factory=AIToolsConfig)
    features: FeatureConfig = field(default_factory=FeatureConfig)
    compliance: ComplianceConfig = field(default_factory=ComplianceConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    def save(self, path: Optional[str] = None) -> str:
        """Save configuration to JSON file"""
        if path is None:
            path = f"config/hospital_{self.hospital_id}.json"
        
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        self.updated_at = datetime.utcnow().isoformat() + "Z"
        
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        
        return path
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HospitalConfig':
        """Create HospitalConfig from dictionary"""
        ehr = EHRConfig(**data.get('ehr', {}))
        
        ai_tools_data = data.get('ai_tools', {})
        ai_tools = AIToolsConfig(
            aidoc=AIAdapterConfig(**ai_tools_data.get('aidoc', {})),
            pathAI=AIAdapterConfig(**ai_tools_data.get('pathAI', {})),
            tempus=AIAdapterConfig(**ai_tools_data.get('tempus', {})),
            butterfly_iq=AIAdapterConfig(**ai_tools_data.get('butterfly_iq', {})),
            caption_health=AIAdapterConfig(**ai_tools_data.get('caption_health', {})),
            ibm_watson=AIAdapterConfig(**ai_tools_data.get('ibm_watson', {})),
            deepmind_health=AIAdapterConfig(**ai_tools_data.get('deepmind_health', {})),
            keragon=AIAdapterConfig(**ai_tools_data.get('keragon', {})),
            nuance_dax=AIAdapterConfig(**ai_tools_data.get('nuance_dax', {})),
        )
        
        features = FeatureConfig(**data.get('features', {}))
        compliance = ComplianceConfig(**data.get('compliance', {}))
        llm = LLMConfig(**data.get('llm', {}))
        
        return cls(
            hospital_id=data.get('hospital_id', 'default'),
            hospital_name=data.get('hospital_name', 'Default Hospital'),
            ehr=ehr,
            ai_tools=ai_tools,
            features=features,
            compliance=compliance,
            llm=llm,
            created_at=data.get('created_at', datetime.utcnow().isoformat() + "Z"),
            updated_at=data.get('updated_at', datetime.utcnow().isoformat() + "Z")
        )
    
    @classmethod
    def load(cls, path: str) -> 'HospitalConfig':
        """Load configuration from JSON file"""
        with open(path, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)


# Global config instance
_current_config: Optional[HospitalConfig] = None


def load_hospital_config(config_path: Optional[str] = None) -> HospitalConfig:
    """
    Load hospital configuration from file or environment.
    
    Args:
        config_path: Path to config file. If None, tries:
            1. HOSPITAL_CONFIG_PATH env var
            2. config/hospital_config.json
            3. Creates default config
    
    Returns:
        HospitalConfig instance
    """
    global _current_config
    
    if config_path is None:
        config_path = os.getenv('HOSPITAL_CONFIG_PATH')
    
    if config_path is None:
        default_paths = [
            'config/hospital_config.json',
            'hospital_config.json',
            '/etc/grokdoc/hospital_config.json'
        ]
        for path in default_paths:
            if Path(path).exists():
                config_path = path
                break
    
    if config_path and Path(config_path).exists():
        _current_config = HospitalConfig.load(config_path)
        print(f"✓ Loaded hospital config from {config_path}")
    else:
        _current_config = HospitalConfig()
        print("⚠️  Using default hospital config (no config file found)")
    
    return _current_config


def get_current_config() -> HospitalConfig:
    """Get the current hospital configuration (loads if not already loaded)"""
    global _current_config
    if _current_config is None:
        return load_hospital_config()
    return _current_config


def create_sample_config(hospital_id: str = "sample_hospital") -> HospitalConfig:
    """Create a sample hospital configuration for reference"""
    config = HospitalConfig(
        hospital_id=hospital_id,
        hospital_name="Sample Medical Center",
        ehr=EHRConfig(
            type="epic",
            fhir_endpoint="https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4",
            client_id="your-client-id",
            client_secret_env="EPIC_CLIENT_SECRET",
            oauth_token_url="https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token"
        ),
        ai_tools=AIToolsConfig(
            aidoc=AIAdapterConfig(
                enabled=True,
                api_endpoint="https://api.aidoc.com/v1",
                api_key_env="AIDOC_API_KEY",
                priority=1
            ),
            tempus=AIAdapterConfig(
                enabled=True,
                api_endpoint="https://api.tempus.com/v1",
                api_key_env="TEMPUS_API_KEY",
                priority=2
            )
        ),
        features=FeatureConfig(
            ambient_scribe=True,
            patient_messaging=True,
            multi_llm_chain=True,
            continuous_learning=True
        ),
        compliance=ComplianceConfig(
            network_subnets=["10.50.0.0/16", "192.168.100.0/24"],
            require_wifi_check=True,
            audit_retention_days=2555
        ),
        llm=LLMConfig(
            default_model="llama-3.1-70b",
            grok_enabled=True,
            grok_has_baa=True  # Important: Must have BAA signed!
        )
    )
    
    return config
