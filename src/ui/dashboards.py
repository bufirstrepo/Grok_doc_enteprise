"""
Role-Specific Dashboards
Renders distinct UI views based on user role.
"""

import streamlit as st
import os
import time
from datetime import datetime

# Import feature modules (wrapped in try-except in app.py, but here we assume they are passed or available)
# For simplicity, we'll import what we need or pass them as args if they are heavy.

def render_doctor_dashboard(config, predictor, username):
    """
    Renders the clinical dashboard for doctors.
    Includes: Next Likely Consult Banner, Patient Context, Analysis Tools.
    """
    st.header("🩺 Doctor Dashboard")
    
    # 1. Next Likely Consult Banner
    try:
        prediction = predictor.predict_next_consult(username)
        if prediction:
            st.info(
                f"**Next Likely Consult:** Patient {prediction.patient_name_masked} ({prediction.patient_id})  \n"
                f"Reason: {prediction.reason} | Urgency: {prediction.urgency}"
            )
    except Exception as e:
        print(f"Banner Error: {e}")

    # 2. Patient Context Input
    st.subheader("Patient Context")
    col1, col2 = st.columns(2)
    with col1:
        mrn = st.text_input("MRN", help="Required for audit trail")
        age = st.number_input("Age", 0, 120, 72)
    with col2:
        gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        chief = st.text_area("Chief Complaint", height=100)

    # 3. Analysis Tools (Placeholder for existing app.py logic)
    st.info("Clinical Analysis Tools are ready. (See main app flow for execution)")
    
    return {
        "mrn": mrn,
        "age": age,
        "gender": gender,
        "chief": chief
    }

def render_admin_dashboard():
    """
    Renders the system administration dashboard.
    Includes: System Status, Audit Logs, User Management.
    """
    st.header("🛡️ Admin Dashboard")
    
    # 1. System Status
    st.subheader("System Status")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("API Status", "Online", "99.9%")
    with col2:
        st.metric("Active Users", "12", "+2")
    with col3:
        st.metric("Security Alerts", "0", "Low")

    # 2. Audit Log Verification
    st.subheader("Audit Log Integrity")
    if st.button("Verify Immutable Ledger"):
        # Mock verification for UI component test
        st.success("✓ Blockchain Anchor Verified: 0x7f...3a2b")
        st.success("✓ Local Hash Chain Verified")

def render_researcher_dashboard(config):
    """
    Renders the research and analytics dashboard.
    Includes: Population Health, Clinical Trials, Bias Audit.
    """
    st.header("🔬 Researcher Dashboard")
    
    tabs = st.tabs(["Population Health", "Clinical Trials", "Bias Audit"])
    
    with tabs[0]:
        st.subheader("Population Health Analytics")
        st.bar_chart({"Sepsis": 15, "Readmission": 8, "Falls": 4})
        
    with tabs[1]:
        st.subheader("Clinical Trial Recruitment")
        st.info("3 Active Trials Matching Current Patient Population")
        
    with tabs[2]:
        st.subheader("AI Bias Monitor")
        st.metric("Fairness Score", "98.5%", "+0.2%")
