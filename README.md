# 🩺 Grok Doc v2.0 - Multi-LLM Clinical AI Co-Pilot

**Zero-cloud, hospital-native clinical decision support powered by local 70B LLM + Multi-LLM Chain + Bayesian reasoning**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-2.0-blue)](CHANGELOG.md)

---

## 🌟 Key Features

### v3.0 (Current - Beta)
- **🤖 CrewAI Agent Swarm**: Autonomous multi-agent orchestration (Pharmacologist, Risk Analyst, Literature, Arbiter).
- **📱 Mobile Co-Pilot PWA**: "Add to Home Screen" capable mobile app with voice-to-SOAP.
- **🖼️ Medical Imaging AI**: Integrated MONAI/CheXNet for X-ray/CT analysis.
- **⚡ Zero-Cloud Architecture**: All inference runs locally (vLLM + Whisper).

### v2.0 (Stable)
- **🔗 Multi-LLM Chain**: 4-stage reasoning pipeline (Kinetics → Adversarial → Literature → Arbiter).
- **🔒 HIPAA Compliance**: On-premises execution, audit trails, network isolation.
- **🏥 EHR Integration**: FHIR-ready data structure.
- **Cryptographic integrity verification** with blockchain-style hash chaining

### Dual-Mode Operation
- **⚡ Fast Mode (v1.0)**: Single LLM call with Bayesian analysis (~2s)
- **🔗 Chain Mode (v2.0)**: 4-stage multi-LLM chain for complex cases (~8s)
- **Easy toggle** in UI - choose the right tool for each scenario

### Enhanced Audit Trail
- Tracks analysis mode (Fast vs Chain) for regulatory compliance
- Full chain reasoning provenance for critical decisions
- Immutable blockchain-style logging with cryptographic verification

---

## 🎯 What Is This?

Grok Doc is a **fully on-premises clinical AI system** designed for hospitals that require:

- ✅ **Zero cloud dependency** - All inference happens locally
- ✅ **HIPAA compliance** - PHI never leaves the hospital network
- ✅ **Hospital WiFi lock** - Only runs on authorized networks
- ✅ **Multi-LLM chain reasoning** - Adversarial validation for critical decisions
- ✅ **Immutable audit trail** - Blockchain-style tamper-evident logging
- ✅ **Bayesian reasoning** - Probabilistic safety assessment over 17k+ cases
- ✅ **Sub-3 second inference** (Fast mode) - Real-time clinical decision support

**Use cases:**
- Antibiotic dosing safety checks
- Drug interaction warnings
- Clinical guideline adherence
- Evidence-based treatment recommendations
- Complex pharmacokinetic calculations

---

## 🏗️ Architecture

### Fast Mode (v1.0)
```
┌─────────────────┐
│  Doctor's Phone │
│   (Streamlit)   │
└────────┬────────┘
         │ Hospital WiFi Only
         ▼
┌─────────────────────────────────────┐
│         Grok Doc Server             │
│  ┌──────────────────────────────┐   │
│  │  1. Vector Search (FAISS)    │   │
│  │     → Retrieve 100 cases     │   │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │  2. Bayesian Analysis        │   │
│  │     → Safety probability     │   │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │  3. LLM Reasoning (70B)      │   │
│  │     → Clinical recommendation│   │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │  4. Physician Sign-Off       │   │
│  │     → Immutable audit log    │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
```

