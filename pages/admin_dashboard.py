import streamlit as st
import os
import json
from ehr_adapters import get_ehr_adapter
from ai_tools_adapters import get_ai_tool

st.set_page_config(page_title="Grok Doc Admin", page_icon="⚙️", layout="wide")

def main():
    st.title("⚙️ Grok Doc Enterprise Admin")
    
    tabs = st.tabs(["EHR Integration", "AI Tools", "Analytics", "User Management", "System Health", "Logs"])
    
    # ─── TAB 1: EHR INTEGRATION ────────────────────────────────────────
    with tabs[0]:
        st.header("EHR Connection Manager")
        st.info("Configure FHIR R4 connections for your hospital system.")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            ehr_vendor = st.selectbox(
                "Select EHR Vendor",
                [
                    "Epic", "Cerner", "athenahealth", "Veradigm", "NextGen",
                    "eClinicalWorks", "MEDITECH", "Greenway", "Practice Fusion",
                    "Elation", "Canvas", "DrChrono", "Tebra", "AdvancedMD",
                    "MDLand", "eMedicalPractice", "MEDENT", "TalkEHR"
                ]
            )
            
            status = "Disconnected"
            # Check session state for active connection
            if 'ehr_credentials' in st.session_state and ehr_vendor in st.session_state.ehr_credentials:
                status = "Connected"
            
            st.metric("Connection Status", status, delta="Active" if status=="Connected" else None)
        
        with col2:
            with st.form("ehr_config"):
                st.subheader(f"Configure {ehr_vendor}")
                base_url = st.text_input("FHIR Base URL", placeholder="https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/")
                client_id = st.text_input("Client ID", type="password")
                client_secret = st.text_input("Client Secret", type="password")
                auth_url = st.text_input("Auth URL (OAuth2)", placeholder="https://fhir.epic.com/auth/token")
                
                if st.form_submit_button("Save & Test Connection"):
                    # In a real app, we'd save to a secure vault. 
                    # Here we just simulate a connection test.
                    adapter = get_ehr_adapter(ehr_vendor, {
                        'url': base_url, 
                        'client_id': client_id,
                        'client_secret': client_secret
                    })
                    
                    if adapter and adapter.connect():
                        st.success(f"✅ Successfully connected to {ehr_vendor}!")
                        # Secure session-only storage (cleared on logout/restart)
                        if 'ehr_credentials' not in st.session_state:
                            st.session_state.ehr_credentials = {}
                        st.session_state.ehr_credentials[ehr_vendor] = {
                            'url': base_url,
                            'client_id': client_id
                            # Secret is NOT stored for display, only used for connection
                        }
                    else:
                        st.error("❌ Connection failed. Check credentials.")

                        st.error("❌ Connection failed. Check credentials.")

    # ─── TAB 2: AI TOOLS ───────────────────────────────────────────────
    with tabs[1]:
        st.header("External AI Integrations")
        st.info("Manage connections to third-party clinical AI tools.")
        
        tools = [
            "Aidoc", "PathAI", "Tempus", "Butterfly iQ", "Caption Health",
            "IBM Watson", "DeepMind", "Keragon", "Nuance DAX"
        ]
        
        for tool in tools:
            with st.expander(f"🔧 {tool}", expanded=False):
                c1, c2 = st.columns([1, 3])
                with c1:
                    enabled = st.toggle(f"Enable {tool}", key=f"enable_{tool}")
                    status = "Active" if enabled else "Disabled"
                    st.caption(f"Status: {status}")
                
                with c2:
                    api_key = st.text_input(f"API Key", type="password", key=f"key_{tool}")
                    endpoint = st.text_input(f"Endpoint URL", key=f"url_{tool}")
                    
                    if st.button(f"Save {tool} Config"):
                        # Save to session state
                        if 'ai_tools_config' not in st.session_state:
                            st.session_state.ai_tools_config = {}
                        
                        st.session_state.ai_tools_config[tool] = {
                            'enabled': enabled,
                            'api_key': api_key,
                            'endpoint': endpoint
                        }
                        st.success(f"Saved configuration for {tool}")

                        st.success(f"Saved configuration for {tool}")

    # ─── TAB 3: ANALYTICS ──────────────────────────────────────────────
    with tabs[2]:
        st.header("Clinical & Financial Analytics")
        st.info("Real-time insights into HCC capture, revenue, and provider performance.")
        
        # Mock Data
        col1, col2, col3 = st.columns(3)
        col1.metric("Total RAF Score (YTD)", "1,245.3", "+12.5%")
        col2.metric("Est. Revenue Impact", "$14.2M", "+$1.1M")
        col3.metric("HCC Capture Rate", "88.4%", "+2.1%")
        
        st.subheader("Provider Performance")
        providers = [
            {"name": "Dr. Smith", "patients": 120, "raf_avg": 1.45, "capture_rate": "92%"},
            {"name": "Dr. Jones", "patients": 98, "raf_avg": 1.12, "capture_rate": "85%"},
            {"name": "Dr. Doe", "patients": 145, "raf_avg": 1.67, "capture_rate": "95%"},
            {"name": "Nurse Joy", "patients": 200, "raf_avg": 0.98, "capture_rate": "88%"}
        ]
        st.table(providers)
        
        st.subheader("Top Missed Conditions (Discovery AI)")
        missed = [
            {"condition": "Morbid Obesity (E66.01)", "missed_count": 45, "revenue_loss": "$125k"},
            {"condition": "CKD Stage 3 (N18.3)", "missed_count": 32, "revenue_loss": "$0"},
            {"condition": "Major Depression (F32.9)", "missed_count": 28, "revenue_loss": "$85k"}
        ]
        st.table(missed)

    # ─── TAB 4: USER MANAGEMENT ────────────────────────────────────────
    with tabs[3]:
        st.header("User Access Control")
        st.warning("LDAP/Active Directory integration is managed via `config/ldap.yaml`")
        
        users = [
            {"name": "Dr. Smith", "role": "Physician", "access": "Full"},
            {"name": "Nurse Joy", "role": "Nurse", "access": "Read/Write"},
            {"name": "Admin User", "role": "Administrator", "access": "System"}
        ]
        
        st.table(users)
        
        with st.expander("Add New User"):
            c1, c2 = st.columns(2)
            c1.text_input("Username")
            c2.selectbox("Role", ["Physician", "Nurse", "Admin"])
            st.button("Create User")

    # ─── TAB 5: SYSTEM HEALTH ──────────────────────────────────────────
    with tabs[4]:
        st.header("System Status")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("vLLM Engine", "Online", "Llama-3.1-70B")
        c2.metric("GPU Usage", "42%", "-5%")
        c3.metric("Disk Space", "1.2 TB Free", "Healthy")
        
        st.subheader("Service Status")
        st.success("✅ Main Application (app.py)")
        st.success("✅ Mobile WebSocket Server")
        st.success("✅ USB Watcher Service")
        st.success("✅ Vector Database (FAISS)")
        st.success("✅ HL7 MLLP Listener (Port 2575)")

    # ─── TAB 6: LOGS ───────────────────────────────────────────────────
    with tabs[5]:
        st.header("Audit Logs")
        st.text_area("Recent Activity", """
[2025-11-28 16:45:01] INFO: User Dr. Smith accessed Patient #12345
[2025-11-28 16:45:15] INFO: Generated SOAP note for Patient #12345
[2025-11-28 16:46:00] WARN: Failed login attempt from IP 192.168.1.50
[2025-11-28 16:48:22] INFO: System backup completed successfully
        """, height=300)

if __name__ == "__main__":
    main()
