#!/usr/bin/env python3
"""
Epic EHR RPA Automation for Grok Doc v2.0
Auto-populate SOAP notes from AI-generated clinical documentation

Supports:
- Epic Hyperspace (web interface) via Playwright
- Epic thick client via pyautogui
- Automatic SOAP note parsing and field population
- Physician review workflow before saving
- Complete audit trail logging
"""

import time
from typing import Dict, Optional
from datetime import datetime
import json
import re

# Playwright for web automation
try:
    from playwright.sync_api import sync_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("WARNING: Playwright not installed. Run: pip install playwright && playwright install")

# pyautogui for desktop automation (Epic thick client)
try:
    import pyautogui
    pyautogui.PAUSE = 0.5  # 500ms between actions for safety
    pyautogui.FAILSAFE = True  # Move mouse to corner to abort
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    print("WARNING: pyautogui not installed. Run: pip install pyautogui")

from audit_log import log_decision


class SOAPNoteParser:
    """Parse AI-generated SOAP note into structured sections"""

    @staticmethod
    def parse(soap_text: str) -> Dict[str, str]:
        """
        Extract SOAP sections from formatted text

        Args:
            soap_text: Complete SOAP note with section headers

        Returns:
            {
                'subjective': str,
                'objective': str,
                'assessment': str,
                'plan': str,
                'billing_code': str (optional)
            }
        """

        sections = {
            'subjective': '',
            'objective': '',
            'assessment': '',
            'plan': '',
            'billing_code': ''
        }

        # Extract SUBJECTIVE
        subj_match = re.search(r'SUBJECTIVE:?\s*(.*?)(?=OBJECTIVE:|$)', soap_text, re.DOTALL | re.IGNORECASE)
        if subj_match:
            sections['subjective'] = subj_match.group(1).strip()

        # Extract OBJECTIVE
        obj_match = re.search(r'OBJECTIVE:?\s*(.*?)(?=ASSESSMENT:|$)', soap_text, re.DOTALL | re.IGNORECASE)
        if obj_match:
            sections['objective'] = obj_match.group(1).strip()

        # Extract ASSESSMENT
        assess_match = re.search(r'ASSESSMENT:?\s*(.*?)(?=PLAN:|$)', soap_text, re.DOTALL | re.IGNORECASE)
        if assess_match:
            sections['assessment'] = assess_match.group(1).strip()

        # Extract PLAN
        plan_match = re.search(r'PLAN:?\s*(.*?)(?=EVIDENCE CITATIONS:|BILLING/COMPLIANCE:|$)', soap_text, re.DOTALL | re.IGNORECASE)
        if plan_match:
            sections['plan'] = plan_match.group(1).strip()

        # Extract billing code
        billing_match = re.search(r'Suggested CPT:\s*(\d+)', soap_text)
        if billing_match:
            sections['billing_code'] = billing_match.group(1)

        return sections


