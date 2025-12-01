"""
Local LLM Inference Engine with Explicit Model Routing

Central model routing for Grok Doc v6.5+
Supports xAI API (Cloud) and legacy local backends.

This is the ONLY file that determines which model is used for inference.
All model selection flows through CURRENT_MODEL or explicit model_name parameter.
"""

from functools import lru_cache
from typing import Literal, Optional, Dict, cast
import os
import sys

# Ensure src is in path for imports if running from root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config.hospital_config import get_config

# ── CENTRAL MODEL SELECTOR ───────────────────────────────────────
# This is the ONLY place you change the default model for the entire system

# Type hint for known models (extensible via config)
ModelType = str

_default_model = os.getenv("GROK_DEFAULT_MODEL", "grok-beta")
CURRENT_MODEL: ModelType = _default_model

# ── SINGLETON FACTORY ────────────────────────────────────────────

@lru_cache(maxsize=5)
def get_llm(model_name: Optional[str] = None) -> Dict:
    """
    Singleton factory with explicit model routing using Unified Dynamic Configuration.
    """
    config = get_config()
    model = model_name or CURRENT_MODEL

    # Validate model against dynamic config
    if model not in config.ai_tools:
        # Fallback logic or error
        print(f"⚠️ Warning: Model '{model}' not found in configuration. Defaulting to xAI.")
        # We can try to find a default xAI tool or just fail if strict
        # For now, let's try to find a tool with 'xai_api' backend or default to hardcoded fallback
        backend_type = "xai_api"
        tool_config = None
    else:
        tool_config = config.ai_tools[model]
        backend_type = tool_config.backend

    # ── xAI API Backend ──
    if backend_type == "xai_api":
        from grok_client import get_grok_client
        client = get_grok_client()
        return {"type": "xai_api", "name": model, "engine": client}
    
    # ── Azure OpenAI Backend (Hospital HIPAA) ──
    elif backend_type == "azure_openai":
        from azure_openai_client import get_azure_client
        client = get_azure_client()
        return {"type": "azure_openai", "name": model, "engine": client}
    
    # ── Anthropic Claude Backend ──
    elif backend_type == "anthropic":
        from anthropic_client import get_anthropic_client
        client = get_anthropic_client()
        return {"type": "anthropic", "name": model, "engine": client}
    
    # ── Google Vertex AI Backend ──
    elif backend_type == "google":
        from google_client import get_google_client
        client = get_google_client()
        return {"type": "google", "name": model, "engine": client}

    # ── vLLM Backend (Local/On-Prem) ──
    elif backend_type == "vllm":
        try:
            from vllm_engine import get_vllm_engine
            engine = get_vllm_engine(model)
            return {"type": "vllm", "name": model, "engine": engine}
        except ImportError:
            raise RuntimeError("vLLM backend not installed.")

    # ── Perplexity Backend ──
    elif backend_type == "perplexity":
        from perplexity_client import get_perplexity_client
        client = get_perplexity_client()
        return {"type": "perplexity", "name": model, "engine": client}

    else:
        raise ValueError(f"Unknown backend type: {backend_type} for model {model}")


# ── PRIMARY INFERENCE FUNCTION ───────────────────────────────────

def grok_query(
    prompt: str,
    temperature: float = 0.0,
    max_tokens: int = 2048,
    model_name: Optional[str] = None,
    system_prompt: Optional[str] = None,
    stream: bool = False,
) -> str:
    """
    Primary entry point for clinical reasoning.
    """
    # Get LLM engine
    llm = get_llm(model_name)

    try:
        # ── Route to appropriate backend ──

        # ── xAI API ──
        if llm["type"] == "xai_api":
            client = llm["engine"]
            return client.query_xai(
                prompt,
                model=llm["name"],
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=system_prompt,
                stream=stream
            )
        
        # ── Azure OpenAI ──
        elif llm["type"] == "azure_openai":
            client = llm["engine"]
            return client.query(
                prompt,
                model=llm["name"],
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=system_prompt
            )
        
        # ── Anthropic Claude ──
        elif llm["type"] == "anthropic":
            client = llm["engine"]
            return client.query(
                prompt,
                model=llm["name"],
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=system_prompt
            )
        
        # ── Google Vertex AI ──
        elif llm["type"] == "google":
            client = llm["engine"]
            return client.query(
                prompt,
                model=llm["name"],
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=system_prompt
            )

        # ── Local vLLM ──
        elif llm["type"] == "vllm":
            from vllm_engine import query_vllm
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            return query_vllm(
                llm["engine"],
                full_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream
            )

        # ── Perplexity ──
        elif llm["type"] == "perplexity":
            client = llm["engine"]
            return client.query(
                prompt,
                model=llm["name"],
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=system_prompt
            )

        else:
            raise RuntimeError(f"Backend {llm['type']} not implemented")

    except Exception as e:
        # ── FALLBACK HANDLING ──
        from audit_log import log_fallback_event

        # Log the fallback event
        log_fallback_event(
            primary_model=llm["name"],
            exception_msg=str(e)
        )
        
        return f"⚠️ AI Error: {str(e)}"


# ── STATUS & DIAGNOSTICS ─────────────────────────────────────────

def check_model_status(model_name: Optional[str] = None) -> dict:
    """Check if a model is ready."""
    model = model_name or CURRENT_MODEL
    try:
        llm = get_llm(model)
        if llm["type"] == "xai_api":
            client = llm["engine"]
            return {
                "model_name": model,
                "backend": "xai_api",
                "loaded": client.is_ready(),
                "api_key_configured": bool(client.api_key)
            }
        else:
            # Generic status for other backends
            return {"model_name": model, "backend": llm["type"], "loaded": True}
    except Exception as e:
        return {"model_name": model, "error": str(e)}


def list_available_models() -> dict:
    """List all available models from dynamic config."""
    config = get_config()
    # Return a dict mapping model_name -> backend_type to match previous signature
    return {name: tool.backend for name, tool in config.ai_tools.items()}


def get_current_model() -> str:
    """Get the current default model."""
    return CURRENT_MODEL


# ── INITIALIZATION ───────────────────────────────────────────────

def init_inference_engine():
    """Initialize the inference engine."""
    print("=" * 60)
    print("Grok Doc Inference Engine - Unified Dynamic Config")
    print("=" * 60)
    print(f"Default Model: {CURRENT_MODEL}")
    
    config = get_config()
    if CURRENT_MODEL in config.ai_tools:
        print(f"Backend: {config.ai_tools[CURRENT_MODEL].backend}")
    else:
        print(f"Backend: Unknown (Model {CURRENT_MODEL} not in config)")
    
    # Check API Key
    if not os.getenv("XAI_API_KEY"):
        print("⚠️  WARNING: XAI_API_KEY not found. API calls will fail.")
    else:
        print("✓ XAI_API_KEY configured")
    print("=" * 60)


# Auto-init on import
if os.getenv("SKIP_AUTO_INIT", "false").lower() != "true":
    init_inference_engine()
