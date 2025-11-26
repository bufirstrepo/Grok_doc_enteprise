"""
Cerner (Oracle Health) FHIR R4 Client

Connects to Cerner's FHIR R4 API for patient data retrieval.
Compatible with Oracle Health Cloud platform.
"""

import os
import time
from typing import Dict, List, Optional
from dataclasses import dataclass

from .base import (
    EHRClient, PatientData, Observation, Medication, 
    Condition, Encounter
)


@dataclass
class OAuth2Token:
    """OAuth2 token with expiration tracking"""
    access_token: str
    token_type: str
    expires_in: int
    scope: str
    created_at: float = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
    
    @property
    def is_expired(self) -> bool:
        return time.time() > (self.created_at + self.expires_in - 60)


class CernerFHIRClient(EHRClient):
    """
    Cerner (Oracle Health) FHIR R4 API client.
    
    Supports:
    - OAuth2 client credentials and authorization code flows
    - Patient, Observation, MedicationRequest, Condition resources
    - Millennium platform compatibility
    """
    
    def __init__(
        self,
        fhir_endpoint: str,
        client_id: str,
        client_secret: Optional[str] = None,
        token_url: Optional[str] = None,
        scopes: Optional[List[str]] = None
    ):
        """
        Initialize Cerner FHIR client.
        
        Args:
            fhir_endpoint: Base FHIR R4 endpoint URL
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            token_url: OAuth2 token endpoint
            scopes: List of requested scopes
        """
        self.fhir_endpoint = fhir_endpoint.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret or os.getenv('CERNER_CLIENT_SECRET')
        self.token_url = token_url or f"{fhir_endpoint.rsplit('/fhir', 1)[0]}/oauth2/token"
        self.scopes = scopes or [
            "patient/Patient.read",
            "patient/Observation.read",
            "patient/Condition.read",
            "patient/MedicationRequest.read"
        ]
        
        self._token: Optional[OAuth2Token] = None
        self._session = None
    
    def _get_session(self):
        """Get or create HTTP session"""
        if self._session is None:
            try:
                import requests
                self._session = requests.Session()
                self._session.headers.update({
                    'Accept': 'application/fhir+json',
                    'Content-Type': 'application/fhir+json'
                })
            except ImportError:
                raise RuntimeError("requests library required for Cerner FHIR client")
        return self._session
    
    def authenticate(self) -> bool:
        """Authenticate using OAuth2 client credentials flow"""
        if not self.client_secret:
            raise ValueError("Cerner client secret not configured")
        
        session = self._get_session()
        
        try:
            import base64
            credentials = base64.b64encode(
                f"{self.client_id}:{self.client_secret}".encode()
            ).decode()
            
            response = session.post(
                self.token_url,
                data={
                    'grant_type': 'client_credentials',
                    'scope': ' '.join(self.scopes)
                },
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Authorization': f'Basic {credentials}'
                }
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self._token = OAuth2Token(
                    access_token=token_data['access_token'],
                    token_type=token_data.get('token_type', 'Bearer'),
                    expires_in=token_data.get('expires_in', 3600),
                    scope=token_data.get('scope', '')
                )
                return True
            else:
                print(f"Cerner OAuth failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Cerner authentication error: {e}")
            return False
    
    def _ensure_authenticated(self):
        """Ensure we have a valid token"""
        if self._token is None or self._token.is_expired:
            if not self.authenticate():
                raise RuntimeError("Cerner authentication failed")
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict:
        """Make authenticated FHIR API request"""
        self._ensure_authenticated()
        
        session = self._get_session()
        url = f"{self.fhir_endpoint}/{endpoint}"
        
        headers = {
            'Authorization': f'{self._token.token_type} {self._token.access_token}'
        }
        
        response = session.request(
            method=method,
            url=url,
            params=params,
            json=data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 401:
            self._token = None
            self._ensure_authenticated()
            response = session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers={
                    'Authorization': f'{self._token.token_type} {self._token.access_token}'
                },
                timeout=30
            )
        
        response.raise_for_status()
        return response.json()
    
    def get_patient(self, patient_id: str) -> Optional[PatientData]:
        """Get patient by FHIR ID"""
        try:
            data = self._make_request('GET', f'Patient/{patient_id}')
            return self._parse_patient(data)
        except Exception as e:
            print(f"Error fetching patient {patient_id}: {e}")
            return None
    
    def _parse_patient(self, data: Dict) -> PatientData:
        """Parse FHIR Patient resource (Cerner format)"""
        name = data.get('name', [{}])[0]
        address = data.get('address', [{}])[0]
        telecom = data.get('telecom', [])
        
        mrn = ""
        for identifier in data.get('identifier', []):
            type_coding = identifier.get('type', {}).get('coding', [])
            for coding in type_coding:
                if coding.get('code') == 'MR':
                    mrn = identifier.get('value', '')
                    break
        
        phone = None
        email = None
        for t in telecom:
            if t.get('system') == 'phone' and t.get('use') in ['home', 'mobile']:
                phone = t.get('value')
            elif t.get('system') == 'email':
                email = t.get('value')
        
        return PatientData(
            id=data.get('id', ''),
            mrn=mrn,
            given_name=' '.join(name.get('given', [])),
            family_name=name.get('family', ''),
            birth_date=data.get('birthDate'),
            gender=data.get('gender'),
            deceased=data.get('deceasedBoolean', False),
            address=', '.join(filter(None, [
                ' '.join(address.get('line', [])),
                address.get('city'),
                address.get('state'),
                address.get('postalCode')
            ])),
            phone=phone,
            email=email,
            source_system='cerner'
        )
    
    def get_observations(
        self,
        patient_id: str,
        category: Optional[str] = None,
        code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Observation]:
        """Get patient observations"""
        params = {'patient': patient_id, '_count': 100}
        
        if category:
            params['category'] = category
        if code:
            params['code'] = code
        if start_date:
            params['date'] = f'ge{start_date}'
        
        try:
            data = self._make_request('GET', 'Observation', params=params)
            observations = []
            
            for entry in data.get('entry', []):
                resource = entry.get('resource', {})
                observations.append(self._parse_observation(resource))
            
            return observations
        except Exception as e:
            print(f"Error fetching observations: {e}")
            return []
    
    def _parse_observation(self, data: Dict) -> Observation:
        """Parse FHIR Observation resource"""
        coding = data.get('code', {}).get('coding', [{}])[0]
        
        value = None
        unit = None
        if 'valueQuantity' in data:
            value = data['valueQuantity'].get('value')
            unit = data['valueQuantity'].get('unit')
        elif 'valueString' in data:
            value = data['valueString']
        elif 'valueCodeableConcept' in data:
            value = data['valueCodeableConcept'].get('text')
        
        ref_range = data.get('referenceRange', [{}])[0]
        ref_low = ref_range.get('low', {}).get('value')
        ref_high = ref_range.get('high', {}).get('value')
        
        interpretation = None
        interp = data.get('interpretation', [{}])[0].get('coding', [{}])[0]
        interpretation = interp.get('code')
        
        category = None
        cat = data.get('category', [{}])[0].get('coding', [{}])[0]
        category = cat.get('code')
        
        return Observation(
            id=data.get('id', ''),
            code=coding.get('code', ''),
            code_system=coding.get('system', ''),
            display=coding.get('display', data.get('code', {}).get('text', '')),
            value=value,
            unit=unit,
            reference_range_low=ref_low,
            reference_range_high=ref_high,
            interpretation=interpretation,
            category=category,
            effective_datetime=data.get('effectiveDateTime'),
            issued=data.get('issued'),
            status=data.get('status', 'unknown')
        )
    
    def get_medications(
        self,
        patient_id: str,
        status: Optional[str] = None
    ) -> List[Medication]:
        """Get patient medications"""
        params = {'patient': patient_id, '_count': 100}
        if status:
            params['status'] = status
        
        try:
            data = self._make_request('GET', 'MedicationRequest', params=params)
            medications = []
            
            for entry in data.get('entry', []):
                resource = entry.get('resource', {})
                medications.append(self._parse_medication(resource))
            
            return medications
        except Exception as e:
            print(f"Error fetching medications: {e}")
            return []
    
    def _parse_medication(self, data: Dict) -> Medication:
        """Parse FHIR MedicationRequest resource"""
        med_concept = data.get('medicationCodeableConcept', {})
        coding = med_concept.get('coding', [{}])[0]
        
        dosage = data.get('dosageInstruction', [{}])[0]
        dose_quant = dosage.get('doseAndRate', [{}])[0].get('doseQuantity', {})
        
        return Medication(
            id=data.get('id', ''),
            code=coding.get('code', ''),
            code_system=coding.get('system', ''),
            display=coding.get('display', med_concept.get('text', '')),
            dose_value=dose_quant.get('value'),
            dose_unit=dose_quant.get('unit'),
            route=dosage.get('route', {}).get('text'),
            frequency=dosage.get('timing', {}).get('code', {}).get('text'),
            status=data.get('status', 'unknown'),
            start_date=data.get('authoredOn'),
            prescriber=data.get('requester', {}).get('display'),
            instructions=dosage.get('text')
        )
    
    def get_conditions(
        self,
        patient_id: str,
        clinical_status: Optional[str] = None
    ) -> List[Condition]:
        """Get patient conditions"""
        params = {'patient': patient_id, '_count': 100}
        if clinical_status:
            params['clinical-status'] = clinical_status
        
        try:
            data = self._make_request('GET', 'Condition', params=params)
            conditions = []
            
            for entry in data.get('entry', []):
                resource = entry.get('resource', {})
                conditions.append(self._parse_condition(resource))
            
            return conditions
        except Exception as e:
            print(f"Error fetching conditions: {e}")
            return []
    
    def _parse_condition(self, data: Dict) -> Condition:
        """Parse FHIR Condition resource"""
        coding = data.get('code', {}).get('coding', [{}])[0]
        
        clinical_status = data.get('clinicalStatus', {}).get('coding', [{}])[0].get('code', 'unknown')
        verification = data.get('verificationStatus', {}).get('coding', [{}])[0].get('code', 'unknown')
        
        return Condition(
            id=data.get('id', ''),
            code=coding.get('code', ''),
            code_system=coding.get('system', ''),
            display=coding.get('display', data.get('code', {}).get('text', '')),
            clinical_status=clinical_status,
            verification_status=verification,
            severity=data.get('severity', {}).get('text'),
            onset_datetime=data.get('onsetDateTime'),
            abatement_datetime=data.get('abatementDateTime'),
            category=data.get('category', [{}])[0].get('coding', [{}])[0].get('code')
        )
    
    def get_full_patient_context(self, patient_id: str) -> PatientData:
        """Get complete patient context"""
        patient = self.get_patient(patient_id)
        if patient is None:
            raise ValueError(f"Patient {patient_id} not found")
        
        patient.observations = self.get_observations(patient_id)
        patient.medications = self.get_medications(patient_id)
        patient.conditions = self.get_conditions(patient_id)
        
        return patient
    
    def search_patients(
        self,
        name: Optional[str] = None,
        mrn: Optional[str] = None,
        birth_date: Optional[str] = None
    ) -> List[PatientData]:
        """Search for patients"""
        params = {'_count': 50}
        
        if name:
            params['name'] = name
        if mrn:
            params['identifier'] = mrn
        if birth_date:
            params['birthdate'] = birth_date
        
        try:
            data = self._make_request('GET', 'Patient', params=params)
            patients = []
            
            for entry in data.get('entry', []):
                resource = entry.get('resource', {})
                patients.append(self._parse_patient(resource))
            
            return patients
        except Exception as e:
            print(f"Error searching patients: {e}")
            return []
    
    @property
    def is_authenticated(self) -> bool:
        """Check if client is authenticated"""
        return self._token is not None and not self._token.is_expired
    
    @property
    def ehr_type(self) -> str:
        """Return EHR type"""
        return "cerner"
