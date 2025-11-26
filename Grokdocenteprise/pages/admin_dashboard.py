"""
Admin Dashboard for Grok Doc v2.5

Hospital administrators can:
- View and toggle AI tool integrations
- View credential status
- View EHR connection status
- View feature flag status
- Display audit log statistics
"""

import streamlit as st
import json
import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.credentials import CredentialManager, get_credential_manager
from src.config.hospital_config import HospitalConfig, load_hospital_config

st.set_page_config(
    page_title="Admin Dashboard - Grok Doc v2.5",
    page_icon="⚙️",
    layout="wide"
)

CONFIG_PATH = "config/hospital_config.json"
AUDIT_DB_PATH = "audit.db"


def load_config() -> dict:
    """Load hospital configuration from JSON file."""
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"Configuration file not found: {CONFIG_PATH}")
        return {}
    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON in configuration file: {e}")
        return {}


def save_config(config: dict) -> bool:
    """Save hospital configuration to JSON file."""
    try:
        config['updated_at'] = datetime.utcnow().isoformat() + "Z"
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Failed to save configuration: {e}")
        return False


def get_audit_statistics() -> dict:
    """Get audit log statistics from the database."""
    stats = {
        "total_decisions": 0,
        "total_fallbacks": 0,
        "total_security_violations": 0,
        "decisions_by_mode": {},
        "decisions_by_model": {},
        "recent_decisions": 0,
        "chain_integrity": None
    }
    
    if not os.path.exists(AUDIT_DB_PATH):
        return stats
    
    try:
        conn = sqlite3.connect(AUDIT_DB_PATH)
        
        cursor = conn.execute("SELECT COUNT(*) FROM decisions")
        stats["total_decisions"] = cursor.fetchone()[0]
        
        cursor = conn.execute(
            "SELECT COUNT(*) FROM decisions WHERE timestamp > datetime('now', '-24 hours')"
        )
        stats["recent_decisions"] = cursor.fetchone()[0]
        
        cursor = conn.execute(
            "SELECT analysis_mode, COUNT(*) FROM decisions GROUP BY analysis_mode"
        )
        stats["decisions_by_mode"] = {row[0] or "unknown": row[1] for row in cursor.fetchall()}
        
        cursor = conn.execute(
            "SELECT model_name, COUNT(*) FROM decisions GROUP BY model_name"
        )
        stats["decisions_by_model"] = {row[0] or "unknown": row[1] for row in cursor.fetchall()}
        
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM fallback_events")
            stats["total_fallbacks"] = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM security_violations")
            stats["total_security_violations"] = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            pass
        
        conn.close()
        
        try:
            from audit_log import verify_audit_integrity
            stats["chain_integrity"] = verify_audit_integrity()
        except ImportError:
            pass
            
    except Exception as e:
        st.warning(f"Could not read audit database: {e}")
    
    return stats


def status_indicator(is_enabled: bool, label: str = "") -> str:
    """Return a status indicator with checkmark or x."""
    if is_enabled:
        return f"✅ {label}" if label else "✅"
    return f"❌ {label}" if label else "❌"


def credential_indicator(is_set: bool) -> str:
    """Return credential status indicator."""
    return "🔑 Configured" if is_set else "⚠️ Not Set"


with st.sidebar:
    st.title("⚙️ Admin Dashboard")
    st.caption("Grok Doc v2.5 Configuration")
    
    st.divider()
    
    nav_selection = st.radio(
        "Navigate to:",
        options=[
            "🔌 AI Integrations",
            "🔐 Credentials",
            "🏥 EHR Status",
            "🚩 Feature Flags",
            "📊 Audit Statistics"
        ],
        label_visibility="collapsed"
    )
    
    st.divider()
    
    config = load_config()
    if config:
        st.caption(f"**Hospital:** {config.get('hospital_name', 'Unknown')}")
        st.caption(f"**ID:** {config.get('hospital_id', 'Unknown')}")
        st.caption(f"**Updated:** {config.get('updated_at', 'Never')[:10]}")

st.title("🏥 Grok Doc v2.5 Admin Dashboard")

config = load_config()
if not config:
    st.error("Failed to load configuration. Please check the config file.")
    st.stop()

cred_manager = get_credential_manager()

