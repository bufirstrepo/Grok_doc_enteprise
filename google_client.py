"""
Google Vertex AI Client for Hospital AI Integration
Supports Med-PaLM 2, Gemini Pro
"""

import os
from typing import Optional

try:
    import google.generativeai as genai
except ImportError:
    genai = None

class GoogleClient:
    """Client for Google Vertex AI / Gemini API"""
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.client = None
        
        if self.api_key and genai:
            genai.configure(api_key=self.api_key)
            self.client = True
    
    def is_ready(self) -> bool:
        return self.client is not None
    
    def query(
        self,
        prompt: str,
        model: str = "gemini-pro",
        temperature: float = 0.0,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None
    ) -> str:
        if not self.client:
            raise RuntimeError("Google API not configured. Set GOOGLE_API_KEY")
        
        try:
            model_obj = genai.GenerativeModel(model)
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            
            response = model_obj.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens
                )
            )
            return response.text
        except Exception as e:
            raise RuntimeError(f"Google API Error: {str(e)}")

def get_google_client():
    return GoogleClient()
