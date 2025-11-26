"""
Continuous Learning Pipeline for Grok Doc v2.5

Captures clinical outcomes, compares predicted vs actual results,
updates Bayesian priors based on new evidence, and tracks model calibration.
"""

import sqlite3
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

from scipy.stats import beta as beta_dist
import numpy as np

OUTCOMES_DB_PATH = "outcomes.db"


class OutcomeType(Enum):
    """Types of clinical outcomes"""
    SAFE = "safe"
    ADVERSE = "adverse"
    UNKNOWN = "unknown"


@dataclass
class OutcomeRecord:
    """
    Captures outcome data after a clinical recommendation.
    
    Links back to the original decision via decision_hash from audit_log.
    """
    decision_hash: str
    mrn: str
    predicted_prob_safe: float
    predicted_risk_category: str
    actual_outcome: OutcomeType
    outcome_details: str
    days_to_outcome: int
    outcome_severity: int
    recorded_by: str
    recorded_at: str
    outcome_hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.outcome_hash:
            self.outcome_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute SHA-256 hash of outcome record for integrity verification"""
        hash_data = {
            "decision_hash": self.decision_hash,
            "mrn": self.mrn,
            "actual_outcome": self.actual_outcome.value if isinstance(self.actual_outcome, OutcomeType) else self.actual_outcome,
            "recorded_at": self.recorded_at
        }
        canonical_json = json.dumps(hash_data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        d = asdict(self)
        d['actual_outcome'] = self.actual_outcome.value if isinstance(self.actual_outcome, OutcomeType) else self.actual_outcome
        return d


@dataclass
class CalibrationBucket:
    """Tracks calibration for a specific probability range"""
    prob_low: float
    prob_high: float
    n_predictions: int = 0
    n_safe_outcomes: int = 0
    
    @property
    def observed_rate(self) -> float:
        """Observed safety rate in this bucket"""
        if self.n_predictions == 0:
            return 0.0
        return self.n_safe_outcomes / self.n_predictions
    
    @property
    def expected_rate(self) -> float:
        """Expected rate based on bucket midpoint"""
        return (self.prob_low + self.prob_high) / 2
    
    @property
    def calibration_error(self) -> float:
        """Absolute calibration error for this bucket"""
        return abs(self.observed_rate - self.expected_rate)


class CalibrationTracker:
    """
    Tracks prediction vs outcome calibration over time.
    
    Uses calibration buckets to measure how well predicted probabilities
    match actual outcome frequencies. Key metrics:
    - ECE (Expected Calibration Error): Weighted average calibration error
    - MCE (Maximum Calibration Error): Worst-case miscalibration
    """
    
    def __init__(self, n_buckets: int = 10):
        self.n_buckets = n_buckets
        self.buckets = self._init_buckets()
        self.history: List[Dict] = []
    
    def _init_buckets(self) -> List[CalibrationBucket]:
        """Initialize calibration buckets spanning [0, 1]"""
        buckets = []
        step = 1.0 / self.n_buckets
        for i in range(self.n_buckets):
            low = i * step
            high = (i + 1) * step
            buckets.append(CalibrationBucket(prob_low=low, prob_high=high))
        return buckets
    
    def add_prediction_outcome(
        self,
        predicted_prob_safe: float,
        actual_outcome: OutcomeType
    ) -> None:
        """Add a prediction-outcome pair to calibration tracking"""
        bucket_idx = min(int(predicted_prob_safe * self.n_buckets), self.n_buckets - 1)
        self.buckets[bucket_idx].n_predictions += 1
        if actual_outcome == OutcomeType.SAFE:
            self.buckets[bucket_idx].n_safe_outcomes += 1
    
    def compute_ece(self) -> float:
        """
        Compute Expected Calibration Error (ECE).
        
        ECE = Σ (n_i / N) * |acc_i - conf_i|
        
        Lower is better. Perfect calibration = 0.
        """
        total_predictions = sum(b.n_predictions for b in self.buckets)
        if total_predictions == 0:
            return 0.0
        
        ece = 0.0
        for bucket in self.buckets:
            if bucket.n_predictions > 0:
                weight = bucket.n_predictions / total_predictions
                ece += weight * bucket.calibration_error
        
        return ece
    
    def compute_mce(self) -> float:
        """
        Compute Maximum Calibration Error (MCE).
        
        MCE = max_i |acc_i - conf_i|
        
        Useful for identifying worst-case miscalibration.
        """
        errors = [b.calibration_error for b in self.buckets if b.n_predictions > 0]
        return max(errors) if errors else 0.0
    
    def compute_brier_score(self, outcomes: List[Tuple[float, OutcomeType]]) -> float:
        """
        Compute Brier score for a set of predictions.
        
        Brier = (1/N) Σ (p_i - o_i)²
        
        Lower is better. Perfect predictions = 0.
        """
        if not outcomes:
            return 0.0
        
        total = 0.0
        for pred_prob, actual in outcomes:
            actual_value = 1.0 if actual == OutcomeType.SAFE else 0.0
            total += (pred_prob - actual_value) ** 2
        
        return total / len(outcomes)
    
    def get_calibration_report(self) -> Dict[str, Any]:
        """Generate comprehensive calibration report"""
        bucket_details = []
        for b in self.buckets:
            if b.n_predictions > 0:
                bucket_details.append({
                    'range': f"{b.prob_low:.1%}-{b.prob_high:.1%}",
                    'n_predictions': b.n_predictions,
                    'n_safe_outcomes': b.n_safe_outcomes,
                    'observed_safe_rate': round(b.observed_rate, 4),
                    'expected_safe_rate': round(b.expected_rate, 4),
                    'calibration_error': round(b.calibration_error, 4)
                })
        
        return {
            'ece': round(self.compute_ece(), 4),
            'mce': round(self.compute_mce(), 4),
            'total_predictions': sum(b.n_predictions for b in self.buckets),
            'total_safe_outcomes': sum(b.n_safe_outcomes for b in self.buckets),
            'buckets': bucket_details,
            'timestamp': datetime.utcnow().isoformat() + "Z"
        }
    
    def snapshot(self) -> Dict[str, Any]:
        """Take a snapshot of current calibration state"""
        report = self.get_calibration_report()
        self.history.append(report)
        return report
    
    def reset(self) -> None:
        """Reset all calibration buckets"""
        self.buckets = self._init_buckets()
        self.history = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize tracker state"""
        return {
            'n_buckets': self.n_buckets,
            'buckets': [
                {
                    'prob_low': b.prob_low,
                    'prob_high': b.prob_high,
                    'n_predictions': b.n_predictions,
                    'n_safe_outcomes': b.n_safe_outcomes
                }
                for b in self.buckets
            ],
            'history': self.history
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CalibrationTracker':
        """Deserialize tracker from dict"""
        tracker = cls(n_buckets=data['n_buckets'])
        for i, b_data in enumerate(data['buckets']):
            tracker.buckets[i].n_predictions = b_data['n_predictions']
            tracker.buckets[i].n_safe_outcomes = b_data['n_safe_outcomes']
        tracker.history = data.get('history', [])
        return tracker


class BayesianUpdater:
    """
    Updates Bayesian priors based on observed outcomes.
    
    Implements Beta-Binomial conjugate prior updates:
    - Prior: Beta(alpha, beta)
    - Posterior: Beta(alpha + n_safe, beta + n_adverse)
    
    Uses exponential smoothing for incremental updates to prevent
    the prior from becoming too rigid as evidence accumulates.
    """
    
    def __init__(
        self,
        initial_alpha: float = 8.0,
        initial_beta: float = 2.0
    ):
        self.alpha = initial_alpha
        self.beta = initial_beta
        self.initial_alpha = initial_alpha
        self.initial_beta = initial_beta
        self.update_history: List[Dict] = []
        self.n_updates = 0
    
    def update_from_outcome(
        self,
        predicted_prob_safe: float,
        actual_outcome: OutcomeType,
        learning_rate: float = 0.1
    ) -> Dict[str, float]:
        """
        Update priors based on a single outcome observation.
        
        Uses exponential moving average to smoothly update priors,
        preventing the model from becoming too rigid.
        
        Args:
            predicted_prob_safe: Model's predicted probability
            actual_outcome: Actual observed outcome
            learning_rate: How much to weight new evidence (0-1)
        
        Returns:
            Dict with updated alpha, beta values
        """
        old_alpha = self.alpha
        old_beta = self.beta
        
        if actual_outcome == OutcomeType.SAFE:
            self.alpha = self.alpha + learning_rate
        elif actual_outcome == OutcomeType.ADVERSE:
            self.beta = self.beta + learning_rate
        
        self.n_updates += 1
        
        update_record = {
            'timestamp': datetime.utcnow().isoformat() + "Z",
            'update_number': self.n_updates,
            'predicted_prob': predicted_prob_safe,
            'outcome': actual_outcome.value if isinstance(actual_outcome, OutcomeType) else actual_outcome,
            'old_alpha': old_alpha,
            'old_beta': old_beta,
            'new_alpha': self.alpha,
            'new_beta': self.beta,
            'learning_rate': learning_rate
        }
        self.update_history.append(update_record)
        
        return {
            'alpha': self.alpha,
            'beta': self.beta,
            'prior_mean': self.alpha / (self.alpha + self.beta)
        }
    
    def batch_update(
        self,
        outcomes: List[Tuple[float, OutcomeType]],
        learning_rate: float = 0.1
    ) -> Dict[str, float]:
        """
        Batch update priors from multiple outcomes.
        
        Args:
            outcomes: List of (predicted_prob, actual_outcome) tuples
            learning_rate: Learning rate per outcome
        
        Returns:
            Final updated prior parameters
        """
        for pred_prob, outcome in outcomes:
            self.update_from_outcome(pred_prob, outcome, learning_rate)
        
        return self.get_current_prior()
    
    def get_current_prior(self) -> Dict[str, float]:
        """Get current prior parameters and derived statistics"""
        mean = self.alpha / (self.alpha + self.beta)
        variance = (self.alpha * self.beta) / (
            (self.alpha + self.beta) ** 2 * (self.alpha + self.beta + 1)
        )
        
        ci_low, ci_high = beta_dist.ppf([0.025, 0.975], self.alpha, self.beta)
        
        return {
            'alpha': self.alpha,
            'beta': self.beta,
            'prior_mean': round(mean, 4),
            'prior_variance': round(variance, 6),
            'ci_low': round(float(ci_low), 4),
            'ci_high': round(float(ci_high), 4),
            'n_updates': self.n_updates
        }
    
    def get_posterior_probability(
        self,
        n_safe: int,
        n_adverse: int
    ) -> Dict[str, float]:
        """
        Compute posterior probability given new observations.
        
        Uses current alpha/beta as prior and updates with observations.
        """
        post_alpha = self.alpha + n_safe
        post_beta = self.beta + n_adverse
        
        mean = post_alpha / (post_alpha + post_beta)
        ci_low, ci_high = beta_dist.ppf([0.025, 0.975], post_alpha, post_beta)
        
        return {
            'prob_safe': round(mean, 4),
            'ci_low': round(float(ci_low), 4),
            'ci_high': round(float(ci_high), 4),
            'posterior_alpha': post_alpha,
            'posterior_beta': post_beta
        }
    
    def reset_priors(
        self,
        alpha: Optional[float] = None,
        beta: Optional[float] = None
    ) -> None:
        """Reset priors to specified or initial values"""
        self.alpha = alpha if alpha is not None else self.initial_alpha
        self.beta = beta if beta is not None else self.initial_beta
        self.update_history = []
        self.n_updates = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize updater state"""
        return {
            'alpha': self.alpha,
            'beta': self.beta,
            'initial_alpha': self.initial_alpha,
            'initial_beta': self.initial_beta,
            'n_updates': self.n_updates,
            'update_history': self.update_history[-100:]  # Keep last 100
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BayesianUpdater':
        """Deserialize updater from dict"""
        updater = cls(
            initial_alpha=data.get('initial_alpha', 8.0),
            initial_beta=data.get('initial_beta', 2.0)
        )
        updater.alpha = data['alpha']
        updater.beta = data['beta']
        updater.n_updates = data.get('n_updates', 0)
        updater.update_history = data.get('update_history', [])
        return updater


def init_outcomes_db(db_path: str = OUTCOMES_DB_PATH) -> None:
    """Initialize SQLite database for outcomes and learning data"""
    conn = sqlite3.connect(db_path)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_hash TEXT NOT NULL,
            mrn TEXT NOT NULL,
            predicted_prob_safe REAL NOT NULL,
            predicted_risk_category TEXT,
            actual_outcome TEXT NOT NULL,
            outcome_details TEXT,
            days_to_outcome INTEGER,
            outcome_severity INTEGER,
            recorded_by TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            outcome_hash TEXT NOT NULL UNIQUE,
            metadata TEXT,
            UNIQUE(decision_hash, recorded_at)
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS calibration_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_at TEXT NOT NULL,
            ece REAL NOT NULL,
            mce REAL NOT NULL,
            total_predictions INTEGER,
            total_safe_outcomes INTEGER,
            bucket_data TEXT NOT NULL
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prior_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            updated_at TEXT NOT NULL,
            outcome_hash TEXT,
            old_alpha REAL NOT NULL,
            old_beta REAL NOT NULL,
            new_alpha REAL NOT NULL,
            new_beta REAL NOT NULL,
            learning_rate REAL NOT NULL
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generated_at TEXT NOT NULL,
            report_type TEXT NOT NULL,
            report_data TEXT NOT NULL
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            current_alpha REAL NOT NULL,
            current_beta REAL NOT NULL,
            n_updates INTEGER DEFAULT 0,
            last_updated TEXT NOT NULL
        )
    """)
    
    conn.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_mrn ON outcomes(mrn)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_decision ON outcomes(decision_hash)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_recorded ON outcomes(recorded_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_outcome ON outcomes(actual_outcome)")
    
    conn.commit()
    conn.close()


class LearningPipeline:
    """
    Main pipeline for continuous learning from clinical outcomes.
    
    Orchestrates:
    - Outcome capture and storage
    - Prediction vs outcome comparison
    - Bayesian prior updates
    - Calibration tracking
    - Learning report generation
    
    Example usage:
        pipeline = LearningPipeline()
        
        # Record an outcome
        record = pipeline.record_outcome(
            decision_hash="abc123...",
            mrn="MRN001",
            predicted_prob_safe=0.85,
            predicted_risk_category="Low Risk",
            actual_outcome=OutcomeType.SAFE,
            outcome_details="Patient tolerated treatment well",
            days_to_outcome=7,
            outcome_severity=1,
            recorded_by="Dr. Smith"
        )
        
        # Generate learning report
        report = pipeline.generate_learning_report()
    """
    
    def __init__(
        self,
        db_path: str = OUTCOMES_DB_PATH,
        initial_alpha: float = 8.0,
        initial_beta: float = 2.0,
        n_calibration_buckets: int = 10,
        learning_rate: float = 0.1
    ):
        self.db_path = db_path
        self.learning_rate = learning_rate
        self.bayesian_updater = BayesianUpdater(initial_alpha, initial_beta)
        self.calibration_tracker = CalibrationTracker(n_calibration_buckets)
        
        init_outcomes_db(db_path)
        self._load_state()
    
    def _load_state(self) -> None:
        """Load existing calibration and prior state from database"""
        conn = sqlite3.connect(self.db_path)
        
        try:
            cursor = conn.execute("""
                SELECT current_alpha, current_beta, n_updates
                FROM learning_state WHERE id = 1
            """)
            result = cursor.fetchone()
            if result:
                self.bayesian_updater.alpha = result[0]
                self.bayesian_updater.beta = result[1]
                self.bayesian_updater.n_updates = result[2]
            
            cursor = conn.execute("""
                SELECT predicted_prob_safe, actual_outcome FROM outcomes
            """)
            for row in cursor.fetchall():
                pred_prob = row[0]
                outcome_str = row[1]
                try:
                    outcome = OutcomeType(outcome_str)
                except ValueError:
                    outcome = OutcomeType.UNKNOWN
                if outcome != OutcomeType.UNKNOWN:
                    self.calibration_tracker.add_prediction_outcome(pred_prob, outcome)
        
        except sqlite3.OperationalError:
            pass
        finally:
            conn.close()
    
    def _save_state(self) -> None:
        """Persist current learning state to database"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO learning_state
                (id, current_alpha, current_beta, n_updates, last_updated)
                VALUES (1, ?, ?, ?, ?)
            """, (
                self.bayesian_updater.alpha,
                self.bayesian_updater.beta,
                self.bayesian_updater.n_updates,
                datetime.utcnow().isoformat() + "Z"
            ))
            conn.commit()
        finally:
            conn.close()
    
    def record_outcome(
        self,
        decision_hash: str,
        mrn: str,
        predicted_prob_safe: float,
        predicted_risk_category: str,
        actual_outcome: OutcomeType,
        outcome_details: str,
        days_to_outcome: int,
        outcome_severity: int,
        recorded_by: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> OutcomeRecord:
        """
        Record a clinical outcome after a recommendation.
        
        Args:
            decision_hash: Hash of the original decision (from audit_log)
            mrn: Patient MRN
            predicted_prob_safe: Original predicted safety probability
            predicted_risk_category: Original risk category
            actual_outcome: What actually happened (SAFE, ADVERSE, UNKNOWN)
            outcome_details: Description of outcome
            days_to_outcome: Days from recommendation to outcome
            outcome_severity: Severity 1-5 (1=mild, 5=severe)
            recorded_by: Physician recording outcome
            metadata: Optional additional data
        
        Returns:
            Created OutcomeRecord
        """
        recorded_at = datetime.utcnow().isoformat() + "Z"
        
        record = OutcomeRecord(
            decision_hash=decision_hash,
            mrn=mrn,
            predicted_prob_safe=predicted_prob_safe,
            predicted_risk_category=predicted_risk_category,
            actual_outcome=actual_outcome,
            outcome_details=outcome_details,
            days_to_outcome=days_to_outcome,
            outcome_severity=outcome_severity,
            recorded_by=recorded_by,
            recorded_at=recorded_at,
            metadata=metadata or {}
        )
        
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                INSERT INTO outcomes
                (decision_hash, mrn, predicted_prob_safe, predicted_risk_category,
                 actual_outcome, outcome_details, days_to_outcome, outcome_severity,
                 recorded_by, recorded_at, outcome_hash, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.decision_hash,
                record.mrn,
                record.predicted_prob_safe,
                record.predicted_risk_category,
                record.actual_outcome.value,
                record.outcome_details,
                record.days_to_outcome,
                record.outcome_severity,
                record.recorded_by,
                record.recorded_at,
                record.outcome_hash,
                json.dumps(record.metadata)
            ))
            conn.commit()
        except sqlite3.IntegrityError as e:
            conn.close()
            raise ValueError(f"Outcome already recorded: {e}")
        finally:
            conn.close()
        
        if actual_outcome != OutcomeType.UNKNOWN:
            self.calibration_tracker.add_prediction_outcome(
                predicted_prob_safe,
                actual_outcome
            )
            self._update_priors(record)
        
        return record
    
    def _update_priors(
        self,
        record: OutcomeRecord
    ) -> None:
        """Update Bayesian priors based on outcome"""
        old_alpha = self.bayesian_updater.alpha
        old_beta = self.bayesian_updater.beta
        
        self.bayesian_updater.update_from_outcome(
            record.predicted_prob_safe,
            record.actual_outcome,
            self.learning_rate
        )
        
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                INSERT INTO prior_updates
                (updated_at, outcome_hash, old_alpha, old_beta, new_alpha, new_beta, learning_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.utcnow().isoformat() + "Z",
                record.outcome_hash,
                old_alpha,
                old_beta,
                self.bayesian_updater.alpha,
                self.bayesian_updater.beta,
                self.learning_rate
            ))
            conn.commit()
        finally:
            conn.close()
        
        self._save_state()
    
    def compare_prediction_outcome(
        self,
        decision_hash: str
    ) -> Optional[Dict[str, Any]]:
        """
        Compare predicted vs actual outcome for a decision.
        
        Args:
            decision_hash: Hash of the original decision
        
        Returns:
            Comparison dict or None if outcome not recorded
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("""
                SELECT predicted_prob_safe, predicted_risk_category,
                       actual_outcome, outcome_severity, outcome_details
                FROM outcomes
                WHERE decision_hash = ?
                ORDER BY recorded_at DESC LIMIT 1
            """, (decision_hash,))
            
            result = cursor.fetchone()
            if not result:
                return None
            
            predicted_prob = result[0]
            predicted_category = result[1]
            actual_outcome = result[2]
            severity = result[3]
            details = result[4]
            
            actual_safe = 1.0 if actual_outcome == OutcomeType.SAFE.value else 0.0
            prediction_error = abs(predicted_prob - actual_safe)
            
            predicted_safe = predicted_prob >= 0.5
            actual_was_safe = actual_outcome == OutcomeType.SAFE.value
            correct = predicted_safe == actual_was_safe
            
            return {
                'decision_hash': decision_hash,
                'predicted_prob_safe': predicted_prob,
                'predicted_risk_category': predicted_category,
                'actual_outcome': actual_outcome,
                'outcome_severity': severity,
                'outcome_details': details,
                'prediction_error': round(prediction_error, 4),
                'prediction_correct': correct,
                'brier_score': round(prediction_error ** 2, 4)
            }
        finally:
            conn.close()
    
    def get_current_priors(self) -> Dict[str, float]:
        """Get current Bayesian prior parameters"""
        return self.bayesian_updater.get_current_prior()
    
    def get_calibration_report(self) -> Dict[str, Any]:
        """Get current calibration report"""
        return self.calibration_tracker.get_calibration_report()
    
    def generate_learning_report(
        self,
        report_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """
        Generate a learning report.
        
        Args:
            report_type: Type of report ("comprehensive", "calibration", "outcomes", "summary")
        
        Returns:
            Report dictionary
        """
        conn = sqlite3.connect(self.db_path)
        
        try:
            cursor = conn.execute("""
                SELECT actual_outcome, COUNT(*) as count
                FROM outcomes
                GROUP BY actual_outcome
            """)
            outcome_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            cursor = conn.execute("""
                SELECT predicted_prob_safe, actual_outcome
                FROM outcomes WHERE actual_outcome != 'unknown'
            """)
            
            total_error = 0.0
            n_outcomes = 0
            n_correct = 0
            
            for row in cursor.fetchall():
                pred_prob = row[0]
                actual = row[1]
                actual_safe = 1.0 if actual == OutcomeType.SAFE.value else 0.0
                total_error += (pred_prob - actual_safe) ** 2
                n_outcomes += 1
                
                predicted_safe = pred_prob >= 0.5
                actual_was_safe = actual == OutcomeType.SAFE.value
                if predicted_safe == actual_was_safe:
                    n_correct += 1
            
            avg_brier_score = total_error / n_outcomes if n_outcomes > 0 else 0.0
            accuracy = n_correct / n_outcomes if n_outcomes > 0 else 0.0
            
            cursor = conn.execute("""
                SELECT AVG(outcome_severity) as avg_severity,
                       MIN(outcome_severity) as min_severity,
                       MAX(outcome_severity) as max_severity
                FROM outcomes WHERE actual_outcome = 'adverse'
            """)
            severity_stats = cursor.fetchone()
            
            report = {
                'report_type': report_type,
                'generated_at': datetime.utcnow().isoformat() + "Z",
                'total_outcomes': n_outcomes + outcome_counts.get(OutcomeType.UNKNOWN.value, 0),
                'evaluated_outcomes': n_outcomes,
                'outcome_distribution': outcome_counts,
                'model_performance': {
                    'brier_score': round(avg_brier_score, 4),
                    'accuracy': round(accuracy, 4),
                    'n_correct': n_correct,
                    'n_evaluated': n_outcomes
                },
                'calibration': self.calibration_tracker.get_calibration_report(),
                'current_priors': self.bayesian_updater.get_current_prior()
            }
            
            if severity_stats and severity_stats[0] is not None:
                report['severity_analysis'] = {
                    'avg_adverse_severity': round(severity_stats[0], 2),
                    'min_adverse_severity': severity_stats[1],
                    'max_adverse_severity': severity_stats[2]
                }
            
            if report_type == "comprehensive":
                cursor = conn.execute("""
                    SELECT date(recorded_at) as date,
                           COUNT(*) as count,
                           SUM(CASE WHEN actual_outcome = 'safe' THEN 1 ELSE 0 END) as safe_count,
                           SUM(CASE WHEN actual_outcome = 'adverse' THEN 1 ELSE 0 END) as adverse_count,
                           AVG(predicted_prob_safe) as avg_prediction
                    FROM outcomes
                    GROUP BY date(recorded_at)
                    ORDER BY date DESC
                    LIMIT 30
                """)
                report['daily_stats'] = [
                    {
                        'date': row[0],
                        'count': row[1],
                        'safe_count': row[2],
                        'adverse_count': row[3],
                        'avg_prediction': round(row[4], 4) if row[4] else None
                    }
                    for row in cursor.fetchall()
                ]
                
                cursor = conn.execute("""
                    SELECT predicted_risk_category,
                           COUNT(*) as count,
                           SUM(CASE WHEN actual_outcome = 'safe' THEN 1 ELSE 0 END) as safe_count,
                           SUM(CASE WHEN actual_outcome = 'adverse' THEN 1 ELSE 0 END) as adverse_count
                    FROM outcomes
                    GROUP BY predicted_risk_category
                """)
                report['risk_category_performance'] = [
                    {
                        'category': row[0],
                        'count': row[1],
                        'safe_count': row[2],
                        'adverse_count': row[3],
                        'accuracy': round(row[2] / row[1], 4) if row[1] > 0 else 0
                    }
                    for row in cursor.fetchall()
                ]
            
            conn.execute("""
                INSERT INTO learning_reports (generated_at, report_type, report_data)
                VALUES (?, ?, ?)
            """, (report['generated_at'], report_type, json.dumps(report)))
            conn.commit()
            
            return report
        
        finally:
            conn.close()
    
    def get_patient_outcomes(
        self,
        mrn: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get outcome history for a patient"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("""
                SELECT decision_hash, predicted_prob_safe, predicted_risk_category,
                       actual_outcome, outcome_details, days_to_outcome,
                       outcome_severity, recorded_at, recorded_by
                FROM outcomes
                WHERE mrn = ?
                ORDER BY recorded_at DESC
                LIMIT ?
            """, (mrn, limit))
            
            return [
                {
                    'decision_hash': row[0],
                    'predicted_prob_safe': row[1],
                    'predicted_risk_category': row[2],
                    'actual_outcome': row[3],
                    'outcome_details': row[4],
                    'days_to_outcome': row[5],
                    'outcome_severity': row[6],
                    'recorded_at': row[7],
                    'recorded_by': row[8]
                }
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()
    
    def export_outcomes(
        self,
        output_path: str = "outcomes_export.json"
    ) -> Dict[str, Any]:
        """Export all outcomes for external analysis"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("""
                SELECT decision_hash, mrn, predicted_prob_safe, predicted_risk_category,
                       actual_outcome, outcome_details, days_to_outcome, outcome_severity,
                       recorded_by, recorded_at, outcome_hash, metadata
                FROM outcomes ORDER BY recorded_at ASC
            """)
            
            outcomes = [
                {
                    'decision_hash': row[0],
                    'mrn': row[1],
                    'predicted_prob_safe': row[2],
                    'predicted_risk_category': row[3],
                    'actual_outcome': row[4],
                    'outcome_details': row[5],
                    'days_to_outcome': row[6],
                    'outcome_severity': row[7],
                    'recorded_by': row[8],
                    'recorded_at': row[9],
                    'outcome_hash': row[10],
                    'metadata': json.loads(row[11]) if row[11] else {}
                }
                for row in cursor.fetchall()
            ]
            
            export_data = {
                'export_timestamp': datetime.utcnow().isoformat() + "Z",
                'total_outcomes': len(outcomes),
                'calibration': self.calibration_tracker.get_calibration_report(),
                'current_priors': self.bayesian_updater.get_current_prior(),
                'outcomes': outcomes
            }
            
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            return export_data
        
        finally:
            conn.close()
    
    def take_calibration_snapshot(self) -> Dict[str, Any]:
        """Take and persist a calibration snapshot"""
        report = self.calibration_tracker.snapshot()
        
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                INSERT INTO calibration_snapshots
                (snapshot_at, ece, mce, total_predictions, total_safe_outcomes, bucket_data)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                report['timestamp'],
                report['ece'],
                report['mce'],
                report['total_predictions'],
                report['total_safe_outcomes'],
                json.dumps(report['buckets'])
            ))
            conn.commit()
        finally:
            conn.close()
        
        return report
    
    def get_calibration_history(
        self,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """Get historical calibration snapshots"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("""
                SELECT snapshot_at, ece, mce, total_predictions, total_safe_outcomes
                FROM calibration_snapshots
                ORDER BY snapshot_at DESC
                LIMIT ?
            """, (limit,))
            
            return [
                {
                    'snapshot_at': row[0],
                    'ece': row[1],
                    'mce': row[2],
                    'total_predictions': row[3],
                    'total_safe_outcomes': row[4]
                }
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()
    
    def get_prior_history(
        self,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get history of Bayesian prior updates"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("""
                SELECT updated_at, old_alpha, old_beta, new_alpha, new_beta, learning_rate
                FROM prior_updates
                ORDER BY updated_at DESC
                LIMIT ?
            """, (limit,))
            
            return [
                {
                    'updated_at': row[0],
                    'old_alpha': row[1],
                    'old_beta': row[2],
                    'new_alpha': row[3],
                    'new_beta': row[4],
                    'learning_rate': row[5],
                    'old_mean': round(row[1] / (row[1] + row[2]), 4),
                    'new_mean': round(row[3] / (row[3] + row[4]), 4)
                }
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()
    
    def verify_outcome_integrity(self) -> Dict[str, Any]:
        """Verify integrity of stored outcomes by recomputing hashes"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("""
                SELECT id, decision_hash, mrn, actual_outcome, recorded_at, outcome_hash
                FROM outcomes ORDER BY id
            """)
            
            total = 0
            valid = 0
            invalid_ids = []
            
            for row in cursor.fetchall():
                total += 1
                hash_data = {
                    "decision_hash": row[1],
                    "mrn": row[2],
                    "actual_outcome": row[3],
                    "recorded_at": row[4]
                }
                canonical_json = json.dumps(hash_data, sort_keys=True, separators=(',', ':'))
                computed_hash = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
                
                if computed_hash == row[5]:
                    valid += 1
                else:
                    invalid_ids.append(row[0])
            
            return {
                'valid': len(invalid_ids) == 0,
                'total_outcomes': total,
                'valid_outcomes': valid,
                'invalid_ids': invalid_ids,
                'verified_at': datetime.utcnow().isoformat() + "Z"
            }
        finally:
            conn.close()


def create_learning_pipeline(
    db_path: str = OUTCOMES_DB_PATH,
    initial_alpha: float = 8.0,
    initial_beta: float = 2.0
) -> LearningPipeline:
    """Factory function to create a LearningPipeline with defaults"""
    return LearningPipeline(
        db_path=db_path,
        initial_alpha=initial_alpha,
        initial_beta=initial_beta
    )