if "🔌 AI Integrations" in nav_selection:
    st.header("🔌 AI Tool Integrations")
    st.caption("Enable or disable AI tool adapters for this hospital.")
    
    ai_tools = config.get('ai_tools', {})
    
    adapter_display_names = {
        'aidoc': 'Aidoc (Radiology AI)',
        'pathAI': 'PathAI (Pathology)',
        'tempus': 'Tempus (Genomics/Oncology)',
        'butterfly_iq': 'Butterfly iQ (Ultrasound)',
        'caption_health': 'Caption Health (Cardiac)',
        'ibm_watson': 'IBM Watson Health',
        'deepmind_health': 'DeepMind Health',
        'keragon': 'Keragon (Workflow)',
        'nuance_dax': 'Nuance DAX (Ambient Scribe)'
    }
    
    adapter_creds = {
        'aidoc': 'AIDOC_API_KEY',
        'pathAI': 'PATHOLOGY_API_KEY',
        'tempus': 'TEMPUS_API_KEY',
        'butterfly_iq': 'BUTTERFLY_API_KEY',
        'caption_health': 'CAPTION_HEALTH_API_KEY',
        'ibm_watson': 'IBM_WATSON_API_KEY',
        'deepmind_health': 'DEEPMIND_API_KEY',
        'keragon': 'KERAGON_API_KEY',
        'nuance_dax': 'NUANCE_DAX_API_KEY'
    }
    
    col1, col2 = st.columns(2)
    
    changes_made = False
    adapters_list = list(adapter_display_names.items())
    mid = len(adapters_list) // 2 + len(adapters_list) % 2
    
    with col1:
        for adapter_key, display_name in adapters_list[:mid]:
            adapter_config = ai_tools.get(adapter_key, {})
            is_enabled = adapter_config.get('enabled', False)
            has_credential = cred_manager.is_set(adapter_creds.get(adapter_key, ''))
            
            with st.container():
                col_toggle, col_status = st.columns([3, 1])
                with col_toggle:
                    new_state = st.toggle(
                        display_name,
                        value=is_enabled,
                        key=f"toggle_{adapter_key}"
                    )
                with col_status:
                    if has_credential:
                        st.markdown("🔑")
                    else:
                        st.markdown("⚠️")
                
                if new_state != is_enabled:
                    if adapter_key not in config['ai_tools']:
                        config['ai_tools'][adapter_key] = {}
                    config['ai_tools'][adapter_key]['enabled'] = new_state
                    changes_made = True
    
    with col2:
        for adapter_key, display_name in adapters_list[mid:]:
            adapter_config = ai_tools.get(adapter_key, {})
            is_enabled = adapter_config.get('enabled', False)
            has_credential = cred_manager.is_set(adapter_creds.get(adapter_key, ''))
            
            with st.container():
                col_toggle, col_status = st.columns([3, 1])
                with col_toggle:
                    new_state = st.toggle(
                        display_name,
                        value=is_enabled,
                        key=f"toggle_{adapter_key}"
                    )
                with col_status:
                    if has_credential:
                        st.markdown("🔑")
                    else:
                        st.markdown("⚠️")
                
                if new_state != is_enabled:
                    if adapter_key not in config['ai_tools']:
                        config['ai_tools'][adapter_key] = {}
                    config['ai_tools'][adapter_key]['enabled'] = new_state
                    changes_made = True
    
    if changes_made:
        if save_config(config):
            st.success("✅ Configuration saved successfully!")
            st.rerun()
    
    st.divider()
    st.caption("🔑 = API key configured | ⚠️ = API key not set")
    
    enabled_count = sum(1 for a in ai_tools.values() if a.get('enabled', False))
    st.info(f"**{enabled_count}** of **{len(adapter_display_names)}** integrations enabled")

elif "🔐 Credentials" in nav_selection:
    st.header("🔐 Credential Status")
    st.caption("Overview of configured API keys and secrets.")
    
    statuses = cred_manager.get_status()
    
    st.subheader("Required Credentials")
    required_creds = [s for s in statuses if s.required]
    
    for cred in required_creds:
        col1, col2, col3 = st.columns([2, 1, 3])
        with col1:
            st.markdown(f"**{cred.name}**")
        with col2:
            if cred.is_set:
                st.markdown("✅ Set")
            else:
                st.markdown("❌ Missing")
        with col3:
            st.caption(cred.description)
    
    st.divider()
    
    st.subheader("Optional Credentials (AI Adapters)")
    optional_creds = [s for s in statuses if not s.required]
    
    col1, col2 = st.columns(2)
    mid = len(optional_creds) // 2 + len(optional_creds) % 2
    
    with col1:
        for cred in optional_creds[:mid]:
            status_icon = "✅" if cred.is_set else "⬜"
            st.markdown(f"{status_icon} **{cred.name}**")
            if cred.is_set:
                st.caption(f"   {cred.description}")
    
    with col2:
        for cred in optional_creds[mid:]:
            status_icon = "✅" if cred.is_set else "⬜"
            st.markdown(f"{status_icon} **{cred.name}**")
            if cred.is_set:
                st.caption(f"   {cred.description}")
    
    st.divider()
    
    st.subheader("Grok HIPAA Status")
    grok_status = cred_manager.validate_grok_for_hipaa()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("API Key", "✅ Set" if grok_status['api_key_set'] else "❌ Not Set")
    with col2:
        st.metric("BAA Confirmed", "✅ Yes" if grok_status['baa_confirmed'] else "❌ No")
    with col3:
        st.metric("HIPAA Ready", "✅ Yes" if grok_status['hipaa_compliant'] else "❌ No")
    
    if grok_status['hipaa_compliant']:
        st.success(grok_status['message'])
    else:
        st.warning(grok_status['message'])
    
    configured_adapters = cred_manager.get_configured_adapters()
    st.divider()
    st.info(f"**{len(configured_adapters)}** adapters have credentials configured: {', '.join(configured_adapters) if configured_adapters else 'None'}")

