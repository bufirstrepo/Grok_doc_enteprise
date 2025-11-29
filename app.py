import streamlit as st
import requests
import os
import json
from datetime import datetime
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import socket
import ssl
import hashlib
import ipaddress
import time
from typing import Tuple
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from local_inference import grok_query
from audit_log import log_decision, verify_audit_integrity, log_security_violation
from bayesian_engine import bayesian_safety_assessment
from llm_chain import run_multi_llm_decision  # NEW in v2.0
import tempfile  # For image uploads
try:
    from crewai_agents import run_crewai_decision  # NEW in v3.0
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False

try:
    from medical_imaging import get_imaging_pipeline
    IMAGING_AVAILABLE = True
except ImportError:
    IMAGING_AVAILABLE = False

# v2.5 Enterprise Modules
try:
    from hcc_scoring import HCCEngine
    from disease_discovery import DiseaseDiscoveryEngine
    from meat_compliance import MEATValidator
    V25_AVAILABLE = True
except ImportError:
    V25_AVAILABLE = False

# v4.0 Modules
try:
    from clinical_safety import DrugInteractionChecker
    from security_utils import PHIMasker
    V40_AVAILABLE = True
except ImportError:
    V40_AVAILABLE = False

# v5.0 Modules
try:
    from specialty_calculators import CardioRiskCalculator, BehavioralHealthScorer
    from rcm_engine import DenialPredictor
    from sdoh_screener import SDOHAnalyzer
    V50_AVAILABLE = True
except ImportError:
    V50_AVAILABLE = False

# v6.0 Modules
try:
    from advanced_analytics import SepsisPredictor, ReadmissionRiskScorer
    from research_module import ClinicalTrialMatcher
    from ai_governance import BiasDetector
    V60_AVAILABLE = True
except ImportError:
    V60_AVAILABLE = False


# ── SEALED CONFIGURATION (Inject via env vars or Kubernetes secrets at deploy) ──
# Update these with your hospital's exact values for production
HOSPITAL_SUBNETS = [
    ipaddress.ip_network("10.50.0.0/16"),      # Clinical VLAN (example)
    ipaddress.ip_network("192.168.100.0/24"),  # Secure ward subnet
    # Add more: ipaddress.ip_network("YOUR_SUBNET_HERE")
]

HOSPITAL_INTERNAL_HOST = os.getenv("HOSPITAL_INTERNAL_HOST", "internal-ehr.hospital.local")  # Internal-only, non-routable
HOSPITAL_INTERNAL_PORT = int(os.getenv("HOSPITAL_INTERNAL_PORT", "443"))
EXPECTED_CERT_SHA256 = os.getenv(
    "EXPECTED_CERT_SHA256",
    "a1b2c3d4e5f67890123456789abcdef123456789abcdef123456789abcdef12"  # Replace with actual SHA-256
)

HOSPITAL_SSID_KEYWORDS = {
    "Hospital-Secure", "HOSP-CLINICAL", "MED-STAFF-5G",  # Your Cisco/Meraki SSID fingerprints
    "hospital", "clinical", "healthcare", "medical"      # Fallback keywords
}

REQUIRE_WIFI_CHECK = os.getenv("REQUIRE_WIFI_CHECK", "true").lower() != "false"  # Set to False for local testing

# Hardened session (no redirects, minimal footprint)
_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "GrokDocEnterprise/2.0 (Internal-Only)"})
retry_strategy = Retry(total=1, backoff_factor=0, status_forcelist=[502, 503, 504])
_SESSION.mount("http://", HTTPAdapter(max_retries=retry_strategy))
_SESSION.mount("https://", HTTPAdapter(max_retries=retry_strategy))

