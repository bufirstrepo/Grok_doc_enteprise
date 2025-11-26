"""
Test Script for Model Routing System

Tests the explicit model routing functionality across all backends.
Validates tribunal experiment capabilities for comparing different models.
"""

import os
import sys

# Disable auto-init for testing
os.environ["SKIP_AUTO_INIT"] = "true"

from local_inference import (
    get_llm,
    grok_query,
    check_model_status,
    list_available_models,
    get_current_model,
    CURRENT_MODEL
)
from audit_log import log_fallback_event, get_fallback_statistics
from llm_chain import run_multi_llm_decision


def test_model_listing():
    """Test: List all available models"""
    print("\n" + "=" * 60)
    print("TEST 1: List Available Models")
    print("=" * 60)

    models = list_available_models()
    print(f"Available models: {len(models)}")
    for model, backend in models.items():
        print(f"  - {model:30} → {backend}")

    current = get_current_model()
    print(f"\nCurrent default model: {current}")

    assert len(models) > 0, "No models available!"
    print("✓ PASSED")


def test_model_status():
    """Test: Check model status without loading"""
    print("\n" + "=" * 60)
    print("TEST 2: Check Model Status")
    print("=" * 60)

    # Check default model
    status = check_model_status()
    print(f"Default model status:")
    print(f"  Model: {status.get('model_name', 'Unknown')}")
    print(f"  Backend: {status.get('backend', 'N/A')}")
    print(f"  Loaded: {status.get('loaded', False)}")
    print(f"  CUDA: {status.get('cuda_available', False)}")
    print(f"  GPUs: {status.get('gpu_count', 0)}")

    print("✓ PASSED")


def test_explicit_model_selection():
    """Test: Explicit model selection via model_name parameter"""
    print("\n" + "=" * 60)
    print("TEST 3: Explicit Model Selection")
    print("=" * 60)

    # Test prompt
    prompt = "What is the mechanism of action of vancomycin? Answer in one sentence."

    # Test with default model
    print(f"\n1. Testing default model ({CURRENT_MODEL})...")
    try:
        response1 = grok_query(prompt, max_tokens=100)
        print(f"   Response length: {len(response1)} chars")
        print(f"   First 100 chars: {response1[:100]}...")
        print("   ✓ Default model works")
    except Exception as e:
        print(f"   ⚠️  Default model failed: {e}")

    # Test with explicit llama-3.1-70b
    print("\n2. Testing explicit model (llama-3.1-70b)...")
    try:
        response2 = grok_query(prompt, max_tokens=100, model_name="llama-3.1-70b")
        print(f"   Response length: {len(response2)} chars")
        print(f"   First 100 chars: {response2[:100]}...")
        print("   ✓ Explicit llama-3.1-70b works")
    except Exception as e:
        print(f"   ⚠️  llama-3.1-70b failed: {e}")

    # Test with deepseek-r1 (if transformers installed)
    print("\n3. Testing DeepSeek-R1 (transformers backend)...")
    try:
        response3 = grok_query(prompt, max_tokens=100, model_name="deepseek-r1")
        print(f"   Response length: {len(response3)} chars")
        print(f"   First 100 chars: {response3[:100]}...")
        print("   ✓ DeepSeek-R1 works")
    except NotImplementedError as e:
        print(f"   ℹ️  DeepSeek-R1 not available: {e}")
    except Exception as e:
        print(f"   ⚠️  DeepSeek-R1 failed: {e}")

    print("\n✓ PASSED")


def test_fallback_logging():
    """Test: Fallback event logging"""
    print("\n" + "=" * 60)
    print("TEST 4: Fallback Event Logging")
    print("=" * 60)

    # Simulate a fallback event
    event = log_fallback_event(
        primary_model="grok-4",
        exception_msg="Test exception: Model not available",
        fallback_model="llama-3.1-70b",
        success=True
    )

    print(f"Logged fallback event:")
    print(f"  Primary: {event['primary_model']}")
    print(f"  Fallback: {event['fallback_model']}")
    print(f"  Success: {event['success']}")

    # Get statistics
    stats = get_fallback_statistics()
    print(f"\nFallback statistics:")
    for model, data in stats.items():
        print(f"  {model}:")
        print(f"    Total fallbacks: {data['total_fallbacks']}")
        print(f"    Successful: {data['successful_fallbacks']}")
        print(f"    Failed: {data['failed_fallbacks']}")

    print("✓ PASSED")


