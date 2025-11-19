# Grok Doc v2.0 - Source Directory Structure

**Production-ready hierarchical organization with clean separation of concerns**

---

## 📁 Directory Structure

```
src/
├── agents/                          # CrewAI Multi-Agent Orchestration
│   ├── __init__.py
│   └── crewai_orchestrator.py       # GrokDocCrew - coordinates 5 specialized agents
│
├── tools/                           # CrewAI Tool Implementations
│   ├── __init__.py
│   ├── monai_tool.py                # MONAI + CheXNet medical imaging (→ imaging_agent)
│   ├── xgboost_tool.py              # XGBoost lab predictions (→ lab_agent, kinetics_agent)
│   ├── neo4j_tool.py                # Neo4j knowledge graph validation (→ graph_agent)
│   ├── scispacy_tool.py             # sciSpaCy medical NLP (→ nlp_agent, adversarial_agent)
│   ├── epic_tool.py                 # Epic EHR automation via RPA (→ epic_agent)
│   └── blockchain_tool.py           # Blockchain audit logging with ZKP (→ logger_agent)
│
├── services/                        # Backend Service Implementations
│   ├── __init__.py
│   ├── monai_chexnet.py             # Medical imaging pipeline (MONAI + CheXNet)
│   ├── epic_rpa.py                  # Epic Hyperspace automation (Playwright + pyautogui)
│   ├── usb_watcher.py               # USB device monitoring (watchdog)
│   └── neo4j_validator.py           # Neo4j medical ontology queries (SNOMED/LOINC/ICD)
│
├── main.py                          # Unified Entry Point (CLI)
└── mobile_server.py                 # WebSocket Server for Mobile Co-Pilot
```

---

## 🚀 Entry Point (`main.py`)

**Unified command-line interface for all services**

### Commands

```bash
# Launch Streamlit UI (desktop)
python src/main.py ui [--port 8501]

# Launch Mobile Co-Pilot UI
python src/main.py mobile-ui [--port 8502]

# Launch WebSocket Server (for mobile app)
python src/main.py mobile-server [--port 8765]

# Run Tests
python src/main.py test [--test-type all|structure|integration|v2]

# Verify System Readiness
python src/main.py verify

# Show System Status
python src/main.py status
```

### Examples

```bash
# Start desktop UI
python src/main.py ui

# Start all services (use docker-compose instead for production)
docker-compose up

# Run code structure verification
python src/main.py test --test-type structure

# Verify all dependencies installed
python src/main.py verify
```

---

## 🤖 Agents (`src/agents/`)

### `crewai_orchestrator.py` - GrokDocCrew

**Multi-agent system replacing manual LLM chain**

#### 5 Specialized Agents

| Agent | Role | Tools | Purpose |
|-------|------|-------|---------|
| **Kinetics Agent** | Clinical Pharmacologist | XGBoostTool, Neo4jTool | PK/PD calculations, dose optimization |
| **Adversarial Agent** | Risk Analyst | Neo4jTool, ScispacyTool | Risk identification, contraindications |
| **Literature Agent** | Clinical Researcher | Neo4jTool, ScispacyTool | Evidence validation, guideline lookup |
| **Arbiter Agent** | Attending Physician | Neo4jTool, XGBoostTool, BlockchainTool | Final decision synthesis, audit logging |
| **Radiology Agent** | Radiologist | MonaiTool, EpicTool | Image analysis, findings interpretation |

#### Usage

```python
from src.agents import GrokDocCrew

# Initialize crew
crew = GrokDocCrew(use_radiology=True)

# Run multi-agent decision
result = crew.run_clinical_decision(
    patient_context={'age': 72, 'gender': 'M', 'labs': 'Cr 1.8'},
    query="Safe vancomycin dose?",
    retrieved_cases=cases,
    bayesian_result={'prob_safe': 0.85}
)

# Result includes:
# - final_recommendation: Attending physician's synthesis
# - final_confidence: Weighted confidence score
# - full_crew_output: All agent conversations
# - task_results: Individual agent outputs
```

---

## 🛠️ Tools (`src/tools/`)

**Functional capabilities that agents can use (not just LLM prompts)**

### 1. `monai_tool.py` - Medical Imaging Analyzer

**Uses**: MONAI + CheXNet
**Agents**: imaging_agent (Radiology Agent)
**Capabilities**:
- Chest X-ray analysis (14 pathologies)
- CT/MRI interpretation
- Heatmap generation
- Differential diagnosis

**Example**:
```python
from src.tools import MonaiTool

tool = MonaiTool()
result = tool._run(
    image_path="/path/to/xray.dcm",
    modality="XR"
)
# Returns: Findings, confidence, differential diagnosis
```

---

### 2. `xgboost_tool.py` - Lab Value Predictor

**Uses**: XGBoost ML models
**Agents**: lab_agent, kinetics_agent
**Capabilities**:
- Creatinine prediction (AKI risk)
- INR prediction (warfarin response)
- Potassium trend prediction

