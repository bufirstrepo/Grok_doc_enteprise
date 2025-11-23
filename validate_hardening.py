#!/usr/bin/env python3
"""
Validation script for hardening features in llm_chain.py

This script validates the structure and configuration without running LLM calls.
"""

import ast
import sys

def validate_llm_chain():
    """Validate that llm_chain.py has all hardening features"""
    print("=" * 60)
    print("VALIDATING HARDENED LLM CHAIN IMPLEMENTATION")
    print("=" * 60)

    with open('llm_chain.py', 'r') as f:
        content = f.read()

    # Parse the file
    tree = ast.parse(content)

    checks_passed = 0
    checks_total = 0

    # Check 1: STAGE_TIMEOUTS configuration
    print("\n[1] Checking STAGE_TIMEOUTS configuration...")
    checks_total += 1
    if 'STAGE_TIMEOUTS' in content:
        print("   ✓ STAGE_TIMEOUTS found")
        if all(stage in content for stage in ['kinetics', 'adversarial', 'literature', 'arbiter']):
            print("   ✓ All 4 stages configured")
            checks_passed += 1
        else:
            print("   ✗ Missing stage configurations")
    else:
        print("   ✗ STAGE_TIMEOUTS not found")

    # Check 2: STAGE_RETRY_COUNT configuration
    print("\n[2] Checking STAGE_RETRY_COUNT configuration...")
    checks_total += 1
    if 'STAGE_RETRY_COUNT' in content:
        print("   ✓ STAGE_RETRY_COUNT found")
        checks_passed += 1
    else:
        print("   ✗ STAGE_RETRY_COUNT not found")

    # Check 3: StageResult TypedDict
    print("\n[3] Checking StageResult interface contract...")
    checks_total += 1
    if 'class StageResult(TypedDict)' in content:
        print("   ✓ StageResult TypedDict found")
        required_fields = ['recommendation', 'confidence', 'reasoning', 'contraindications', 'timestamp', 'stage_name', '_stage_metadata']
        if all(field in content for field in required_fields):
            print(f"   ✓ All {len(required_fields)} required fields present")
            checks_passed += 1
        else:
            print("   ✗ Missing required fields")
    else:
        print("   ✗ StageResult TypedDict not found")

    # Check 4: _execute_stage wrapper
    print("\n[4] Checking _execute_stage wrapper function...")
    checks_total += 1
    if 'def _execute_stage(' in content:
        print("   ✓ _execute_stage function found")
        if 'retry_count' in content and 'execution_time_ms' in content:
            print("   ✓ Retry and timing logic present")
            checks_passed += 1
        else:
            print("   ✗ Missing retry or timing logic")
    else:
        print("   ✗ _execute_stage function not found")

    # Check 5: Stage implementation functions
    print("\n[5] Checking stage implementation functions...")
    checks_total += 1
    impl_functions = [
        '_run_kinetics_model_impl',
        '_run_adversarial_model_impl',
        '_run_literature_model_impl',
        '_run_arbiter_model_impl'
    ]
    found = sum(1 for func in impl_functions if f'def {func}' in content)
    if found == 4:
        print(f"   ✓ All 4 stage implementation functions found")
        checks_passed += 1
    else:
        print(f"   ✗ Only {found}/4 implementation functions found")

    # Check 6: Performance summary in export_chain
    print("\n[6] Checking performance summary in export_chain...")
    checks_total += 1
    if 'performance_summary' in content:
        print("   ✓ performance_summary found in export")
        if all(metric in content for metric in ['total_execution_time_ms', 'stage_timings', 'retries']):
            print("   ✓ All performance metrics present")
            checks_passed += 1
        else:
            print("   ✗ Missing performance metrics")
    else:
        print("   ✗ performance_summary not found")

    # Check 7: Stage metadata injection
    print("\n[7] Checking stage metadata injection...")
    checks_total += 1
    if 'result["_stage_metadata"]' in content or "result['_stage_metadata']" in content:
        print("   ✓ Stage metadata injection found")
        checks_passed += 1
    else:
        print("   ✗ Stage metadata injection not found")

    # Check 8: Logging configuration
    print("\n[8] Checking logging configuration...")
    checks_total += 1
    if 'import logging' in content and 'logger' in content:
        print("   ✓ Logging configured")
        checks_passed += 1
    else:
        print("   ✗ Logging not configured")

    # Summary
    print("\n" + "=" * 60)
    print(f"VALIDATION RESULTS: {checks_passed}/{checks_total} checks passed")
    print("=" * 60)

    if checks_passed == checks_total:
        print("✓ All hardening features successfully implemented!")
        return 0
    else:
        print(f"✗ {checks_total - checks_passed} checks failed")
        return 1

if __name__ == '__main__':
    sys.exit(validate_llm_chain())
