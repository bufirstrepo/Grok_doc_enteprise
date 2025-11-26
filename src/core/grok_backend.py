"""
Grok API Backend

HIPAA-compliant integration with xAI's Grok API.
Requires Business Associate Agreement (BAA) for PHI processing.

IMPORTANT: This backend is DISABLED BY DEFAULT for HIPAA compliance.
To enable, you MUST:
1. Sign a Business Associate Agreement (BAA) with xAI
2. Set GROK_HAS_BAA=true environment variable
3. Set GROK_CLOUD_ENABLED=true environment variable

Without these safeguards, the system operates in LOCAL-ONLY mode to prevent
accidental PHI transmission to cloud services.
"""

import os
import json
import time
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from datetime import datetime


class CloudDisabledError(Exception):
    """Raised when cloud API is called without proper authorization"""
    pass


@dataclass
class GrokResponse:
    """Response from Grok API"""
    content: str
    model: str
    usage: Dict[str, int]
    latency_ms: float
    finish_reason: str
    timestamp: str


class GrokAPIBackend:
    """
    HIPAA-compliant Grok API backend.
    
    SECURITY: This backend has a HARD SAFEGUARD to prevent PHI transmission.
    
    To use cloud Grok API, you MUST:
    1. Sign a BAA with xAI
    2. Set GROK_HAS_BAA=true
    3. Set GROK_CLOUD_ENABLED=true (explicit opt-in)
    
    Without GROK_CLOUD_ENABLED=true, all API calls will raise CloudDisabledError.
    This ensures 100% on-premises operation by default.
    
    Usage:
        backend = GrokAPIBackend()
        if backend.is_hipaa_ready():
            response = backend.query("Clinical question here")
    """
    
    SUPPORTED_MODELS = [
        "grok-3",
        "grok-3-fast",
        "grok-3-mini",
        "grok-3-mini-fast"
    ]
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "grok-3",
        base_url: str = "https://api.x.ai/v1"
    ):
        """
        Initialize Grok API backend.
        
        Args:
            api_key: xAI API key (or set GROK_API_KEY env var)
            model: Grok model to use
            base_url: API base URL
        """
        self.api_key = api_key or os.getenv('GROK_API_KEY')
        self.model = model
        self.base_url = base_url
        self._session = None
        self._baa_confirmed = os.getenv('GROK_HAS_BAA', 'false').lower() == 'true'
        self._cloud_enabled = os.getenv('GROK_CLOUD_ENABLED', 'false').lower() == 'true'
    
    def _get_session(self):
        """Get or create HTTP session"""
        if self._session is None:
            try:
                import requests
                self._session = requests.Session()
                self._session.headers.update({
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.api_key}'
                })
            except ImportError:
                raise RuntimeError("requests library required")
        return self._session
    
    def is_configured(self) -> bool:
        """Check if API key is configured"""
        return self.api_key is not None
    
    def is_cloud_enabled(self) -> bool:
        """
        Check if cloud API is explicitly enabled.
        
        Returns True only if GROK_CLOUD_ENABLED=true.
        This is an additional safeguard beyond BAA confirmation.
        """
        return self._cloud_enabled
    
    def is_hipaa_ready(self) -> bool:
        """
        Check if Grok is ready for HIPAA-compliant use.
        
        Returns True only if:
        1. API key is configured
        2. BAA confirmation flag is set
        3. Cloud is explicitly enabled
        """
        return self.is_configured() and self._baa_confirmed and self._cloud_enabled
    
    def get_hipaa_status(self) -> Dict[str, Any]:
        """Get detailed HIPAA compliance status"""
        if self.is_hipaa_ready():
            message = "Ready for HIPAA-compliant cloud use"
        elif not self.is_configured():
            message = "Cloud DISABLED: API key not configured (local inference only)"
        elif not self._baa_confirmed:
            message = "Cloud DISABLED: BAA not confirmed (set GROK_HAS_BAA=true after signing)"
        elif not self._cloud_enabled:
            message = "Cloud DISABLED: Explicit opt-in required (set GROK_CLOUD_ENABLED=true)"
        else:
            message = "Cloud DISABLED: Configuration error"
            
        return {
            'api_key_configured': self.is_configured(),
            'baa_confirmed': self._baa_confirmed,
            'cloud_enabled': self._cloud_enabled,
            'hipaa_ready': self.is_hipaa_ready(),
            'model': self.model,
            'mode': 'cloud' if self.is_hipaa_ready() else 'local_only',
            'message': message
        }
    
    def query(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        stream: bool = False
    ) -> GrokResponse:
        """
        Query Grok API.
        
        Args:
            prompt: User prompt/question
            system_prompt: System context
            temperature: Sampling temperature (0.0 for deterministic)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream response
            
        Returns:
            GrokResponse object
            
        Raises:
            CloudDisabledError: If cloud API is not explicitly enabled
            RuntimeError: If API key not configured or API error
        """
        if not self._cloud_enabled:
            raise CloudDisabledError(
                "Cloud API is DISABLED for HIPAA compliance. "
                "To enable, set GROK_CLOUD_ENABLED=true and GROK_HAS_BAA=true "
                "after signing a BAA with xAI. Use local inference instead."
            )
        
        if not self._baa_confirmed:
            raise CloudDisabledError(
                "Cloud API blocked: BAA not confirmed. "
                "Set GROK_HAS_BAA=true only after signing a BAA with xAI."
            )
        
        if not self.is_configured():
            raise RuntimeError("Grok API key not configured")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        request_data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        start_time = time.time()
        
        try:
            session = self._get_session()
            response = session.post(
                f"{self.base_url}/chat/completions",
                json=request_data,
                timeout=60
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            if response.status_code != 200:
                raise RuntimeError(f"Grok API error: {response.status_code} - {response.text}")
            
            data = response.json()
            
            choice = data.get('choices', [{}])[0]
            message = choice.get('message', {})
            
            return GrokResponse(
                content=message.get('content', ''),
                model=data.get('model', self.model),
                usage=data.get('usage', {}),
                latency_ms=latency_ms,
                finish_reason=choice.get('finish_reason', 'unknown'),
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
            
        except Exception as e:
            raise RuntimeError(f"Grok API request failed: {e}")
    
    def query_clinical(
        self,
        clinical_question: str,
        patient_context: Dict[str, Any],
        include_safety_warning: bool = True
    ) -> GrokResponse:
        """
        Clinical-specific query with appropriate system prompts.
        
        Args:
            clinical_question: The clinical question
            patient_context: Patient data context
            include_safety_warning: Add disclaimer about AI limitations
            
        Returns:
            GrokResponse with clinical reasoning
        """
        system_prompt = """You are a clinical decision support AI assistant.

IMPORTANT DISCLAIMERS:
- Your responses are for clinical decision SUPPORT only
- Final clinical decisions must be made by licensed healthcare providers
- Always recommend consultation with specialists when appropriate
- Acknowledge uncertainty when evidence is limited

When providing recommendations:
1. Consider patient-specific factors (age, comorbidities, medications)
2. Reference evidence-based guidelines when applicable
3. Highlight critical safety considerations
4. Suggest appropriate monitoring parameters"""

        context_str = json.dumps(patient_context, indent=2)
        
        prompt = f"""PATIENT CONTEXT:
{context_str}

CLINICAL QUESTION:
{clinical_question}

Please provide a structured clinical recommendation."""

        return self.query(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.0,
            max_tokens=1500
        )
    
    def list_models(self) -> List[str]:
        """List available Grok models"""
        return self.SUPPORTED_MODELS.copy()


_grok_backend: Optional[GrokAPIBackend] = None


def get_grok_backend() -> GrokAPIBackend:
    """Get or create global Grok backend instance"""
    global _grok_backend
    if _grok_backend is None:
        _grok_backend = GrokAPIBackend()
    return _grok_backend
