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
├── Mobile Co-Pilot (NEW in v2.0 - Voice-to-SOAP Documentation)
│   ├── mobile_note.py            # Mobile-optimized Streamlit interface
│   ├── whisper_inference.py      # Local HIPAA-compliant speech-to-text (Whisper)
│   └── soap_generator.py         # Converts LLM chain output to SOAP notes
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
│   ├── ROADMAP.md                # Product roadmap v3.0-v7.0 (NEW in v2.0)
│   ├── MULTI_LLM_CHAIN.md        # Technical architecture docs (NEW in v2.0)
│   ├── MOBILE_DEPLOYMENT.md      # Mobile co-pilot deployment guide (NEW in v2.0)
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

### 7. `whisper_inference.py` - Local Speech-to-Text (NEW in v2.0)
**Lines**: ~212 | **Purpose**: HIPAA-compliant voice transcription using local Whisper models

**Key Features**:
- Zero-cloud architecture (all processing on-premises)
- Supports faster-whisper (4x faster than OpenAI Whisper)
- Multiple model sizes: tiny, base, small, medium, large-v3
- Voice activity detection (VAD) to filter silence
- Timestamped segment output

**Key Classes**:
```python
class WhisperTranscriber:
    def __init__(self, model_size: str = "base", device: str = "cuda"):
        """Initialize Whisper with faster-whisper backend"""

    def transcribe_file(self, audio_path: str, language: str = "en") -> dict:
        """Returns: {text, segments, language, duration}"""

    def transcribe_bytes(self, audio_bytes: bytes) -> dict:
        """For Streamlit audio input (mobile)"""
```

**Model Recommendations**:
- **base**: Recommended for mobile (1GB VRAM, good accuracy)
- **small**: Better accuracy (2GB VRAM)
- **large-v3**: Best accuracy (10GB VRAM, hospital workstation)

**Performance** (on A100):
- base model: ~0.5s for 60s audio
- large-v3 model: ~2s for 60s audio

### 8. `soap_generator.py` - SOAP Note Formatting (NEW in v2.0)
**Lines**: ~380 | **Purpose**: Converts voice transcripts and LLM chain output into structured SOAP notes

**Key Features**:
- Extracts Subjective/Objective/Assessment/Plan sections automatically
- Integrates multi-LLM chain reasoning into Assessment
- Adds evidence citations from Literature Model
- Suggests CPT/ICD billing codes based on complexity
- Cryptographic integrity (timestamps, hashes)

**Key Classes**:
```python
class SOAPGenerator:
    def generate_soap(
        self,
        transcript: str,
        chain_result: Dict,
        patient_context: Optional[Dict] = None
    ) -> Dict:
        """Returns: {soap_text, subjective, objective, assessment, plan, citations, metadata}"""
```

**Section Extraction**:
- **Subjective**: Keyword matching ("patient reports", "cc:", "hpi:", etc.)
- **Objective**: Extracts vitals, labs, physical exam findings
- **Assessment**: Pulls clinical reasoning from chain steps (Kinetics, Adversarial, Literature)
- **Plan**: Recommendation + monitoring instructions from Arbiter Model

**Billing Code Logic**:
- 4+ LLM steps → 99215 (high complexity)
- 2-3 steps → 99214 (moderate complexity)
- 1 step → 99213 (low complexity)

**Example Output**:
```
============================================================
SOAP NOTE - AI-ASSISTED CLINICAL DOCUMENTATION
Generated: 2025-11-19T01:23:45Z
Safety Score: 89.0%
✓ Chain Integrity Verified
============================================================

SUBJECTIVE:
Patient reports severe headache, 8/10 pain, started 2 hours ago.
Associated with nausea and photophobia. No recent trauma.

OBJECTIVE:
Vitals: BP 145/92, HR 88, Temp 98.6F, SpO2 99%
Physical exam: Alert and oriented x3. PERRL. No focal deficits.

ASSESSMENT:
**Pharmacokinetic Analysis:**
Sumatriptan clearance normal for age/weight.

**Risk Assessment:**
Check for contraindications - CAD, uncontrolled HTN (BP elevated).

**Evidence Review:**
2024 AAN guidelines support triptans. CAMERA2 trial: 75% efficacy.

**Clinical Decision Confidence:** 89.0%

PLAN:
**Recommendation:**
Migraine with aura. Recommend sumatriptan 100mg PO now.

**Monitoring:**
BP, headache severity at 2hr

**Follow-up:**
Reassess in 24-48 hours or PRN if symptoms worsen.

EVIDENCE CITATIONS:
  1. 2024 AAN guidelines
  2. CAMERA2 trial

------------------------------------------------------------
BILLING/COMPLIANCE:
Suggested CPT: 99215
AI Mode: Multi-LLM Chain
⚠️ This is AI-assisted documentation requiring physician review.
------------------------------------------------------------
```

