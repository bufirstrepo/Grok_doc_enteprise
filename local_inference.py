"""
Local LLM inference engine for Grok Doc.
Supports vLLM for high-performance inference on DGX Spark or equivalent hardware.
"""

import os
import torch
from typing import Optional
from pathlib import Path

# ── CONFIGURATION ────────────────────────────────────────────────

# Model paths (set these to your local model directory)
MODEL_PATH = os.getenv("GROK_MODEL_PATH", "/models/llama-3.1-70b-instruct-awq")
FALLBACK_MODEL = "meta-llama/Meta-Llama-3.1-8B-Instruct"  # Smaller model for testing

# Inference settings
TEMPERATURE = 0.0  # Deterministic for medical use
MAX_TOKENS = 500  # Increased for thorough medical responses
TOP_P = 0.95
FREQUENCY_PENALTY = 0.1

# Hardware configuration
TENSOR_PARALLEL_SIZE = torch.cuda.device_count() if torch.cuda.is_available() else 1
GPU_MEMORY_UTILIZATION = 0.9  # Use 90% of available GPU memory
QUANTIZATION = "awq"  # Options: "awq", "gptq", None

# ── LAZY MODEL LOADING ───────────────────────────────────────────

_llm_instance = None
_model_loaded = False

def get_llm():
    """
    Lazy-load LLM to avoid startup delays.
    Only loads model when first query is made.
    """
    global _llm_instance, _model_loaded
    
    if _llm_instance is not None:
        return _llm_instance
    
    if _model_loaded:
        raise RuntimeError("Model failed to load previously. Restart required.")
    
    try:
        from vllm import LLM, SamplingParams
        
        # Check if local model exists
        model_path = Path(MODEL_PATH)
        if not model_path.exists():
            print(f"⚠️  Local model not found at {MODEL_PATH}")
            print(f"Using fallback model: {FALLBACK_MODEL}")
            print("For production, download model to local path for zero-cloud operation")
            model_to_load = FALLBACK_MODEL
        else:
            model_to_load = str(model_path)
            print(f"✓ Loading local model from {model_to_load}")
        
        # Detect available GPUs
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA not available. This system requires GPU for inference.")
        
        num_gpus = torch.cuda.device_count()
        print(f"✓ Detected {num_gpus} GPU(s)")
        
        # Adjust tensor parallel size based on available GPUs
        tp_size = min(TENSOR_PARALLEL_SIZE, num_gpus)
        if tp_size != TENSOR_PARALLEL_SIZE:
            print(f"⚠️  Requested {TENSOR_PARALLEL_SIZE} GPUs but only {num_gpus} available")
            print(f"Adjusting tensor_parallel_size to {tp_size}")
        
        # Load model with vLLM
        _llm_instance = LLM(
            model=model_to_load,
            quantization=QUANTIZATION,
            tensor_parallel_size=tp_size,
            gpu_memory_utilization=GPU_MEMORY_UTILIZATION,
            trust_remote_code=True,  # Required for some models
            dtype="auto",  # Let vLLM choose optimal dtype
            max_model_len=4096,  # Context window
        )
        
        _model_loaded = True
        print(f"✓ Model loaded successfully on {tp_size} GPU(s)")
        
        return _llm_instance
        
    except ImportError:
        raise RuntimeError(
            "vLLM not installed. Install with: pip install vllm\n"
            "For AWQ quantization: pip install autoawq\n"
            "For GPTQ quantization: pip install auto-gptq"
        )
    except Exception as e:
        _model_loaded = True  # Prevent retry loops
        raise RuntimeError(f"Failed to load model: {str(e)}")

def grok_query(
    prompt: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    system_prompt: Optional[str] = None
) -> str:
    """
    Query the local LLM with a clinical prompt.
    
    Args:
        prompt: The clinical question/prompt
        temperature: Sampling temperature (default: 0.0 for deterministic)
        max_tokens: Maximum tokens to generate (default: 500)
        system_prompt: Optional system prompt to prepend
    
    Returns:
        str: Model response text
    
    Raises:
        RuntimeError: If model loading or inference fails
        ValueError: If prompt is empty or too long
    """
    
    # Validation
    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty")
    
    if len(prompt) > 15000:  # Rough token estimate
        raise ValueError("Prompt too long. Consider summarizing the context.")
    
    try:
        from vllm import SamplingParams
        
        # Get or load model
        llm = get_llm()
        
        # Build full prompt with system message
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        else:
            full_prompt = prompt
        
        # Configure sampling
        sampling_params = SamplingParams(
            temperature=temperature if temperature is not None else TEMPERATURE,
            max_tokens=max_tokens if max_tokens is not None else MAX_TOKENS,
            top_p=TOP_P,
            frequency_penalty=FREQUENCY_PENALTY,
            stop=["<|eot_id|>", "<|end|>", "</s>"],  # Common stop tokens
        )
        
        # Generate response
        outputs = llm.generate([full_prompt], sampling_params)
        
        if not outputs or not outputs[0].outputs:
            raise RuntimeError("Model returned empty output")
        
        response_text = outputs[0].outputs[0].text.strip()
        
        # Validation
        if not response_text:
            raise RuntimeError("Model generated empty response")
        
        return response_text
        
    except Exception as e:
        # Fallback error message for medical safety
        error_msg = f"LLM inference failed: {str(e)}"
        print(f"ERROR: {error_msg}")
        
        return (
            "⚠️ AUTOMATED RESPONSE UNAVAILABLE\n\n"
            "The AI inference engine encountered an error. "
            "Please review this case manually and consult standard clinical guidelines. "
            f"Technical details: {str(e)}"
        )

def check_model_status() -> dict:
    """
    Check if model is loaded and get system info.
    Useful for debugging and status pages.
    
    Returns:
        dict: Model status information
    """
    status = {
        "model_loaded": _model_loaded,
        "model_path": MODEL_PATH,
        "cuda_available": torch.cuda.is_available(),
        "gpu_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
        "tensor_parallel_size": TENSOR_PARALLEL_SIZE,
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

def warmup_model():
    """
    Warmup the model with a simple query to preload everything.
    Call this during application startup to hide latency.
    """
    try:
        test_prompt = "What is the mechanism of action of vancomycin?"
        _ = grok_query(test_prompt, max_tokens=50)
        print("✓ Model warmup complete")
        return True
    except Exception as e:
        print(f"⚠️  Model warmup failed: {e}")
        return False

# ── ALTERNATIVE: TRANSFORMERS BACKEND ────────────────────────────
# If vLLM isn't available, fall back to standard Transformers

def grok_query_transformers(prompt: str) -> str:
    """
    Fallback inference using HuggingFace Transformers.
    Slower than vLLM but works without specialized setup.
    """
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch
        
        model_path = MODEL_PATH if Path(MODEL_PATH).exists() else FALLBACK_MODEL
        
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            device_map="auto",
            torch_dtype=torch.float16,
            load_in_8bit=True  # 8-bit quantization
        )
        
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                do_sample=TEMPERATURE > 0,
                pad_token_id=tokenizer.eos_token_id
            )
        
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Remove prompt from response
        response = response[len(prompt):].strip()
        
        return response
        
    except Exception as e:
        return f"⚠️ Inference failed: {str(e)}"