**Example**:
```python
from src.tools import XGBoostTool

tool = XGBoostTool()
result = tool._run(
    patient_data={'age': 72, 'labs': {'creatinine': 1.8}},
    lab_type='creatinine'
)
# Returns: Predicted Cr 24h ahead, AKI risk assessment
```

---

### 3. `neo4j_tool.py` - Knowledge Graph Validator

**Uses**: Neo4j with SNOMED/LOINC/ICD ontologies
**Agents**: graph_agent, adversarial_agent, literature_agent, arbiter_agent
**Capabilities**:
- Drug-condition validation
- Drug-drug interaction checking
- Alternative therapy search
- Ontology linking

**Example**:
```python
from src.tools import Neo4jTool

tool = Neo4jTool()
result = tool._run(
    query_type='validate_indication',
    drug='vancomycin',
    condition='MRSA bacteremia'
)
# Returns: Validation status, evidence level, guidelines
```

---

### 4. `scispacy_tool.py` - Medical NLP

**Uses**: sciSpaCy + UMLS
**Agents**: nlp_agent, adversarial_agent, literature_agent
**Capabilities**:
- Medication extraction
- Diagnosis extraction
- Procedure identification
- Lab value parsing
- UMLS concept linking

**Example**:
```python
from src.tools import ScispacyTool

tool = ScispacyTool()
result = tool._run(
    clinical_text="Patient reports chest pain. Started aspirin 81mg daily. ECG shows ST elevation.",
    extract_type='all'
)
# Returns: Medications, diagnoses, procedures, labs with UMLS codes
```

---

### 5. `epic_tool.py` - Epic EHR Automation

**Uses**: Playwright (web) + pyautogui (desktop)
**Agents**: epic_agent, radiology_agent
**Capabilities**:
- Auto-populate SOAP notes
- Retrieve patient data
- Place lab orders
- Submit prescriptions

**Example**:
```python
from src.tools import EpicTool

tool = EpicTool()
result = tool._run(
    action='populate_soap',
    mrn='123456789',
    data={'soap_text': 'Subjective: Patient reports...'}
)
# Returns: Epic Note ID, timestamp, success status
```

---

### 6. `blockchain_tool.py` - Immutable Audit Logger

**Uses**: Ethereum + IPFS + Zero-Knowledge Proofs
**Agents**: logger_agent (Arbiter Agent)
**Capabilities**:
- Blockchain audit logging
- Chain integrity verification
- Zero-Knowledge Proof generation
- Privacy-preserving compliance

**Example**:
```python
from src.tools import BlockchainTool

tool = BlockchainTool()
result = tool._run(
    action='log_decision',
    decision_data={
        'mrn': '123456789',
        'physician': 'Dr. Smith',
        'query': 'Safe vancomycin dose?',
        'recommendation': '1250mg q12h'
    }
)
# Returns: Transaction hash, block number, entry hash, IPFS hash
```

---

## 🔧 Services (`src/services/`)

**Backend implementations that tools wrap**

### `monai_chexnet.py` - Medical Imaging Pipeline

- DenseNet121 architecture (Stanford CheXNet)
- MONAI transforms and preprocessing
- Heatmap generation with CAM
- 14-pathology classification

### `epic_rpa.py` - Epic EHR Controller

- Playwright browser automation (Epic Hyperspace web)
- pyautogui desktop automation (Epic thick client)
- Session management and login
- Error handling and retry logic

### `usb_watcher.py` - USB Device Monitor

- watchdog file system observer
- DICOM file detection
- Auto-copy to server
- Triggers MONAI analysis pipeline

### `neo4j_validator.py` - Medical Ontology Queries

- SNOMED CT clinical term validation
- LOINC lab code mapping
- ICD-10 diagnosis codes
- DrugBank interaction queries

---

## 📱 Mobile Server (`mobile_server.py`)

**WebSocket server for real-time mobile → server communication**

### Endpoints

| Endpoint | Purpose | Protocol |
|----------|---------|----------|
| `/ws/transcribe` | Audio streaming → Whisper transcription | WebSocket |
| `/ws/decision` | LLM chain execution with progress | WebSocket |
| `/ws/soap` | SOAP note generation | WebSocket |

### Features

- JWT authentication (8-hour expiry)
- Real-time progress updates
- Binary audio streaming (base64)
- Hospital WiFi-only access
- Async concurrent connections

### Usage

```bash
# Standalone
python src/mobile_server.py

# Via main.py
python src/main.py mobile-server --port 8765

# Via docker-compose
docker-compose up websocket-server
```

---

## 🐳 Docker Deployment

**One-command deployment of all services**

### Start All Services

```bash
docker-compose up -d
```

### Services Launched

