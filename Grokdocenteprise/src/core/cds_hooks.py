"""
CDS Hooks Integration for Grok Doc v2.5

Implements CDS Hooks 2.0 specification for clinical decision support
within EHR workflows. Provides real-time recommendations at key
clinical decision points.

Reference: https://cds-hooks.hl7.org/2.0/
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import uuid
import json
import hashlib

from ..ehr.unified_model import UnifiedPatientModel, normalize_patient_data
from ..ehr.base import PatientData, Observation, Medication, Condition


class CardIndicator(Enum):
    """Visual indicator for CDS card urgency"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    HARD_STOP = "hard-stop"


class SelectionBehavior(Enum):
    """Selection behavior for card suggestions"""
    ANY = "any"
    AT_MOST_ONE = "at-most-one"
    EXACTLY_ONE = "exactly-one"


class HookType(Enum):
    """Supported CDS Hooks types"""
    PATIENT_VIEW = "patient-view"
    ORDER_SELECT = "order-select"
    ORDER_SIGN = "order-sign"
    ENCOUNTER_START = "encounter-start"
    ENCOUNTER_DISCHARGE = "encounter-discharge"
    MEDICATION_PRESCRIBE = "medication-prescribe"


@dataclass
class CDSSource:
    """Source attribution for a CDS card"""
    label: str
    url: Optional[str] = None
    icon: Optional[str] = None
    topic: Optional[Dict[str, str]] = None


@dataclass
class CDSSuggestion:
    """Suggested action for a CDS card"""
    uuid: str
    label: str
    isRecommended: bool = False
    actions: List[Dict[str, Any]] = field(default_factory=list)
    
    @classmethod
    def create(
        cls,
        label: str,
        is_recommended: bool = False,
        resource_type: Optional[str] = None,
        resource: Optional[Dict] = None,
        action_type: str = "create"
    ) -> "CDSSuggestion":
        """Create a suggestion with optional FHIR action"""
        actions = []
        if resource_type and resource:
            actions.append({
                "type": action_type,
                "description": label,
                "resource": resource
            })
        return cls(
            uuid=str(uuid.uuid4()),
            label=label,
            isRecommended=is_recommended,
            actions=actions
        )


@dataclass
class CDSLink:
    """External link for a CDS card"""
    label: str
    url: str
    type: str = "absolute"
    appContext: Optional[str] = None


