"""Hospital Configuration System for Grok Doc v2.5 Enterprise"""
from .hospital_config import HospitalConfig, load_hospital_config, get_current_config

__all__ = [
    'HospitalConfig',
    'load_hospital_config', 
    'get_current_config',
]
