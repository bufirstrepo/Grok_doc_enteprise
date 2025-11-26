"""
Local LLM Inference Engine with Explicit Model Routing

Central model routing for Grok Doc v2.0+
Supports multiple models across different backends (vLLM, Transformers).

This is the ONLY file that determines which model is used for inference.
All model selection flows through CURRENT_MODEL or explicit model_name parameter.
"""

from functools import lru_cache
from typing import Literal, Optional, Dict
import os

# ── CENTRAL MODEL SELECTOR ───────────────────────────────────────
# This is the ONLY place you change the default model for the entire system

CURRENT_MODEL: Literal[
    "grok-4",
    "claude-3.5-sonnet",
    "deepseek-r1",
    "deepseek-r1-distill-llama-70b",
    "llama-3.1-70b",
    "mixtral-8x22b"
] = os.getenv("GROK_DEFAULT_MODEL", "llama-3.1-70b")  # Default to llama-3.1-70b


# ── MODEL BACKEND MAPPING ────────────────────────────────────────

MODEL_BACKENDS = {
    # vLLM-compatible models (high performance, GPU-optimized)
    "grok-4": "vllm",
    "llama-3.1-70b": "vllm",
    "mixtral-8x22b": "vllm",

    # Transformers-only models (broader compatibility)
    "deepseek-r1": "transformers",
    "deepseek-r1-distill-llama-70b": "transformers",

    # Future: Local Claude proxy (when available)
    "claude-3.5-sonnet": "claude_proxy",
    "claude-3-opus": "claude_proxy",
}


# ── SINGLETON FACTORY ────────────────────────────────────────────

