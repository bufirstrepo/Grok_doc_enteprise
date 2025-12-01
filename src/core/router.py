import os
import sys
from typing import Literal, Dict, Any

# Ensure root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from local_inference import grok_query

class ModelRouter:
    def __init__(self):
        # We don't need to init clients here because local_inference handles it via singleton factory
        pass

    def route_request(self, stage: str, prompt: str, context: str) -> str:
        """
        Routes the clinical task to the absolute best model for that specific cognitive function.
        
        Args:
            stage: The clinical stage (SCRIBE, KINETICS, etc.)
            prompt: The system persona / instructions
            context: The user input / patient context
        """
        if stage == "SCRIBE":
            # Claude 3.5 Sonnet is undisputed king of structured JSON extraction & OCR
            return self._call_provider("claude", "claude-3-5-sonnet-20250620", prompt, context)
        
        elif stage == "KINETICS":
            # DeepSeek or Gemini Pro for pure math/logic reasoning
            # We use a 'Diversity Fallback' - if one fails, try the other
            try:
                return self._call_provider("gemini", "gemini-1.5-pro-002", prompt, context)
            except Exception as e:
                print(f"   >>> [ROUTER] Primary Kinetics failed: {e}. Fallback to Grok-4.")
                return self._call_provider("grok", "grok-4-math", prompt, context)

        elif stage == "BLUE_TEAM":
            # Claude is the best "Rule Follower" for finding syntax/guideline errors
            return self._call_provider("claude", "claude-3-5-sonnet-20250620", prompt, context)

        elif stage == "RED_TEAM":
            # Grok is the only model uncensored enough to aggressively simulate a "Killer" doctor
            return self._call_provider("grok", "grok-4", prompt, context)

        elif stage == "LITERATURE":
            # Perplexity for real-time web retrieval (2025 citations)
            return self._call_provider("perplexity", "sonar-pro-online", prompt, context)

        elif stage == "ARBITER":
            # Claude for the final safe, empathetic synthesis
            return self._call_provider("claude", "claude-3-opus-2025", prompt, context)
            
        else:
            raise ValueError(f"Unknown Clinical Stage: {stage}")

    def _call_provider(self, provider: str, model: str, system: str, user_msg: str) -> str:
        print(f"   >>> ROUTING TO: {provider.upper()} ({model})")
        
        # Call local_inference.grok_query
        # system is the persona
        # user_msg is the context/input
        
        response = grok_query(
            prompt=user_msg,
            model_name=model,
            system_prompt=system,
            temperature=0.0 # Default strict
        )
        
        # Handle dict response if any (grok_query returns str usually, but safe_grok_query handles dict)
        if isinstance(response, dict):
            return response.get("text", "")
        return str(response)
