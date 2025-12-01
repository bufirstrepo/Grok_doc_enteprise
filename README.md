# 🩺 Grok Doc v6.5 Enterprise - Multi-LLM Clinical AI Platform

**Cloud-Hybrid clinical decision support: Grok orchestrates multiple AI vendors (xAI, Azure, Anthropic, Google, Local) for consensus-based medical recommendations**

⚠️ **INVESTIGATIONAL DEVICE - NOT FDA-CLEARED**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-6.5-blue)](CHANGELOG.md)

---

## 🌟 Key Features

### v6.5 Enterprise (Current)
- **📊 HCC Gap Analysis Reports**: CSV/PDF reporting for revenue cycle management.
- **💡 AI-Powered M.E.A.T. Suggestions**: Automated documentation improvement hints.
- **🔢 Batch RAF Scoring**: Population health analytics for 100+ patients.
- **🕸️ Doctor-Patient Graph Index**: FAISS-powered overlap analysis for referral optimization.
- **🖥️ Role-Specific Dashboards**: Tailored views for Doctors, Admins, and Researchers.
- **⚡ Instant Consult Prediction**: Login banner predicting next likely patient consult.

### v6.0 (Advanced Analytics)
- **🔮 Predictive Analytics**: Sepsis (qSOFA) and Readmission (LACE) risk scoring.
- **🔬 Clinical Trials**: Automated eligibility matching.
- **⚖️ AI Governance**: Bias detection and fairness auditing.

### v5.0 (Specialty & RCM)
- **❤️ Specialty Modules**: Cardiology (ASCVD, CHA2DS2-VASc) and Behavioral Health (PHQ-9).
- **💰 RCM Engine**: Claims denial prediction.
- **social SDOH Screening**: Social determinants of health analysis.

### v4.0 (Safety & Security)
- **💊 Drug-Drug Interaction**: Real-time safety checks.
- **🔒 PHI Masking**: Automated redaction for demo/training.

### v3.0 (Integration)
- **🤖 CrewAI Agent Swarm**: Autonomous multi-agent orchestration.
- **📱 Mobile Co-Pilot**: Voice-to-SOAP PWA.
- **🏥 HL7 v2 Messaging**: ADT/ORU integration.

### v2.0 (Core)
- **🔗 Multi-LLM Chain**: 4-stage reasoning pipeline (Kinetics → Adversarial → Literature → Arbiter).
- **⚡ Fast Mode**: Sub-3 second inference for routine cases.
- **🔒 HIPAA Compliance**: On-premises execution, immutable audit trails.

---

## 🎯 What Is This?

Grok Doc is a **Cloud-Hybrid clinical decision support system** designed for hospitals that require:

- ✅ **Cloud-Hybrid Architecture** - Grok orchestrates top-tier AI models (xAI, Azure, Anthropic)
- ✅ **HIPAA Compliance** - PHI masked before cloud transmission
- ✅ **Network Awareness** - Basic hospital network verification
- ✅ **Multi-LLM Chain Reasoning** - Adversarial validation for critical decisions
- ✅ **Immutable Audit Trail** - Blockchain-style tamper-evident logging
- ✅ **Sub-3 Second Inference** (Fast Mode) - Real-time clinical decision support

**Use cases:**
- Antibiotic dosing safety checks
- Drug interaction warnings
- Clinical guideline adherence
- Evidence-based treatment recommendations
- Complex pharmacokinetic calculations

---

## 🏗️ Architecture (Cloud-Hybrid)

### Fast Mode (v1.0)
```
┌─────────────────┐
│  Doctor's Phone │
│   (Streamlit)   │
└────────┬────────┘
         │ Secure HTTPS (TLS 1.3)
         ▼
┌─────────────────────────────────────┐
│         Grok Doc Server             │
│  ┌──────────────────────────────┐   │
│  │  1. Vector Search (FAISS)    │   │
│  │     → Retrieve 100 cases     │   │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │  2. PHI Masking Engine       │   │
│  │     → Redact Names/MRNs      │   │
│  └──────────────┬───────────────┘   │
│                 │ xAI API (JSON)    │
│                 ▼                   │
│  ┌──────────────────────────────┐   │
│  │  3. xAI Cloud (Grok-Beta)    │   │
│  │     → Clinical reasoning     │   │
│  └──────────────┬───────────────┘   │
│                 │ Response          │
│                 ▼                   │
│  ┌──────────────────────────────┐   │
│  │  4. Physician Sign-Off       │   │
│  │     → Immutable audit log    │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **Hardware:** Standard Server or Laptop (No GPU required)
- **Software:** Python 3.10+
- **API Key:** xAI API Key (`XAI_API_KEY`)

### Installation

```bash
# Clone repository
git clone https://github.com/bufirstrepo/Grok_doc_enteprise.git
cd Grok_doc_enteprise

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set API Key
export XAI_API_KEY="your-key-here"

# Build sample case database
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
├── app.py                    # Main Streamlit UI (v6.5 Enterprise)
├── hcc_scoring.py            # HCC/RAF Scoring Engine (v2.5/v6.5)
├── meat_compliance.py        # M.E.A.T. Validator (v2.5/v6.5)
├── advanced_analytics.py     # Sepsis/Readmission (v6.0)
├── research_module.py        # Clinical Trials (v6.0)
├── ai_governance.py          # Bias Detection (v6.0)
├── llm_chain.py              # Multi-LLM chain orchestrator
├── local_inference.py        # LLM inference engine (vLLM)
├── audit_log.py              # Immutable blockchain-style logging
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── DEPLOYMENT.md             # Deployment guide
├── CHANGELOG.md              # Version history
├── CONTRIBUTING.md           # Contribution guidelines
│
├── /docs/
│   ├── /technical/           # Deep dives (Architecture, Prompts)
│   └── /archive/             # Historical reports
│
├── /tests/
│   ├── test_enterprise_features.py  # Main test suite
│   ├── test_integration.py          # Integration tests
│   └── /quality/                    # Code quality tests
│
└── [Generated Data]
    ├── case_index.faiss
    ├── cases_17k.jsonl
    └── audit.db
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
| Model | Inference Time | Cost |
|-------|----------------|------|
| Grok-beta (API) | ~1.5s | Usage-based |

### Chain Mode (v2.0)
| Model | Inference Time | Cost |
|-------|----------------|------|
| Grok-beta (API) | ~6.0s (4× LLM calls) | Usage-based |

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

### Step 1: API Configuration

```bash
# Ensure XAI_API_KEY is set in your environment
export XAI_API_KEY="your-production-key"
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

**Custom License with Clinical/Commercial Use Restrictions**

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

- Powered by [xAI Grok-beta](https://x.ai/)
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

- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment & Mobile Guide
- [CHANGELOG.md](CHANGELOG.md) - Version history
- [docs/technical/multi_llm_chain.md](docs/technical/multi_llm_chain.md) - Chain architecture
- [docs/technical/prompt_comparison.md](docs/technical/prompt_comparison.md) - Prompt engineering
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development guide

---

**Made with ❤️ for safer hospital care**

![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)
![License](https://img.shields.io/badge/License-Custom%20Restrictions-yellow.svg)
![On-Prem](https://img.shields.io/badge/100%25-On--Prem-brightgreen)
![v6.5](https://img.shields.io/badge/version-6.5-blue)