### Chain Mode (v2.0) - NEW
```
┌─────────────────────────────────────────────────────────┐
│              Multi-LLM Reasoning Chain                  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  LLM #1: Kinetics Model                          │  │
│  │  "Clinical pharmacologist"                       │  │
│  │  → PK/PD calculations, dose recommendations     │  │
│  └────────────────┬─────────────────────────────────┘  │
│                   │ (Cryptographic hash chain)        │
│                   ▼                                    │
│  ┌──────────────────────────────────────────────────┐  │
│  │  LLM #2: Adversarial Model                       │  │
│  │  "Paranoid risk analyst"                         │  │
│  │  → Drug interactions, edge cases, risks         │  │
│  └────────────────┬─────────────────────────────────┘  │
│                   │ (Hash chaining continues)          │
│                   ▼                                    │
│  ┌──────────────────────────────────────────────────┐  │
│  │  LLM #3: Literature Model                        │  │
│  │  "Clinical researcher"                           │  │
│  │  → Evidence from recent studies, alternatives   │  │
│  └────────────────┬─────────────────────────────────┘  │
│                   │ (Hash verification)                │
│                   ▼                                    │
│  ┌──────────────────────────────────────────────────┐  │
│  │  LLM #4: Arbiter Model                           │  │
│  │  "Attending physician"                           │  │
│  │  → Final recommendation with confidence score   │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  All steps verified via cryptographic hash chain       │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **Hardware:** DGX Spark, DGX Station, or 128GB+ VRAM GPU server
- **Software:** Python 3.9+, CUDA 12.1+
- **Network:** Hospital WiFi with controlled access

### Installation

```bash
# Clone repository
git clone https://github.com/bufirstrepo/Grok_doc_enteprise.git
cd Grok_doc_enteprise

# Install dependencies
pip install -r requirements.txt

# Download model (one-time, ~140GB)
huggingface-cli download meta-llama/Meta-Llama-3.1-70B-Instruct-AWQ \
  --local-dir /models/llama-3.1-70b-instruct-awq

# Set model path
export GROK_MODEL_PATH="/models/llama-3.1-70b-instruct-awq"

# Build sample case database (for testing)
python data_builder.py

# Run application
streamlit run app.py --server.port 8501
```

### First Query

1. **Connect to hospital WiFi** (enforced by app)
2. **Navigate to:** `http://localhost:8501`
3. **Enter patient context:**
   - MRN: `12345678`
   - Age: `72`
   - Question: *"72M septic shock on vancomycin, Cr 2.9→1.8. Safe trough?"*
4. **Choose analysis mode:**
   - **Fast Mode**: Quick single-LLM decision (~2s)
   - **Chain Mode**: Multi-LLM adversarial reasoning (~8s)
5. **Review AI recommendation**
6. **Sign and log** decision to immutable audit trail

---

## 📁 File Structure

```
Grok_doc_enteprise/
├── app.py                    # Main Streamlit UI (v2.0 with mode toggle)
├── llm_chain.py              # Multi-LLM chain orchestrator (NEW)
├── local_inference.py        # LLM inference engine (vLLM)
├── bayesian_engine.py        # Bayesian safety analysis
├── audit_log.py              # Immutable blockchain-style logging (v2.0 updated)
├── data_builder.py           # Case database generator
├── requirements.txt          # Python dependencies
├── LICENSE                   # MIT with clinical restriction
├── README.md                 # This file
├── CHANGELOG.md              # Version history
├── CLAUDE.md                 # AI assistant documentation
├── MULTI_LLM_CHAIN.md        # Chain architecture details (NEW)
├── QUICK_START_V2.md         # Quick reference guide (NEW)
│
├── case_index.faiss          # Vector database (generated)
├── cases_17k.jsonl           # Clinical cases (generated)
├── audit.db                  # SQLite audit log (generated)
└── audit_chain.jsonl         # Human-readable log backup (generated)
```

---

## 🔒 Security & Compliance

### HIPAA Safeguards

1. **Network Isolation**
   - WiFi SSID verification before any operation
   - Captive portal detection
   - No external API calls

2. **Audit Trail**
   - Every decision logged with SHA-256 hash
   - Blockchain-style chain (prev_hash linking)
   - Tamper detection via `verify_audit_integrity()`
   - Physician e-signature required
   - **NEW**: Analysis mode tracking (Fast vs Chain)

