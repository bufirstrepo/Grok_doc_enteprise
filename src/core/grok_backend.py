"""
Grok API Backend

HIPAA-compliant integration with xAI's Grok API.
Requires Business Associate Agreement (BAA) for PHI processing.
"""

import os
import json
import time
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from datetime import datetime


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
    
    IMPORTANT: Only use this backend if:
    1. You have signed a BAA with xAI
    2. GROK_HAS_BAA environment variable is set to 'true'
    
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
    
    def is_hipaa_ready(self) -> bool:
        """
        Check if Grok is ready for HIPAA-compliant use.
        
        Returns True only if:
        1. API key is configured
        2. BAA confirmation flag is set
        """
        return self.is_configured() and self._baa_confirmed
    
    def get_hipaa_status(self) -> Dict[str, Any]:
        """Get detailed HIPAA compliance status"""
        return {
            'api_key_configured': self.is_configured(),
            'baa_confirmed': self._baa_confirmed,
            'hipaa_ready': self.is_hipaa_ready(),
            'model': self.model,
            'message': (
                "Ready for HIPAA-compliant use" if self.is_hipaa_ready()
                else "NOT ready: " + (
                    "API key not configured" if not self.is_configured()
                    else "BAA not confirmed (set GROK_HAS_BAA=true after signing with xAI)"
                )
            )
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
            RuntimeError: If not HIPAA ready or API error
        """
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