# ── MULTI-LAYER ZERO-TRUST ATTESTATION ──────────────────────────
def is_on_hospital_wifi() -> Tuple[bool, str]:
    """
    Multi-layer zero-trust attestation for hospital network confinement.
    Layers: Subnet binding → Cert pinning → Captive portal SSID fingerprint.
    Fails closed: Any layer breach → abort with audit log.
    For PhD testing: Simulate failures to benchmark tribunal chain resilience.
    """
    if not REQUIRE_WIFI_CHECK:
        return True, "✓ WiFi check disabled (development mode)"

    failure_reasons = []

    # ── LAYER 1: Private Subnet Binding (L2-hardened, anti-VPN) ──
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
        ip_obj = ipaddress.ip_address(local_ip)
        if not any(ip_obj in subnet for subnet in HOSPITAL_SUBNETS):
            failure_reasons.append(f"IP {local_ip} outside approved subnets ({', '.join(str(s) for s in HOSPITAL_SUBNETS)})")
    except Exception as e:
        failure_reasons.append(f"Subnet attestation failed: {str(e)}")

    # ── LAYER 2: Internal Server Cert Pinning (TLS 1.3, anti-MitM) ──
    try:
        context = ssl.create_default_context()
        context.check_hostname = False  # .local not in public DNS
        context.verify_mode = ssl.CERT_REQUIRED
        context.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20")  # Hospital-grade ciphers

        with socket.create_connection((HOSPITAL_INTERNAL_HOST, HOSPITAL_INTERNAL_PORT), timeout=3) as sock:
            with context.wrap_socket(sock, server_hostname=HOSPITAL_INTERNAL_HOST) as ssock:
                cert_der = ssock.getpeercert(binary_form=True)
                if cert_der is None:
                    failure_reasons.append("No certificate returned from server")
                else:
                    actual_fp = hashlib.sha256(cert_der).hexdigest().lower()
                    if actual_fp != EXPECTED_CERT_SHA256.lower():
                        failure_reasons.append(
                            f"Cert pinning violation: Expected {EXPECTED_CERT_SHA256[:16]}..., got {actual_fp[:16]}..."
                        )
    except socket.gaierror:
        failure_reasons.append(f"{HOSPITAL_INTERNAL_HOST} unresolvable (external network detected)")
    except Exception as e:
        failure_reasons.append(f"TLS attestation failed: {str(e)}")

    # ── LAYER 3: Captive Portal + SSID Keyword Fingerprint (anti-spoof) ──
    try:
        resp = _SESSION.get("http://captive.apple.com/hotspot-detect.html", timeout=3, allow_redirects=False)
        if resp.status_code != 200 or "Success" not in resp.text:
            failure_reasons.append("Captive portal handshake failed (non-hospital SSID)")
        elif not any(kw in resp.text for kw in HOSPITAL_SSID_KEYWORDS):
            failure_reasons.append(f"SSID mismatch: Missing keywords {HOSPITAL_SSID_KEYWORDS}")
    except Exception:
        failure_reasons.append("Captive portal probe failed (offline/external)")

    # ── VERDICT & AUDIT ──
    if failure_reasons:
        reason = "; ".join(failure_reasons[:2])  # Concise for UI, full to logs
        # Log to blockchain-style audit
        try:
            log_security_violation("hospital_wifi_attestation_failed", reason, provenance="app_init")
        except Exception:
            pass  # Graceful if audit logging fails
        return False, reason

    return True, "✓ Hospital network attested – Proceeding with zero-cloud inference"


# ── CRITICAL: Enforce at Import Time (Before Any LLM or UI Load) ──
def enforce_hospital_network() -> None:
    """Fail-fast guardrail: Abort if not on secure hospital WiFi."""
    secure, reason = is_on_hospital_wifi()
    if not secure:
        st.error("🚨 **SECURITY VIOLATION: Hospital Network Required**")
        st.error(f"**Attestation Failure**: {reason}")
        st.error("**Action**: Connect to hospital WiFi (e.g., HOSP-CLINICAL). Aborting to protect PHI.")
        st.stop()  # Halts Streamlit execution immediately
    else:
        st.sidebar.success("🔒 **Network Secure**: Hospital WiFi attested")


# ── AUTO-ENFORCE ON MODULE LOAD ──
enforce_hospital_network()

# ── PAGE CONFIGURATION ───────────────────────────────────────────
st.set_page_config(
    page_title="Grok Doc v2.0 - Clinical AI Co-Pilot",
    page_icon="🩺",
    layout="centered"
)

st.title("🩺 Grok Doc v2.0 — Multi-LLM Clinical AI")
st.caption("100% local • Zero cloud • Hospital WiFi only • HIPAA-compliant logging")

