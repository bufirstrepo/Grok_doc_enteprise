# Grok Doc v6.0 Enterprise

**Multi-LLM Clinical AI Co-Pilot with Zero-Cloud Architecture**

Grok Doc is a HIPAA-compliant, on-premises clinical decision support system designed for hospital environments. It features a multi-agent swarm, medical imaging analysis, and automated risk adjustment coding.

## 🚀 Key Features

### 1. Clinical AI Assistant
-   **Multi-Agent Swarm (CrewAI)**: Pharmacologist, Risk Analyst, and Specialist agents debate complex cases.
-   **Medical Imaging (MONAI)**: Auto-analysis of X-rays and CT scans for pathology.
-   **Evidence-Based**: Retrieval Augmented Generation (RAG) from 17,000+ clinical cases.
-   **Bayesian Safety**: Probabilistic risk assessment for every recommendation.

### 2. Admin & Operations (v3.0 Enterprise)
-   **AI Tools Integration**: Adapters for 9 tools (Aidoc, PathAI, DeepMind, etc.).
-   **Peer Review Workflow**: Human-in-the-loop validation with specialty routing.
-   **HL7 v2 Messaging**: MLLP listener (Port 2575) for ADT/ORU integration.
-   **HCC/RAF Scoring**: Expanded to ~4,200 ICD-10 codes.
-   **Disease Discovery**: NLP engine identifies undocumented conditions.
-   **M.E.A.T. Compliance**: Real-time validation of clinical documentation.
-   **EHR Integration**: Adapters for 18 major EHRs (Epic, Cerner, etc.) via FHIR R4.

### 3. Advanced Clinical & Safety (v4.0)
-   **Clinical Safety**: Real-time Drug-Drug Interaction (DDI) alerts.
-   **Analytics Dashboard**: Provider-level HCC capture rates and revenue forecasting.
-   **Security**: PHI Data Masking ("Demo Mode") for safe training environments.

### 4. Specialty & RCM (v5.0)
-   **Specialty Modules**: Cardiology (ASCVD, CHA2DS2-VASc) & Behavioral Health (PHQ-9).
-   **RCM Engine**: Claims denial prediction based on documentation gaps.
-   **Care Coordination**: SDOH Screener identifies housing/food/transport needs.

### 5. Research & Governance (v6.0)
-   **Advanced Analytics**: Sepsis (qSOFA) and Readmission (LACE) prediction models.
-   **Clinical Research**: Automated matching of patients to active clinical trials.
-   **AI Governance**: Real-time bias detection in AI recommendations.

### 6. Security & Compliance
-   **Zero-Cloud**: All inference runs locally (Llama-3.1-70B via vLLM).
-   **Network Attestation**: 3-layer verification (Subnet, Cert Pinning, SSID).
-   **Immutable Audit**: Blockchain-style logging of all decisions.

## 🛠️ Installation

### Prerequisites
-   Ubuntu 22.04+ / Debian 12+
-   NVIDIA GPU (24GB+ VRAM recommended)
-   Python 3.10+

### Setup
```bash
# 1. Clone repository
git clone https://github.com/bufirstrepo/Grok_doc_enteprise.git
cd Grok_doc_enteprise

# 2. Run setup script (installs dependencies & models)
./setup.sh

# 3. Launch Application
./launch_v2.sh
```

## 📱 Mobile Co-Pilot
Access the PWA interface at `http://<server-ip>:8502`
-   Voice-to-SOAP transcription
-   "Add to Home Screen" supported on iOS/Android

## 🏥 EHR Integration
Configure connections in the **Admin Dashboard**:
1.  Navigate to `Admin Dashboard` in the sidebar.
2.  Select your EHR vendor (e.g., Epic).
3.  Enter FHIR Base URL and OAuth2 credentials.
4.  Test connection.

## 📄 License
Enterprise License - Internal Hospital Use Only.
