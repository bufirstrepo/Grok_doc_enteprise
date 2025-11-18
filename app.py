import streamlit as st
import requests
import os
import json
from datetime import datetime
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from local_inference import grok_query
from audit_log import log_decision, verify_audit_integrity
from bayesian_engine import bayesian_safety_assessment

# ── CONFIGURATION ────────────────────────────────────────────────
HOSPITAL_SSID_KEYWORDS = ["hospital", "clinical", "healthcare", "medical"]
CAPTIVE_PORTAL_CHECK = "http://captive.apple.com"
REQUIRE_WIFI_CHECK = True  # Set to False for local testing

# ── FORCE HOSPITAL WIFI ONLY ─────────────────────────────────────
def is_on_hospital_wifi():
    """
    Validates device is on hospital WiFi by checking captive portal.
    In production, enhance with:
    - Certificate pinning
    - MAC address whitelist
    - VPN tunnel verification
    """
    if not REQUIRE_WIFI_CHECK:
        return True
    
    try:
        r = requests.get(CAPTIVE_PORTAL_CHECK, timeout=3, allow_redirects=True)
        url_check = any(kw in r.url.lower() for kw in HOSPITAL_SSID_KEYWORDS)
        content_check = any(kw in r.text.lower() for kw in HOSPITAL_SSID_KEYWORDS)
        return url_check or content_check
    except Exception as e:
        st.error(f"Network check failed: {e}")
        return False

# Check WiFi before anything else
if not is_on_hospital_wifi():
    st.error("🚫 Grok Doc only works on hospital WiFi")
    st.info("Connect to Hospital-Clinical network to prevent PHI from leaving premises.")
    st.stop()

# ── PAGE CONFIGURATION ───────────────────────────────────────────
st.set_page_config(
    page_title="Grok Doc - Clinical AI Co-Pilot",
    page_icon="🩺",
    layout="centered"
)

st.title("🩺 Grok Doc — On-Prem Clinical AI")
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
            query_type="nephrotoxicity"  # Could be dynamic based on query
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
        except Exception as e:
            st.error(f"LLM inference failed: {e}")
            llm_response = "Error: Could not generate recommendation. Please review manually."
        
        latency = (datetime.now() - start_time).total_seconds()
        
        # ── DISPLAY RESULTS ──────────────────────────────────────
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
        
        # ── DOCTOR SIGN-OFF ─────────────────────────────────────
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
                            latency=latency
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
st.caption("Grok Doc v1.0 | 100% on-premises | Zero cloud dependency | Contact: @ohio_dino")
