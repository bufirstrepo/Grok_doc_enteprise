#!/usr/bin/env python3
"""
Epic EHR Integration Tool for CrewAI
Wraps epic_rpa.py for use by epic_agent
"""

from crewai.tools import BaseTool
from typing import Type, Dict, Any
from pydantic import BaseModel, Field
import sys
import os

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.services.epic_rpa import EpicRPAController


class EpicToolInput(BaseModel):
    """Input schema for Epic EHR automation"""
    action: str = Field(..., description="Action: 'populate_soap', 'retrieve_patient', 'order_lab', 'prescribe_medication'")
    mrn: str = Field(..., description="Medical Record Number")
    data: Dict[str, Any] = Field(default_factory=dict, description="Action-specific data (SOAP note, medication order, etc.)")


class EpicTool(BaseTool):
    """
    Epic EHR Automation using RPA (Robotic Process Automation)

    Automates Epic Hyperspace tasks:
    - Populate SOAP notes from AI-generated text
    - Retrieve patient demographics and history
    - Place lab orders
    - Submit medication orders
    - Generate clinical reports

    Uses Playwright for web automation + pyautogui for desktop client.

    Used by: epic_agent (Epic Integration Agent)
    """

    name: str = "Epic EHR Automation (RPA)"
    description: str = """Automate Epic Hyperspace tasks via RPA. Populate SOAP notes, retrieve patient data,
    order labs, submit prescriptions. Requires Epic login credentials and hospital network access."""
    args_schema: Type[BaseModel] = EpicToolInput

    def _run(self, action: str, mrn: str, data: Dict[str, Any] = None) -> str:
        """
        Execute Epic EHR automation task

        Args:
            action: 'populate_soap', 'retrieve_patient', 'order_lab', 'prescribe_medication'
            mrn: Medical Record Number
            data: Action-specific data

        Returns:
            Execution status report for epic_agent
        """
        if data is None:
            data = {}

        try:
            epic = EpicRPAController()

            if action == 'populate_soap':
                return self._populate_soap(epic, mrn, data)

            elif action == 'retrieve_patient':
                return self._retrieve_patient(epic, mrn)

            elif action == 'order_lab':
                return self._order_lab(epic, mrn, data)

            elif action == 'prescribe_medication':
                return self._prescribe_medication(epic, mrn, data)

            else:
                return f"""=== EPIC RPA ERROR ===
Unknown action: '{action}'

Supported actions:
  - populate_soap (auto-fill SOAP note from AI text)
  - retrieve_patient (get demographics and history)
  - order_lab (place lab orders)
  - prescribe_medication (submit prescription orders)
"""

        except Exception as e:
            return f"""=== EPIC RPA FAILED ===
Error: {str(e)}

Possible causes:
  1. Epic not running or not accessible
  2. Hospital network/VPN not connected
  3. Login credentials invalid
  4. Playwright browser not configured

Recommendation: Manual Epic entry required.
"""

    def _populate_soap(self, epic: EpicRPAController, mrn: str, data: Dict[str, Any]) -> str:
        """Auto-populate SOAP note in Epic"""
        soap_text = data.get('soap_text', '')

        if not soap_text:
            return "ERROR: No SOAP text provided. Include 'soap_text' in data parameter."

        result = epic.populate_soap_note(mrn, soap_text)

        if result.get('success'):
            return f"""=== SOAP NOTE POPULATED ===

Patient MRN: {mrn}
Note Length: {len(soap_text)} characters

Status: ✓ Successfully populated in Epic

Epic Note ID: {result.get('note_id', 'N/A')}
Timestamp: {result.get('timestamp', 'N/A')}

Recommendation: Physician must review and sign note in Epic.
"""
        else:
            error = result.get('error', 'Unknown error')
            return f"""=== SOAP POPULATION FAILED ===

Patient MRN: {mrn}
Error: {error}

Recommendation: Manual note entry required.
"""

    def _retrieve_patient(self, epic: EpicRPAController, mrn: str) -> str:
        """Retrieve patient data from Epic"""
        patient = epic.retrieve_patient_data(mrn)

        if patient.get('found'):
            return f"""=== PATIENT DATA RETRIEVED ===

MRN: {mrn}
Name: {patient.get('name', 'N/A')}
DOB: {patient.get('dob', 'N/A')}
Age: {patient.get('age', 'N/A')}
Gender: {patient.get('gender', 'N/A')}

Allergies: {', '.join(patient.get('allergies', [])) or 'None on file'}

Active Medications ({len(patient.get('medications', []))}):
{self._format_medications(patient.get('medications', []))}

Recent Labs:
{self._format_labs(patient.get('recent_labs', {}))}

Problem List ({len(patient.get('problems', []))}):
{self._format_problems(patient.get('problems', []))}
"""
        else:
            return f"""=== PATIENT NOT FOUND ===

MRN: {mrn}

Error: {patient.get('error', 'Patient not found in Epic')}

Recommendation: Verify MRN or search by name/DOB.
"""

    def _order_lab(self, epic: EpicRPAController, mrn: str, data: Dict[str, Any]) -> str:
        """Place lab order in Epic"""
        lab_name = data.get('lab_name', '')
        priority = data.get('priority', 'Routine')

        if not lab_name:
            return "ERROR: No lab name provided. Include 'lab_name' in data parameter."

        result = epic.order_lab(mrn, lab_name, priority=priority)

        if result.get('success'):
            return f"""=== LAB ORDER PLACED ===

Patient MRN: {mrn}
Lab: {lab_name}
Priority: {priority}

Order ID: {result.get('order_id', 'N/A')}
Status: ✓ Order submitted

Recommendation: Verify order appears in Epic Orders tab.
"""
        else:
            return f"""=== LAB ORDER FAILED ===

Patient MRN: {mrn}
Lab: {lab_name}
Error: {result.get('error', 'Unknown error')}

Recommendation: Manual order entry required.
"""

    def _prescribe_medication(self, epic: EpicRPAController, mrn: str, data: Dict[str, Any]) -> str:
        """Submit medication order in Epic"""
        medication = data.get('medication', '')
        dose = data.get('dose', '')
        frequency = data.get('frequency', '')
        duration = data.get('duration', '')

        if not all([medication, dose, frequency]):
            return "ERROR: Missing required fields. Include 'medication', 'dose', 'frequency' in data parameter."

        result = epic.prescribe_medication(mrn, medication, dose, frequency, duration)

        if result.get('success'):
            return f"""=== MEDICATION ORDERED ===

Patient MRN: {mrn}
Medication: {medication} {dose} {frequency}
Duration: {duration or 'Ongoing'}

Order ID: {result.get('order_id', 'N/A')}
Status: ✓ Prescription submitted

Recommendation: Verify order in Epic Medications tab and sign.
"""
        else:
            return f"""=== MEDICATION ORDER FAILED ===

Patient MRN: {mrn}
Medication: {medication}
Error: {result.get('error', 'Unknown error')}

Recommendation: Manual prescription entry required.
"""

    def _format_medications(self, medications: list, max_items: int = 5) -> str:
        """Format medication list"""
        if not medications:
            return "  None active"

        output = ""
        for i, med in enumerate(medications[:max_items], 1):
            output += f"  {i}. {med.get('name', 'Unknown')} {med.get('dose', '')} {med.get('frequency', '')}\n"

        if len(medications) > max_items:
            output += f"  ... and {len(medications) - max_items} more\n"

        return output

    def _format_labs(self, labs: dict, max_items: int = 5) -> str:
        """Format recent labs"""
        if not labs:
            return "  None on file"

        output = ""
        for i, (test, value) in enumerate(list(labs.items())[:max_items], 1):
            output += f"  {test}: {value}\n"

        if len(labs) > max_items:
            output += f"  ... and {len(labs) - max_items} more\n"

        return output

    def _format_problems(self, problems: list, max_items: int = 5) -> str:
        """Format problem list"""
        if not problems:
            return "  None on file"

        output = ""
        for i, problem in enumerate(problems[:max_items], 1):
            output += f"  {i}. {problem.get('name', 'Unknown')} (Status: {problem.get('status', 'Active')})\n"

        if len(problems) > max_items:
            output += f"  ... and {len(problems) - max_items} more\n"

        return output


# Export
__all__ = ['EpicTool']


if __name__ == "__main__":
    print("Epic Tool - EHR Automation (RPA)")
    print("=" * 50)

    tool = EpicTool()
    print(f"Tool Name: {tool.name}")
    print(f"Description: {tool.description}")
    print("\nActions: populate_soap, retrieve_patient, order_lab, prescribe_medication")