- **streamlit-ui** (port 8501) - Desktop web interface
- **mobile-ui** (port 8502) - Mobile co-pilot interface
- **websocket-server** (port 8765) - WebSocket for mobile
- **vllm-server** (port 8000) - 70B LLM inference
- **neo4j** (ports 7474, 7687) - Knowledge graph
- **ganache** (port 8545) - Local Ethereum blockchain
- **ipfs** (ports 4001, 5001, 8080) - Decentralized storage
- **postgres** (port 5432) - Structured data (optional)
- **prometheus** (port 9090) - Metrics (optional)
- **grafana** (port 3000) - Monitoring dashboards (optional)

### Stop All Services

```bash
docker-compose down
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f streamlit-ui
```

---

## 📊 Architecture

```
┌─────────────────────────────────────────────────────────┐
│           Mobile App (iOS/Android)                      │
│  [Voice Recording] → WebSocket → mobile_server.py      │
└────────────────────┬────────────────────────────────────┘
                     │ WSS (JWT Auth)
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Hospital Server (Linux/Windows)            │
│  ┌─────────────────────────────────────────────────┐   │
│  │  src/agents/crewai_orchestrator.py              │   │
│  │  GrokDocCrew: 5 Specialized Agents              │   │
│  │  ├─ Kinetics Agent                              │   │
│  │  ├─ Adversarial Agent                           │   │
│  │  ├─ Literature Agent                            │   │
│  │  ├─ Arbiter Agent                               │   │
│  │  └─ Radiology Agent                             │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │  src/tools/ - Agent Capabilities                │   │
│  │  ├─ MonaiTool       (imaging analysis)          │   │
│  │  ├─ XGBoostTool     (lab predictions)           │   │
│  │  ├─ Neo4jTool       (knowledge graph)           │   │
│  │  ├─ ScispacyTool    (medical NLP)               │   │
│  │  ├─ EpicTool        (EHR automation)            │   │
│  │  └─ BlockchainTool  (audit logging)             │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │  src/services/ - Backend Implementations        │   │
│  │  ├─ monai_chexnet.py   (MONAI + CheXNet)        │   │
│  │  ├─ epic_rpa.py        (Playwright + pyautogui) │   │
│  │  ├─ usb_watcher.py     (watchdog)               │   │
│  │  └─ neo4j_validator.py (Neo4j queries)          │   │
│  └─────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
    ┌──────┐    ┌──────┐    ┌───────────┐
    │Neo4j │    │vLLM  │    │Ethereum   │
    │Graph │    │70B   │    │+IPFS      │
    └──────┘    └──────┘    └───────────┘
```

---

## 🧪 Testing

### Run All Tests

```bash
python src/main.py test
```

### Run Specific Test Suite

```bash
# Code structure verification
python src/main.py test --test-type structure

# Integration tests (requires dependencies)
python src/main.py test --test-type integration

# V2 feature tests
python src/main.py test --test-type v2
```

### Test Files

- `test_code_structure.py` - Syntax, imports, agent-tool connections
- `test_integration_v2.py` - Full integration with dependencies
- `test_v2.py` - V2 multi-LLM chain tests

---

## 📝 Configuration

### Environment Variables

```bash
# LLM Inference
export GROK_MODEL_PATH="/models/llama-3.1-70b-instruct-awq"

# Security (DISABLE IN PRODUCTION)
export REQUIRE_WIFI_CHECK=false

# WebSocket Server
export JWT_SECRET="your-secret-key-change-in-production"

# Neo4j
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="change_me"

# Ethereum
export ETH_RPC_URL="http://localhost:8545"
export ETH_PRIVATE_KEY="0x..."

# IPFS
export IPFS_API_URL="http://localhost:5001"
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Verify System

```bash
python src/main.py verify
```

### 3. Start Services

```bash
# Development (single service)
python src/main.py ui

# Production (all services)
docker-compose up -d
```

### 4. Access Interfaces

- **Desktop UI**: http://localhost:8501
- **Mobile UI**: http://localhost:8502
- **WebSocket**: ws://localhost:8765
- **Neo4j Browser**: http://localhost:7474
- **Grafana**: http://localhost:3000

---

## 📚 Documentation

- **README.md** - User-facing documentation
- **CLAUDE.md** - AI assistant development guide
- **ROADMAP.md** - Future enhancements
- **MULTI_LLM_CHAIN.md** - Technical architecture
- **MOBILE_DEPLOYMENT.md** - Mobile co-pilot deployment
- **VERIFICATION_REPORT.md** - Integration verification

---

## 🔒 Security

- **Zero-cloud architecture**: All processing on-premises
- **Hospital WiFi enforcement**: Network-level access control
- **JWT authentication**: 8-hour token expiry
- **Blockchain audit trail**: Immutable, tamper-evident logging
- **Zero-Knowledge Proofs**: Privacy-preserving compliance
- **E-signature required**: Physician approval for all decisions

---

## 📄 License

MIT License with clinical use restrictions. See LICENSE file.

---

**Last Updated**: 2025-11-19
**Version**: 2.0.0 Enterprise
**Author**: @ohio_dino
**Repository**: https://github.com/bufirstrepo/Grok_doc_enteprise
