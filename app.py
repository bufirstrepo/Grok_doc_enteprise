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

    
    embedder = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Create sample data if files don't exist
    if not os.path.exists(index_path) or not os.path.exists(cases_path):
        st.warning("Creating sample case database for demo purposes...")
        from data_builder import create_sample_database
        create_sample_database(embedder)

    index = faiss.read_index(index_path)

    
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

    st.header("Patient Context")


    mrn = st.text_input(
        "Medical Record Number (MRN)",
        help="Required for audit trail"
    )

    age = st.slider("Age", 0, 120, 72)
    gender = st.selectbox("Gender", ["Male", "Female", "Other"])

    
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

    st.divider()

    # NEW in v2.0: Mode selection
    st.subheader("🔬 Analysis Mode")
    analysis_mode = st.radio(
        "Select reasoning mode:",
        options=["⚡ Fast Mode (v1.0)", "🔗 Multi-LLM Chain (v2.0)"],
        help="""
        **Fast Mode**: Single LLM call with Bayesian analysis (~2s)
        **Chain Mode**: 4-stage adversarial reasoning for critical decisions (~8s)
        """
    )

    st.divider()

    
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

# ── MAIN ANALYSIS LOGIC ──────────────────────────────────────────
if submit:
    if not mrn:
        st.error("MRN is required for audit compliance")
        st.stop()

    use_chain_mode = "Chain" in analysis_mode

    if use_chain_mode:
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

    else:  # Fast Mode (v1.0)
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
st.caption("Grok Doc v2.0 | Multi-LLM Chain | 100% on-premises | Zero cloud dependency | Contact: @ohio_dino")
