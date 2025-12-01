"""
Anthropic Claude Client for Hospital AI Integration
Supports Claude 3.5 Sonnet, Claude 3 Opus
"""

import os
from typing import Optional

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

class AnthropicClient:
    """Client for Anthropic Claude API"""
    
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = None
        
        if self.api_key and Anthropic:
            self.client = Anthropic(api_key=self.api_key)
    
    def is_ready(self) -> bool:
        return self.client is not None
    
    def query(
        self,
        prompt: str,
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.0,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None
    ) -> str:
        if not self.client:
            raise RuntimeError("Anthropic API not configured. Set ANTHROPIC_API_KEY")
        
        try:
            response = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt or "You are a clinical AI assistant.",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            raise RuntimeError(f"Anthropic Error: {str(e)}")

def get_anthropic_client():
    return AnthropicClient()
