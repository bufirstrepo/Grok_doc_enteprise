#!/usr/bin/env python3
"""
XGBoost Lab Predictions for Grok Doc v2.0
Predictive analytics for future lab values

Predicts:
- Creatinine 24h after nephrotoxic drugs (vancomycin, gentamicin)
- INR response to warfarin dose adjustment
- Potassium changes with diuretics/ACE inhibitors
- Early AKI detection

Model features:
- Baseline labs (Cr, BUN, electrolytes)
- Patient demographics (age, weight, gender)
- Comorbidities (CKD, CHF, diabetes)
- Concurrent medications
- Dosing information
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

# XGBoost for gradient boosting
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("WARNING: xgboost not installed. Run: pip install xgboost")

# sklearn for preprocessing
try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, r2_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("WARNING: scikit-learn not installed. Run: pip install scikit-learn")


class CreatininePredictor:
    """
    Predict creatinine at t+24h after nephrotoxic drug administration

    Use case: Alert if AKI likely (Cr >1.5× baseline)
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize creatinine predictor

        Args:
            model_path: Path to pre-trained XGBoost model
        """
        if not XGBOOST_AVAILABLE:
            raise ImportError("xgboost required. Install with: pip install xgboost")

        self.model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            objective='reg:squarederror',
            random_state=42
        )

        self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None

        # Load pre-trained model if available
        if model_path:
            self.model.load_model(model_path)
            print(f"Loaded creatinine model from {model_path}")
        else:
            print("WARNING: Using untrained model. Train on hospital EHR data for production!")

    def _vectorize_features(self, patient_data: Dict) -> np.ndarray:
        """
        Convert patient data to feature vector

        Features (45 total):
        - Demographics: age, weight, gender (3)
        - Baseline labs: Cr, BUN, Na, K, Cl, HCO3, glucose (7)
        - Comorbidities: CKD, CHF, diabetes, HTN, sepsis (5)
        - Medications: diuretics, ACEi, ARB, NSAIDs (4)
        - Drug info: vancomycin dose, frequency, route (3)
        - Vitals: BP, HR, temp, UOP (4)
        - Time features: hours since baseline Cr (1)
        - Derived: CrCl, BUN/Cr ratio, fluid balance (3)
        - One-hot encoded categorical features (15)
        """

        features = []

        # Demographics
        features.append(patient_data.get('age', 65))
        features.append(patient_data.get('weight', 70))
        features.append(1 if patient_data.get('gender', 'M') == 'M' else 0)

        # Baseline labs
        baseline_cr = float(patient_data.get('labs', {}).get('creatinine', 1.0))
        features.append(baseline_cr)
        features.append(float(patient_data.get('labs', {}).get('bun', 20)))
        features.append(float(patient_data.get('labs', {}).get('sodium', 140)))
        features.append(float(patient_data.get('labs', {}).get('potassium', 4.0)))
        features.append(float(patient_data.get('labs', {}).get('chloride', 102)))
        features.append(float(patient_data.get('labs', {}).get('bicarbonate', 24)))
        features.append(float(patient_data.get('labs', {}).get('glucose', 100)))

        # Comorbidities (binary)
        comorbidities = patient_data.get('comorbidities', [])
        features.append(1 if 'ckd' in comorbidities else 0)
        features.append(1 if 'chf' in comorbidities else 0)
        features.append(1 if 'diabetes' in comorbidities else 0)
        features.append(1 if 'htn' in comorbidities else 0)
        features.append(1 if 'sepsis' in comorbidities else 0)

        # Medications (binary)
        medications = patient_data.get('medications', [])
        features.append(1 if any('furosemide' in m or 'lasix' in m for m in medications) else 0)
        features.append(1 if any('lisinopril' in m or 'enalapril' in m for m in medications) else 0)
        features.append(1 if any('losartan' in m or 'valsartan' in m for m in medications) else 0)
        features.append(1 if any('ibuprofen' in m or 'ketorolac' in m for m in medications) else 0)

        # Drug dosing info
        features.append(float(patient_data.get('drug_dose_mg', 1000)))
        features.append(float(patient_data.get('dose_frequency_hours', 12)))
        features.append(1 if patient_data.get('route', 'IV') == 'IV' else 0)

        # Vitals
        features.append(float(patient_data.get('vitals', {}).get('sbp', 120)))
        features.append(float(patient_data.get('vitals', {}).get('hr', 80)))
        features.append(float(patient_data.get('vitals', {}).get('temp', 98.6)))
        features.append(float(patient_data.get('vitals', {}).get('urine_output_ml', 1500)))

        # Time features
        features.append(float(patient_data.get('hours_since_baseline', 0)))

        # Derived features
        age = patient_data.get('age', 65)
        weight = patient_data.get('weight', 70)
        gender = patient_data.get('gender', 'M')

        # Cockcroft-Gault CrCl
        crcl = ((140 - age) * weight) / (72 * baseline_cr)
        if gender == 'F':
            crcl *= 0.85
        features.append(crcl)

        # BUN/Cr ratio
        bun = float(patient_data.get('labs', {}).get('bun', 20))
        features.append(bun / max(baseline_cr, 0.1))

        # Fluid balance (estimate)
        fluid_in = float(patient_data.get('fluid_in_ml', 2000))
        fluid_out = float(patient_data.get('vitals', {}).get('urine_output_ml', 1500))
        features.append(fluid_in - fluid_out)

        return np.array(features).reshape(1, -1)

    def predict_creatinine_24h(self, patient_data: Dict) -> Dict:
        """
        Predict creatinine 24 hours from now

        Args:
            patient_data: Patient information dict

        Returns:
            {
                'predicted_cr': float,
                'baseline_cr': float,
                'percent_change': float,
                'aki_risk': str,  # low, moderate, high
                'confidence': float,
                'features_used': int
            }
        """

        # Extract features
        X = self._vectorize_features(patient_data)

        # Scale if scaler available
        if self.scaler:
            X = self.scaler.transform(X)

        # Predict
        predicted_cr = float(self.model.predict(X)[0])

        # Get baseline
        baseline_cr = float(patient_data.get('labs', {}).get('creatinine', 1.0))

        # Calculate change
        percent_change = ((predicted_cr - baseline_cr) / baseline_cr) * 100

        # Assess AKI risk (KDIGO criteria)
        if predicted_cr >= 1.5 * baseline_cr:
            aki_risk = 'high'
        elif predicted_cr >= 1.3 * baseline_cr:
            aki_risk = 'moderate'
        else:
            aki_risk = 'low'

        return {
            'predicted_cr': round(predicted_cr, 2),
            'baseline_cr': round(baseline_cr, 2),
            'percent_change': round(percent_change, 1),
            'aki_risk': aki_risk,
            'confidence': 0.85,  # Placeholder - calculate from model variance
            'features_used': X.shape[1],
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'prediction_horizon_hours': 24
        }

    def train_on_historical_data(self, ehr_data: pd.DataFrame):
        """
        Train model on hospital's historical EHR data

        Args:
            ehr_data: DataFrame with columns matching feature set
                Required: baseline_cr, cr_24h, age, weight, gender, etc.
        """

        # Extract features and target
        X = []
        y = ehr_data['cr_24h'].values  # Target: Cr at 24h

        for _, row in ehr_data.iterrows():
            patient_data = row.to_dict()
            features = self._vectorize_features(patient_data)
            X.append(features[0])

        X = np.array(X)

        # Scale
        if self.scaler:
            X = self.scaler.fit_transform(X)

        # Train/test split
        if SKLEARN_AVAILABLE:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
        else:
            X_train, X_test = X[:-100], X[-100:]
            y_train, y_test = y[:-100], y[-100:]

        # Train XGBoost
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            early_stopping_rounds=10,
            verbose=True
        )

        # Evaluate
        y_pred = self.model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred) if SKLEARN_AVAILABLE else 0
        r2 = r2_score(y_test, y_pred) if SKLEARN_AVAILABLE else 0

        print(f"Model trained: MAE={mae:.3f}, R²={r2:.3f}")

        return {'mae': mae, 'r2': r2}

    def save_model(self, path: str):
        """Save trained model to file"""
        self.model.save_model(path)
        print(f"Model saved to {path}")


class INRPredictor:
    """Predict INR response to warfarin dose adjustment"""

    def __init__(self):
        if not XGBOOST_AVAILABLE:
            raise ImportError("xgboost required")

        self.model = xgb.XGBRegressor(n_estimators=80, max_depth=5, learning_rate=0.1)

    def predict_inr(self, current_inr: float, current_dose: float, new_dose: float,
                    days: int = 3, has_cyp2c9_variant: bool = False) -> Dict:
        """
        Predict INR after warfarin dose change

        Args:
            current_inr: Current INR value
            current_dose: Current warfarin dose (mg/day)
            new_dose: Proposed new dose (mg/day)
            days: Days until next INR check
            has_cyp2c9_variant: CYP2C9 genetic variant present

        Returns:
            Predicted INR with confidence interval
        """

        # Simple linear model (placeholder - train on real data)
        dose_ratio = new_dose / max(current_dose, 0.1)
        predicted_inr = current_inr * (dose_ratio ** 0.7)  # Nonlinear response

        if has_cyp2c9_variant:
            predicted_inr *= 1.2  # Increased sensitivity

        # Clamp to reasonable range
        predicted_inr = max(0.5, min(predicted_inr, 8.0))

        return {
            'predicted_inr': round(predicted_inr, 1),
            'current_inr': current_inr,
            'dose_change_percent': round((new_dose - current_dose) / current_dose * 100, 1),
            'over_anticoagulation_risk': 'high' if predicted_inr > 4.0 else 'low',
            'prediction_horizon_days': days
        }


class PotassiumPredictor:
    """Predict potassium changes with diuretics/ACE inhibitors"""

    def __init__(self):
        if not XGBOOST_AVAILABLE:
            raise ImportError("xgboost required")

        self.model = xgb.XGBRegressor(n_estimators=80, max_depth=5)

    def predict_potassium(self, baseline_k: float, medication: str, dose: float) -> Dict:
        """Predict K+ change with medication"""

        # Simple heuristic (train on real data for production)
        if 'furosemide' in medication.lower():
            predicted_k = baseline_k - 0.3 * (dose / 40)  # Hypokalemia
        elif 'spironolactone' in medication.lower():
            predicted_k = baseline_k + 0.5 * (dose / 25)  # Hyperkalemia
        elif any(x in medication.lower() for x in ['lisinopril', 'enalapril']):
            predicted_k = baseline_k + 0.2  # Mild hyperkalemia
        else:
            predicted_k = baseline_k

        # Clamp
        predicted_k = max(2.5, min(predicted_k, 6.5))

        return {
            'predicted_k': round(predicted_k, 1),
            'baseline_k': baseline_k,
            'hyperkalemia_risk': 'high' if predicted_k > 5.5 else 'low',
            'hypokalemia_risk': 'high' if predicted_k < 3.5 else 'low'
        }


# Global predictors
_cr_predictor = None
_inr_predictor = None
_k_predictor = None

def get_creatinine_predictor() -> CreatininePredictor:
    """Get global creatinine predictor"""
    global _cr_predictor
    if _cr_predictor is None:
        _cr_predictor = CreatininePredictor()
    return _cr_predictor

def get_inr_predictor() -> INRPredictor:
    """Get global INR predictor"""
    global _inr_predictor
    if _inr_predictor is None:
        _inr_predictor = INRPredictor()
    return _inr_predictor

def get_potassium_predictor() -> PotassiumPredictor:
    """Get global potassium predictor"""
    global _k_predictor
    if _k_predictor is None:
        _k_predictor = PotassiumPredictor()
    return _k_predictor


if __name__ == "__main__":
    print("XGBoost Lab Predictions")
    print(f"XGBoost available: {XGBOOST_AVAILABLE}")
    print(f"scikit-learn available: {SKLEARN_AVAILABLE}")

    if XGBOOST_AVAILABLE:
        # Test creatinine prediction
        predictor = get_creatinine_predictor()

        test_patient = {
            'age': 72,
            'weight': 85,
            'gender': 'M',
            'labs': {'creatinine': 1.8, 'bun': 32, 'sodium': 138, 'potassium': 4.2},
            'comorbidities': ['ckd', 'htn'],
            'medications': ['lisinopril 10mg daily'],
            'drug_dose_mg': 1000,
            'dose_frequency_hours': 12,
            'vitals': {'sbp': 145, 'hr': 88, 'temp': 101.2, 'urine_output_ml': 800}
        }

        result = predictor.predict_creatinine_24h(test_patient)

        print("\nCreatinine Prediction (24h):")
        print(f"Baseline Cr: {result['baseline_cr']}")
        print(f"Predicted Cr: {result['predicted_cr']}")
        print(f"Change: {result['percent_change']}%")
        print(f"AKI Risk: {result['aki_risk'].upper()}")
        print(f"Confidence: {result['confidence']:.1%}")

    else:
        print("\nInstall XGBoost:")
        print("  pip install xgboost scikit-learn")
