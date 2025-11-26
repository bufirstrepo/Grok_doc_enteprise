"""
Adapter Registry

Central registry for managing hospital AI tool adapters.
Handles auto-discovery, initialization, and orchestration.
"""

from typing import Dict, List, Optional, Type, Any
from dataclasses import dataclass
import os

from .base import AIToolAdapter, AdapterResult, InsightCategory


@dataclass
class AdapterConfig:
    """Configuration for an adapter"""
    adapter_class: Type[AIToolAdapter]
    enabled: bool = False
    api_endpoint: str = ""
    api_key_env: str = ""
    priority: int = 1
    timeout: int = 30


class AdapterRegistry:
    """
    Registry for managing hospital AI tool adapters.
    
    Features:
    - Auto-discovery of configured adapters
    - Parallel execution of multiple adapters
    - Fallback handling
    - Result aggregation
    """
    
    def __init__(self):
        self._adapters: Dict[str, AIToolAdapter] = {}
        self._configs: Dict[str, AdapterConfig] = {}
        self._initialized = False
    
    def register(
        self,
        name: str,
        adapter_class: Type[AIToolAdapter],
        enabled: bool = False,
        api_endpoint: str = "",
        api_key_env: str = "",
        priority: int = 1,
        timeout: int = 30
    ):
        """Register an adapter configuration"""
        self._configs[name] = AdapterConfig(
            adapter_class=adapter_class,
            enabled=enabled,
            api_endpoint=api_endpoint,
            api_key_env=api_key_env,
            priority=priority,
            timeout=timeout
        )
    
    def initialize_from_config(self, hospital_config: Dict[str, Any]):
        """
        Initialize adapters from hospital configuration.
        
        Args:
            hospital_config: Hospital AI tools configuration dict
        """
        from .aidoc import AidocAdapter
        from .pathAI import PathAIAdapter
        from .tempus import TempusAdapter
        from .butterfly import ButterflyAdapter
        from .caption_health import CaptionHealthAdapter
        from .ibm_watson import IBMWatsonAdapter
        from .deepmind import DeepMindAdapter
        from .keragon import KeragonAdapter
        
        adapter_map = {
            'aidoc': AidocAdapter,
            'pathAI': PathAIAdapter,
            'tempus': TempusAdapter,
            'butterfly_iq': ButterflyAdapter,
            'caption_health': CaptionHealthAdapter,
            'ibm_watson': IBMWatsonAdapter,
            'deepmind_health': DeepMindAdapter,
            'keragon': KeragonAdapter
        }
        
        ai_tools = hospital_config.get('ai_tools', {})
        
        for adapter_name, adapter_class in adapter_map.items():
            config = ai_tools.get(adapter_name, {})
            
            if config.get('enabled', False):
                api_key = None
                api_key_env = config.get('api_key_env', '')
                if api_key_env:
                    api_key = os.getenv(api_key_env)
                
                try:
                    adapter = adapter_class(
                        api_endpoint=config.get('api_endpoint', ''),
                        api_key=api_key,
                        timeout=config.get('timeout_seconds', 30),
                        enabled=True
                    )
                    self._adapters[adapter_name] = adapter
                    print(f"✓ Initialized {adapter_name} adapter")
                except Exception as e:
                    print(f"⚠️ Failed to initialize {adapter_name}: {e}")
        
        self._initialized = True
    
    def get_adapter(self, name: str) -> Optional[AIToolAdapter]:
        """Get a specific adapter by name"""
        return self._adapters.get(name)
    
    def get_enabled_adapters(self) -> Dict[str, AIToolAdapter]:
        """Get all enabled adapters"""
        return {
            name: adapter 
            for name, adapter in self._adapters.items()
            if adapter.enabled
        }
    
    def get_adapters_by_category(
        self,
        category: InsightCategory
    ) -> List[AIToolAdapter]:
        """Get adapters that support a specific insight category"""
        return [
            adapter for adapter in self._adapters.values()
            if adapter.enabled and category in adapter.supported_categories
        ]
    
    def analyze_all(
        self,
        patient_data: Dict[str, Any],
        categories: Optional[List[InsightCategory]] = None
    ) -> List[AdapterResult]:
        """
        Run analysis across all enabled adapters.
        
        Args:
            patient_data: Unified patient data
            categories: Filter by insight categories
            
        Returns:
            Aggregated list of results from all adapters
        """
        results = []
        
        adapters = self.get_enabled_adapters()
        
        if categories:
            adapters = {
                name: adapter for name, adapter in adapters.items()
                if any(cat in adapter.supported_categories for cat in categories)
            }
        
        for name, adapter in adapters.items():
            try:
                result = adapter.analyze(patient_data)
                results.append(result)
            except Exception as e:
                results.append(AdapterResult(
                    success=False,
                    adapter_name=name,
                    category="error",
                    content="",
                    error_message=str(e)
                ))
        
        return results
    
    def get_all_insights(
        self,
        patient_id: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> List[AdapterResult]:
        """
        Retrieve insights from all enabled adapters.
        
        Args:
            patient_id: Patient identifier
            from_date: Start date filter
            to_date: End date filter
            
        Returns:
            Aggregated list of insights
        """
        all_insights = []
        
        for name, adapter in self.get_enabled_adapters().items():
            try:
                insights = adapter.get_insights(
                    patient_id=patient_id,
                    from_date=from_date,
                    to_date=to_date
                )
                all_insights.extend(insights)
            except Exception as e:
                print(f"⚠️ Failed to get insights from {name}: {e}")
        
        all_insights.sort(key=lambda x: x.timestamp, reverse=True)
        
        return all_insights
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all adapters"""
        return {
            'initialized': self._initialized,
            'total_registered': len(self._configs),
            'total_enabled': len(self.get_enabled_adapters()),
            'adapters': {
                name: adapter.get_status()
                for name, adapter in self._adapters.items()
            }
        }


_registry: Optional[AdapterRegistry] = None


def get_adapter_registry() -> AdapterRegistry:
    """Get the global adapter registry"""
    global _registry
    if _registry is None:
        _registry = AdapterRegistry()
    return _registry