class EpicWebAutomation:
    """
    Epic Hyperspace (web interface) automation using Playwright

    Supports:
    - Patient search by MRN
    - Opening new note templates
    - Filling SOAP sections
    - Physician review workflow
    - Saving to EHR
    """

    def __init__(self, epic_url: str = "https://epic.hospital.local"):
        """
        Initialize Epic web automation

        Args:
            epic_url: Base URL for Epic Hyperspace
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright required. Install with: pip install playwright")

        self.epic_url = epic_url
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    def __enter__(self):
        """Context manager: launch browser"""
        playwright = sync_playwright().start()
        self.browser = playwright.chromium.launch(
            headless=False,  # Show browser for physician review
            args=['--start-maximized']
        )
        self.page = self.browser.new_page()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager: close browser"""
        if self.browser:
            self.browser.close()

    def login(self, username: Optional[str] = None, password: Optional[str] = None):
        """
        Login to Epic (uses Windows SSO if no credentials provided)

        Args:
            username: Optional username (if not using SSO)
            password: Optional password (if not using SSO)
        """
        self.page.goto(self.epic_url)

        if username and password:
            # Manual login (not recommended - use SSO)
            self.page.fill('#username', username)
            self.page.fill('#password', password)
            self.page.click('#login_button')
        else:
            # Wait for Windows SSO to complete
            print("Waiting for Windows SSO authentication...")
            self.page.wait_for_url(f"{self.epic_url}/dashboard", timeout=60000)

        print("Epic login successful")

    def search_patient(self, mrn: str):
        """
        Search for patient by MRN

        Args:
            mrn: Medical Record Number
        """
        # Navigate to patient search
        self.page.click('text=Search')
        self.page.fill('#mrn_input', mrn)
        self.page.press('#mrn_input', 'Enter')

        # Wait for patient chart to load
        self.page.wait_for_selector('.patient-header', timeout=10000)
        print(f"Patient {mrn} loaded")

    def open_new_note(self, note_template: str = "Progress Note"):
        """
        Open new clinical note template

        Args:
            note_template: Note template name (Progress Note, H&P, Consult, etc.)
        """
        # Click "New Note" button
        self.page.click('text=New Note')

        # Wait for template selector
        self.page.wait_for_selector('.note-templates')

        # Select template
        self.page.click(f'text={note_template}')

        # Wait for note editor to load
        self.page.wait_for_selector('.note-editor')
        print(f"Opened {note_template} template")

    def fill_soap_note(self, soap_sections: Dict[str, str]):
        """
        Fill SOAP note sections into Epic note template

        Args:
            soap_sections: Dict with subjective, objective, assessment, plan
        """

        # Subjective
        if soap_sections.get('subjective'):
            self.page.click('#subjective_section')
            self.page.fill('#subjective_text', soap_sections['subjective'])
            print("Filled Subjective section")

        # Objective
        if soap_sections.get('objective'):
            self.page.click('#objective_section')
            self.page.fill('#objective_text', soap_sections['objective'])
            print("Filled Objective section")

        # Assessment
        if soap_sections.get('assessment'):
            self.page.click('#assessment_section')
            self.page.fill('#assessment_text', soap_sections['assessment'])
            print("Filled Assessment section")

        # Plan
        if soap_sections.get('plan'):
            self.page.click('#plan_section')
            self.page.fill('#plan_text', soap_sections['plan'])
            print("Filled Plan section")

        # Billing code (if available)
        if soap_sections.get('billing_code'):
            self.page.click('#billing_section')
            self.page.fill('#cpt_code', soap_sections['billing_code'])
            print(f"Set billing code: {soap_sections['billing_code']}")

    def physician_review(self) -> bool:
        """
        Pause for physician to review note

        Returns:
            True if physician approves, False if rejected
        """
        print("\n" + "="*60)
        print("PHYSICIAN REVIEW REQUIRED")
        print("Please review the AI-generated note in Epic.")
        print("Make any necessary edits, then:")
        print("  - Press ENTER to approve and save")
        print("  - Type 'reject' to discard")
        print("="*60)

        response = input("Approve note? [ENTER/reject]: ").strip().lower()

        if response in ['reject', 'r', 'n', 'no']:
            print("Note rejected by physician")
            return False

        print("Note approved by physician")
        return True

    def save_note(self):
        """Save note to EHR"""
        self.page.click('#save_note_button')
        self.page.wait_for_selector('.save_confirmation', timeout=5000)
        print("Note saved to Epic")

    def discard_note(self):
        """Discard note without saving"""
        self.page.click('#discard_note_button')
        print("Note discarded")


