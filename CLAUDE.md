# CLAUDE.md - AI Assistant Guide for Grok_doc_enteprise v2.0

## Repository Overview

This repository implements **Grok Doc v2.0**, a complete on-premises clinical AI system with dual-mode operation:
- **Fast Mode (v1.0)**: Single-LLM decision support with Bayesian analysis
- **Chain Mode (v2.0)**: Multi-LLM adversarial reasoning chain for critical decisions

**Repository**: `Grok_doc_enteprise`
**Primary Language**: Python
**Domain**: Clinical decision support, pharmacokinetics, medical AI
**Architecture**: Dual-mode system with multi-agent LLM chain + cryptographic verification
**Version**: 2.0.0

---

## Codebase Structure

```
Grok_doc_enteprise/
├── Core Application Files
│   ├── app.py                    # Streamlit UI with Fast/Chain mode toggle (v2.0)
│   ├── llm_chain.py              # 4-stage multi-LLM reasoning chain (NEW in v2.0)
│   ├── local_inference.py        # vLLM inference engine (70B LLM)
│   ├── bayesian_engine.py        # Bayesian safety assessment
│   ├── audit_log.py              # Blockchain-style immutable logging (updated for v2.0)
│   └── data_builder.py           # Synthetic case database generator (17k cases)
│
├── Deployment Scripts
│   ├── launch_v2.sh              # Automated launch script (NEW in v2.0)
│   ├── setup.sh                  # One-time setup script (NEW in v2.0)
│   └── requirements.txt          # Python dependencies
│
├── Testing
│   └── test_v2.py                # Test suite for multi-LLM chain (NEW in v2.0)
│
├── Documentation
│   ├── README.md                 # User-facing documentation (v2.0)
│   ├── CLAUDE.md                 # This file - AI assistant guide
│   ├── MULTI_LLM_CHAIN.md        # Technical architecture docs (NEW in v2.0)
│   ├── QUICK_START_V2.md         # Quick reference guide (NEW in v2.0)
│   ├── CHANGELOG.md              # Version history
│   ├── CONTRIBUTING.md           # Contribution guidelines (NEW in v2.0)
│   └── SECURITY.md               # Security policy (NEW in v2.0)
│
├── Configuration
│   ├── .gitignore                # Git ignore rules
│   └── LICENSE                   # MIT with clinical restrictions
│
└── Generated Files (not in git)
    ├── case_index.faiss          # Vector database
    ├── cases_17k.jsonl           # Clinical cases
    ├── audit.db                  # SQLite audit log
    └── audit_chain.jsonl         # Human-readable backup
```

---

## Core Components

### 1. `app.py` - Streamlit UI (v2.0)
**Lines**: ~450 | **Purpose**: Web interface with dual-mode operation

**Key Features**:
- Hospital WiFi verification (`is_on_hospital_wifi()`)
- Mode selection radio button (Fast Mode / Chain Mode)
- Patient context input (MRN, age, gender, labs)
- Bayesian analysis integration
- E-signature workflow for physicians
- Audit trail verification button

**Mode Toggle** (NEW in v2.0):
```python
analysis_mode = st.radio(
    "Select reasoning mode:",
    options=["⚡ Fast Mode (v1.0)", "🔗 Multi-LLM Chain (v2.0)"]
)
```

**Important Functions**:
- `is_on_hospital_wifi()` - Enforces hospital network (line ~19)
- `load_vector_db()` - Loads FAISS index and cases (line ~56)
- Fast Mode logic (line ~220)
- Chain Mode logic (line ~147)

### 2. `llm_chain.py` - Multi-LLM Chain (v2.0)
**Lines**: 167 | **Purpose**: Four-stage adversarial reasoning chain

**Classes**:
- `ChainStep` (dataclass): Single step with cryptographic hash
- `MultiLLMChain` (class): Orchestrates 4-model chain

**Four-Stage Chain**:
1. **Kinetics Model** (`_run_kinetics_model()` line 63)
   - Role: Clinical pharmacologist
   - Tokens: 200 (terse PK calculations)
   - Confidence: Uses Bayesian `prob_safe`

2. **Adversarial Model** (`_run_adversarial_model()` line 82)
   - Role: Paranoid risk analyst
   - Tokens: 250 (focused risk analysis)
   - Confidence: None (risk only)

3. **Literature Model** (`_run_literature_model()` line 98)
   - Role: Clinical researcher
   - Tokens: 300 (evidence synthesis)
   - Confidence: 0.90 (hardcoded)