### 9. `mobile_note.py` - Mobile Co-Pilot Interface (NEW in v2.0)
**Lines**: ~303 | **Purpose**: Mobile-optimized Streamlit app for voice-to-SOAP workflow

**Workflow**:
1. **Record Audio**: Tap microphone → speak clinical note (60-90 seconds)
2. **Transcribe**: Local Whisper converts speech → text (HIPAA-safe, zero-cloud)
3. **Generate SOAP**: Multi-LLM chain → structured SOAP note with evidence
4. **Review & Edit**: Physician reviews AI-generated note
5. **Approve & Sign**: One-tap e-signature → logged to immutable audit trail

**Key Features**:
- Mobile-first CSS (large touch targets, responsive layout)
- Audio file upload (supports wav, mp3, m4a, ogg, webm)
- Live transcript editing before SOAP generation
- Mode toggle: Fast Mode vs Chain Mode
- Patient context input (MRN, age, gender)
- Evidence citations display
- Cryptographic note signing via `audit_log.sign_note()`

**ROI Impact**:
- Traditional documentation time: 15-40 min per patient
- Mobile co-pilot time: < 2 min per patient
- Time savings: 13-38 min per patient
- For 20 patients/day: **4.3-12.7 hours saved daily**
- Annual value (10 physicians): **$3M+ in recovered clinical time**

**Session State**:
```python
st.session_state.transcript       # Voice transcript
st.session_state.soap_result      # Generated SOAP note + chain
st.session_state.physician_id     # Logged-in physician
st.session_state.patient_mrn      # Current patient
```

**Integration with Core System**:
- Uses `get_transcriber()` from whisper_inference.py
- Calls `run_multi_llm_decision()` from llm_chain.py
- Uses `generate_soap_from_voice()` from soap_generator.py
- Logs via `log_decision()` from audit_log.py

**Mobile Deployment**:
See `MOBILE_DEPLOYMENT.md` for complete setup guide including:
- iOS/Android browser compatibility
- Hospital WiFi configuration
- Audio codec support
- Offline capability

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

**Mobile Co-Pilot Mode (v2.0)**:
```
Voice Recording (60-90s audio)
    → Local Whisper Transcription (0.5-2s)
    → Transcript Review/Edit
    → Multi-LLM Chain OR Fast Mode
    → SOAP Note Generation
    → Evidence Citations
    → Physician Review & E-Sign
    → Cryptographic Audit Log
```
**Latency**: 12-18s total (including transcription) | **Documentation Time**: < 2 min (vs 15-40 min traditional)

**ROI**: 13-38 min saved per patient × 20 patients/day = **4.3-12.7 hours saved/day**

---

### Full Enterprise Architecture (Roadmap)

The complete vision extends beyond the current v2.0 implementation to include medical imaging, RPA automation, and multi-agent orchestration:

```
┌─────────────────────────────────────────────────────────┐
│           Doctor's Mobile (Hospital WiFi Only)          │
│  [🎤 Voice Input] → WebSocket → Hospital Server        │
└────────────────────┬────────────────────────────────────┘
                     │ HTTPS (Hospital VPN)
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Hospital Server (Linux/Windows)            │
│  ┌─────────────────────────────────────────────────┐   │
│  │  LLM Array (Kinetics → Adversarial → Lit → Arb)│   │
│  │  [vLLM: 70B Llama running locally]             │   │
│  │  Orchestration: CrewAI (role-based agents)     │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Medical AI Tools (Roadmap)                     │   │
│  │  • MONAI (X-ray/CT/MRI analysis)                │   │
│  │  • CheXNet (Chest X-ray pneumonia detection)    │   │
│  │  • XGBoost (Lab result predictions)             │   │
│  │  • scispaCy (Medical NLP entity extraction)     │   │
│  │  • Neo4j Knowledge Graph (Truth validation)     │   │
│  │  • Nvidia Clara (Medical imaging pipeline)      │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Cross-Verification Engine                      │   │
│  │  • AutoGen: Multi-agent collaboration           │   │
│  │  • Compare LLM outputs against each other       │   │
│  │  • Validate against SNOMED/LOINC/ICD codes      │   │
│  │  • Durable rules engine (FDA compliance)        │   │
│  │  • OHDSI integration (clinical research data)   │   │
│  └─────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────┘
                     │ RDP / VNC / HTTP
                     ▼
┌─────────────────────────────────────────────────────────┐
│         Doctor's Office Desktop (Windows/Mac)           │
│  ┌─────────────────────────────────────────────────┐   │
│  │  RPA Controller (Roadmap)                       │   │
│  │  • pyautogui + Playwright automation            │   │
│  │  • Opens Epic, Word, Excel, Adobe, PACS         │   │
│  │  • Controls mouse/keyboard for data entry       │   │
│  │  • Creates reports, draws diagrams              │   │
│  │  • Auto-populates EHR forms from SOAP notes     │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Docking Station Watcher (Roadmap)              │   │
│  │  • watchdog library monitors USB devices        │   │
│  │  • USB plugged in → auto-copy to server         │   │
│  │  • X-rays/labs → MONAI/CheXNet analysis         │   │
│  │  • Results → Auto-insert into SOAP notes        │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**Current Status**: v2.0 implements the core LLM chain and mobile co-pilot. Medical imaging, RPA, and advanced verification are roadmap items.

---

## Technology Stack

### Core (v2.0 - Implemented)
- **LLM Inference**: vLLM + AWQ quantization (70B Llama 3.1)
- **Vector Database**: FAISS (similarity search)
- **Bayesian Analysis**: PyMC (probabilistic safety assessment)
- **Web Framework**: Streamlit (mobile + desktop UI)
- **Speech-to-Text**: faster-whisper (HIPAA-compliant transcription)
- **Audit Trail**: SQLite + SHA-256 hash chaining

### Multi-Agent Orchestration (Roadmap)
- **CrewAI**: Role-based agent system for 4-LLM chain coordination
  - Perfect fit for Kinetics → Adversarial → Literature → Arbiter workflow
  - Each LLM becomes a specialized "crew member" with defined role
  - Built-in task delegation and result aggregation
- **AutoGen**: Multi-agent collaboration for cross-verification
  - Enables LLMs to debate and challenge each other's conclusions
  - Adversarial model can automatically critique Kinetics model output
  - Literature model can fact-check both using agent-to-agent messaging

### Medical AI Tools (Roadmap)
| Tool | Purpose | Integration Point |
|------|---------|-------------------|
| **Nvidia Clara** | Medical imaging pipeline | Process DICOM files from PACS |
| **MONAI** | Radiology AI (X-ray/CT/MRI) | Pre-trained models for image analysis |
| **CheXNet** | Chest X-ray detection | Pneumonia/pathology detection |
| **FastAI Medical** | Transfer learning | Retinal scans, pathology slides |
| **XGBoost** | Lab predictions | Predict trends from time-series labs |
| **scispaCy** | Medical NLP | Extract entities from clinical notes |
| **Neo4j** | Knowledge graph | Validate LLM outputs against medical ontologies |
| **OHDSI** | Clinical research data | Standardized health data for evidence retrieval |
| **i2b2** | Clinical data warehouse | Hospital analytics integration |
| **OpenMRS** | Open EHR system | EHR integration patterns |

### RPA & Automation (Roadmap)
- **pyautogui**: Desktop automation (mouse/keyboard control)
- **Playwright**: Browser automation (Epic web interface)
- **watchdog**: File system monitoring (USB device detection)
- **python-docx**: Word document generation
- **openpyxl**: Excel report generation
- **pydicom**: DICOM medical image handling

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

## Roadmap & Future Enhancements

### Phase 3: Multi-Agent Orchestration (v3.0)

**Goal**: Replace manual chain coordination with CrewAI role-based agents

**Implementation**:
```python
from crewai import Agent, Task, Crew