3. **Data Handling**
   - All PHI stays on local hardware
   - No cloud uploads
   - SQLite encryption at rest (hospital managed)

4. **Chain Integrity (v2.0)**
   - Cryptographic verification of multi-LLM reasoning
   - Hash chaining across all 4 model stages
   - Complete provenance for regulatory compliance

### Access Control

- Modify `HOSPITAL_SSID_KEYWORDS` in `app.py` to match your network
- For production, add:
  - LDAP/AD authentication
  - Certificate pinning
  - MAC address whitelist
  - VPN tunnel verification

---

## 📊 Performance Benchmarks

### Fast Mode (v1.0)
| Hardware | Model | Inference Time | Cost |
|----------|-------|----------------|------|
| DGX Spark (8× H100) | Llama-3.1-70B-AWQ | 2.1s | $65k |
| 4× A100 (80GB) | Llama-3.1-70B-AWQ | 3.8s | $40k |
| 2× A100 (80GB) | Llama-3.1-70B-AWQ | 6.2s | $20k |

### Chain Mode (v2.0)
| Hardware | Model | Inference Time | Cost |
|----------|-------|----------------|------|
| DGX Spark (8× H100) | Llama-3.1-70B-AWQ | 7.8s (4× LLM calls) | $65k |
| 4× A100 (80GB) | Llama-3.1-70B-AWQ | 14.2s (4× LLM calls) | $40k |

*All benchmarks: 17k case retrieval + Bayesian + LLM (500 tokens per call)*

---

## 🧪 Testing

### Test WiFi Check (Development Mode)

```python
# In app.py, temporarily disable WiFi check:
REQUIRE_WIFI_CHECK = False
```

### Verify Audit Integrity

```python
from audit_log import verify_audit_integrity

result = verify_audit_integrity()
print(result)
# {'valid': True, 'entries': 142, 'tampered_index': None}
```

### Test Multi-LLM Chain

```python
from llm_chain import run_multi_llm_decision

result = run_multi_llm_decision(
    patient_context={'age': 45, 'gender': 'F', 'labs': 'Cr 1.2'},
    query="Safe fentanyl dose for colonoscopy?",
    retrieved_cases=evidence_list,
    bayesian_result={'prob_safe': 0.85, 'n_cases': 150}
)

print(f"Final recommendation: {result['final_recommendation']}")
print(f"Confidence: {result['final_confidence']:.1%}")
print(f"Chain verified: {result['chain_export']['chain_verified']}")
```

### Export Audit Trail

```python
from audit_log import export_audit_trail

export_audit_trail("audit_export_2025.json")
```

---

## 🏥 Production Deployment

### Step 1: Hardware Setup

```bash
# Verify GPU availability
nvidia-smi

# Should show 8× H100 (or equivalent) with 640GB+ total VRAM
```

### Step 2: Model Download

```bash
# Download quantized model locally (AWQ recommended)
huggingface-cli download meta-llama/Meta-Llama-3.1-70B-Instruct-AWQ \
  --local-dir /opt/models/llama-70b

# Verify model files
ls -lh /opt/models/llama-70b/
# Should see: config.json, model-*.safetensors, tokenizer files
```

### Step 3: Build Real Case Database

```python
# Replace data_builder.py synthetic cases with real de-identified EHR data
# Ensure HIPAA compliance: no PII, no PHI identifiers

from sentence_transformers import SentenceTransformer
from data_builder import create_sample_database

embedder = SentenceTransformer('all-MiniLM-L6-v2')

# Load your hospital's de-identified cases
# cases = load_from_ehr_export()

create_sample_database(embedder, n_cases=50000)
```

### Step 4: Configure Security

```python
# app.py - Update WiFi keywords
HOSPITAL_SSID_KEYWORDS = ["YourHospital-Secure", "YourHospital-Clinical"]

# Enable SSL/TLS
streamlit run app.py \
  --server.sslCertFile=/path/to/cert.pem \
  --server.sslKeyFile=/path/to/key.pem \
  --server.port 443
```

