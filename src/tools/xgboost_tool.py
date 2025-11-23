#!/usr/bin/env python3
"""
XGBoost Lab Prediction Tool for CrewAI
Wraps lab_predictions.py for use by lab_agent
"""

from crewai.tools import BaseTool
from typing import Type, Dict, Any
from pydantic import BaseModel, Field
import sys
import os

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

# Import from root directory (lab_predictions is still there)
from lab_predictions import get_creatinine_predictor, get_inr_predictor


class XGBoostToolInput(BaseModel):
    """Input schema for XGBoost lab predictor"""
    patient_data: Dict[str, Any] = Field(..., description="Patient data dictionary with age, weight, labs, medications")
    lab_type: str = Field(..., description="Lab to predict: 'creatinine', 'inr', or 'potassium'")


class XGBoostTool(BaseTool):
    """
    Lab Value Predictor using XGBoost ML models

    Predicts future lab values (Cr, INR, K+) 24-48 hours ahead based on:
    - Current lab values
    - Patient demographics
    - Medication regimen
    - Clinical context

    Used by: lab_agent (Laboratory Agent) and kinetics_agent
    """

    name: str = "XGBoost Lab Value Predictor"
    description: str = """Predict future lab values using machine learning models.
    Supports creatinine (AKI risk), INR (warfarin response), and potassium predictions.
    Returns predicted values, percent change, and risk assessment."""
    args_schema: Type[BaseModel] = XGBoostToolInput

    def _run(self, patient_data: Dict[str, Any], lab_type: str) -> str:
        """
        Predict lab values using XGBoost models

        Args:
            patient_data: Patient data dict with demographics, labs, medications
            lab_type: 'creatinine', 'inr', or 'potassium'

        Returns:
            Prediction summary with risk assessment for lab_agent
        """
        try:
            if lab_type.lower() == 'creatinine':
                return self._predict_creatinine(patient_data)

            elif lab_type.lower() == 'inr':
                return self._predict_inr(patient_data)

            elif lab_type.lower() == 'potassium':
                return self._predict_potassium(patient_data)

            else:
                return f"""=== LAB PREDICTION ERROR ===
Unsupported lab type: '{lab_type}'

Supported types:
  - creatinine (AKI risk prediction)
  - inr (warfarin response)
  - potassium (electrolyte trend)
"""

        except Exception as e:
            return f"""=== LAB PREDICTION FAILED ===
Error: {str(e)}

Recommendation: Use clinical judgment and standard monitoring protocols.
"""

    def _predict_creatinine(self, patient_data: Dict[str, Any]) -> str:
        """Predict creatinine and AKI risk"""
        predictor = get_creatinine_predictor()
        result = predictor.predict_creatinine_24h(patient_data)

        baseline = result.get('baseline_cr', 0.0)
        predicted = result.get('predicted_cr', 0.0)
        change = result.get('percent_change', 0.0)
        aki_risk = result.get('aki_risk', 'unknown')
        confidence = result.get('confidence', 0.0)

        return f"""=== CREATININE PREDICTION (24h) ===

Baseline Cr:  {baseline:.2f} mg/dL
Predicted Cr: {predicted:.2f} mg/dL
Change:       {change:+.1f}%

AKI Risk:     {aki_risk.upper()}
Confidence:   {confidence:.1%}

Recommendation: {self._get_aki_recommendation(aki_risk, change)}
"""

    def _predict_inr(self, patient_data: Dict[str, Any]) -> str:
        """Predict INR response to warfarin dose change"""
        predictor = get_inr_predictor()

        current_inr = patient_data.get('labs', {}).get('inr', 2.0)
        current_dose = patient_data.get('drug_dose_mg', 5.0)
        new_dose = patient_data.get('new_dose_mg', 5.0)

        result = predictor.predict_inr(current_inr, current_dose, new_dose)

        return f"""=== INR PREDICTION (3 days) ===

Current INR:     {result['current_inr']:.1f}
Predicted INR:   {result['predicted_inr']:.1f}
Dose Change:     {result['dose_change_percent']:+.0f}%

Over-anticoag Risk: {result['over_anticoagulation_risk'].upper()}

Recommendation: {self._get_inr_recommendation(result['predicted_inr'])}
"""

    def _predict_potassium(self, patient_data: Dict[str, Any]) -> str:
        """Predict potassium trend (simplified model)"""
        # Simplified potassium prediction
        baseline_k = patient_data.get('labs', {}).get('potassium', 4.0)

        # Check for medications affecting K+
        meds = patient_data.get('medications', [])
        k_sparing = any('spironolactone' in m.lower() or 'amiloride' in m.lower() for m in meds)
        loop_diuretic = any('furosemide' in m.lower() or 'torsemide' in m.lower() for m in meds)

        if k_sparing:
            predicted_k = baseline_k + 0.3
            trend = "RISING"
        elif loop_diuretic:
            predicted_k = baseline_k - 0.4
            trend = "FALLING"
        else:
            predicted_k = baseline_k
            trend = "STABLE"

        return f"""=== POTASSIUM PREDICTION (24h) ===

Baseline K+:  {baseline_k:.1f} mEq/L
Predicted K+: {predicted_k:.1f} mEq/L
Trend:        {trend}

Recommendation: {self._get_potassium_recommendation(predicted_k, trend)}
"""

    def _get_aki_recommendation(self, aki_risk: str, change: float) -> str:
        """Generate AKI management recommendation"""
        if aki_risk.lower() == 'high' or change > 50:
            return "HIGH RISK. Consider dose reduction, increase monitoring, nephrology consult."
        elif aki_risk.lower() == 'moderate' or change > 25:
            return "Moderate risk. Daily Cr monitoring, ensure adequate hydration."
        else:
            return "Low risk. Continue standard monitoring."

    def _get_inr_recommendation(self, predicted_inr: float) -> str:
        """Generate warfarin dosing recommendation"""
        if predicted_inr > 3.5:
            return "RISK OF OVER-ANTICOAGULATION. Consider dose reduction."
        elif predicted_inr < 1.8:
            return "Risk of sub-therapeutic INR. Consider dose increase."
        else:
            return "INR within therapeutic range. Continue current dose."

    def _get_potassium_recommendation(self, predicted_k: float, trend: str) -> str:
        """Generate potassium management recommendation"""
        if predicted_k > 5.5:
            return "HYPERKALEMIA RISK. Monitor closely, consider K+ binder or dose adjustment."
        elif predicted_k < 3.0:
            return "HYPOKALEMIA RISK. Consider K+ supplementation."
        else:
            return "Potassium within normal range. Routine monitoring."


# Export
__all__ = ['XGBoostTool']


if __name__ == "__main__":
    print("XGBoost Tool - Lab Value Predictor")
    print("=" * 50)

    tool = XGBoostTool()
    print(f"Tool Name: {tool.name}")
    print(f"Description: {tool.description}")
    print("\nSupported predictions: creatinine, inr, potassium")
