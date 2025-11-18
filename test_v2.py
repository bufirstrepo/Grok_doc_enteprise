"""Test script for Grok Doc v2.0 Multi-LLM Chain"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Test imports with error handling
try:
    from llm_chain import MultiLLMChain, run_multi_llm_decision
    CHAIN_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Warning: llm_chain not available: {e}")
    CHAIN_AVAILABLE = False

try:
    import local_inference
    INFERENCE_AVAILABLE = True
except ImportError:
    print("⚠️  Warning: local_inference not available")
    INFERENCE_AVAILABLE = False

def mock_grok_query(prompt, **kwargs):
    """Mock LLM for testing"""
    if "kinetics" in prompt.lower() or "pharmacologist" in prompt.lower():
        return "1.4 mg/kg recommended, 85% safe"
    elif "adversarial" in prompt.lower() or "paranoid" in prompt.lower():
        return "Risk of nephrotoxicity 15%, higher if dehydrated"
    elif "literature" in prompt.lower() or "researcher" in prompt.lower():
        return "2025 IDSA guidelines recommend monitoring"
    elif "arbiter" in prompt.lower() or "attending" in prompt.lower():
        return "Recommendation: Continue with daily monitoring. 90% confident."
    return "Analysis complete"

def test_chain_basic():
    print("=" * 60)
    print("TEST 1: Basic Chain Execution")
    print("=" * 60)
    
    if not CHAIN_AVAILABLE:
        print("✗ SKIP: llm_chain not available")
        return False
    
    try:
        patient_context = {'age': 72, 'gender': 'Male', 'labs': 'Cr 1.8', 'query': 'Vanc safe?'}
        sample_cases = [
            {'summary': '70M vanc safe', 'outcome': 'safe', 'nephrotoxicity': False},
            {'summary': '75F vanc AKI', 'outcome': 'adverse', 'nephrotoxicity': True}
        ]
        bayesian_result = {'prob_safe': 0.85, 'ci_low': 0.75, 'ci_high': 0.92, 'n_cases': 100, 'n_safe': 85, 'n_adverse': 15}
        
        chain = MultiLLMChain()
        print("✓ MultiLLMChain initialized")
        
        # Mock LLM if needed
        if INFERENCE_AVAILABLE:
            original = local_inference.grok_query
            local_inference.grok_query = mock_grok_query
        
        result = chain.run_chain(patient_context, 'Vanc safe?', sample_cases, bayesian_result)
        
        if INFERENCE_AVAILABLE:
            local_inference.grok_query = original
        
        print(f"✓ Chain completed: {result['total_steps']} steps")
        print(f"✓ Chain hash: {result['chain_hash'][:16]}...")
        
        if chain.verify_chain():
            print("✓ Chain verification: PASSED")
        else:
            print("✗ Chain verification: FAILED")
            return False
        
        print("=" * 60)
        print("✅ TEST 1 PASSED")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"✗ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_chain_steps():
    print("\n" + "=" * 60)
    print("TEST 2: Individual Chain Steps")
    print("=" * 60)
    
    if not CHAIN_AVAILABLE:
        print("✗ SKIP: llm_chain not available")
        return False
    
    try:
        chain = MultiLLMChain()
        assert chain._get_last_hash() == "GENESIS_CHAIN"
        print("✓ Genesis block correct")
        
        test_hash = chain._compute_step_hash("Test", "Prompt", "Response", "GENESIS_CHAIN")
        assert len(test_hash) == 64
        print("✓ Hash computation working")
        
        test_hash2 = chain._compute_step_hash("Test", "Prompt", "Response", "GENESIS_CHAIN")
        assert test_hash == test_hash2
        print("✓ Hash is deterministic")
        
        print("=" * 60)
        print("✅ TEST 2 PASSED")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"✗ TEST 2 FAILED: {e}")
        return False

def test_chain_tampering():
    print("\n" + "=" * 60)
    print("TEST 3: Tampering Detection")
    print("=" * 60)
    
    if not CHAIN_AVAILABLE:
        print("✗ SKIP: llm_chain not available")
        return False
    
    try:
        from llm_chain import ChainStep
        from datetime import datetime
        
        chain = MultiLLMChain()
        
        step1 = ChainStep("Step1", "P1", "R1", datetime.utcnow().isoformat() + "Z", "GENESIS_CHAIN", "")
        step1.step_hash = chain._compute_step_hash(step1.step_name, step1.prompt, step1.response, step1.prev_hash)
        chain.chain_history.append(step1)
        
        step2 = ChainStep("Step2", "P2", "R2", datetime.utcnow().isoformat() + "Z", step1.step_hash, "")
        step2.step_hash = chain._compute_step_hash(step2.step_name, step2.prompt, step2.response, step2.prev_hash)
        chain.chain_history.append(step2)
        
        assert chain.verify_chain() == True
        print("✓ Valid chain verifies")
        
        chain.chain_history[0].response = "TAMPERED"
        assert chain.verify_chain() == False
        print("✓ Tampering detected")
        
        print("=" * 60)
        print("✅ TEST 3 PASSED")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"✗ TEST 3 FAILED: {e}")
        return False

def test_chain_export():
    print("\n" + "=" * 60)
    print("TEST 4: Chain Export")
    print("=" * 60)
    
    if not CHAIN_AVAILABLE:
        print("✗ SKIP: llm_chain not available")
        return False
    
    try:
        from llm_chain import ChainStep
        from datetime import datetime
        
        chain = MultiLLMChain()
        step = ChainStep("Test", "P", "R", datetime.utcnow().isoformat() + "Z", "GENESIS_CHAIN", "", 0.95)
        step.step_hash = chain._compute_step_hash(step.step_name, step.prompt, step.response, step.prev_hash)
        chain.chain_history.append(step)
        
        export = chain.export_chain()
        
        assert 'chain_id' in export
        assert 'steps' in export
        assert export['total_steps'] == 1
        assert export['chain_verified'] == True
        
        print("✓ Export structure correct")
        
        print("=" * 60)
        print("✅ TEST 4 PASSED")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"✗ TEST 4 FAILED: {e}")
        return False

def run_all_tests():
    print("\n" + "═" * 60)
    print("GROK DOC v2.0 - MULTI-LLM CHAIN TEST SUITE")
    print("═" * 60)
    
    if not CHAIN_AVAILABLE:
        print("\n⚠️  llm_chain.py not available - limited testing")
    
    tests = [
        ("Basic Chain", test_chain_basic),
        ("Chain Steps", test_chain_steps),
        ("Tampering Detection", test_chain_tampering),
        ("Chain Export", test_chain_export)
    ]
    
    results = []
    for name, func in tests:
        try:
            result = func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} crashed: {e}")
            results.append((name, False))
    
    print("\n" + "═" * 60)
    print("TEST SUMMARY")
    print("═" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
