# CLAUDE.md - AI Assistant Guide for Grok_doc_enteprise

## Repository Overview

This repository implements a **Multi-LLM Decision Chain for Clinical Reasoning**, specifically designed for pharmacokinetic analysis and medical decision support. The system orchestrates multiple specialized LLM agents in a sequential chain to provide robust, validated clinical recommendations.

**Repository**: `Grok_doc_enteprise`
**Primary Language**: Python
**Domain**: Clinical decision support, pharmacokinetics, medical AI
**Architecture**: Multi-agent LLM chain with cryptographic verification

---

## Codebase Structure

```
Grok_doc_enteprise/
├── llm_chain.py          # Core multi-LLM orchestration engine
└── CLAUDE.md            # This file
```

### Core Components

#### `llm_chain.py` (167 lines)
The main implementation file containing:

- **`ChainStep` (dataclass)**: Represents a single step in the reasoning chain with cryptographic hash chaining
- **`MultiLLMChain` (class)**: Orchestrates the four-stage LLM decision process
- **`run_multi_llm_decision()` (function)**: Entry point for executing the complete decision chain

---

## System Architecture

### Four-Stage LLM Chain

The system implements a specialized multi-agent architecture with distinct roles:

1. **Kinetics Model** (`_run_kinetics_model()` at line 63)
   - Role: Clinical pharmacologist focused on pharmacokinetic calculations
   - Input: Patient context, query, evidence, Bayesian results
   - Output: Dose recommendations based on PK/PD calculations
   - Max tokens: 200

