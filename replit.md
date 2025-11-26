# Grok Doc v2.5 Enterprise

HIPAA-compliant clinical AI decision support system with multi-LLM adversarial reasoning.

## Overview

Grok Doc is a four-stage multi-LLM reasoning engine that integrates with hospital EHRs and AI tools to provide unified clinical decision support. Designed for 100% on-premises deployment with zero-cloud architecture.

## Project Structure

```
grok-doc/
├── app.py                     # Main Streamlit application
├── llm_chain.py               # Multi-LLM reasoning chain (Kinetics→Adversarial→Literature→Arbiter)
├── local_inference.py         # Local LLM inference wrapper
├── bayesian_engine.py         # Bayesian safety analysis (17k+ cases)
├── audit_log.py               # Blockchain-style audit trail
├── vllm_engine.py             # vLLM backend for GPU inference
├── transformers_backend.py    # Transformers backend (DeepSeek-R1)
├── data_builder.py            # Case database builder
│
├── config/
│   └── hospital_config.json   # Hospital deployment configuration
│
├── src/
│   ├── config/
│   │   ├── hospital_config.py # Hospital configuration dataclasses
│   │   └── credentials.py     # Secure credential management
│   │
│   ├── ehr/
│   │   ├── base.py           # Abstract EHR client interface
│   │   ├── epic_fhir.py      # Epic FHIR R4 client
│   │   ├── cerner_fhir.py    # Cerner FHIR R4 client
│   │   └── unified_model.py  # Unified patient data model
│   │
│   ├── adapters/
│   │   ├── base.py           # AI adapter base class
│   │   ├── adapter_registry.py # Adapter discovery and orchestration
│   │   ├── aidoc.py          # Aidoc radiology AI
│   │   ├── pathAI.py         # PathAI digital pathology
│   │   ├── tempus.py         # Tempus precision medicine
│   │   ├── butterfly.py      # Butterfly iQ ultrasound
│   │   ├── caption_health.py # Caption Health cardiac AI
│   │   ├── ibm_watson.py     # IBM Watson Health
│   │   ├── deepmind.py       # DeepMind Health (AKI prediction)
│   │   └── keragon.py        # Keragon workflow automation
│   │
│   └── core/
│       ├── grok_backend.py   # Grok API with BAA support
│       ├── kinetics_enhanced.py # Enhanced Kinetics reasoning engine
│       └── adversarial_stage.py # Adversarial red-team reasoning stage
```

## Key Features

1. **Multi-LLM Reasoning Chain**: Kinetics → Adversarial → Literature → Arbiter
2. **EHR Integration**: Epic and Cerner FHIR R4 clients
3. **Hospital AI Aggregation**: 8 vendor adapters (Aidoc, PathAI, Tempus, etc.)
4. **Bayesian Safety Analysis**: Beta-Binomial inference over 17k+ cases
5. **Blockchain Audit Trail**: SHA-256 hash-chained decision logging
6. **HIPAA Compliance**: Credential management, BAA tracking

## Configuration

### Hospital Configuration

Edit `config/hospital_config.json` to customize:
- EHR connection (Epic, Cerner, etc.)
- Enabled AI tool adapters
- Feature flags
- Compliance settings
- LLM preferences

### Required Secrets (Environment Variables)

```bash
# EHR Authentication
EPIC_CLIENT_SECRET=xxx
CERNER_CLIENT_SECRET=xxx

# Optional: Hospital AI Tools
AIDOC_API_KEY=xxx
TEMPUS_API_KEY=xxx
PATHOLOGY_API_KEY=xxx

# Optional: Grok API (requires BAA)
GROK_API_KEY=xxx
GROK_HAS_BAA=true  # Set only after signing BAA with xAI
```

## Running the Application

The application runs via Streamlit:
```bash
streamlit run app.py --server.port 5000 --server.address 0.0.0.0
```

## Recent Changes

- 2025-11-26: Added AdversarialStage for red-team testing of clinical recommendations
- 2025-01-26: Created modular architecture with src/ folder
- 2025-01-26: Added Epic and Cerner FHIR clients
- 2025-01-26: Built 8 hospital AI tool adapters
- 2025-01-26: Added Grok API backend with BAA support
- 2025-01-26: Created Enhanced Kinetics reasoning engine
- 2025-01-26: Added hospital configuration system

## User Preferences

- No package installations during development (code-only changes)
- Prefer on-premises/local inference when possible
- Maintain HIPAA compliance at all times

## Technical Notes

- All imports are conditional to handle missing packages gracefully
- LSP errors for missing packages are expected (not installed per user request)
- The Streamlit workflow requires package installation to run
- Demo mode available when running without full dependencies