class EpicDesktopAutomation:
    """
    Epic thick client automation using pyautogui

    For hospitals using Epic client application (not web)
    """

    def __init__(self):
        """Initialize desktop automation"""
        if not PYAUTOGUI_AVAILABLE:
            raise ImportError("pyautogui required. Install with: pip install pyautogui")

    def find_epic_window(self) -> bool:
        """Locate Epic application window"""
        # Platform-specific window detection
        # On Windows: uses pygetwindow
        try:
            import pygetwindow as gw
            epic_windows = gw.getWindowsWithTitle('Epic')
            if epic_windows:
                epic_windows[0].activate()
                return True
        except ImportError:
            print("pygetwindow not installed. Manual window focus required.")

        return False

    def fill_soap_note_desktop(self, soap_sections: Dict[str, str]):
        """
        Fill SOAP note using keyboard automation

        CAUTION: This is fragile and depends on Epic UI layout
        """

        # Ensure Epic is focused
        if not self.find_epic_window():
            print("Please manually focus Epic window, then press ENTER")
            input()

        # Tab to Subjective field (number of tabs depends on Epic config)
        pyautogui.press('tab', presses=3)
        time.sleep(0.5)

        # Type Subjective
        pyautogui.write(soap_sections.get('subjective', ''), interval=0.01)

        # Tab to Objective
        pyautogui.press('tab', presses=2)
        time.sleep(0.5)
        pyautogui.write(soap_sections.get('objective', ''), interval=0.01)

        # Tab to Assessment
        pyautogui.press('tab', presses=2)
        time.sleep(0.5)
        pyautogui.write(soap_sections.get('assessment', ''), interval=0.01)

        # Tab to Plan
        pyautogui.press('tab', presses=2)
        time.sleep(0.5)
        pyautogui.write(soap_sections.get('plan', ''), interval=0.01)

        print("SOAP note filled via desktop automation")


def populate_epic_note(
    soap_text: str,
    mrn: str,
    physician_id: str,
    use_web: bool = True,
    epic_url: str = "https://epic.hospital.local"
) -> bool:
    """
    Main entry point for Epic note population

    Args:
        soap_text: AI-generated SOAP note
        mrn: Medical Record Number
        physician_id: Physician identifier
        use_web: True for web (Playwright), False for desktop (pyautogui)
        epic_url: Epic Hyperspace URL (if use_web=True)

    Returns:
        True if note saved successfully, False otherwise
    """

    # Parse SOAP note
    parser = SOAPNoteParser()
    soap_sections = parser.parse(soap_text)

    if use_web:
        # Web automation (Playwright)
        with EpicWebAutomation(epic_url) as epic:
            try:
                # Login (using Windows SSO)
                epic.login()

                # Search patient
                epic.search_patient(mrn)

                # Open note template
                epic.open_new_note("Progress Note")

                # Fill SOAP sections
                epic.fill_soap_note(soap_sections)

                # Physician review
                if epic.physician_review():
                    epic.save_note()

                    # Log to audit trail
                    log_decision(
                        mrn=mrn,
                        patient_context={'mrn': mrn},
                        doctor=physician_id,
                        question="SOAP note auto-population",
                        labs='',
                        answer=soap_text,
                        bayesian_prob=1.0,  # RPA doesn't use Bayesian
                        latency=0,
                        analysis_mode='rpa'
                    )

                    return True
                else:
                    epic.discard_note()
                    return False

            except Exception as e:
                print(f"Error during Epic automation: {e}")
                return False

    else:
        # Desktop automation (pyautogui)
        desktop = EpicDesktopAutomation()

        try:
            desktop.fill_soap_note_desktop(soap_sections)

            # Manual review
            print("\nPlease review the note in Epic, then save manually.")
            print("Press ENTER when done.")
            input()

            return True

        except Exception as e:
            print(f"Error during desktop automation: {e}")
            return False


if __name__ == "__main__":
    # Test SOAP parsing
    test_soap = """
SUBJECTIVE:
Patient reports headache, 8/10 severity, started 2 hours ago.

OBJECTIVE:
Vitals: BP 145/92, HR 88, Temp 98.6F
Neuro: Alert, oriented x3, no focal deficits

ASSESSMENT:
Migraine with aura

PLAN:
Sumatriptan 100mg PO now
Reassess in 2 hours

BILLING/COMPLIANCE:
Suggested CPT: 99214
    """

    parser = SOAPNoteParser()
    sections = parser.parse(test_soap)

    print("Parsed SOAP sections:")
    print(json.dumps(sections, indent=2))

    print(f"\nPlaywright available: {PLAYWRIGHT_AVAILABLE}")
    print(f"pyautogui available: {PYAUTOGUI_AVAILABLE}")
