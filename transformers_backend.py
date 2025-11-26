"""
HuggingFace Transformers Backend

Handles Transformers-based model loading and inference.
Supports: DeepSeek-R1, and other HuggingFace models not yet compatible with vLLM.
Slower than vLLM but provides broader model compatibility.
"""

import os
import torch
from typing import Optional
from pathlib import Path
from functools import lru_cache

# ── MODEL CONFIGURATION ──────────────────────────────────────────

MODEL_PATHS = {
    "deepseek-r1": os.getenv("DEEPSEEK_MODEL_PATH", "deepseek-ai/DeepSeek-R1"),
    "deepseek-r1-distill-llama-70b": os.getenv("DEEPSEEK_DISTILL_PATH", "deepseek-ai/DeepSeek-R1-Distill-Llama-70B"),
}

# Inference settings
TEMPERATURE = 0.0  # Deterministic for medical use
MAX_NEW_TOKENS = 2048
LOAD_IN_8BIT = True  # Enable 8-bit quantization for memory efficiency


# ── SINGLETON PATTERN ────────────────────────────────────────────

_transformers_pipelines = {}  # model_name -> (model, tokenizer)


@lru_cache(maxsize=3)
def get_deepseek_pipeline(model_name: str = "deepseek-r1"):
    """
    Get or create DeepSeek model pipeline.

    Args:
        model_name: DeepSeek model variant

    Returns:
        tuple: (model, tokenizer)

    Raises:
        RuntimeError: If model loading fails
        ValueError: If model_name not supported
    """
    if model_name not in MODEL_PATHS:
        raise ValueError(
            f"Unsupported Transformers model: {model_name}. "
            f"Supported models: {', '.join(MODEL_PATHS.keys())}"
        )

    # Check if already loaded
    if model_name in _transformers_pipelines:
        return _transformers_pipelines[model_name]

    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer

        model_path = MODEL_PATHS[model_name]
        local_path = Path(model_path)

        # Use local path if exists, otherwise download from HuggingFace
        if local_path.exists():
            model_to_load = str(local_path)
            print(f"✓ Loading {model_name} from local path: {model_to_load}")
        else:
            model_to_load = model_path
            print(f"✓ Loading {model_name} from HuggingFace: {model_to_load}")

        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            model_to_load,
            trust_remote_code=True
        )

        # Ensure pad token is set
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        # Load model with optimizations
        print(f"Loading model (this may take a few minutes)...")

        # Check device
        if not torch.cuda.is_available():
            print("⚠️  CUDA not available. Loading model on CPU (slow!)")
            device_map = "cpu"
            load_kwargs = {}
        else:
            device_map = "auto"
            load_kwargs = {
                "load_in_8bit": LOAD_IN_8BIT,
                "torch_dtype": torch.float16,
            }

        model = AutoModelForCausalLM.from_pretrained(
            model_to_load,
            device_map=device_map,
            trust_remote_code=True,
            **load_kwargs
        )

        print(f"✓ {model_name} loaded successfully")

        # Cache the pipeline
        pipeline = (model, tokenizer)
        _transformers_pipelines[model_name] = pipeline

        return pipeline

    except ImportError:
        raise RuntimeError(
            "Transformers not installed. Install with:\n"
            "  pip install transformers accelerate\n"
            "  pip install bitsandbytes  # For 8-bit quantization"
        )
    except Exception as e:
        raise RuntimeError(f"Failed to load {model_name}: {str(e)}")


def query_transformers(
    pipeline,
    prompt: str,
    temperature: float = 0.0,
    max_tokens: int = 2048,
    stream: bool = False
) -> str:
    """
    Query Transformers model with a prompt.

    Args:
        pipeline: tuple of (model, tokenizer) from get_deepseek_pipeline()
        prompt: Clinical prompt text
        temperature: Sampling temperature (0.0 = deterministic)
        max_tokens: Maximum tokens to generate
        stream: Whether to stream output (not yet implemented)

    Returns:
        Generated text response

    Raises:
        RuntimeError: If inference fails
        ValueError: If prompt is empty or too long
    """
    model, tokenizer = pipeline

    # Validation
    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty")

    if len(prompt) > 15000:
        raise ValueError("Prompt too long. Consider summarizing context.")

    try:
        # Tokenize input
        inputs = tokenizer(prompt, return_tensors="pt")

        # Move to same device as model
        if hasattr(model, 'device'):
            inputs = {k: v.to(model.device) for k, v in inputs.items()}

        # Generate
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature if temperature > 0 else None,
                do_sample=temperature > 0,
                top_p=0.95 if temperature > 0 else None,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )

        # Decode response
        response_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Remove prompt from response (model echoes input)
        if response_text.startswith(prompt):
            response_text = response_text[len(prompt):].strip()

        if not response_text:
            raise RuntimeError("Model generated empty response")

        return response_text

    except Exception as e:
        raise RuntimeError(f"Transformers inference failed: {str(e)}")


def get_transformers_status(model_name: str) -> dict:
    """
    Get status information for a Transformers model.

    Args:
        model_name: Model to check

    Returns:
        Status dictionary with model info
    """
    status = {
        "model_name": model_name,
        "model_path": MODEL_PATHS.get(model_name, "Unknown"),
        "loaded": model_name in _transformers_pipelines,
        "cuda_available": torch.cuda.is_available(),
        "gpu_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
    }

    if torch.cuda.is_available():
        status["gpu_names"] = [
            torch.cuda.get_device_name(i)
            for i in range(torch.cuda.device_count())
        ]
        status["total_gpu_memory_gb"] = sum([
            torch.cuda.get_device_properties(i).total_memory / 1e9
            for i in range(torch.cuda.device_count())
        ])

    return status


def warmup_transformers(model_name: str):
    """
    Warmup a Transformers model with a test query.

    Args:
        model_name: Model to warmup

    Returns:
        True if successful, False otherwise
    """
    try:
        pipeline = get_deepseek_pipeline(model_name)
        test_prompt = "What is the mechanism of action of vancomycin?"
        _ = query_transformers(pipeline, test_prompt, max_tokens=50)
        print(f"✓ {model_name} warmup complete")
        return True
    except Exception as e:
        print(f"⚠️  {model_name} warmup failed: {e}")
        return False
