"""
xAI Grok API Client
Wraps the OpenAI SDK to communicate with xAI's Grok models.
"""

import os
from typing import Optional, Dict, Any
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

class GrokClient:
    """
    Client for interacting with xAI's Grok API.
    Uses the OpenAI SDK as xAI is API-compatible.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Grok client.
        
        Args:
            api_key: xAI API key. If None, tries to load from XAI_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("XAI_API_KEY")
        self.client = None
        
        if self.api_key and OpenAI:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.x.ai/v1"
            )
            
    def is_ready(self) -> bool:
        """Check if client is configured and ready."""
        return self.client is not None

    def query_xai(
        self,
        prompt: str,
        model: str = "grok-beta",
        temperature: float = 0.0,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None,
        stream: bool = False
    ) -> str:
        """
        Send a query to xAI's Grok API.
        
        Args:
            prompt: User query
            model: Model name (e.g., "grok-beta", "grok-2")
            temperature: Sampling temperature
            max_tokens: Max output tokens
            system_prompt: Optional system instruction
            stream: Whether to stream output (not yet implemented)
            
        Returns:
            Generated text response
        """
        if not self.client:
            raise RuntimeError("xAI API Key not configured. Set XAI_API_KEY environment variable.")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream
            )
            
            if stream:
                # Placeholder for streaming support
                return "Streaming not yet implemented in this wrapper."
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise RuntimeError(f"xAI API Error: {str(e)}")

def get_grok_client() -> GrokClient:
    """Factory to get a singleton-like client instance."""
    return GrokClient()
