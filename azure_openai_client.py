"""
Azure OpenAI Client for Hospital AI Integration
Supports GPT-4, GPT-4-Turbo with Azure's HIPAA-compliant infrastructure
"""

import os
from typing import Optional

try:
    from openai import AzureOpenAI
except ImportError:
    AzureOpenAI = None

class AzureOpenAIClient:
    """Client for Azure OpenAI endpoint (HIPAA-compliant)"""
    
    def __init__(self):
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        self.client = None
        
        if self.api_key and self.endpoint and AzureOpenAI:
            self.client = AzureOpenAI(
                api_key=self.api_key,
                azure_endpoint=self.endpoint,
                api_version=self.api_version
            )
    
    def is_ready(self) -> bool:
        return self.client is not None
    
    def query(
        self,
        prompt: str,
        model: str = "gpt-4-turbo",
        temperature: float = 0.0,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None
    ) -> str:
        if not self.client:
            raise RuntimeError("Azure OpenAI not configured. Set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"Azure OpenAI Error: {str(e)}")

def get_azure_client():
    return AzureOpenAIClient()