# Define specialized agents
kinetics_agent = Agent(
    role='Clinical Pharmacologist',
    goal='Calculate precise pharmacokinetics and dosing',
    backstory='Expert in PK/PD modeling with 20 years experience',
    llm=grok_query  # Use existing vLLM backend
)

adversarial_agent = Agent(
    role='Risk Analyst',
    goal='Identify all potential risks and contraindications',
    backstory='Paranoid devil\'s advocate focused on patient safety'
)

literature_agent = Agent(
    role='Clinical Researcher',
    goal='Validate recommendations against current evidence',
    backstory='Evidence-based medicine expert'
)

arbiter_agent = Agent(
    role='Attending Physician',
    goal='Synthesize inputs into final clinical decision',
    backstory='Senior physician with decision-making authority'
)

# Define workflow
crew = Crew(
    agents=[kinetics_agent, adversarial_agent, literature_agent, arbiter_agent],
    tasks=[kinetics_task, adversarial_task, literature_task, arbiter_task],
    process='sequential'  # Maintains current chain structure
)

result = crew.kickoff(inputs={'patient': patient_context, 'query': query})
```

**Benefits**:
- Agents can autonomously request more information from each other
- Built-in memory and context sharing
- Easier to add new specialized agents (e.g., Radiology agent, Lab agent)

**Timeline**: Q1 2026

---

### Phase 4: Medical Imaging AI (v4.0)

**Goal**: Integrate radiology AI for automated image analysis

**Components**:

1. **MONAI Integration** (`monai_analyzer.py`)
   ```python
   from monai.networks.nets import DenseNet121
   from monai.transforms import LoadImage, EnsureChannelFirst, ScaleIntensity

   class MedicalImageAnalyzer:
       def analyze_xray(self, dicom_path: str) -> Dict:
           """Analyze chest X-ray for pneumonia, effusion, etc."""
           image = LoadImage()(dicom_path)
           prediction = self.model(image)
           return {
               'findings': ['Right lower lobe opacity', 'Cardiomegaly'],
               'confidence': 0.87,
               'heatmap': heatmap_overlay
           }
   ```

2. **CheXNet Integration** (`chexnet_detector.py`)
   - Stanford's 121-layer DenseNet trained on ChestX-ray14
   - Detects 14 pathologies: Pneumonia, Effusion, Cardiomegaly, etc.
   - Generates visual heatmaps for radiologist review

3. **Workflow**:
   ```
   USB Device Plugged In (X-ray CD)
       → watchdog detects new DICOM files
       → Copy to server /incoming/
       → MONAI/CheXNet analysis
       → Results → Radiology LLM Agent
       → Auto-insert findings into SOAP note
   ```

**Integration with LLM Chain**:
- New **Radiology Agent** joins the crew
- Receives image analysis results
- Contributes radiologic perspective to clinical decision

**Hardware Requirements**:
- GPU: A100 40GB (can run alongside 70B LLM with MIG slicing)
- Storage: 500GB for DICOM cache

**Timeline**: Q2 2026

---

### Phase 5: RPA Desktop Automation (v5.0)

**Goal**: Auto-populate EHR systems from AI-generated SOAP notes

**Components**:

1. **Epic Automation** (`epic_rpa.py`)
   ```python
   from playwright.sync_api import sync_playwright
   import pyautogui

   class EpicRPA:
       def populate_soap_note(self, soap_text: str, mrn: str):
           """Opens Epic and auto-fills SOAP note"""
           with sync_playwright() as p:
               browser = p.chromium.launch()
               page = browser.new_page()

               # Navigate to Epic web interface
               page.goto('https://epic.hospital.local')
               page.fill('#mrn_input', mrn)
               page.click('#search_patient')

               # Open new note
               page.click('text=New Note')

               # Parse SOAP sections
               sections = self.parse_soap(soap_text)
               page.fill('#subjective', sections['subjective'])
               page.fill('#objective', sections['objective'])
               page.fill('#assessment', sections['assessment'])
               page.fill('#plan', sections['plan'])

               # Physician reviews before saving
               input("Press Enter after reviewing note...")
               page.click('#save_note')
   ```

2. **Docking Station Watcher** (`usb_watcher.py`)
   ```python
   from watchdog.observers import Observer
   from watchdog.events import FileSystemEventHandler

   class USBHandler(FileSystemEventHandler):
       def on_created(self, event):
           if event.src_path.endswith('.dcm'):  # DICOM file
               print(f"New X-ray detected: {event.src_path}")
               # Copy to server for MONAI analysis
               self.copy_to_server(event.src_path)
           elif event.src_path.endswith('.csv'):  # Lab results
               # Parse and send to XGBoost predictor
               self.process_labs(event.src_path)

   observer = Observer()
   observer.schedule(USBHandler(), path='/media/usb/', recursive=True)
   observer.start()
   ```

3. **Document Generation**:
   - `python-docx`: Generate Word reports for consultations
   - `openpyxl`: Create Excel spreadsheets for lab trends
   - `reportlab`: Generate PDF discharge summaries
   - `matplotlib`: Create charts for patient presentations

**Security Considerations**:
- RPA runs on doctor's workstation (not server)
- Requires physician approval before any EHR modification
- All actions logged to audit trail
- Session timeout after 5 minutes of inactivity

**Timeline**: Q3 2026

---

### Phase 6: Cross-Verification Engine (v6.0)

**Goal**: Validate LLM outputs against medical ontologies and enable agent debate

**Components**:

1. **AutoGen Multi-Agent Debate**
   ```python
   from autogen import AssistantAgent, UserProxyAgent

   # Kinetics agent proposes dose
   kinetics_agent = AssistantAgent("Kinetics")

   # Adversarial agent challenges
   adversarial_agent = AssistantAgent("Adversarial")

   # Enable debate
   result = kinetics_agent.initiate_chat(
       adversarial_agent,
       message="I recommend vancomycin 1500mg q12h based on CrCl 45"
   )
   # Adversarial: "That's too high for CrCl 45. AUC will exceed 600.
   #               Recommend 1250mg q12h with trough monitoring."
   ```

2. **Neo4j Knowledge Graph** (`knowledge_graph.py`)
   ```python
   from neo4j import GraphDatabase

   class MedicalKnowledgeGraph:
       def validate_recommendation(self, drug: str, condition: str) -> bool:
           """Check if drug is indicated for condition per SNOMED"""
           query = """
           MATCH (d:Drug {name: $drug})-[:INDICATED_FOR]->(c:Condition {name: $condition})
           RETURN count(d) > 0 as is_valid
           """
           result = self.driver.execute_query(query, drug=drug, condition=condition)
           return result[0]['is_valid']
   ```

3. **SNOMED/LOINC/ICD Validation**:
   - Verify all diagnoses map to valid ICD-10 codes
   - Check lab orders use correct LOINC codes
   - Validate drug names against RxNorm

4. **OHDSI Integration**:
   - Query Observational Health Data Sciences database
   - Retrieve real-world evidence for drug safety
   - Compare recommendations to cohort outcomes

**Timeline**: Q4 2026

---

### Phase 7: XGBoost Lab Predictions (v7.0)

**Goal**: Predict future lab values and trends

**Use Cases**:
- Predict Cr 24h after vancomycin dose
- Forecast INR response to warfarin adjustment
- Anticipate potassium changes with diuretic dosing

**Implementation**:
```python
import xgboost as xgb

class LabPredictor:
    def predict_creatinine_24h(self, patient_features: Dict) -> float:
        """Predict Cr 24 hours after nephrotoxic drug"""
        X = self.vectorize_features(patient_features)
        prediction = self.xgb_model.predict(X)
        return prediction[0]

# Integration with Kinetics Agent
predicted_cr = lab_predictor.predict_creatinine_24h(patient_context)
if predicted_cr > 1.5 * baseline_cr:
    kinetics_agent.adjust_dose(reason="Predicted AKI in 24h")
```

**Timeline**: Q1 2027

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
- **ROADMAP.md** - Product roadmap for v3.0-v7.0 (multi-agent, imaging, RPA)
- **MULTI_LLM_CHAIN.md** - Deep dive on chain architecture
- **MOBILE_DEPLOYMENT.md** - Mobile co-pilot deployment guide
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

**Last Updated**: 2025-11-19
**Repository Status**: Production-ready v2.0 with enterprise roadmap
**File Count**: 22 files (11 Python, 2 Shell, 9 Markdown)
**Lines of Code**: ~4,100 (excluding generated files)
**Roadmap**: v3.0-v7.0 planned through Q1 2027