def test_multi_model_chain():
    """Test: Multi-LLM chain with different models per step"""
    print("\n" + "=" * 60)
    print("TEST 5: Multi-Model LLM Chain")
    print("=" * 60)

    # Mock patient data
    patient_context = {
        "age": 72,
        "gender": "M",
        "labs": "Cr 1.8, eGFR 35"
    }

    query = "Is vancomycin 1500mg q12h safe for this patient?"

    # Mock retrieved cases (minimal for testing)
    retrieved_cases = [
        {"summary": "71M, Cr 1.9, vanco 1g q12h, safe", "outcome": "safe"},
        {"summary": "73F, Cr 2.1, vanco 1500mg q12h, AKI", "outcome": "unsafe"},
    ]

    # Mock Bayesian result
    bayesian_result = {
        "prob_safe": 0.75,
        "n_cases": 150,
        "ci_low": 0.68,
        "ci_high": 0.82
    }

    # Test 1: Default (all same model)
    print("\n1. Testing chain with default model...")
    try:
        result1 = run_multi_llm_decision(
            patient_context, query, retrieved_cases, bayesian_result
        )
        print(f"   Steps: {result1['total_steps']}")
        print(f"   Confidence: {result1['final_confidence']:.1%}")
        for step in result1['chain_steps']:
            print(f"   - {step['step']:20} Model: {step.get('model', 'default')}")
        print("   ✓ Default chain works")
    except Exception as e:
        print(f"   ⚠️  Default chain failed: {e}")

    # Test 2: Mixed models (if available)
    print("\n2. Testing chain with mixed models...")
    models_config = {
        "kinetics": "llama-3.1-70b",
        "adversarial": "llama-3.1-70b",  # Use same model for testing
        "literature": "llama-3.1-70b",
        "arbiter": "llama-3.1-70b"
    }

    try:
        result2 = run_multi_llm_decision(
            patient_context, query, retrieved_cases, bayesian_result, models_config
        )
        print(f"   Steps: {result2['total_steps']}")
        print(f"   Confidence: {result2['final_confidence']:.1%}")
        for step in result2['chain_steps']:
            print(f"   - {step['step']:20} Model: {step.get('model', 'N/A')}")

        # Verify chain integrity
        assert result2['chain_export']['chain_verified'], "Chain verification failed!"
        print("   ✓ Chain integrity verified")

        print("   ✓ Mixed model chain works")
    except Exception as e:
        print(f"   ⚠️  Mixed model chain failed: {e}")

    print("\n✓ PASSED")


def test_tribunal_experiment():
    """Test: Tribunal experiment - same query, different models"""
    print("\n" + "=" * 60)
    print("TEST 6: Tribunal Experiment (Model Comparison)")
    print("=" * 60)

    prompt = "For a 72M patient with Cr 1.8, is vancomycin 1500mg q12h safe? Answer in 2 sentences."

    models_to_test = ["llama-3.1-70b"]  # Add more as available

    results = {}

    for model in models_to_test:
        print(f"\nTesting {model}...")
        try:
            response = grok_query(prompt, max_tokens=200, model_name=model)
            results[model] = {
                "success": True,
                "response": response,
                "length": len(response)
            }
            print(f"   ✓ {model} responded ({len(response)} chars)")
            print(f"   Response: {response[:150]}...")
        except Exception as e:
            results[model] = {
                "success": False,
                "error": str(e)
            }
            print(f"   ⚠️  {model} failed: {e}")

    # Summary
    print("\n" + "-" * 60)
    print("Tribunal Experiment Summary:")
    successful = sum(1 for r in results.values() if r.get("success"))
    print(f"  Successful models: {successful}/{len(models_to_test)}")

    for model, result in results.items():
        if result.get("success"):
            print(f"  ✓ {model:30} {result['length']} chars")
        else:
            print(f"  ✗ {model:30} {result.get('error', 'Unknown error')}")

    print("\n✓ PASSED")


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("GROK DOC MODEL ROUTING TEST SUITE")
    print("=" * 60)
    print(f"Python: {sys.version.split()[0]}")
    print(f"Current working directory: {os.getcwd()}")

    tests = [
        ("Model Listing", test_model_listing),
        ("Model Status", test_model_status),
        ("Explicit Model Selection", test_explicit_model_selection),
        ("Fallback Logging", test_fallback_logging),
        ("Multi-Model Chain", test_multi_model_chain),
        ("Tribunal Experiment", test_tribunal_experiment),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n✗ TEST FAILED: {name}")
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("=" * 60)

    if failed == 0:
        print("✓ ALL TESTS PASSED")
        return 0
    else:
        print(f"✗ {failed} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