4. **Arbiter Model** (`_run_arbiter_model()` line 114)
   - Role: Attending physician
   - Tokens: 300 (final synthesis)
   - Confidence: Weighted average (30% kinetics + 20% baseline + 50% literature)

**Hash Chaining**:
- Genesis hash: `"GENESIS_CHAIN"`
- Each step links via `prev_hash`
- SHA-256 of `{step, prompt, response, prev_hash}`
- Verification: `verify_chain()` at line 147

### 3. `local_inference.py` - LLM Engine
**Lines**: ~290 | **Purpose**: vLLM-based 70B model inference

**Key Function**:
```python
def grok_query(prompt: str, max_tokens: int = 500) -> str:
    """Query local LLM using vLLM engine"""
```

**Performance**:
- Uses AWQ quantization (4-bit)
- DGX Spark (8× H100): ~2s per call
- 4× A100: ~3.8s per call

### 4. `bayesian_engine.py` - Safety Assessment
**Lines**: ~335 | **Purpose**: Bayesian probability of safety

**Key Function**:
```python
def bayesian_safety_assessment(
    retrieved_cases: List[Dict],
    query_type: str = "nephrotoxicity"
) -> Dict:
    """
    Returns:
        {
            'prob_safe': float,      # 0.0-1.0
            'ci_low': float,         # 95% CI lower
            'ci_high': float,        # 95% CI upper
            'n_cases': int
        }
    """
```

**Uses**: PyMC for Bayesian inference

### 5. `audit_log.py` - Immutable Logging (v2.0 Updated)
**Lines**: ~235 | **Purpose**: Blockchain-style tamper-evident logging

**Database Schema** (v2.0):
```sql
CREATE TABLE decisions (
    id INTEGER PRIMARY KEY,
    timestamp TEXT,
    mrn TEXT,
    patient_context TEXT,
    doctor TEXT,
    question TEXT,
    labs TEXT,
    answer TEXT,
    bayesian_prob REAL,
    latency REAL,
    analysis_mode TEXT,     -- NEW in v2.0: "fast" or "chain"
    prev_hash TEXT,
    entry_hash TEXT
)
```

**Key Functions**:
- `log_decision()` - Logs with e-signature (line 77)
- `verify_audit_integrity()` - Checks hash chain (line 169)
- `export_audit_trail()` - Export for compliance (line 201)

**Hash Chaining**:
```python
entry_hash = SHA256({
    timestamp, mrn, context, doctor, query, labs,
    response, bayesian_prob, latency, analysis_mode, prev_hash
})
```

### 6. `data_builder.py` - Case Database Generator
**Lines**: ~375 | **Purpose**: Creates synthetic 17k case database

**Generated Files**:
- `case_index.faiss` - Vector index for similarity search
- `cases_17k.jsonl` - JSONL file with case summaries

**Example Case**:
```json
{
    "summary": "72M septic shock, vancomycin, Cr 2.9→1.8, safe trough?",
    "outcome": "safe",
    "embedding": [0.12, -0.45, ...]
}
```

---

## System Architecture

### Dual-Mode Operation

**Fast Mode (v1.0)**:
```
User Input → FAISS Retrieval (100 cases)
          → Bayesian Analysis
          → Single LLM Call
          → Physician Sign-Off
          → Audit Log
```
**Latency**: 2-3s | **Accuracy**: 87% pharmacist agreement

**Chain Mode (v2.0)**:
```
User Input → FAISS Retrieval (100 cases)
          → Bayesian Analysis
          → Kinetics Model → Adversarial Model
          → Literature Model → Arbiter Model
          (hash chain verification)
          → Physician Sign-Off
          → Audit Log (with full chain)
```
**Latency**: 7-10s | **Accuracy**: 94% pharmacist agreement

---

## Key Design Patterns

### 1. Cryptographic Integrity
All modifications to chain or audit log must update hashes:
```python
# Canonical JSON serialization
json.dumps(data, sort_keys=True, separators=(',', ':'))

# SHA-256 hash
hashlib.sha256(canonical.encode()).hexdigest()
```

### 2. Hospital WiFi Lock
**CRITICAL**: Never disable in production
```python
REQUIRE_WIFI_CHECK = True  # app.py line 16
HOSPITAL_SSID_KEYWORDS = ["hospital", "clinical", "healthcare"]
```

### 3. Zero-Cloud Architecture
- All inference happens locally
- No external API calls (except captive portal check)
- All PHI stays on hospital hardware

### 4. Physician-in-the-Loop
- E-signature required before logging
- Physician can modify recommendations
- All decisions labeled as "decision support"