### Step 5: Integration

```bash
# Mount on hospital network
# Set up reverse proxy (nginx/Apache)
# Configure firewall rules (block external access)
# Enable automatic backups of audit.db
```

---

## 🛠️ Troubleshooting

### "Model loading failed"

```bash
# Check GPU memory
nvidia-smi

# Verify model path
ls $GROK_MODEL_PATH

# Try smaller model first
export GROK_MODEL_PATH="/models/llama-8b"
```

### "FAISS index not found"

```bash
# Generate database
python data_builder.py

# Verify files created
ls -lh case_index.faiss cases_17k.jsonl
```

### "WiFi check failed"

```python
# Temporarily disable for local testing
# In app.py:
REQUIRE_WIFI_CHECK = False
```

### "Chain integrity verification failed"

```python
# Check chain export
from llm_chain import MultiLLMChain

chain = MultiLLMChain()
# ... run chain ...
if not chain.verify_chain():
    print("Hash chain compromised - review audit logs")
```

---

## 📜 License

**MIT License with Clinical/Commercial Use Restriction**

Free for:
- Academic research
- Personal projects
- Open-source development

**Requires written authorization for:**
- Clinical deployment in hospitals
- Commercial sale or licensing
- Integration into proprietary systems

Contact: [@ohio_dino](https://twitter.com/ohio_dino) for partnership inquiries.

See [LICENSE](LICENSE) for full terms.

---

## 🤝 Contributing

We welcome contributions! Areas of focus:

- [ ] Additional clinical specialties (cardiology, oncology, etc.)
- [ ] EHR integration modules (Epic, Cerner)
- [ ] Advanced Bayesian models
- [ ] Multi-language support
- [ ] Clinical validation studies
- [ ] Additional LLM chain architectures

**Pull requests:** Please ensure all changes maintain zero-cloud architecture and HIPAA compliance.

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## 🔐 Security

For security issues, please see [SECURITY.md](SECURITY.md) for our responsible disclosure policy.

---

## 📞 Contact & Support

- **Creator:** Dino Silvestri ([@ohio_dino](https://twitter.com/ohio_dino))
- **Issues:** [GitHub Issues](https://github.com/bufirstrepo/Grok_doc_enteprise/issues)
- **Hospital Pilots:** DM on Twitter or email partnerships@[domain].com
- **Technical Support:** Open an issue with logs and system specs

---

## 🌟 Acknowledgments

- Built with [vLLM](https://github.com/vllm-project/vllm) for fast inference
- Powered by [Meta Llama 3.1](https://llama.meta.com/)
- Bayesian engine uses [PyMC](https://www.pymc.io/)
- Vector search via [FAISS](https://github.com/facebookresearch/faiss)
- UI built with [Streamlit](https://streamlit.io/)

---

## ⚠️ Disclaimer

**This is a clinical decision support tool, not a substitute for professional medical judgment.**

- All recommendations must be reviewed by licensed clinicians
- System accuracy depends on case database quality
- No warranty for clinical outcomes
- Hospitals assume all liability for deployment and use

**Always follow your institution's clinical protocols and guidelines.**

---

## 📚 Documentation

- [CHANGELOG.md](CHANGELOG.md) - Version history
- [MULTI_LLM_CHAIN.md](MULTI_LLM_CHAIN.md) - Technical architecture of the multi-LLM chain
- [QUICK_START_V2.md](QUICK_START_V2.md) - Quick reference guide
- [CLAUDE.md](CLAUDE.md) - AI assistant development guide

---

**Made with ❤️ for safer hospital care**

![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)
![License](https://img.shields.io/badge/License-MIT%20with%20restrictions-yellow.svg)
![On-Prem](https://img.shields.io/badge/100%25-On--Prem-brightgreen)
![v2.0](https://img.shields.io/badge/version-2.0-blue)