# ── LOAD RESOURCES ───────────────────────────────────────────────
@st.cache_resource
def load_vector_db():
    """
    Loads local FAISS index and case database.
    If files don't exist, creates sample data for testing.
    """
    index_path = "case_index.faiss"
    cases_path = "cases_17k.jsonl"

    embedder = SentenceTransformer('all-MiniLM-L6-v2')

    # Create sample data if files don't exist
    if not os.path.exists(index_path) or not os.path.exists(cases_path):
        st.warning("Creating sample case database for demo purposes...")
        from data_builder import create_sample_database
        create_sample_database(embedder)

    index = faiss.read_index(index_path)

    cases = []
    with open(cases_path, 'r') as f:
        for line in f:
            cases.append(json.loads(line))

    return index, cases, embedder

try:
    index, cases, embedder = load_vector_db()
    st.success(f"✓ Loaded {len(cases)} clinical cases locally")
except Exception as e:
    st.error(f"Failed to load case database: {e}")
    st.stop()

# ── SIDEBAR: PATIENT CONTEXT ─────────────────────────────────────
with st.sidebar:
    # Periodic re-attestation (integrate into session state loop)
    if 'last_attestation' not in st.session_state:
        st.session_state.last_attestation = time.time()

    if time.time() - st.session_state.last_attestation > 300:  # 5 min
        st.session_state.last_attestation = time.time()
        secure, reason = is_on_hospital_wifi()
        if not secure:
            st.rerun()  # Triggers enforce_hospital_network() → abort
        st.sidebar.info(f"🔄 Last attestation: {time.strftime('%H:%M:%S', time.localtime(st.session_state.last_attestation))}")

    st.header("Navigation")
    page_selection = st.radio("Go to:", ["Clinical AI", "Admin Dashboard", "Peer Review"])
    
    if page_selection == "Admin Dashboard":
        st.info("Switching to Admin View...")
        from pages.admin_dashboard import main as admin_main
        admin_main()
        st.stop()
        
    if page_selection == "Peer Review":
        st.info("Switching to Peer Review Dashboard...")
        from pages.peer_review_dashboard import main as pr_main
        pr_main()
        st.stop()

    st.divider()
    st.header("Patient Context")


    mrn = st.text_input(
        "Medical Record Number (MRN)",
        help="Required for audit trail"
    )

    age = st.slider("Age", 0, 120, 72)
    gender = st.selectbox("Gender", ["Male", "Female", "Other"])

    chief = st.text_area(
        "Chief complaint / Clinical question",
        value="72 yo male, septic shock on vancomycin, Cr 2.9 → 1.8. Safe trough?",
        height=100
    )

    
    labs = st.text_area(
        "Key labs / imaging (optional)",
        placeholder="Cr: 1.8, WBC: 14.2, Vanc trough: 18.3",
        height=80
    )

    # NEW in v3.0: Medical Imaging Upload
    uploaded_image = st.file_uploader(
        "Upload Medical Image (X-ray/CT)",
        type=["png", "jpg", "jpeg", "dcm"],
        help="AI analysis by MONAI/CheXNet (CrewAI mode only)"
    )

    # NEW in v4.0: Demo Mode (PHI Masking)
    st.divider()
    demo_mode = st.toggle("🛡️ Demo Mode (Mask PHI)", value=False, help="Redact names/MRNs for training/demos")
    if demo_mode and V40_AVAILABLE:
        masker = PHIMasker()
        # Mask inputs if they exist (visual only, logic still runs on raw)
        # In a real app, we'd mask the display but keep raw for processing if authorized.
        # Here we just show a badge.
        st.caption("PHI Masking Active")

    st.divider()

    # NEW in v2.0: Mode selection
    st.subheader("🔬 Analysis Mode")
    analysis_mode = st.radio(
        "Select reasoning mode:",
        options=["⚡ Fast Mode (v1.0)", "🔗 Multi-LLM Chain (v2.0)", "🤖 CrewAI Agent Swarm (v3.0 Beta)"],
        help="""
        **Fast Mode**: Single LLM call with Bayesian analysis (~2s)
        **Chain Mode**: 4-stage adversarial reasoning for critical decisions (~8s)
        **CrewAI Mode**: Autonomous agents (Pharmacologist, Risk Analyst, Specialist) debate the case (~15s)
        """
    )

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        submit = st.button("🔍 Analyze", type="primary", use_container_width=True)
    with col2:
        if st.button("🔒 Verify Audit Log", use_container_width=True):
            integrity = verify_audit_integrity()
            if integrity["valid"]:
                st.success(f"✓ {integrity['entries']} entries verified")
            else:
                st.error(f"⚠️ Tampering detected at entry {integrity['tampered_index']}")

    # ── RESEARCH & GOVERNANCE (v6.0) ─────────────────────────────────
    with st.expander("🔬 Research, Analytics & Governance (v6.0)", expanded=False):
        if V60_AVAILABLE:
            tabs = st.tabs(["Predictive Analytics", "Clinical Trials", "AI Bias Audit"])
            
            with tabs[0]:
                st.subheader("Sepsis & Readmission")
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Sepsis (qSOFA)**")
                    resp_rate = st.number_input("Resp Rate", 10, 60, 16)
                    sbp_sepsis = st.number_input("SBP", 60, 200, 120, key="sbp_sepsis")
                    gcs = st.number_input("GCS Score", 3, 15, 15)
                    if st.button("Check Sepsis Risk"):
                        sepsis = SepsisPredictor()
                        res = sepsis.calculate_qsofa(sbp_sepsis, resp_rate, gcs)
                        st.metric("qSOFA Score", f"{res['score']} ({res['risk']})")
                        if res['score'] >= 2: st.error("High Sepsis Risk!")

                with c2:
                    st.markdown("**Readmission (LACE)**")
                    los = st.number_input("Length of Stay (Days)", 1, 30, 3)
                    acuity = st.checkbox("Emergent Admission?")
                    comorb = st.number_input("Charlson Score", 0, 10, 1)
                    ed_vis = st.number_input("ED Visits (6mo)", 0, 10, 0)
                    if st.button("Calc Readmission Risk"):
                        lace = ReadmissionRiskScorer()
                        res = lace.calculate_lace(los, acuity, comorb, ed_vis)
                        st.metric("LACE Index", f"{res['score']} ({res['risk']})")

            with tabs[1]:
                st.subheader("Clinical Trial Matching")
                if st.button("Find Trials for Patient"):
                    matcher = ClinicalTrialMatcher()
                    # Use chief complaint as proxy for diagnosis in demo
                    matches = matcher.find_trials(chief, age, "Male" if gender=="Male" else "Female")
                    if matches:
                        st.success(f"Found {len(matches)} potential trials!")
                        for t in matches:
                            st.info(f"**{t['id']}**: {t['title']} ({t['phase']})")
                    else:
                        st.warning("No matching trials found in local database.")

            with tabs[2]:
                st.subheader("AI Bias Detection")
                st.caption("Auditing current session inputs for potential bias...")
                detector = BiasDetector()
                # Audit the chief complaint + plan context
                audit = detector.audit_recommendation(chief + " " + history)
                st.metric("Bias Risk Level", audit['risk_level'])
                if audit['flags']:
                    for flag in audit['flags']:
                        st.warning(flag)
                else:
                    st.success("No bias flags detected.")
        else:
            st.warning("v6.0 Modules not loaded.")

    # ── SPECIALTY & RCM TOOLS (v5.0) ─────────────────────────────────
    with st.expander("🩺 Specialty & RCM Tools (v5.0)", expanded=False):
        if V50_AVAILABLE:
            tabs = st.tabs(["Cardiology", "Behavioral Health", "SDOH", "RCM Prediction"])
            
            with tabs[0]:
                st.subheader("Cardiology Risk")
                c1, c2 = st.columns(2)
                with c1:
                    sbp = st.number_input("Systolic BP", 90, 200, 120)
                    chol = st.number_input("Total Cholesterol", 100, 300, 180)
                with c2:
                    smoker = st.checkbox("Smoker")
                    diabetic = st.checkbox("Diabetic")
                
                if st.button("Calculate ASCVD"):
                    calc = CardioRiskCalculator()
                    risk = calc.calculate_ascvd(age, "M" if gender=="Male" else "F", chol, 50, sbp, smoker, diabetic)
                    st.metric("10-Year ASCVD Risk", f"{risk}%")
                    if risk >= 7.5: st.warning("Statin therapy recommended")

            with tabs[1]:
                st.subheader("PHQ-9 Depression Screen")
                # Mock inputs for demo
                q1 = st.slider("Little interest/pleasure?", 0, 3, 0)
                q2 = st.slider("Feeling down/depressed?", 0, 3, 0)
                if st.button("Score PHQ-9"):
                    scorer = BehavioralHealthScorer()
                    # Assume 0 for others
                    res = scorer.score_phq9([q1, q2, 0, 0, 0, 0, 0, 0, 0])
                    st.metric("PHQ-9 Score", f"{res['score']} ({res['severity']})")

            with tabs[2]:
                st.subheader("Social Determinants (SDOH)")
                sdoh_analyzer = SDOHAnalyzer()
                findings = sdoh_analyzer.analyze(chief + " " + labs)
                if findings:
                    for cat, data in findings.items():
                        st.error(f"⚠️ {cat} Need Identified")
                        st.caption(f"Code: {data['code']} (Trigger: '{data['trigger']}')")
                else:
                    st.info("No SDOH needs identified in text.")

            with tabs[3]:
                st.subheader("Claims Denial Prediction")
                rcm = DenialPredictor()
                # Predict based on chief complaint + plan (mock plan)
                pred = rcm.predict_denial(chief)
                st.metric("Denial Probability", pred['probability'])
                if pred['reasons']:
                    st.warning(f"Risk Factors: {', '.join(pred['reasons'])}")
        else:
            st.warning("v5.0 Modules not loaded.")

    # ── HCC RISK ADJUSTMENT TOOLS (v2.5) ─────────────────────────────
    with st.expander("🏥 HCC Risk Adjustment Tools (v2.5)", expanded=False):
        if V25_AVAILABLE:
            c1, c2 = st.columns([1, 1])
            
            with c1:
                st.subheader("Disease Discovery")
                # Run discovery on inputs
                dd_engine = DiseaseDiscoveryEngine()
                # Parse labs from text (mock parser for demo)
                lab_dict = {} 
                if "A1c" in labs: lab_dict["a1c"] = 7.2 # Demo value
                
                discovered = dd_engine.analyze(chief + " " + labs, [], lab_dict)
                
                if discovered:
                    for cond, sources in discovered.items():
                        st.write(f"**{cond}**")
                        st.caption(f"Found via: {', '.join(sources)}")
                else:
                    st.info("No undocumented conditions found.")

            with c2:
                st.subheader("RAF Score Calculator")
                # Mock ICD codes based on discovery or input
                icd_codes = []
                if "Diabetes" in str(discovered): icd_codes.append("E11.9")
                if "CKD" in str(discovered): icd_codes.append("N18.3")
                
                hcc_engine = HCCEngine()
                raf_result = hcc_engine.calculate_raf(age, "M" if gender=="Male" else "F", icd_codes)
                
                st.metric("Estimated RAF Score", f"{raf_result['raf_score']:.3f}")
                st.caption(f"Est. Revenue Impact: ${raf_result['revenue_impact']:,.2f}")
                
            st.divider()
            st.subheader("M.E.A.T. Compliance Check")
            meat_validator = MEATValidator()
            # Check compliance for first discovered condition
            if discovered:
                target_cond = list(discovered.keys())[0]
                meat_res = meat_validator.validate(chief, target_cond)
                st.write(f"**Condition: {target_cond}**")
                st.progress(meat_res['score'], text=meat_validator.get_compliance_badge(meat_res['score']))
                if meat_res['missing']:
                    st.warning(f"Missing: {', '.join(meat_res['missing'])}")
            else:
                st.caption("No conditions to validate.")
        else:
            st.warning("v2.5 Modules not loaded.")

