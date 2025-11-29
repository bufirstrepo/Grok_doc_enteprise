import unittest
from clinical_safety import DrugInteractionChecker
from security_utils import PHIMasker

class TestV40Features(unittest.TestCase):
    
    def test_ddi_checker(self):
        checker = DrugInteractionChecker()
        
        # Test Major Interaction
        meds = ["Warfarin", "Aspirin"]
        alerts = checker.check_interactions(meds)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['severity'], 'Major')
        self.assertIn('bleeding', alerts[0]['description'])
        
        # Test No Interaction
        meds = ["Tylenol", "Vitamin C"]
        alerts = checker.check_interactions(meds)
        self.assertEqual(len(alerts), 0)
        
        # Test Multiple Interactions
        meds = ["Warfarin", "Aspirin", "Ibuprofen"]
        alerts = checker.check_interactions(meds)
        # Warfarin+Aspirin, Warfarin+Ibuprofen
        self.assertEqual(len(alerts), 2)

    def test_phi_masker(self):
        masker = PHIMasker()
        
        # Test MRN Masking
        text = "Patient MRN: 123456"
        masked = masker.mask_text(text)
        self.assertIn("[MRN-REDACTED]", masked)
        self.assertNotIn("123456", masked)
        
        # Test SSN Masking
        text = "SSN: 123-45-6789"
        masked = masker.mask_text(text)
        self.assertIn("[SSN-REDACTED]", masked)
        self.assertNotIn("123-45-6789", masked)
        
        # Test Date Masking
        text = "DOB: 01/01/1980"
        masked = masker.mask_text(text)
        self.assertIn("[DATE-REDACTED]", masked)
        self.assertNotIn("01/01/1980", masked)

if __name__ == '__main__':
    unittest.main()
