import streamlit as st
from peer_review import PeerReviewSystem
import json

st.set_page_config(page_title="Peer Review Dashboard", page_icon="🩺", layout="wide")

def main():
    st.title("🩺 Clinical Peer Review Dashboard")
    
    # Initialize system (mock singleton)
    if 'peer_review_system' not in st.session_state:
        st.session_state.peer_review_system = PeerReviewSystem()
        # Add some mock data
        st.session_state.peer_review_system.submit_for_review({
            'mrn': 'MRN-998877',
            'chief_complaint': 'Chest pain, troponin negative',
            'ai_recommendation': 'Discharge with outpatient follow-up',
            'specialty': 'Cardiology'
        }, priority="Normal")
        st.session_state.peer_review_system.submit_for_review({
            'mrn': 'MRN-112233',
            'chief_complaint': 'Sepsis alert, lactate 4.2',
            'ai_recommendation': 'Start broad spectrum antibiotics immediately',
            'specialty': 'Critical Care'
        }, priority="High")

    system = st.session_state.peer_review_system
    
    # Sidebar filters
    st.sidebar.header("Filters")
    specialty_filter = st.sidebar.selectbox("Specialty", ["All", "Cardiology", "Critical Care", "Neurology"])
    
    # Main Queue
    st.subheader("Pending Reviews")
    
    queue = system.get_queue(None if specialty_filter == "All" else specialty_filter)
    
    if not queue:
        st.info("No pending cases for review.")
    else:
        for case in queue:
            with st.expander(f"{'🔴' if case['priority']=='High' else '🟡'} {case['data']['mrn']} - {case['data']['chief_complaint']}", expanded=True):
                c1, c2 = st.columns([2, 1])
                
                with c1:
                    st.markdown("**AI Recommendation:**")
                    st.info(case['data']['ai_recommendation'])
                    st.json(case['data'])
                
                with c2:
                    st.markdown("**Action**")
                    reviewer = st.text_input("Reviewer Name", key=f"rev_{case['id']}")
                    comment = st.text_area("Comments", key=f"com_{case['id']}")
                    
                    b1, b2 = st.columns(2)
                    if b1.button("✅ Approve", key=f"app_{case['id']}"):
                        if reviewer:
                            system.approve_case(case['id'], reviewer, comment)
                            st.success("Case Approved!")
                            st.rerun()
                        else:
                            st.error("Reviewer name required")
                            
                    if b2.button("❌ Reject", key=f"rej_{case['id']}"):
                        if reviewer and comment:
                            system.reject_case(case['id'], reviewer, comment)
                            st.warning("Case Rejected!")
                            st.rerun()
                        else:
                            st.error("Name and reason required for rejection")

    st.divider()
    
    # History
    st.subheader("Review History")
    stats = system.get_stats()
    c1, c2, c3 = st.columns(3)
    c1.metric("Pending", stats['pending'])
    c2.metric("Approved", stats['approved'])
    c3.metric("Rejected", stats['rejected'])
    
    if system.history:
        st.dataframe(system.history)

if __name__ == "__main__":
    main()