---

## Development Workflows

### Adding a New Model to Chain

1. Create method in `MultiLLMChain`:
```python
def _run_new_model(self, patient_context, query, prev_step):
    prompt = f"""You are a [persona]...

    INPUTS: {prev_step.response}
    TASK: [specific task]
    """

    response = grok_query(prompt, max_tokens=250)
    step = ChainStep(
        "New Model",
        prompt,
        response,
        datetime.utcnow().isoformat() + "Z",
        self._get_last_hash(),
        "",
        confidence=0.85
    )
    step.step_hash = self._compute_step_hash(...)
    self.chain_history.append(step)
    return step
```

2. Update `run_chain()` to call new model (line 46)
3. Adjust confidence calculation in arbiter (line 129)
4. Update `export_chain()` if needed

### Modifying UI

When editing `app.py`:
1. Preserve WiFi check logic (lines 19-43)
2. Maintain dual-mode structure
3. Update audit logging to include new fields
4. Test both Fast and Chain modes

### Testing

**Run test suite**:
```bash
python -m unittest test_v2.py -v
```

**Test chain integrity**:
```python
from llm_chain import MultiLLMChain

chain = MultiLLMChain()
result = chain.run_chain(patient_context, query, evidence, bayesian)
assert chain.verify_chain() == True
```

**Test audit integrity**:
```python
from audit_log import verify_audit_integrity

result = verify_audit_integrity()
assert result['valid'] == True
```

---

## Configuration & Deployment

### Environment Variables

```bash
# Required
export GROK_MODEL_PATH="/models/llama-3.1-70b-instruct-awq"

# Optional (for development)
export REQUIRE_WIFI_CHECK=false  # NEVER in production!
```

### Hospital WiFi Configuration

Edit `app.py` line 14:
```python
HOSPITAL_SSID_KEYWORDS = ["YourHospital-Secure", "YourHospital-Clinical"]
```

### Launch Scripts

**Setup (one-time)**:
```bash
./setup.sh                # Full setup with model download
./setup.sh --skip-model   # Skip model download
```

**Launch**:
```bash
./launch_v2.sh                    # Default (port 8501)
./launch_v2.sh --port 8080        # Custom port
./launch_v2.sh --no-wifi-check    # Dev mode (NEVER in production)
```

**Manual launch**:
```bash
streamlit run app.py --server.port 8501
```

---

## Medical AI Best Practices

### When to Use Which Mode

**Use Fast Mode for**:
- Straightforward questions
- Time-sensitive decisions (< 3s required)
- High Bayesian confidence (> 90%)
- Low-risk scenarios

**Use Chain Mode for**:
- Complex pharmacokinetics
- High-risk medications (vancomycin, warfarin)
- Multiple comorbidities
- Uncertain Bayesian confidence (< 70%)
- Regulatory documentation needed

### Safety Considerations

1. **Never skip adversarial model** - Critical safety check
2. **Always verify chain integrity** - Ensures no tampering
3. **Require physician sign-off** - Human-in-the-loop
4. **Log complete chain** - Regulatory compliance
5. **Maintain zero-cloud** - PHI protection

---

## Security

### HIPAA Compliance

- **Network Isolation**: Hospital WiFi enforcement + firewall rules
- **Audit Trail**: Immutable blockchain-style logging
- **Access Control**: E-signature required
- **PHI Protection**: All data stays on-premises
- **Encryption**: SQLite database should be encrypted at rest

See `SECURITY.md` for complete security policy.

### Threat Model

**In Scope**:
- PHI exposure to external networks
- Audit log tampering
- Unauthorized access
- Prompt injection attacks

**Mitigations**:
- WiFi check + firewall rules
- Hash chain verification
- E-signature requirement
- Structured prompts (no raw user input)

---

## Common Tasks

### Running the Full System

```bash
# 1. Setup (one-time)
./setup.sh

# 2. Launch
./launch_v2.sh

# 3. Access UI
# http://localhost:8501

# 4. Choose mode and enter patient info

# 5. Review and sign recommendation
```

### Exporting Audit Trail

```python
from audit_log import export_audit_trail

export_audit_trail("audit_export_2025-11-18.json")
```

### Verifying Multi-LLM Chain

```python
from llm_chain import run_multi_llm_decision

result = run_multi_llm_decision(
    patient_context={'age': 72, 'gender': 'M', 'labs': 'Cr 1.8'},
    query="Safe vancomycin dose?",
    retrieved_cases=cases,
    bayesian_result={'prob_safe': 0.85, 'n_cases': 150}
)

print(f"Final recommendation: {result['final_recommendation']}")
print(f"Confidence: {result['final_confidence']:.1%}")
print(f"Chain verified: {result['chain_export']['chain_verified']}")
```

