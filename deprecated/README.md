# Deprecated Files - Production Deployment Sanitization

These files have been moved from `src/` during the production deployment sanitization process.

## Reason for Deprecation

These files were identified as "zombie files" - Python modules under `src/` that are **not imported** by any of the main application entry points:
- `app.py` (main Streamlit application)
- `local_inference.py` (inference engine)
- `src/core/router.py` (model routing)
- `src/main.py` (CLI entry point)
- `src/mobile_server.py` (mobile WebSocket server)

## Files Moved

### Adapters (src/adapters/)
- `adapter_registry.py`
- `aidoc.py`
- `base.py`
- `butterfly.py`
- `caption_health.py`
- `deepmind.py`
- `ibm_watson.py`
- `keragon.py`
- `pathAI.py`
- `tempus.py`

### Agents (src/agents/)
- `crewai_orchestrator.py`

### Config (src/config/)
- `credentials.py`
- `migrate_config.py`

### Core (src/core/)
- `access_control.py`
- `adversarial_stage.py`
- `alert_system.py`
- `ambient_scribe.py`
- `cds_hooks.py`
- `continuous_learning.py`
- `grok_backend.py`
- `kinetics_enhanced.py`
- `literature_stage.py`

### EHR (src/ehr/)
- `base.py`
- `cerner_fhir.py`
- `epic_fhir.py`
- `unified_model.py`

### Services (src/services/)
- `epic_rpa.py`
- `monai_chexnet.py`
- `neo4j_validator.py`
- `usb_watcher.py`

### Tools (src/tools/)
- `blockchain_tool.py`
- `epic_tool.py`
- `monai_tool.py`
- `neo4j_tool.py`
- `scispacy_tool.py`
- `xgboost_tool.py`

## Action Required

Before deleting these files permanently, please review:
1. Confirm no runtime features depend on lazy/dynamic imports
2. Check if any are used via configuration files or reflection
3. Review if any represent future planned features

## Date Moved

$(date +%Y-%m-%d)

## Sanitization Context

Part of the production deployment sanitization to remove:
- Hallucinated/fictional libraries and imports
- Dead code and zombie files
- Prompt-injection header tokens
- Sci-fi/simulation logic
