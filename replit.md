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
├── pages/
│   └── admin_dashboard.py     # Admin dashboard for configuration management
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
│       ├── grok_backend.py       # Grok API with BAA support (DISABLED by default)
│       ├── kinetics_enhanced.py  # Enhanced Kinetics reasoning engine
│       ├── adversarial_stage.py  # Adversarial red-team reasoning stage
│       ├── literature_stage.py   # PubMed integration and evidence grading
│       ├── cds_hooks.py          # CDS Hooks 2.0 integration
│       ├── alert_system.py       # Multi-severity alert system with auto-escalation
│       ├── access_control.py     # Role-based access control (6 roles, 22 permissions)
│       ├── ambient_scribe.py     # SOAP note generation with ICD-10/CPT coding
│       └── continuous_learning.py # Outcome capture + Bayesian continuous learning
```

## Key Features

1. **Multi-LLM Reasoning Chain**: Kinetics → Adversarial → Literature → Arbiter
2. **EHR Integration**: Epic and Cerner FHIR R4 clients with OAuth2
3. **Hospital AI Aggregation**: 8 vendor adapters (Aidoc, PathAI, Tempus, Butterfly, Caption Health, IBM Watson, DeepMind, Keragon)
4. **Bayesian Safety Analysis**: Beta-Binomial inference over 17k+ cases with continuous learning
5. **Blockchain Audit Trail**: SHA-256 hash-chained decision logging
6. **HIPAA Compliance**: Credential management, BAA tracking, cloud safeguards
7. **CDS Hooks 2.0**: Integration with EHR clinical decision points
8. **Alert System**: Multi-severity alerts with auto-escalation and notification channels
9. **Role-Based Access Control**: 6 roles (Admin, Physician, Nurse, Pharmacist, Resident, Guest) with 22 granular permissions
10. **Ambient Scribe**: SOAP note generation with ICD-10/CPT code suggestions
11. **Continuous Learning**: Outcome capture, calibration tracking (ECE/MCE/Brier), Bayesian prior updates

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

# Optional: Grok Cloud API (DISABLED by default for HIPAA)
# To enable, you MUST:
# 1. Sign a BAA with xAI
# 2. Set GROK_API_KEY=xxx
# 3. Set GROK_HAS_BAA=true
# 4. Set GROK_CLOUD_ENABLED=true (explicit opt-in)
```

## Security: Zero-Cloud Architecture

By default, Grok Doc operates in **LOCAL-ONLY mode**:
- Cloud API calls are blocked with `CloudDisabledError`
- All inference uses on-premises models
- No PHI leaves the hospital network

To enable cloud Grok API (optional):
1. Sign a Business Associate Agreement (BAA) with xAI
2. Set `GROK_HAS_BAA=true`
3. Set `GROK_CLOUD_ENABLED=true` (explicit opt-in)

## Running the Application

The application runs via Streamlit:
```bash
streamlit run app.py --server.port 5000 --server.address 0.0.0.0
```

## Recent Changes

- 2025-11-26: Fixed continuous_learning.py to remove SciPy dependency (zero external deps)
- 2025-11-26: Added hard safeguard to Grok cloud backend (DISABLED by default)
- 2025-11-26: Added CloudDisabledError for explicit cloud opt-in
- 2025-11-26: Added AdversarialStage for red-team testing of clinical recommendations
- 2025-11-26: Added LiteratureStage with PubMed integration and evidence grading (Level I-V)
- 2025-11-26: Added CDS Hooks 2.0 integration
- 2025-11-26: Added multi-severity alert system with auto-escalation
- 2025-11-26: Added role-based access control (6 roles, 22 permissions)
- 2025-11-26: Added ambient scribe with SOAP note generation
- 2025-11-26: Added continuous learning pipeline with calibration tracking
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
- Zero external dependencies for core functionality

## Technical Notes

- All imports are conditional to handle missing packages gracefully
- LSP errors for missing packages are expected (not installed per user request)
- The Streamlit workflow requires package installation to run
- Demo mode available when running without full dependencies
- Beta distribution operations use standard library math (no SciPy required)
- Cloud APIs are disabled by default with explicit opt-in required

## Architecture Decisions

1. **Zero-Cloud Default**: All cloud APIs blocked unless explicitly enabled
2. **Standard Library First**: Core functionality uses only Python standard library
3. **Modular Adapters**: Plug-and-play hospital AI tool integration
4. **Blockchain Audit**: SHA-256 hash-chained logging for compliance
5. **Bayesian Safety**: Beta-Binomial conjugate priors for continuous learning