@lru_cache(maxsize=5)
def get_llm(model_name: Optional[str] = None) -> Dict:
    """
    Singleton factory with explicit model routing.

    This function is the heart of the tribunal experiment system:
    - Returns model engine + metadata for any supported model
    - LRU cache allows multiple models in memory (up to 5)
    - Explicit backend selection ensures reproducibility

    Args:
        model_name: Optional model override. If None, uses CURRENT_MODEL.

    Returns:
        dict: {
            "type": str,         # Backend type: "vllm", "transformers", "claude_proxy"
            "name": str,         # Model name
            "engine": Any,       # Backend-specific engine/pipeline
        }

    Raises:
        ValueError: If model not supported
        NotImplementedError: If backend not yet implemented
        RuntimeError: If model loading fails
    """
    model = model_name or CURRENT_MODEL

    # Validate model
    if model not in MODEL_BACKENDS:
        raise ValueError(
            f"Unsupported model: {model}\n"
            f"Supported models: {', '.join(MODEL_BACKENDS.keys())}"
        )

    backend = MODEL_BACKENDS[model]

    # ── vLLM Backend ──
    if backend == "vllm":
        from vllm_engine import get_vllm_engine
        engine = get_vllm_engine(model)
        return {"type": "vllm", "name": model, "engine": engine}

    # ── Transformers Backend ──
    elif backend == "transformers":
        from transformers_backend import get_deepseek_pipeline
        pipeline = get_deepseek_pipeline(model)
        return {"type": "transformers", "name": model, "engine": pipeline}

    # ── Claude Proxy (Future) ──
    elif backend == "claude_proxy":
        # Future: Local Claude proxy via Anthropic on-prem or vLLM when available
        raise NotImplementedError(
            f"Claude local backend not yet integrated for {model}.\n"
            "Planned for future release when on-premises Claude becomes available."
        )

    else:
        raise ValueError(f"Unknown backend: {backend}")


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

    This function provides:
    - Explicit model selection (critical for tribunal comparison)
    - Full provenance (backend type logged in audit trail)
    - Automatic logged fallback only if primary engine crashes
    - Zero-cloud guarantee (all inference on-premises)

    Args:
        prompt: Clinical question or prompt
        temperature: Sampling temperature (0.0 = deterministic for medical use)
        max_tokens: Maximum tokens to generate
        model_name: Optional model override (if None, uses CURRENT_MODEL)
        system_prompt: Optional system prompt to prepend
        stream: Whether to stream output (not yet implemented)

    Returns:
        str: Generated clinical response

    Raises:
        ValueError: If prompt invalid
        RuntimeError: If inference fails with no fallback available
    """
    # Get LLM engine
    llm = get_llm(model_name)

    # Build full prompt with system message
    if system_prompt:
        full_prompt = f"{system_prompt}\n\n{prompt}"
    else:
        full_prompt = prompt

    try:
        # ── Route to appropriate backend ──

        if llm["type"] == "vllm":
            from vllm_engine import query_vllm
            response = query_vllm(
                llm["engine"],
                full_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream
            )
            return response

        elif llm["type"] == "transformers":
            from transformers_backend import query_transformers
            response = query_transformers(
                llm["engine"],
                full_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream
            )
            return response

        else:
            raise RuntimeError(f"Backend {llm['type']} not implemented")

    except Exception as e:
        # ── FALLBACK HANDLING ──
        # This is the ONLY place fallback is allowed → auditable & measurable

        from audit_log import log_fallback_event

        # Log the fallback event
        fallback_logged = log_fallback_event(
            primary_model=llm["name"],
            exception_msg=str(e)
        )

        # Try fallback to smallest model (if not already using it)
        if llm["name"] != "llama-3.1-70b" and model_name is None:
            print(f"⚠️  Primary model {llm['name']} failed. Attempting fallback to llama-3.1-70b...")
            try:
                return grok_query(
                    prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    model_name="llama-3.1-70b",  # Explicit fallback
                    system_prompt=system_prompt,
                    stream=stream
                )
            except Exception as fallback_error:
                # Even fallback failed - return safe error message
                error_msg = (
                    "⚠️ AUTOMATED RESPONSE UNAVAILABLE\n\n"
                    "The AI inference engine encountered an error. "
                    "Please review this case manually and consult standard clinical guidelines.\n\n"
                    f"Primary model: {llm['name']}\n"
                    f"Error: {str(e)}\n"
                    f"Fallback error: {str(fallback_error)}"
                )
                return error_msg

        # No fallback available or explicit model requested - return error
        error_msg = (
            "⚠️ AUTOMATED RESPONSE UNAVAILABLE\n\n"
            "The AI inference engine encountered an error. "
            "Please review this case manually and consult standard clinical guidelines.\n\n"
            f"Model: {llm['name']}\n"
            f"Error: {str(e)}"
        )
        return error_msg


# ── ALTERNATIVE LEGACY FUNCTION ──────────────────────────────────
# Kept for backward compatibility with existing code

def grok_query_transformers(
    prompt: str,
    temperature: float = 0.0,
    max_tokens: int = 2048
) -> str:
    """
    Legacy fallback function using Transformers backend.
    Kept for backward compatibility.

    New code should use grok_query(model_name="deepseek-r1") instead.
    """
    return grok_query(
        prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        model_name="deepseek-r1"
    )


# ── STATUS & DIAGNOSTICS ─────────────────────────────────────────

def check_model_status(model_name: Optional[str] = None) -> dict:
    """
    Check if a model is loaded and get system info.

    Args:
        model_name: Model to check (if None, checks CURRENT_MODEL)

    Returns:
        dict: Model status information
    """
    model = model_name or CURRENT_MODEL

    try:
        llm = get_llm(model)

        if llm["type"] == "vllm":
            from vllm_engine import get_vllm_status
            return get_vllm_status(model)
        elif llm["type"] == "transformers":
            from transformers_backend import get_transformers_status
            return get_transformers_status(model)
        else:
            return {
                "model_name": model,
                "backend": llm["type"],
                "loaded": False,
                "error": "Backend not yet implemented"
            }
    except Exception as e:
        return {
            "model_name": model,
            "loaded": False,
            "error": str(e)
        }


def warmup_model(model_name: Optional[str] = None):
    """
    Warmup a model with a simple query to preload everything.
    Call during application startup to hide latency.

    Args:
        model_name: Model to warmup (if None, uses CURRENT_MODEL)

    Returns:
        bool: True if successful, False otherwise
    """
    model = model_name or CURRENT_MODEL

    try:
        llm = get_llm(model)

        if llm["type"] == "vllm":
            from vllm_engine import warmup_vllm
            return warmup_vllm(model)
        elif llm["type"] == "transformers":
            from transformers_backend import warmup_transformers
            return warmup_transformers(model)
        else:
            print(f"⚠️  Warmup not supported for backend: {llm['type']}")
            return False
    except Exception as e:
        print(f"⚠️  Model warmup failed for {model}: {e}")
        return False


def list_available_models() -> dict:
    """
    List all available models and their backends.

    Returns:
        dict: Model name -> backend mapping
    """
    return MODEL_BACKENDS.copy()


def get_current_model() -> str:
    """
    Get the current default model.

    Returns:
        str: Current model name
    """
    return CURRENT_MODEL


# ── INITIALIZATION ───────────────────────────────────────────────

def init_inference_engine():
    """
    Initialize the inference engine.
    Prints configuration and optionally warms up the default model.
    """
    print("=" * 60)
    print("Grok Doc Inference Engine - Model Routing System")
    print("=" * 60)
    print(f"Default Model: {CURRENT_MODEL}")
    print(f"Backend: {MODEL_BACKENDS.get(CURRENT_MODEL, 'Unknown')}")
    print(f"Available Models: {', '.join(MODEL_BACKENDS.keys())}")
    print("=" * 60)

    # Optional: Warmup default model
    warmup = os.getenv("WARMUP_MODEL", "false").lower() == "true"
    if warmup:
        print(f"Warming up {CURRENT_MODEL}...")
        warmup_model()


# Auto-init on import (can be disabled with env var)
if os.getenv("SKIP_AUTO_INIT", "false").lower() != "true":
    init_inference_engine()