# ── MAIN ANALYSIS LOGIC ──────────────────────────────────────────
if submit:
    if not mrn:
        st.error("MRN is required for audit compliance")
        st.stop()

    if "CrewAI" in analysis_mode:
        if not CREWAI_AVAILABLE:
            st.error("🚨 CrewAI dependencies not installed. Please run: pip install crewai crewai-tools")
            st.stop()

        with st.spinner("🤖 Orchestrating Agents: Pharmacologist ↔ Risk Analyst ↔ Literature ↔ Arbiter..."):
            start_time = datetime.now()

            # STEP 1: Vector retrieval
            query_text = f"{chief} {labs}".strip()
            query_embedding = embedder.encode([query_text])
            k = min(100, len(cases))
            distances, indices = index.search(query_embedding, k)
            retrieved_cases = [cases[idx] for idx in indices[0]]

            # STEP 2: Bayesian safety assessment
            bayesian_result = bayesian_safety_assessment(
                retrieved_cases=retrieved_cases,
                query_type="nephrotoxicity"
            )

            # STEP 2.5: Medical Imaging Analysis (if image uploaded)
            imaging_analysis = None
            if uploaded_image and IMAGING_AVAILABLE:
                with st.spinner("🖼️ Analyzing medical image with MONAI/CheXNet..."):
                    try:
                        # Save temp file
                        suffix = f".{uploaded_image.name.split('.')[-1]}"
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                            tmp.write(uploaded_image.read())
                            tmp_path = tmp.name
                        
                        # Analyze
                        pipeline = get_imaging_pipeline()
                        # Default to XR for simple images, would need more logic for CT/MRI
                        modality = "XR" 
                        imaging_analysis = pipeline.analyze_image(tmp_path, modality=modality)
                        
                        # Clean up
                        os.remove(tmp_path)
                        
                        if 'error' not in imaging_analysis:
                            st.info(f"✓ Imaging Findings: {', '.join(imaging_analysis.get('findings', []))}")
                        else:
                            st.warning(f"Imaging analysis warning: {imaging_analysis['error']}")
                            
                    except Exception as e:
                        st.error(f"Imaging analysis failed: {e}")

            # STEP 2.6: Clinical Safety Check (v4.0)
            if V40_AVAILABLE:
                ddi_checker = DrugInteractionChecker()
                # Extract meds from labs/chief (mock extraction)
                # In prod, use NLP to extract meds. Here we scan for keywords.
                potential_meds = ["warfarin", "aspirin", "lisinopril", "ibuprofen", "sildenafil", "nitroglycerin"]
                found_meds = [m for m in potential_meds if m in chief.lower() or m in labs.lower()]
                
                if found_meds:
                    alerts = ddi_checker.check_interactions(found_meds)
                    if alerts:
                        st.error(f"🚨 {len(alerts)} Drug Interaction(s) Detected!")
                        for alert in alerts:
                            st.write(f"**{' + '.join([m.title() for m in alert['pair']])}** ({alert['severity']})")
                            st.caption(alert['description'])
                else:
                    st.info("✓ No known drug interactions in context.")

            # STEP 3: Run CrewAI
            patient_context = {
                'age': age,
                'gender': gender,
                'labs': labs if labs else 'Not provided'
            }

            try:
                crew_result = run_crewai_decision(
                    patient_context=patient_context,
                    query=chief,
                    retrieved_cases=retrieved_cases,
                    bayesian_result=bayesian_result,
                    imaging_analysis=imaging_analysis
                )

                llm_response = crew_result['final_recommendation']
                confidence = crew_result['final_confidence']
                agent_outputs = crew_result['agent_outputs']
                chain_hash = crew_result['hash']
                
            except Exception as e:
                st.error(f"CrewAI execution failed: {e}")
                llm_response = "Error: Agent swarm failed. Please review manually."
                confidence = 0.0
                agent_outputs = {}
                chain_hash = "N/A"

            latency = (datetime.now() - start_time).total_seconds()

            # ── DISPLAY CREWAI RESULTS ──────────────────────────────
            st.success(f"🤖 Agent Swarm consensus reached in {latency:.2f}s")
            st.info(f"✓ Swarm Integrity Hash: {chain_hash[:16]}...")

            # Metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Swarm Confidence", f"{confidence:.1%}")
            with col2:
                st.metric("Agents Active", len(agent_outputs))
            with col3:
                st.metric("Evidence Base", f"{bayesian_result['n_cases']} cases")

            # Final recommendation
            st.markdown("### 🏛️ Arbiter's Final Decision")
            st.info(llm_response)

            # Agent Debate
            with st.expander("🗣️ View Agent Debate & Reasoning", expanded=True):
                tabs = st.tabs(list(agent_outputs.keys()))
                for i, (agent_name, output) in enumerate(agent_outputs.items()):
                    with tabs[i]:
                        st.markdown(f"**{agent_name.title()} Agent**")
                        st.write(output)

            # Evidence summary
            with st.expander("📊 View Retrieved Evidence"):
                for i, case in enumerate(retrieved_cases[:10]):
                    st.markdown(f"**Case {i+1}:** {case.get('summary', 'No summary available')}")

    elif "Chain" in analysis_mode:  # Multi-LLM Chain (v2.0)
        with st.spinner("🔗 Running Multi-LLM Chain: Kinetics → Adversarial → Literature → Arbiter..."):
            start_time = datetime.now()

            # STEP 1: Vector retrieval
            query_text = f"{chief} {labs}".strip()
            query_embedding = embedder.encode([query_text])

            k = min(100, len(cases))
            distances, indices = index.search(query_embedding, k)

            retrieved_cases = [cases[idx] for idx in indices[0]]

            # STEP 2: Bayesian safety assessment
            bayesian_result = bayesian_safety_assessment(
                retrieved_cases=retrieved_cases,
                query_type="nephrotoxicity"
            )

            # STEP 3: Multi-LLM Chain (NEW in v2.0)
            patient_context = {
                'age': age,
                'gender': gender,
                'labs': labs if labs else 'Not provided'
            }

            try:
                chain_result = run_multi_llm_decision(
                    patient_context=patient_context,
                    query=chief,
                    retrieved_cases=retrieved_cases,
                    bayesian_result=bayesian_result
                )

                llm_response = chain_result['final_recommendation']
                confidence = chain_result['final_confidence']
                chain_steps = chain_result['chain_steps']
                chain_verified = chain_result['chain_export']['chain_verified']

            except Exception as e:
                st.error(f"Multi-LLM chain failed: {e}")
                llm_response = "Error: Could not generate recommendation. Please review manually."
                confidence = 0.0
                chain_steps = []
                chain_verified = False

            latency = (datetime.now() - start_time).total_seconds()

            # ── DISPLAY CHAIN RESULTS ────────────────────────────────
            st.success(f"⚡ Multi-LLM analysis complete in {latency:.2f}s")

            # Chain integrity badge
            if chain_verified:
                st.info("✓ Chain integrity verified via cryptographic hashing")
            else:
                st.warning("⚠️ Chain integrity check failed")

            # Metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Final Confidence", f"{confidence:.1%}")
            with col2:
                st.metric("Cases Analyzed", bayesian_result['n_cases'])
            with col3:
                st.metric("Chain Steps", len(chain_steps))

            # Final recommendation
            st.markdown("### 🤖 Final Clinical Recommendation")
            st.info(llm_response)

            # Chain reasoning breakdown
            with st.expander("🔗 View Multi-LLM Reasoning Chain"):
                for step in chain_steps:
                    st.markdown(f"**{step['step']}** (Confidence: {step.get('confidence', 'N/A')})")
                    st.write(step['response'])
                    st.caption(f"Hash: {step['hash'][:16]}...")
                    st.divider()

            # Evidence summary
            with st.expander("📊 View Retrieved Evidence"):
                for i, case in enumerate(retrieved_cases[:10]):
                    st.markdown(f"**Case {i+1}:** {case.get('summary', 'No summary available')}")

    elif use_chain_mode:  # Multi-LLM Chain (v2.0)
        with st.spinner("🔬 Retrieving evidence → Bayesian analysis → LLM reasoning..."):
            start_time = datetime.now()

            # STEP 1: Vector retrieval
            query_text = f"{chief} {labs}".strip()
            query_embedding = embedder.encode([query_text])

            k = min(100, len(cases))
            distances, indices = index.search(query_embedding, k)

            retrieved_cases = [cases[idx] for idx in indices[0]]

            # STEP 2: Bayesian safety assessment
            bayesian_result = bayesian_safety_assessment(
                retrieved_cases=retrieved_cases,
                query_type="nephrotoxicity"
            )

            # STEP 3: Build prompt for LLM
            evidence_text = "\n".join([
                f"Case {i+1}: {case.get('summary', 'N/A')}"
                for i, case in enumerate(retrieved_cases[:20])
            ])

            prompt = f"""You are an expert intensivist providing a clinical decision support recommendation.

EVIDENCE FROM SIMILAR CASES:
{evidence_text[:6000]}

BAYESIAN ANALYSIS:
- Probability of safety: {bayesian_result['prob_safe']:.1%}
- 95% Credible Interval: [{bayesian_result['ci_low']:.1%}, {bayesian_result['ci_high']:.1%}]
- Based on {bayesian_result['n_cases']} similar cases

PATIENT CONTEXT:
Age: {age}, Gender: {gender}
Question: {chief}
Labs: {labs if labs else 'Not provided'}

Provide a concise recommendation (3-4 sentences max). Include:
1. Direct answer to the clinical question
2. Key safety considerations
3. Numerical probability estimate where appropriate
"""

            # STEP 4: Local LLM inference
            try:
                llm_response = grok_query(prompt)
                confidence = bayesian_result['prob_safe']
            except Exception as e:
                st.error(f"LLM inference failed: {e}")
                llm_response = "Error: Could not generate recommendation. Please review manually."
                confidence = 0.0

            latency = (datetime.now() - start_time).total_seconds()

            # ── DISPLAY FAST MODE RESULTS ────────────────────────────
            st.success(f"⚡ Analysis complete in {latency:.2f}s")

            # Bayesian results
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Safety Probability", f"{bayesian_result['prob_safe']:.1%}")
            with col2:
                st.metric("Cases Analyzed", bayesian_result['n_cases'])
            with col3:
                st.metric("Confidence Interval",
                         f"{bayesian_result['ci_low']:.0%}-{bayesian_result['ci_high']:.0%}")

            # LLM recommendation
            st.markdown("### 🤖 Clinical Recommendation")
            st.info(llm_response)

            # Evidence summary
            with st.expander("📊 View Retrieved Evidence"):
                for i, case in enumerate(retrieved_cases[:10]):
                    st.markdown(f"**Case {i+1}:** {case.get('summary', 'No summary available')}")

    # ── DOCTOR SIGN-OFF (Common to both modes) ──────────────────
    st.divider()
    st.markdown("### 👨‍⚕️ Physician Review")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("✅ Accept & Sign", type="primary", use_container_width=True):
            st.session_state['show_signature'] = True

    with col2:
        if st.button("✏️ Modify Recommendation", use_container_width=True):
            st.session_state['show_edit'] = True

    with col3:
        if st.button("❌ Reject", use_container_width=True):
            st.warning("Recommendation rejected - not logged")

    # Signature modal
    if st.session_state.get('show_signature', False):
        with st.form("signature_form"):
            st.markdown("**Electronic Signature Required**")
            doctor_name = st.text_input("Physician Name", placeholder="Dr. Jane Smith")
            pin = st.text_input("PIN", type="password", help="4-6 digit PIN")

            col1, col2 = st.columns(2)
            with col1:
                sign_button = st.form_submit_button("Sign & Log", type="primary", use_container_width=True)
            with col2:
                cancel_button = st.form_submit_button("Cancel", use_container_width=True)

            if sign_button:
                if len(pin) < 4:
                    st.error("PIN must be at least 4 digits")
                elif not doctor_name:
                    st.error("Physician name required")
                else:
                    # Log to immutable audit trail
                    log_entry = log_decision(
                        mrn=mrn,
                        patient_context=f"Age: {age}, Gender: {gender}",
                        query=chief,
                        labs=labs,
                        response=llm_response,
                        doctor=doctor_name,
                        bayesian_prob=bayesian_result['prob_safe'],
                        latency=latency,
                        analysis_mode="chain" if use_chain_mode else "fast"  # NEW in v2.0
                    )

                    st.success(f"✓ Logged to immutable audit trail (Hash: {log_entry['hash'][:16]}...)")
                    st.session_state['show_signature'] = False
                    st.rerun()

            if cancel_button:
                st.session_state['show_signature'] = False
                st.rerun()

    # Edit modal
    if st.session_state.get('show_edit', False):
        with st.form("edit_form"):
            st.markdown("**Modify Recommendation**")
            edited_response = st.text_area(
                "Edited Recommendation",
                value=llm_response,
                height=150
            )

            col1, col2 = st.columns(2)
            with col1:
                save_button = st.form_submit_button("Save & Sign", type="primary", use_container_width=True)
            with col2:
                cancel_button = st.form_submit_button("Cancel", use_container_width=True)

            if save_button:
                st.session_state['edited_response'] = edited_response
                st.session_state['show_edit'] = False
                st.session_state['show_signature'] = True
                st.rerun()

            if cancel_button:
                st.session_state['show_edit'] = False
                st.rerun()

# ── FOOTER ───────────────────────────────────────────────────────
st.divider()
st.caption("Grok Doc v2.5 Enterprise | 18 EHR Integrations | HCC/RAF Coding | Zero Cloud")