@dataclass
class CDSCard:
    """
    CDS Hooks card representing a clinical recommendation.
    
    Follows CDS Hooks 2.0 specification for card structure.
    """
    uuid: str
    summary: str
    indicator: str
    source: CDSSource
    detail: Optional[str] = None
    suggestions: List[CDSSuggestion] = field(default_factory=list)
    links: List[CDSLink] = field(default_factory=list)
    selectionBehavior: Optional[str] = None
    overrideReasons: List[Dict[str, str]] = field(default_factory=list)
    
    @classmethod
    def create(
        cls,
        summary: str,
        indicator: CardIndicator = CardIndicator.INFO,
        source_label: str = "Grok Doc CDS",
        source_url: Optional[str] = None,
        detail: Optional[str] = None,
        suggestions: Optional[List[CDSSuggestion]] = None,
        links: Optional[List[CDSLink]] = None,
        selection_behavior: Optional[SelectionBehavior] = None,
        override_reasons: Optional[List[str]] = None
    ) -> "CDSCard":
        """Factory method to create a CDS card"""
        if len(summary) > 140:
            summary = summary[:137] + "..."
        
        return cls(
            uuid=str(uuid.uuid4()),
            summary=summary,
            indicator=indicator.value,
            source=CDSSource(label=source_label, url=source_url),
            detail=detail,
            suggestions=suggestions or [],
            links=links or [],
            selectionBehavior=selection_behavior.value if selection_behavior else None,
            overrideReasons=[
                {"code": reason.lower().replace(" ", "_"), "display": reason}
                for reason in (override_reasons or [])
            ]
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to CDS Hooks JSON format"""
        result = {
            "uuid": self.uuid,
            "summary": self.summary,
            "indicator": self.indicator,
            "source": {
                "label": self.source.label
            }
        }
        
        if self.source.url:
            result["source"]["url"] = self.source.url
        if self.source.icon:
            result["source"]["icon"] = self.source.icon
        
        if self.detail:
            result["detail"] = self.detail
        
        if self.suggestions:
            result["suggestions"] = [
                {
                    "uuid": s.uuid,
                    "label": s.label,
                    "isRecommended": s.isRecommended,
                    "actions": s.actions
                }
                for s in self.suggestions
            ]
        
        if self.links:
            result["links"] = [
                {"label": l.label, "url": l.url, "type": l.type}
                for l in self.links
            ]
        
        if self.selectionBehavior:
            result["selectionBehavior"] = self.selectionBehavior
        
        if self.overrideReasons:
            result["overrideReasons"] = self.overrideReasons
        
        return result


@dataclass
class CDSFHIRAuthorization:
    """FHIR authorization for CDS service"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    scope: str = ""
    subject: str = ""


@dataclass
class CDSRequest:
    """
    Incoming CDS Hooks request from EHR.
    
    Contains hook context, prefetched data, and FHIR server info.
    """
    hookInstance: str
    hook: str
    context: Dict[str, Any]
    prefetch: Dict[str, Any] = field(default_factory=dict)
    fhirServer: Optional[str] = None
    fhirAuthorization: Optional[CDSFHIRAuthorization] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CDSRequest":
        """Parse CDS request from JSON dict"""
        fhir_auth = None
        if "fhirAuthorization" in data:
            auth_data = data["fhirAuthorization"]
            fhir_auth = CDSFHIRAuthorization(
                access_token=auth_data.get("access_token", ""),
                token_type=auth_data.get("token_type", "Bearer"),
                expires_in=auth_data.get("expires_in", 3600),
                scope=auth_data.get("scope", ""),
                subject=auth_data.get("subject", "")
            )
        
        return cls(
            hookInstance=data.get("hookInstance", str(uuid.uuid4())),
            hook=data.get("hook", ""),
            context=data.get("context", {}),
            prefetch=data.get("prefetch", {}),
            fhirServer=data.get("fhirServer"),
            fhirAuthorization=fhir_auth
        )
    
    def get_patient_id(self) -> Optional[str]:
        """Extract patient ID from context"""
        if "patientId" in self.context:
            return self.context["patientId"]
        if "patient" in self.context:
            return self.context["patient"]
        if "userId" in self.context:
            return self.context["userId"]
        return None
    
    def get_user_id(self) -> Optional[str]:
        """Extract user/practitioner ID from context"""
        return self.context.get("userId")
    
    def get_encounter_id(self) -> Optional[str]:
        """Extract encounter ID from context"""
        return self.context.get("encounterId")
    
    def get_selections(self) -> List[str]:
        """Get selected order IDs (for order-select hook)"""
        return self.context.get("selections", [])
    
    def get_draft_orders(self) -> Dict[str, Any]:
        """Get draft orders bundle (for order-select/order-sign)"""
        return self.context.get("draftOrders", {})
    
    def get_prefetch_resource(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a prefetched FHIR resource by key"""
        return self.prefetch.get(key)
    
    def extract_patient_data(self) -> Optional[PatientData]:
        """Extract patient data from prefetch"""
        patient_resource = self.prefetch.get("patient")
        if not patient_resource:
            return None
        
        patient_id = patient_resource.get("id", "unknown")
        mrn = ""
        for identifier in patient_resource.get("identifier", []):
            if identifier.get("type", {}).get("coding", [{}])[0].get("code") == "MR":
                mrn = identifier.get("value", "")
                break
        
        name = patient_resource.get("name", [{}])[0]
        
        return PatientData(
            id=patient_id,
            mrn=mrn or patient_id,
            given_name=" ".join(name.get("given", [])),
            family_name=name.get("family", ""),
            birth_date=patient_resource.get("birthDate"),
            gender=patient_resource.get("gender"),
            source_system="cds-hooks"
        )
    
    def extract_medications(self) -> List[Medication]:
        """Extract medications from prefetch or draft orders"""
        medications = []
        
        med_request = self.prefetch.get("medicationRequests", {})
        if med_request.get("resourceType") == "Bundle":
            for entry in med_request.get("entry", []):
                resource = entry.get("resource", {})
                if resource.get("resourceType") == "MedicationRequest":
                    medications.append(self._parse_medication_request(resource))
        
        draft_orders = self.get_draft_orders()
        if draft_orders.get("resourceType") == "Bundle":
            for entry in draft_orders.get("entry", []):
                resource = entry.get("resource", {})
                if resource.get("resourceType") == "MedicationRequest":
                    medications.append(self._parse_medication_request(resource))
        
        return medications
    
    def _parse_medication_request(self, resource: Dict) -> Medication:
        """Parse FHIR MedicationRequest into Medication"""
        med_code = resource.get("medicationCodeableConcept", {})
        coding = med_code.get("coding", [{}])[0]
        
        dosage = resource.get("dosageInstruction", [{}])[0]
        dose_quantity = dosage.get("doseAndRate", [{}])[0].get("doseQuantity", {})
        
        return Medication(
            id=resource.get("id", str(uuid.uuid4())),
            code=coding.get("code", ""),
            code_system=coding.get("system", ""),
            display=med_code.get("text", coding.get("display", "")),
            dose_value=dose_quantity.get("value"),
            dose_unit=dose_quantity.get("unit"),
            route=dosage.get("route", {}).get("text"),
            status=resource.get("status", "draft")
        )


@dataclass
class CDSSystemAction:
    """System action for automated CDS response"""
    type: str
    description: str
    resource: Dict[str, Any]


@dataclass
class CDSResponse:
    """
    CDS Hooks response containing cards and optional system actions.
    """
    cards: List[CDSCard] = field(default_factory=list)
    systemActions: List[CDSSystemAction] = field(default_factory=list)
    
    def add_card(self, card: CDSCard):
        """Add a card to the response"""
        self.cards.append(card)
    
    def add_system_action(
        self,
        action_type: str,
        description: str,
        resource: Dict[str, Any]
    ):
        """Add a system action"""
        self.systemActions.append(CDSSystemAction(
            type=action_type,
            description=description,
            resource=resource
        ))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to CDS Hooks JSON format"""
        result = {
            "cards": [card.to_dict() for card in self.cards]
        }
        
        if self.systemActions:
            result["systemActions"] = [
                {
                    "type": action.type,
                    "description": action.description,
                    "resource": action.resource
                }
                for action in self.systemActions
            ]
        
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class CDSServiceDefinition:
    """Definition of a CDS Hooks service endpoint"""
    id: str
    hook: str
    title: str
    description: str
    prefetch: Dict[str, str] = field(default_factory=dict)
    usageRequirements: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to discovery format"""
        result: Dict[str, Any] = {
            "id": self.id,
            "hook": self.hook,
            "title": self.title,
            "description": self.description
        }
        if self.prefetch:
            result["prefetch"] = self.prefetch
        if self.usageRequirements:
            result["usageRequirements"] = self.usageRequirements
        return result


class CDSHooksService:
    """
    Main CDS Hooks service that manages hook handlers and generates cards.
    
    Integrates with Kinetics engine for clinical reasoning and provides
    decision support at key clinical workflow points.
    """
    
    STANDARD_PREFETCH = {
        "patient": "Patient/{{context.patientId}}",
        "conditions": "Condition?patient={{context.patientId}}&clinical-status=active",
        "medications": "MedicationRequest?patient={{context.patientId}}&status=active",
        "observations": "Observation?patient={{context.patientId}}&_count=50&_sort=-date",
        "allergies": "AllergyIntolerance?patient={{context.patientId}}&clinical-status=active"
    }
    
    def __init__(
        self,
        service_id: str = "grok-doc-cds",
        service_title: str = "Grok Doc Clinical Decision Support",
        use_kinetics: bool = True
    ):
        """
        Initialize CDS Hooks service.
        
        Args:
            service_id: Unique service identifier
            service_title: Human-readable service title
            use_kinetics: Whether to use Kinetics engine for analysis
        """
        self.service_id = service_id
        self.service_title = service_title
        self.use_kinetics = use_kinetics
        
        self._hook_handlers: Dict[str, Callable] = {}
        self._services: List[CDSServiceDefinition] = []
        
        self._register_default_handlers()
        self._register_default_services()
    
    def _register_default_handlers(self):
        """Register default hook handlers"""
        self.register_handler(HookType.PATIENT_VIEW.value, self._handle_patient_view)
        self.register_handler(HookType.ORDER_SELECT.value, self._handle_order_select)
        self.register_handler(HookType.ORDER_SIGN.value, self._handle_order_sign)
        self.register_handler(HookType.MEDICATION_PRESCRIBE.value, self._handle_medication_prescribe)
    
    def _register_default_services(self):
        """Register default service definitions"""
        self._services = [
            CDSServiceDefinition(
                id=f"{self.service_id}-patient-view",
                hook=HookType.PATIENT_VIEW.value,
                title=f"{self.service_title} - Patient View",
                description="Provides clinical insights when viewing a patient chart",
                prefetch={
                    "patient": self.STANDARD_PREFETCH["patient"],
                    "conditions": self.STANDARD_PREFETCH["conditions"],
                    "medications": self.STANDARD_PREFETCH["medications"],
                    "observations": self.STANDARD_PREFETCH["observations"],
                    "allergies": self.STANDARD_PREFETCH["allergies"]
                }
            ),
            CDSServiceDefinition(
                id=f"{self.service_id}-order-select",
                hook=HookType.ORDER_SELECT.value,
                title=f"{self.service_title} - Order Selection",
                description="Analyzes selected orders for safety and appropriateness",
                prefetch={
                    "patient": self.STANDARD_PREFETCH["patient"],
                    "medications": self.STANDARD_PREFETCH["medications"],
                    "allergies": self.STANDARD_PREFETCH["allergies"]
                }
            ),
            CDSServiceDefinition(
                id=f"{self.service_id}-order-sign",
                hook=HookType.ORDER_SIGN.value,
                title=f"{self.service_title} - Order Signing",
                description="Final safety check before order submission",
                prefetch={
                    "patient": self.STANDARD_PREFETCH["patient"],
                    "conditions": self.STANDARD_PREFETCH["conditions"],
                    "medications": self.STANDARD_PREFETCH["medications"],
                    "allergies": self.STANDARD_PREFETCH["allergies"]
                }
            )
        ]
    
    def register_handler(self, hook: str, handler: Callable[[CDSRequest], CDSResponse]):
        """Register a handler for a hook type"""
        self._hook_handlers[hook] = handler
    
    def register_service(self, service: CDSServiceDefinition):
        """Register a custom service definition"""
        self._services.append(service)
    
    def get_discovery(self) -> Dict[str, Any]:
        """
        Get CDS Hooks discovery document.
        
        Returns:
            Discovery document for /.well-known/cds-services
        """
        return {
            "services": [service.to_dict() for service in self._services]
        }
    
    def handle_request(self, request: CDSRequest) -> CDSResponse:
        """
        Process a CDS Hooks request and generate response.
        
        Args:
            request: Incoming CDS request
            
        Returns:
            CDSResponse with appropriate cards
        """
        handler = self._hook_handlers.get(request.hook)
        if not handler:
            return CDSResponse(cards=[
                CDSCard.create(
                    summary=f"Unsupported hook type: {request.hook}",
                    indicator=CardIndicator.INFO,
                    detail="This CDS service does not support the requested hook."
                )
            ])
        
        try:
            return handler(request)
        except Exception as e:
            return CDSResponse(cards=[
                CDSCard.create(
                    summary="CDS service error occurred",
                    indicator=CardIndicator.WARNING,
                    detail=f"An error occurred processing the request: {str(e)}"
                )
            ])
    
    def _handle_patient_view(self, request: CDSRequest) -> CDSResponse:
        """Handle patient-view hook"""
        response = CDSResponse()
        
        patient_data = request.extract_patient_data()
        if not patient_data:
            return response
        
        unified_model = normalize_patient_data(ehr_data=patient_data)
        
        self._add_abnormal_lab_cards(response, request)
        self._add_drug_interaction_cards(response, request)
        self._add_risk_assessment_cards(response, unified_model)
        
        if self.use_kinetics:
            self._add_kinetics_insights(response, unified_model, "patient-view")
        
        return response
    
    def _handle_order_select(self, request: CDSRequest) -> CDSResponse:
        """Handle order-select hook"""
        response = CDSResponse()
        
        draft_orders = request.get_draft_orders()
        selections = request.get_selections()
        
        if not draft_orders:
            return response
        
        selected_meds = self._get_selected_medications(draft_orders, selections)
        
        for med in selected_meds:
            self._check_medication_safety(response, request, med)
        
        return response
    
    def _handle_order_sign(self, request: CDSRequest) -> CDSResponse:
        """Handle order-sign hook"""
        response = CDSResponse()
        
        draft_orders = request.get_draft_orders()
        if not draft_orders:
            return response
        
        all_meds = request.extract_medications()
        
        for med in all_meds:
            safety_issues = self._check_medication_safety(response, request, med, is_signing=True)
            
            if safety_issues and safety_issues.get("critical"):
                response.cards[-1].overrideReasons = [
                    {"code": "patient_need", "display": "Patient clinical need"},
                    {"code": "alternative_unavailable", "display": "Alternative not available"},
                    {"code": "benefit_outweighs_risk", "display": "Benefit outweighs risk"},
                    {"code": "patient_informed", "display": "Patient informed and consents"}
                ]
        
        return response
    
    def _handle_medication_prescribe(self, request: CDSRequest) -> CDSResponse:
        """Handle medication-prescribe hook"""
        response = CDSResponse()
        
        medications = request.extract_medications()
        
        for med in medications:
            self._check_medication_safety(response, request, med)
            self._add_dosing_guidance(response, request, med)
        
        return response
    
    def _get_selected_medications(
        self,
        draft_orders: Dict,
        selections: List[str]
    ) -> List[Medication]:
        """Extract selected medications from draft orders"""
        medications = []
        
        if draft_orders.get("resourceType") != "Bundle":
            return medications
        
        for entry in draft_orders.get("entry", []):
            resource = entry.get("resource", {})
            resource_id = resource.get("id", "")
            
            full_id = f"MedicationRequest/{resource_id}"
            if full_id in selections or resource_id in selections:
                if resource.get("resourceType") == "MedicationRequest":
                    med_code = resource.get("medicationCodeableConcept", {})
                    coding = med_code.get("coding", [{}])[0]
                    
                    medications.append(Medication(
                        id=resource_id,
                        code=coding.get("code", ""),
                        code_system=coding.get("system", ""),
                        display=med_code.get("text", coding.get("display", "")),
                        status="draft"
                    ))
        
        return medications
    
    def _add_abnormal_lab_cards(self, response: CDSResponse, request: CDSRequest):
        """Add cards for abnormal lab values"""
        observations_bundle = request.get_prefetch_resource("observations")
        if not observations_bundle:
            return
        
        abnormal_labs = []
        for entry in observations_bundle.get("entry", []):
            obs = entry.get("resource", {})
            interpretation = obs.get("interpretation", [{}])[0]
            coding = interpretation.get("coding", [{}])[0]
            
            if coding.get("code") in ["H", "L", "HH", "LL", "A", "AA", "critical"]:
                value_quantity = obs.get("valueQuantity", {})
                abnormal_labs.append({
                    "name": obs.get("code", {}).get("text", "Unknown"),
                    "value": value_quantity.get("value"),
                    "unit": value_quantity.get("unit", ""),
                    "interpretation": coding.get("code")
                })
        
        if abnormal_labs:
            critical = [l for l in abnormal_labs if l["interpretation"] in ["HH", "LL", "AA", "critical"]]
            
            if critical:
                lab_summary = ", ".join([
                    f"{l['name']}: {l['value']} {l['unit']}"
                    for l in critical[:3]
                ])
                response.add_card(CDSCard.create(
                    summary=f"CRITICAL lab values detected: {lab_summary}",
                    indicator=CardIndicator.CRITICAL,
                    detail=f"Patient has {len(critical)} critical lab value(s) requiring immediate attention.",
                    suggestions=[
                        CDSSuggestion.create("Review critical labs", is_recommended=True),
                        CDSSuggestion.create("Contact ordering physician")
                    ]
                ))
            elif abnormal_labs:
                response.add_card(CDSCard.create(
                    summary=f"{len(abnormal_labs)} abnormal lab value(s) detected",
                    indicator=CardIndicator.WARNING,
                    detail="Review abnormal laboratory results before proceeding.",
                    suggestions=[
                        CDSSuggestion.create("View lab results", is_recommended=True)
                    ]
                ))
    
    def _add_drug_interaction_cards(self, response: CDSResponse, request: CDSRequest):
        """Add cards for potential drug interactions"""
        medications = request.extract_medications()
        allergies_bundle = request.get_prefetch_resource("allergies")
        
        if not medications:
            return
        
        allergy_substances = []
        if allergies_bundle:
            for entry in allergies_bundle.get("entry", []):
                allergy = entry.get("resource", {})
                substance = allergy.get("code", {}).get("text", "")
                if substance:
                    allergy_substances.append(substance.lower())
        
        for med in medications:
            med_name = med.display.lower()
            for allergy in allergy_substances:
                if allergy in med_name or med_name in allergy:
                    response.add_card(CDSCard.create(
                        summary=f"Potential allergy alert: {med.display}",
                        indicator=CardIndicator.CRITICAL,
                        detail=f"Patient has documented allergy to {allergy}. "
                               f"Medication {med.display} may be contraindicated.",
                        suggestions=[
                            CDSSuggestion.create("Cancel order", is_recommended=True),
                            CDSSuggestion.create("Select alternative"),
                            CDSSuggestion.create("Override with documentation")
                        ],
                        override_reasons=[
                            "Allergy no longer active",
                            "Cross-reactivity unlikely",
                            "No suitable alternative",
                            "Patient informed consent"
                        ]
                    ))
    
    def _add_risk_assessment_cards(self, response: CDSResponse, patient: UnifiedPatientModel):
        """Add cards based on clinical risk scores"""
        risk_scores = patient.risk_scores
        
        high_risk = [r for r in risk_scores if r.value > 0.7]
        
        for risk in high_risk:
            indicator = CardIndicator.CRITICAL if risk.value > 0.85 else CardIndicator.WARNING
            
            response.add_card(CDSCard.create(
                summary=f"Elevated {risk.name}: {risk.value:.0%}",
                indicator=indicator,
                detail=f"Patient has elevated {risk.name} score ({risk.value:.1%}). "
                       f"Category: {risk.category}. Factors: {', '.join(risk.factors[:3])}.",
                suggestions=[
                    CDSSuggestion.create(f"Review {risk.name} assessment", is_recommended=True),
                    CDSSuggestion.create("Implement risk mitigation protocol")
                ]
            ))
    
    def _check_medication_safety(
        self,
        response: CDSResponse,
        request: CDSRequest,
        medication: Medication,
        is_signing: bool = False
    ) -> Optional[Dict]:
        """Check medication for safety issues"""
        safety_issues = {"warnings": [], "critical": False}
        
        current_meds = request.extract_medications()
        current_med_names = [m.display.lower() for m in current_meds if m.id != medication.id]
        
        high_risk_combos = [
            (["warfarin"], ["aspirin", "ibuprofen", "naproxen"], "Increased bleeding risk"),
            (["metformin"], ["contrast", "iodine"], "Risk of lactic acidosis"),
            (["ssri", "sertraline", "fluoxetine"], ["tramadol", "fentanyl"], "Serotonin syndrome risk"),
            (["ace inhibitor", "lisinopril", "enalapril"], ["potassium", "spironolactone"], "Hyperkalemia risk")
        ]
        
        med_lower = medication.display.lower()
        for drug_group_a, drug_group_b, warning in high_risk_combos:
            med_in_a = any(d in med_lower for d in drug_group_a)
            med_in_b = any(d in med_lower for d in drug_group_b)
            
            current_has_a = any(any(d in m for d in drug_group_a) for m in current_med_names)
            current_has_b = any(any(d in m for d in drug_group_b) for m in current_med_names)
            
            if (med_in_a and current_has_b) or (med_in_b and current_has_a):
                safety_issues["warnings"].append(warning)
                if "syndrome" in warning.lower() or "acidosis" in warning.lower():
                    safety_issues["critical"] = True
        
        if safety_issues["warnings"]:
            indicator = CardIndicator.CRITICAL if safety_issues["critical"] else CardIndicator.WARNING
            
            response.add_card(CDSCard.create(
                summary=f"Drug interaction alert: {medication.display}",
                indicator=indicator,
                detail=f"Potential interactions detected: {'; '.join(safety_issues['warnings'])}",
                suggestions=[
                    CDSSuggestion.create("Review interaction details", is_recommended=True),
                    CDSSuggestion.create("Select alternative medication"),
                    CDSSuggestion.create("Proceed with enhanced monitoring")
                ]
            ))
        
        return safety_issues if safety_issues["warnings"] else None
    
    def _add_dosing_guidance(
        self,
        response: CDSResponse,
        request: CDSRequest,
        medication: Medication
    ):
        """Add dosing guidance for medication"""
        patient_data = request.extract_patient_data()
        if not patient_data:
            return
        
        age = patient_data.get_age()
        
        if age and age >= 65:
            response.add_card(CDSCard.create(
                summary=f"Geriatric dosing consideration for {medication.display}",
                indicator=CardIndicator.INFO,
                detail=f"Patient is {age} years old. Consider reduced initial dosing "
                       f"and careful titration for elderly patients.",
                suggestions=[
                    CDSSuggestion.create("Review geriatric dosing guidelines"),
                    CDSSuggestion.create("Check renal function")
                ],
                links=[
                    CDSLink(
                        label="Beers Criteria",
                        url="https://www.americangeriatrics.org/beers-criteria"
                    )
                ]
            ))
    
    def _add_kinetics_insights(
        self,
        response: CDSResponse,
        patient: UnifiedPatientModel,
        hook_type: str
    ):
        """Add insights from Kinetics engine"""
        try:
            from .kinetics_enhanced import EnhancedKineticsEngine, KineticsContext
            
            engine = EnhancedKineticsEngine(use_local_llm=True)
            
            context = KineticsContext(
                patient=patient,
                clinical_question=f"Provide clinical decision support for {hook_type} context",
                metadata={"hook_type": hook_type, "cds_source": True}
            )
            
            result = engine.analyze(context)
            
            if result.warnings:
                for warning in result.warnings[:2]:
                    response.add_card(CDSCard.create(
                        summary=warning[:140],
                        indicator=CardIndicator.WARNING,
                        detail=f"Kinetics engine identified: {warning}",
                        source_label="Grok Doc Kinetics Engine"
                    ))
            
            if result.suggested_actions:
                response.add_card(CDSCard.create(
                    summary="Clinical action recommendations available",
                    indicator=CardIndicator.INFO,
                    detail="; ".join(result.suggested_actions),
                    suggestions=[
                        CDSSuggestion.create(action, is_recommended=(i == 0))
                        for i, action in enumerate(result.suggested_actions[:3])
                    ],
                    source_label="Grok Doc Kinetics Engine"
                ))
        except Exception:
            pass


def create_cds_service(
    service_id: str = "grok-doc-cds",
    service_title: str = "Grok Doc Clinical Decision Support",
    use_kinetics: bool = True
) -> CDSHooksService:
    """
    Factory function to create a configured CDS Hooks service.
    
    Args:
        service_id: Unique service identifier
        service_title: Human-readable service title
        use_kinetics: Whether to use Kinetics engine
        
    Returns:
        Configured CDSHooksService instance
    """
    return CDSHooksService(
        service_id=service_id,
        service_title=service_title,
        use_kinetics=use_kinetics
    )


def handle_cds_request(
    request_data: Dict[str, Any],
    service: Optional[CDSHooksService] = None
) -> Dict[str, Any]:
    """
    Convenience function to handle a CDS request.
    
    Args:
        request_data: Raw CDS request JSON
        service: Optional CDSHooksService instance
        
    Returns:
        CDS response as dictionary
    """
    if service is None:
        service = create_cds_service()
    
    request = CDSRequest.from_dict(request_data)
    response = service.handle_request(request)
    
    return response.to_dict()