---

## Known Limitations

1. **WiFi check can be bypassed** - `REQUIRE_WIFI_CHECK=False` (remove in production)
2. **PIN in plaintext** - Integrate LDAP/AD for production
3. **No rate limiting** - Add throttling for production
4. **Model integrity not checked** - Verify SHA-256 of downloaded model
5. **No automatic audit backup** - Hospital must configure backups
6. **Hardcoded confidence values** - Literature model: 0.90, could be dynamic
7. **Sequential chain execution** - Adversarial and Literature could run in parallel

---

## Testing Strategy

### Unit Tests

- Test each model independently
- Mock `grok_query()` to avoid LLM calls
- Verify hash computation
- Test chain verification with tampered data

### Integration Tests

- Full chain execution with mocked LLM
- Audit log integration
- Mode switching (Fast ↔ Chain)

### Clinical Validation

- Retrospective case reviews
- Pharmacist agreement studies
- Comparison to guidelines
- IRB-approved prospective trials

---

## File Modification Guidelines

### When editing `llm_chain.py`:

1. **Preserve hash computation** (lines 36-40)
2. **Maintain chain verification** (lines 147-159)
3. **Keep confidence calculation** (line 129)
4. **Test integrity after changes**:
   ```bash
   python -m unittest test_v2.TestMultiLLMChain.test_chain_verification
   ```

### When editing `app.py`:

1. **Never remove WiFi check** in production builds
2. **Maintain dual-mode structure**
3. **Update audit_log calls** if changing data model
4. **Test both Fast and Chain modes**

### When editing `audit_log.py`:

1. **Never break hash chain** - all entries must link via `prev_hash`
2. **Maintain database schema compatibility**
3. **Test integrity verification** after changes
4. **Update migration scripts** if schema changes

---

## Git Workflow

**Current Branch**: `claude/claude-md-mi54iie7un3nrr8a-01HRQs6LTyAzZxG4x4hFy4J8`

### Branch Naming
- Feature branches: `claude/claude-md-<session-id>`
- Development on feature branches only

### Commit Style
- Imperative mood: "Add multi-LLM chain" (not "Added")
- Reference issues: "Fix #123: Resolve hash collision"
- Keep commits atomic and focused

### Push Protocol
```bash
git push -u origin claude/claude-md-<session-id>
```

---

## Documentation Map

- **README.md** - User-facing documentation, deployment guide
- **CLAUDE.md** - This file, AI assistant development guide
- **MULTI_LLM_CHAIN.md** - Deep dive on chain architecture
- **QUICK_START_V2.md** - 5-minute quick start guide
- **CHANGELOG.md** - Version history
- **CONTRIBUTING.md** - Contribution guidelines
- **SECURITY.md** - Security policy and best practices

---

## Questions to Ask Users

Before making significant changes:

1. **Mode Selection**: When should system auto-route to Chain Mode?
2. **Confidence Thresholds**: What confidence triggers physician alert?
3. **Error Handling**: What happens if chain fails mid-execution?
4. **Caching**: Should identical queries return cached results?
5. **Integration**: Which EHR system (Epic, Cerner, other)?
6. **Deployment**: DGX Spark, A100 cluster, or other hardware?

---

## Related Documentation

- [vLLM Documentation](https://docs.vllm.ai/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [HIPAA Guidelines](https://www.hhs.gov/hipaa/index.html)
- [FDA Software as Medical Device](https://www.fda.gov/medical-devices/software-medical-device)

---

## Change Log

- **2025-11-18 (v2.0)**: Multi-LLM chain, dual-mode UI, enhanced documentation
- **2025-11-18 (v1.0)**: Initial release with single-LLM mode

---

## Contact & Contribution

**Repository**: https://github.com/bufirstrepo/Grok_doc_enteprise
**Issues**: https://github.com/bufirstrepo/Grok_doc_enteprise/issues
**Creator**: [@ohio_dino](https://twitter.com/ohio_dino)

When contributing:
- Maintain zero-cloud architecture
- Preserve HIPAA compliance
- Test both Fast and Chain modes
- Update this CLAUDE.md if modifying workflows

**Last Updated**: 2025-11-18
**Repository Status**: Production-ready v2.0
**File Count**: 18 files (Python, Shell, Markdown)
**Lines of Code**: ~2,650 (excluding generated files)
