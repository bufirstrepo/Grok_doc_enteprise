"""
vLLM Inference Engine Backend

Handles vLLM-based model loading and inference for high-performance GPU execution.
Supports models: grok-4, llama-3.1-70b, mixtral-8x22b
"""

import os
import torch
from typing import Optional
from pathlib import Path
from functools import lru_cache

# ── MODEL CONFIGURATION ──────────────────────────────────────────

MODEL_PATHS = {
    "grok-4": os.getenv("GROK4_MODEL_PATH", "/models/grok-4-awq"),
    "llama-3.1-70b": os.getenv("LLAMA_MODEL_PATH", "/models/llama-3.1-70b-instruct-awq"),
    "mixtral-8x22b": os.getenv("MIXTRAL_MODEL_PATH", "/models/mixtral-8x22b-instruct-awq"),
}

FALLBACK_MODEL = "meta-llama/Meta-Llama-3.1-8B-Instruct"  # HuggingFace fallback

# Hardware configuration
GPU_MEMORY_UTILIZATION = 0.9
QUANTIZATION = "awq"  # AWQ quantization for efficiency
MAX_MODEL_LEN = 4096  # Context window


# ── SINGLETON PATTERN ────────────────────────────────────────────

_vllm_instances = {}  # model_name -> LLM instance


@lru_cache(maxsize=5)
def get_vllm_engine(model_name: str):
    """
    Get or create vLLM engine for specified model.
    Uses LRU cache to support multiple models in memory (up to 5).

    Args:
        model_name: One of "grok-4", "llama-3.1-70b", "mixtral-8x22b"

    Returns:
        vLLM LLM instance

    Raises:
        RuntimeError: If CUDA unavailable or model loading fails
        ValueError: If model_name not supported
    """
    if model_name not in MODEL_PATHS:
        raise ValueError(
            f"Unsupported vLLM model: {model_name}. "
            f"Supported models: {', '.join(MODEL_PATHS.keys())}"
        )

    # Check if already loaded (outside LRU cache for immediate access)
    if model_name in _vllm_instances:
        return _vllm_instances[model_name]

    try:
        from vllm import LLM

        # Get model path
        model_path = Path(MODEL_PATHS[model_name])
        if not model_path.exists():
            print(f"⚠️  Local model not found at {model_path}")
            print(f"Falling back to HuggingFace: {FALLBACK_MODEL}")
            print("For production, download model to local path for zero-cloud operation")
            model_to_load = FALLBACK_MODEL
        else:
            model_to_load = str(model_path)
            print(f"✓ Loading {model_name} from {model_to_load}")

        # Check CUDA availability
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA not available. vLLM requires GPU for inference.")

        num_gpus = torch.cuda.device_count()
        print(f"✓ Detected {num_gpus} GPU(s)")

        # Determine tensor parallelism based on model size
        if model_name in ["grok-4", "llama-3.1-70b", "mixtral-8x22b"]:
            # Large models need multiple GPUs
            tp_size = min(num_gpus, 4)  # Max 4-way tensor parallelism
        else:
            tp_size = 1

        # Load model with vLLM
        llm_instance = LLM(
            model=model_to_load,
            quantization=QUANTIZATION,
            tensor_parallel_size=tp_size,
            gpu_memory_utilization=GPU_MEMORY_UTILIZATION,
            trust_remote_code=True,
            dtype="auto",
            max_model_len=MAX_MODEL_LEN,
        )

        print(f"✓ {model_name} loaded successfully on {tp_size} GPU(s)")

        # Cache the instance
        _vllm_instances[model_name] = llm_instance

        return llm_instance

    except ImportError:
        raise RuntimeError(
            "vLLM not installed. Install with:\n"
            "  pip install vllm\n"
            "  pip install autoawq  # For AWQ quantization"
        )
    except Exception as e:
        raise RuntimeError(f"Failed to load {model_name}: {str(e)}")


def query_vllm(
    engine,
    prompt: str,
    temperature: float = 0.0,
    max_tokens: int = 500,
    stream: bool = False
) -> str:
    """
    Query vLLM engine with a prompt.

    Args:
        engine: vLLM LLM instance from get_vllm_engine()
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
    from vllm import SamplingParams

    # Validation
    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty")

    if len(prompt) > 15000:
        raise ValueError("Prompt too long. Consider summarizing context.")

    # Configure sampling
    sampling_params = SamplingParams(
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=0.95,
        frequency_penalty=0.1,
        stop=["<|eot_id|>", "<|end|>", "</s>", "<|im_end|>"],
    )

    # Generate
    try:
        outputs = engine.generate([prompt], sampling_params)

        if not outputs or not outputs[0].outputs:
            raise RuntimeError("vLLM returned empty output")

        response_text = outputs[0].outputs[0].text.strip()

        if not response_text:
            raise RuntimeError("vLLM generated empty response")

        return response_text

    except Exception as e:
        raise RuntimeError(f"vLLM inference failed: {str(e)}")


def get_vllm_status(model_name: str) -> dict:
    """
    Get status information for a vLLM model.

    Args:
        model_name: Model to check

    Returns:
        Status dictionary with model info
    """
    status = {
        "model_name": model_name,
        "model_path": MODEL_PATHS.get(model_name, "Unknown"),
        "loaded": model_name in _vllm_instances,
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


def warmup_vllm(model_name: str):
    """
    Warmup a vLLM model with a test query.

    Args:
        model_name: Model to warmup

    Returns:
        True if successful, False otherwise
    """
    try:
        engine = get_vllm_engine(model_name)
        test_prompt = "What is the mechanism of action of vancomycin?"
        _ = query_vllm(engine, test_prompt, max_tokens=50)
        print(f"✓ {model_name} warmup complete")
        return True
    except Exception as e:
        print(f"⚠️  {model_name} warmup failed: {e}")
        return False
