"""Hospital AI Tool Adapter Framework"""
from .base import AIToolAdapter, AdapterResult
from .adapter_registry import AdapterRegistry, get_adapter_registry
from .aidoc import AidocAdapter
from .pathAI import PathAIAdapter
from .tempus import TempusAdapter
from .butterfly import ButterflyAdapter
from .caption_health import CaptionHealthAdapter
from .ibm_watson import IBMWatsonAdapter
from .deepmind import DeepMindAdapter
from .keragon import KeragonAdapter

__all__ = [
    'AIToolAdapter',
    'AdapterResult',
    'AdapterRegistry',
    'get_adapter_registry',
    'AidocAdapter',
    'PathAIAdapter', 
    'TempusAdapter',
    'ButterflyAdapter',
    'CaptionHealthAdapter',
    'IBMWatsonAdapter',
    'DeepMindAdapter',
    'KeragonAdapter'
]