elif "🏥 EHR Status" in nav_selection:
    st.header("🏥 EHR Connection Status")
    st.caption("Electronic Health Record system configuration.")
    
    ehr_config = config.get('ehr', {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Connection Details")
        
        ehr_type = ehr_config.get('type', 'unknown').upper()
        st.markdown(f"**EHR System:** {ehr_type}")
        
        fhir_endpoint = ehr_config.get('fhir_endpoint', '')
        if fhir_endpoint:
            st.markdown(f"**FHIR Endpoint:** `{fhir_endpoint[:50]}...`" if len(fhir_endpoint) > 50 else f"**FHIR Endpoint:** `{fhir_endpoint}`")
        else:
            st.markdown("**FHIR Endpoint:** ⚠️ Not configured")
        
        client_id = ehr_config.get('client_id', '')
        st.markdown(f"**Client ID:** {'✅ Set' if client_id else '❌ Not Set'}")
        
        secret_env = ehr_config.get('client_secret_env', '')
        has_secret = cred_manager.is_set(secret_env) if secret_env else False
        st.markdown(f"**Client Secret:** {'✅ Configured' if has_secret else '❌ Not Set'}")
    
    with col2:
        st.subheader("Capabilities")
        
        st.markdown(status_indicator(bool(ehr_config.get('supports_bulk_export')), "Bulk Export"))
        st.markdown(status_indicator(bool(ehr_config.get('hl7v2_enabled')), "HL7v2 Integration"))
        
        if ehr_config.get('hl7v2_enabled'):
            st.caption(f"   Port: {ehr_config.get('hl7v2_port', 2575)}")
        
        oauth_url = ehr_config.get('oauth_token_url', '')
        st.markdown(status_indicator(bool(oauth_url), "OAuth Configured"))
    
    st.divider()
    
    st.subheader("FHIR Scopes")
    scopes = ehr_config.get('scopes', [])
    if scopes:
        cols = st.columns(4)
        for i, scope in enumerate(scopes):
            with cols[i % 4]:
                st.code(scope, language=None)
    else:
        st.warning("No FHIR scopes configured")
    
    st.divider()
    
    ehr_cred_valid = cred_manager.validate_ehr_credentials(ehr_config.get('type', ''))
    if ehr_cred_valid:
        st.success(f"✅ {ehr_type} credentials are properly configured")
    else:
        st.error(f"❌ {ehr_type} credentials are missing or incomplete")

elif "🚩 Feature Flags" in nav_selection:
    st.header("🚩 Feature Flags")
    st.caption("Enable or disable system features.")
    
    features = config.get('features', {})
    
    feature_display_names = {
        'ambient_scribe': ('🎙️ Ambient Scribe', 'AI-powered voice documentation'),
        'patient_messaging': ('💬 Patient Messaging', 'Secure patient communication'),
        'discharge_summaries': ('📋 Discharge Summaries', 'Automated discharge documentation'),
        'risk_prediction': ('⚠️ Risk Prediction', 'Clinical risk scoring'),
        'cds_hooks': ('🔗 CDS Hooks', 'Clinical Decision Support integration'),
        'multi_llm_chain': ('🔗 Multi-LLM Chain', 'Multi-model reasoning (v2.0)'),
        'bayesian_analysis': ('📊 Bayesian Analysis', 'Statistical safety assessment'),
        'continuous_learning': ('🧠 Continuous Learning', 'Adaptive model improvement'),
        'mobile_copilot': ('📱 Mobile Co-Pilot', 'Mobile device support')
    }
    
    col1, col2 = st.columns(2)
    
    changes_made = False
    features_list = list(feature_display_names.items())
    mid = len(features_list) // 2 + len(features_list) % 2
    
    with col1:
        for feature_key, (display_name, description) in features_list[:mid]:
            is_enabled = features.get(feature_key, False)
            
            new_state = st.toggle(
                display_name,
                value=is_enabled,
                key=f"feature_{feature_key}",
                help=description
            )
            
            if new_state != is_enabled:
                config['features'][feature_key] = new_state
                changes_made = True
    
    with col2:
        for feature_key, (display_name, description) in features_list[mid:]:
            is_enabled = features.get(feature_key, False)
            
            new_state = st.toggle(
                display_name,
                value=is_enabled,
                key=f"feature_{feature_key}",
                help=description
            )
            
            if new_state != is_enabled:
                config['features'][feature_key] = new_state
                changes_made = True
    
    if changes_made:
        if save_config(config):
            st.success("✅ Feature flags updated!")
            st.rerun()
    
    st.divider()
    
    enabled_count = sum(1 for v in features.values() if v)
    st.info(f"**{enabled_count}** of **{len(feature_display_names)}** features enabled")
    
    st.divider()
    st.subheader("Compliance Settings")
    
    compliance = config.get('compliance', {})
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Audit Retention:** {compliance.get('audit_retention_days', 2555)} days")
        st.markdown(status_indicator(compliance.get('require_wifi_check', True), "WiFi Check Required"))
        st.markdown(status_indicator(compliance.get('ssl_cert_pinning', False), "SSL Cert Pinning"))
    
    with col2:
        subnets = compliance.get('network_subnets', [])
        st.markdown(f"**Allowed Subnets:** {len(subnets)}")
        for subnet in subnets[:3]:
            st.caption(f"   • {subnet}")
        if len(subnets) > 3:
            st.caption(f"   ... and {len(subnets) - 3} more")

elif "📊 Audit Statistics" in nav_selection:
    st.header("📊 Audit Log Statistics")
    st.caption("Overview of system audit trail and activity.")
    
    stats = get_audit_statistics()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Decisions", stats["total_decisions"])
    with col2:
        st.metric("Last 24 Hours", stats["recent_decisions"])
    with col3:
        st.metric("Fallback Events", stats["total_fallbacks"])
    with col4:
        st.metric("Security Violations", stats["total_security_violations"])
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Decisions by Analysis Mode")
        if stats["decisions_by_mode"]:
            for mode, count in stats["decisions_by_mode"].items():
                pct = (count / stats["total_decisions"] * 100) if stats["total_decisions"] > 0 else 0
                st.markdown(f"**{mode or 'Unknown'}:** {count} ({pct:.1f}%)")
                st.progress(pct / 100)
        else:
            st.info("No decision data available")
    
    with col2:
        st.subheader("Decisions by Model")
        if stats["decisions_by_model"]:
            for model, count in stats["decisions_by_model"].items():
                pct = (count / stats["total_decisions"] * 100) if stats["total_decisions"] > 0 else 0
                st.markdown(f"**{model or 'Unknown'}:** {count} ({pct:.1f}%)")
                st.progress(pct / 100)
        else:
            st.info("No model data available")
    
    st.divider()
    
    st.subheader("Chain Integrity")
    if stats["chain_integrity"]:
        integrity = stats["chain_integrity"]
        if integrity.get("valid"):
            st.success(f"✅ Audit chain verified - {integrity.get('entries', 0)} entries intact")
        else:
            st.error(f"❌ Chain integrity violation detected at entry {integrity.get('tampered_index')}")
            if integrity.get("error"):
                st.error(f"Error: {integrity['error']}")
    else:
        st.info("No audit data to verify")
    
    st.divider()
    
    if st.button("🔄 Refresh Statistics"):
        st.rerun()
    
    llm_config = config.get('llm', {})
    st.divider()
    st.subheader("LLM Configuration")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Default Model:** {llm_config.get('default_model', 'Not set')}")
        st.markdown(f"**Fallback Model:** {llm_config.get('fallback_model', 'Not set')}")
        st.markdown(status_indicator(llm_config.get('grok_enabled', False), "Grok Enabled"))
    with col2:
        st.markdown(f"**Temperature:** {llm_config.get('temperature', 0.0)}")
        st.markdown(f"**Max Tokens:** {llm_config.get('max_tokens', 2048)}")
        st.markdown(status_indicator(llm_config.get('grok_has_baa', False), "Grok BAA Signed"))

st.divider()
st.caption(f"Grok Doc v2.5 Admin Dashboard | Hospital: {config.get('hospital_name', 'Unknown')} | Config last updated: {config.get('updated_at', 'Unknown')}")