2. **Adversarial Model** (`_run_adversarial_model()` at line 82)
   - Role: Paranoid risk analyst (devil's advocate)
   - Input: Patient context, query, kinetics recommendation
   - Output: Potential risks, drug interactions, edge cases
   - Max tokens: 250

3. **Literature Model** (`_run_literature_model()` at line 98)
   - Role: Clinical researcher with current evidence
   - Input: Kinetics recommendation + adversarial risks
   - Output: Evidence-based validation, alternative approaches
   - Max tokens: 300

4. **Arbiter Model** (`_run_arbiter_model()` at line 114)
   - Role: Attending physician making final decision
   - Input: All previous model outputs
   - Output: Synthesized recommendation with confidence score
   - Max tokens: 300

### Chain Integrity System

The implementation includes a **blockchain-inspired verification system**:

- Each step has a cryptographic hash (`step_hash`)
- Each step references the previous hash (`prev_hash`)
- Genesis hash: `"GENESIS_CHAIN"`
- Hash computation: SHA-256 of `{step, prompt, response, prev_hash}`
- Verification method: `verify_chain()` at line 147

---

## Key Design Patterns & Conventions

### 1. Dataclass Usage
- Use `@dataclass` for structured data (see `ChainStep` at line 18)
- Include type hints for all fields
- Use `Optional[]` for nullable fields

### 2. Cryptographic Integrity
- All chain modifications must update hashes
- Use canonical JSON serialization: `json.dumps(data, sort_keys=True, separators=(',', ':'))`
- Always verify chain integrity before trusting results

### 3. Confidence Scoring
- Kinetics model uses Bayesian probability (`bayesian['prob_safe']`)
- Literature model: hardcoded 0.90
- Arbiter model: weighted average (30% kinetics, 20% baseline, 50% literature)
- See line 129 for confidence calculation

### 4. Timestamp Format
- ISO 8601 with UTC timezone: `datetime.utcnow().isoformat() + "Z"`
- Consistent across all chain steps

### 5. Prompt Engineering Patterns
- Each model has a distinct persona and strict role
- Use constraint language: "ONLY", "2 sentences max", "ANY reason"
- Structured format for final output (Arbiter model at line 126)

---

## Dependencies

### External Dependencies
```python
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from local_inference import grok_query  # NOT IN REPO - external dependency
```

### Missing Component
**CRITICAL**: The repository references `local_inference.grok_query()` which is **not included**. This is the LLM inference backend.

**When working with this code, you must:**
- Ask the user about the `local_inference` module implementation
- Do not assume the API signature beyond what's visible in usage
- Current usage pattern: `grok_query(prompt: str, max_tokens: int) -> str`

---

## Development Workflows

### Adding a New Model to the Chain

1. Create a new method `_run_<model_name>_model()` following the pattern at lines 63-112
2. Define the model's persona and role in the prompt
3. Call `grok_query()` with appropriate `max_tokens`
4. Create `ChainStep` with proper hash chaining
5. Update `run_chain()` to include the new step (line 46)
6. Adjust confidence calculation in arbiter model if needed (line 129)

### Modifying Chain Logic

**IMPORTANT**: Any changes to chain execution must:
1. Preserve hash chain integrity
2. Update `_get_last_hash()` calls appropriately
3. Maintain temporal ordering of steps
4. Update `export_chain()` if adding new fields

### Testing Chain Integrity

Always verify chains after modifications:
```python
chain = MultiLLMChain()
result = chain.run_chain(patient_context, query, evidence, bayesian)
assert chain.verify_chain() == True
```

---

## Working with Patient Context

### Expected Patient Context Schema
```python
patient_context = {
    'age': int,              # Patient age in years
    'gender': str,           # Patient gender
    'labs': str | dict,      # Laboratory values (optional)
    # Other fields as needed
}
```

### Retrieved Evidence Schema
```python
retrieved_evidence = [
    {
        'summary': str,      # Case summary
        # Other fields as needed
    },
    # ... more cases
]
```

### Bayesian Result Schema
```python
bayesian_result = {
    'prob_safe': float,      # Probability of safety (0.0-1.0)
    'n_cases': int,          # Number of cases in analysis
    # Other fields as needed
}
```

---

## Code Style & Conventions

### Docstrings
- Module-level docstring explains the four-stage architecture (lines 1-9)
- Class-level docstrings describe purpose
- Method docstrings use format: `"""LLM #N: Model Name"""`

### Variable Naming
- `patient_context`, `query`, `evidence`, `bayesian` - standard input names
- `*_result` suffix for step outputs
- `*_step` suffix for ChainStep objects
- `*_hash` suffix for cryptographic hashes

### Error Handling
**IMPORTANT**: The current implementation has **no error handling**. When modifying:
- Add try-except blocks around `grok_query()` calls
- Handle missing required fields in input dictionaries
- Validate hash chain integrity
- Handle JSON serialization errors

### Token Budgets
Respect the defined token limits:
- Kinetics: 200 tokens (terse PK calculations)
- Adversarial: 250 tokens (focused risk analysis)
- Literature: 300 tokens (evidence summary)
- Arbiter: 300 tokens (final synthesis)

---

## Git Workflow

**Current Branch**: `claude/claude-md-mi54iie7un3nrr8a-01HRQs6LTyAzZxG4x4hFy4J8`

### Branch Naming Convention
- Feature branches: `claude/claude-md-<session-id>`
- All development happens on feature branches
- Never push to main/master without explicit permission

### Commit Message Style
Based on git history:
- Imperative mood: "Create llm_chain.py" (not "Created" or "Creates")
- Concise subject line
- Focus on "what" was done

### Push Protocol
```bash
git push -u origin claude/claude-md-<session-id>
```

---

## Medical/Clinical AI Best Practices

### Safety Considerations
When modifying this medical decision support system:

1. **Never skip the adversarial model** - it's a critical safety check
2. **Preserve confidence scoring** - downstream systems may use thresholds
3. **Maintain audit trail** - `export_chain()` provides complete decision provenance
4. **Hash verification** - always verify chain integrity for regulatory compliance

### Clinical Validation
- Kinetics model should cite PK/PD principles
- Literature model should reference actual studies when possible
- Arbiter model must provide clear monitoring parameters
- All recommendations should be falsifiable and measurable

### Prompt Security
- Avoid user input directly in prompts (injection risk)
- Sanitize patient data before inclusion
- Use structured formats to prevent prompt hijacking

---

## Common Tasks

### Running the Chain
```python
from llm_chain import run_multi_llm_decision

result = run_multi_llm_decision(
    patient_context={'age': 45, 'gender': 'F', 'labs': 'Cr 1.2'},
    query="Safe fentanyl dose for colonoscopy?",
    retrieved_cases=evidence_list,
    bayesian_result={'prob_safe': 0.85, 'n_cases': 150}
)

print(result['final_recommendation'])
print(f"Confidence: {result['final_confidence']:.1%}")
print(f"Chain verified: {result['chain_export']['chain_verified']}")
```

### Exporting Chain for Audit
```python
chain = MultiLLMChain()
chain.run_chain(patient_context, query, evidence, bayesian)
audit_log = chain.export_chain()
# Save audit_log to database or file system
```

### Verifying Chain Integrity
```python
if not chain.verify_chain():
    raise ValueError("Chain integrity compromised!")
```

---

## Testing Strategy

### Unit Tests (Recommended)
- Test each model method independently
- Mock `grok_query()` to avoid actual LLM calls
- Verify hash computation logic
- Test chain verification with tampered data

### Integration Tests
- Full chain execution with real/mock LLM backend
- Edge cases: empty evidence, missing patient data
- Confidence score ranges

### Validation Tests
- Verify prompts contain required context
- Check output format compliance
- Ensure token limits are respected

---

## Known Limitations & TODOs

1. **No error handling** around LLM calls
2. **Missing dependency**: `local_inference` module not in repo
3. **Hardcoded confidence values** (e.g., line 109: 0.90)
4. **No input validation** for patient_context or bayesian_result
5. **No retry logic** if LLM calls fail
6. **No caching** of LLM responses
7. **No parallel execution** - chain is strictly sequential
8. **No logging** - consider adding for production use

---

## File Modification Guidelines

### When editing `llm_chain.py`:

1. **Preserve line structure** for critical sections:
   - Hash computation (lines 36-40)
   - Chain verification (lines 147-159)
   - Confidence calculation (line 129)

2. **Add features incrementally**:
   - Don't refactor multiple models simultaneously
   - Test hash integrity after each change
   - Update export format if adding new fields

3. **Document medical reasoning**:
   - Explain why specific prompts are structured certain ways
   - Reference clinical guidelines when applicable
   - Note any regulatory requirements

---

## Questions to Ask Users

Before making significant changes, clarify:

1. **LLM Backend**: What is the `local_inference.grok_query()` implementation?
2. **Error Handling**: What should happen if an LLM call fails mid-chain?
3. **Caching**: Should identical queries return cached results?
4. **Parallel Execution**: Can any models run in parallel?
5. **Monitoring**: What metrics should be logged?
6. **Deployment**: How is this system deployed (API, CLI, embedded)?

---

## Related Documentation

- Refer to medical literature on clinical decision support systems
- Familiarize with pharmacokinetic principles (Vd, Cl, t½)
- Understand Bayesian inference in medical contexts
- Review prompt injection attack vectors for healthcare AI

---

## Change Log

- **2025-11-18**: Initial CLAUDE.md creation
- **2025-11-18**: Repository created with llm_chain.py

---

## Contact & Contribution

When contributing to this repository:
- Ensure all changes maintain HIPAA compliance principles
- Test with synthetic patient data only
- Document any changes to the chain architecture
- Update this CLAUDE.md file if modifying workflows

**Last Updated**: 2025-11-18
**Repository Status**: Early development
**Primary File Count**: 1 Python file (167 lines)
