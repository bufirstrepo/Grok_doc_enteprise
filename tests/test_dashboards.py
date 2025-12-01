import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ui.dashboards import render_doctor_dashboard, render_admin_dashboard, render_researcher_dashboard

class TestDashboards(unittest.TestCase):
    @patch('streamlit.header')
    @patch('streamlit.info')
    def test_doctor_dashboard(self, mock_info, mock_header):
        """Verify doctor dashboard renders banner"""
        mock_config = MagicMock()
        mock_predictor = MagicMock()
        mock_prediction = MagicMock()
        mock_prediction.patient_name_masked = "P. X."
        mock_prediction.patient_id = "PAT-123"
        mock_prediction.reason = "Test Reason"
        mock_prediction.urgency = "Routine"
        
        mock_predictor.predict_next_consult.return_value = mock_prediction
        
        # Mock streamlit input widgets to avoid errors
        with patch('streamlit.text_input'), \
             patch('streamlit.number_input'), \
             patch('streamlit.selectbox'), \
             patch('streamlit.text_area'), \
             patch('streamlit.columns', return_value=(MagicMock(), MagicMock())):
            
            render_doctor_dashboard(mock_config, mock_predictor, "doctor_user")
            
        mock_header.assert_called_with("🩺 Doctor Dashboard")
        # Verify banner info was called
        self.assertTrue(mock_info.called)

    @patch('streamlit.header')
    def test_admin_dashboard(self, mock_header):
        """Verify admin dashboard renders"""
        with patch('streamlit.columns', return_value=(MagicMock(), MagicMock(), MagicMock())), \
             patch('streamlit.metric'):
            render_admin_dashboard()
        
        mock_header.assert_called_with("🛡️ Admin Dashboard")

    @patch('streamlit.header')
    def test_researcher_dashboard(self, mock_header):
        """Verify researcher dashboard renders"""
        mock_config = MagicMock()
        with patch('streamlit.tabs', return_value=(MagicMock(), MagicMock(), MagicMock())), \
             patch('streamlit.bar_chart'):
            render_researcher_dashboard(mock_config)
            
        mock_header.assert_called_with("🔬 Researcher Dashboard")

if __name__ == '__main__':
    unittest.main()
