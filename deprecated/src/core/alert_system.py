"""
Alert and Notification System for Grok Doc v2.5

Handles critical clinical findings with:
- Multi-level severity alerts
- Multiple notification channels
- Alert acknowledgment tracking
- Auto-escalation for unacknowledged critical alerts
- SQLite persistence
"""

import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

ALERTS_DB_PATH = "alerts.db"


class AlertSeverity(Enum):
    """Alert severity levels for clinical findings"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    
    @property
    def priority(self) -> int:
        """Numeric priority for sorting (lower = higher priority)"""
        priorities = {
            "critical": 1,
            "high": 2,
            "medium": 3,
            "low": 4,
            "info": 5
        }
        return priorities.get(self.value, 5)
    
    @property
    def escalation_threshold_minutes(self) -> Optional[int]:
        """Minutes before auto-escalation (None = no escalation)"""
        thresholds = {
            "critical": 5,
            "high": 15,
            "medium": 60,
            "low": None,
            "info": None
        }
        return thresholds.get(self.value)


class AlertStatus(Enum):
    """Alert lifecycle status"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    EXPIRED = "expired"


class NotificationChannel(Enum):
    """Supported notification channels"""
    IN_APP = "in_app"
    SMS = "sms"
    EMAIL = "email"
    PAGER = "pager"
    EHR_INBOX = "ehr_inbox"


class AlertType(Enum):
    """Types of clinical alerts"""
    CRITICAL_LAB = "critical_lab"
    ABNORMAL_VITAL = "abnormal_vital"
    DRUG_INTERACTION = "drug_interaction"
    ALLERGY_WARNING = "allergy_warning"
    BAYESIAN_RISK = "bayesian_risk"
    AI_INSIGHT = "ai_insight"
    IMAGING_FINDING = "imaging_finding"
    SEPSIS_RISK = "sepsis_risk"
    DETERIORATION = "deterioration"
    MEDICATION_DUE = "medication_due"
    FOLLOW_UP_REQUIRED = "follow_up_required"
    SYSTEM = "system"


@dataclass
class Alert:
    """Clinical alert with full tracking"""
    id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    patient_mrn: Optional[str]
    source: str
    status: AlertStatus = AlertStatus.ACTIVE
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    acknowledged_at: Optional[str] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    escalated: bool = False
    escalation_count: int = 0
    last_escalation_at: Optional[str] = None
    notification_channels: List[NotificationChannel] = field(default_factory=list)
    notifications_sent: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    related_alerts: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if isinstance(self.alert_type, str):
            self.alert_type = AlertType(self.alert_type)
        if isinstance(self.severity, str):
            self.severity = AlertSeverity(self.severity)
        if isinstance(self.status, str):
            self.status = AlertStatus(self.status)
        if self.notification_channels and isinstance(self.notification_channels[0], str):
            self.notification_channels = [NotificationChannel(ch) for ch in self.notification_channels]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'alert_type': self.alert_type.value,
            'severity': self.severity.value,
            'title': self.title,
            'message': self.message,
            'patient_mrn': self.patient_mrn,
            'source': self.source,
            'status': self.status.value,
            'created_at': self.created_at,
            'acknowledged_at': self.acknowledged_at,
            'acknowledged_by': self.acknowledged_by,
            'resolved_at': self.resolved_at,
            'resolved_by': self.resolved_by,
            'escalated': self.escalated,
            'escalation_count': self.escalation_count,
            'last_escalation_at': self.last_escalation_at,
            'notification_channels': [ch.value for ch in self.notification_channels],
            'notifications_sent': self.notifications_sent,
            'metadata': self.metadata,
            'related_alerts': self.related_alerts
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Alert':
        """Create Alert from dictionary"""
        data = data.copy()
        if 'notification_channels' in data:
            data['notification_channels'] = [
                NotificationChannel(ch) if isinstance(ch, str) else ch
                for ch in data['notification_channels']
            ]
        return cls(**data)
    
    def requires_immediate_attention(self) -> bool:
        """Check if alert requires immediate clinical attention"""
        return (
            self.severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH] and
            self.status == AlertStatus.ACTIVE
        )
    
    def is_overdue_for_escalation(self) -> bool:
        """Check if alert should be escalated based on time threshold"""
        threshold = self.severity.escalation_threshold_minutes
        if threshold is None or self.status != AlertStatus.ACTIVE:
            return False
        
        created = datetime.fromisoformat(self.created_at.replace('Z', '+00:00'))
        deadline = created + timedelta(minutes=threshold)
        return datetime.now(created.tzinfo) > deadline
    
    def compute_hash(self) -> str:
        """Compute hash for deduplication"""
        hash_data = {
            'alert_type': self.alert_type.value,
            'severity': self.severity.value,
            'patient_mrn': self.patient_mrn,
            'title': self.title,
            'source': self.source
        }
        canonical = json.dumps(hash_data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]


class AlertManager:
    """
    Manages alert lifecycle including creation, acknowledgment, 
    escalation, and persistence.
    """
    
    def __init__(self, db_path: str = ALERTS_DB_PATH):
        self.db_path = db_path
        self._notification_handlers: Dict[NotificationChannel, Callable] = {}
        self._escalation_handlers: List[Callable] = []
        self.init_db()
    
    def init_db(self):
        """Initialize SQLite database with proper schema"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                patient_mrn TEXT,
                source TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                acknowledged_at TEXT,
                acknowledged_by TEXT,
                resolved_at TEXT,
                resolved_by TEXT,
                escalated BOOLEAN DEFAULT FALSE,
                escalation_count INTEGER DEFAULT 0,
                last_escalation_at TEXT,
                notification_channels TEXT,
                notifications_sent TEXT,
                metadata TEXT,
                related_alerts TEXT,
                alert_hash TEXT
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alert_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT NOT NULL,
                action TEXT NOT NULL,
                actor TEXT,
                timestamp TEXT NOT NULL,
                details TEXT,
                FOREIGN KEY (alert_id) REFERENCES alerts(id)
            )
        """)
        
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_mrn ON alerts(patient_mrn)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alert_hash ON alerts(alert_hash)")
        
        conn.commit()
        conn.close()
    
    def register_notification_handler(
        self,
        channel: NotificationChannel,
        handler: Callable[[Alert], bool]
    ):
        """Register a notification handler for a channel"""
        self._notification_handlers[channel] = handler
    
    def register_escalation_handler(self, handler: Callable[[Alert], None]):
        """Register an escalation handler"""
        self._escalation_handlers.append(handler)
    
    def create_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: str,
        patient_mrn: Optional[str] = None,
        source: str = "system",
        notification_channels: Optional[List[NotificationChannel]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        deduplicate: bool = True
    ) -> Alert:
        """
        Create and persist a new alert.
        
        Args:
            alert_type: Type of clinical alert
            severity: Alert severity level
            title: Short alert title
            message: Detailed alert message
            patient_mrn: Patient MRN if patient-specific
            source: Source system/module
            notification_channels: Channels to notify
            metadata: Additional context data
            deduplicate: Skip if similar active alert exists
            
        Returns:
            Created Alert object
        """
        if notification_channels is None:
            notification_channels = self._get_default_channels(severity)
        
        alert = Alert(
            id=str(uuid.uuid4()),
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            patient_mrn=patient_mrn,
            source=source,
            notification_channels=notification_channels,
            metadata=metadata or {}
        )
        
        if deduplicate:
            existing = self._find_duplicate(alert)
            if existing:
                return existing
        
        self._persist_alert(alert)
        self._log_history(alert.id, "created", None, {"severity": severity.value})
        self._send_notifications(alert)
        
        return alert
    
    def _get_default_channels(self, severity: AlertSeverity) -> List[NotificationChannel]:
        """Get default notification channels based on severity"""
        defaults = {
            AlertSeverity.CRITICAL: [
                NotificationChannel.IN_APP,
                NotificationChannel.SMS,
                NotificationChannel.PAGER
            ],
            AlertSeverity.HIGH: [
                NotificationChannel.IN_APP,
                NotificationChannel.SMS
            ],
            AlertSeverity.MEDIUM: [
                NotificationChannel.IN_APP,
                NotificationChannel.EMAIL
            ],
            AlertSeverity.LOW: [NotificationChannel.IN_APP],
            AlertSeverity.INFO: [NotificationChannel.IN_APP]
        }
        return defaults.get(severity, [NotificationChannel.IN_APP])
    
    def _find_duplicate(self, alert: Alert) -> Optional[Alert]:
        """Find existing active alert with same hash"""
        alert_hash = alert.compute_hash()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT * FROM alerts 
            WHERE alert_hash = ? AND status = 'active'
            ORDER BY created_at DESC LIMIT 1
        """, (alert_hash,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_alert(row)
        return None
    
    def _persist_alert(self, alert: Alert):
        """Save alert to database"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO alerts (
                id, alert_type, severity, title, message, patient_mrn,
                source, status, created_at, acknowledged_at, acknowledged_by,
                resolved_at, resolved_by, escalated, escalation_count,
                last_escalation_at, notification_channels, notifications_sent,
                metadata, related_alerts, alert_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            alert.id,
            alert.alert_type.value,
            alert.severity.value,
            alert.title,
            alert.message,
            alert.patient_mrn,
            alert.source,
            alert.status.value,
            alert.created_at,
            alert.acknowledged_at,
            alert.acknowledged_by,
            alert.resolved_at,
            alert.resolved_by,
            alert.escalated,
            alert.escalation_count,
            alert.last_escalation_at,
            json.dumps([ch.value for ch in alert.notification_channels]),
            json.dumps(alert.notifications_sent),
            json.dumps(alert.metadata),
            json.dumps(alert.related_alerts),
            alert.compute_hash()
        ))
        conn.commit()
        conn.close()
    
    def _update_alert(self, alert: Alert):
        """Update existing alert in database"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE alerts SET
                status = ?,
                acknowledged_at = ?,
                acknowledged_by = ?,
                resolved_at = ?,
                resolved_by = ?,
                escalated = ?,
                escalation_count = ?,
                last_escalation_at = ?,
                notifications_sent = ?,
                metadata = ?,
                related_alerts = ?
            WHERE id = ?
        """, (
            alert.status.value,
            alert.acknowledged_at,
            alert.acknowledged_by,
            alert.resolved_at,
            alert.resolved_by,
            alert.escalated,
            alert.escalation_count,
            alert.last_escalation_at,
            json.dumps(alert.notifications_sent),
            json.dumps(alert.metadata),
            json.dumps(alert.related_alerts),
            alert.id
        ))
        conn.commit()
        conn.close()
    
    def _log_history(
        self,
        alert_id: str,
        action: str,
        actor: Optional[str],
        details: Optional[Dict] = None
    ):
        """Log alert action to history"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO alert_history (alert_id, action, actor, timestamp, details)
            VALUES (?, ?, ?, ?, ?)
        """, (
            alert_id,
            action,
            actor,
            datetime.utcnow().isoformat() + "Z",
            json.dumps(details or {})
        ))
        conn.commit()
        conn.close()
    
    def _send_notifications(self, alert: Alert):
        """Send notifications through configured channels"""
        for channel in alert.notification_channels:
            handler = self._notification_handlers.get(channel)
            if handler:
                try:
                    success = handler(alert)
                    alert.notifications_sent.append({
                        'channel': channel.value,
                        'sent_at': datetime.utcnow().isoformat() + "Z",
                        'success': success
                    })
                except Exception as e:
                    alert.notifications_sent.append({
                        'channel': channel.value,
                        'sent_at': datetime.utcnow().isoformat() + "Z",
                        'success': False,
                        'error': str(e)
                    })
            else:
                alert.notifications_sent.append({
                    'channel': channel.value,
                    'sent_at': datetime.utcnow().isoformat() + "Z",
                    'success': True,
                    'note': 'placeholder_handler'
                })
        
        self._update_alert(alert)
    
    def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str,
        notes: Optional[str] = None
    ) -> Optional[Alert]:
        """
        Acknowledge an alert.
        
        Args:
            alert_id: Alert ID to acknowledge
            acknowledged_by: User/system acknowledging
            notes: Optional acknowledgment notes
            
        Returns:
            Updated Alert or None if not found
        """
        alert = self.get_alert(alert_id)
        if not alert:
            return None
        
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.utcnow().isoformat() + "Z"
        alert.acknowledged_by = acknowledged_by
        
        if notes:
            alert.metadata['acknowledgment_notes'] = notes
        
        self._update_alert(alert)
        self._log_history(alert_id, "acknowledged", acknowledged_by, {"notes": notes})
        
        return alert
    
    def resolve_alert(
        self,
        alert_id: str,
        resolved_by: str,
        resolution: Optional[str] = None
    ) -> Optional[Alert]:
        """
        Resolve an alert.
        
        Args:
            alert_id: Alert ID to resolve
            resolved_by: User/system resolving
            resolution: Optional resolution notes
            
        Returns:
            Updated Alert or None if not found
        """
        alert = self.get_alert(alert_id)
        if not alert:
            return None
        
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.utcnow().isoformat() + "Z"
        alert.resolved_by = resolved_by
        
        if resolution:
            alert.metadata['resolution'] = resolution
        
        self._update_alert(alert)
        self._log_history(alert_id, "resolved", resolved_by, {"resolution": resolution})
        
        return alert
    
    def escalate_alert(self, alert_id: str, reason: Optional[str] = None) -> Optional[Alert]:
        """
        Escalate an unacknowledged alert.
        
        Args:
            alert_id: Alert ID to escalate
            reason: Reason for escalation
            
        Returns:
            Updated Alert or None if not found
        """
        alert = self.get_alert(alert_id)
        if not alert:
            return None
        
        alert.escalated = True
        alert.escalation_count += 1
        alert.last_escalation_at = datetime.utcnow().isoformat() + "Z"
        
        if alert.escalation_count >= 3:
            alert.status = AlertStatus.ESCALATED
        
        if reason:
            alert.metadata['escalation_reason'] = reason
        
        for handler in self._escalation_handlers:
            try:
                handler(alert)
            except Exception as e:
                alert.metadata['escalation_error'] = str(e)
        
        self._update_alert(alert)
        self._log_history(
            alert_id,
            "escalated",
            "system",
            {"count": alert.escalation_count, "reason": reason}
        )
        
        return alert
    
    def auto_escalate(self) -> List[Alert]:
        """
        Check and escalate overdue alerts.
        
        Returns:
            List of escalated alerts
        """
        escalated = []
        active_alerts = self.get_alerts(status=AlertStatus.ACTIVE)
        
        for alert in active_alerts:
            if alert.is_overdue_for_escalation():
                escalated_alert = self.escalate_alert(
                    alert.id,
                    reason="Auto-escalation: acknowledgment threshold exceeded"
                )
                if escalated_alert:
                    escalated.append(escalated_alert)
        
        return escalated
    
    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get single alert by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_alert(row)
        return None
    
    def get_alerts(
        self,
        patient_mrn: Optional[str] = None,
        status: Optional[AlertStatus] = None,
        severity: Optional[AlertSeverity] = None,
        alert_type: Optional[AlertType] = None,
        since: Optional[str] = None,
        limit: int = 100
    ) -> List[Alert]:
        """
        Query alerts with filters.
        
        Args:
            patient_mrn: Filter by patient
            status: Filter by status
            severity: Filter by severity
            alert_type: Filter by type
            since: Filter by created_at >= timestamp
            limit: Maximum results
            
        Returns:
            List of matching alerts
        """
        query = "SELECT * FROM alerts WHERE 1=1"
        params = []
        
        if patient_mrn:
            query += " AND patient_mrn = ?"
            params.append(patient_mrn)
        
        if status:
            query += " AND status = ?"
            params.append(status.value)
        
        if severity:
            query += " AND severity = ?"
            params.append(severity.value)
        
        if alert_type:
            query += " AND alert_type = ?"
            params.append(alert_type.value)
        
        if since:
            query += " AND created_at >= ?"
            params.append(since)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_alert(row) for row in rows]
    
    def get_unacknowledged_critical(self) -> List[Alert]:
        """Get all unacknowledged critical and high alerts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT * FROM alerts 
            WHERE status = 'active' 
            AND severity IN ('critical', 'high')
            ORDER BY 
                CASE severity 
                    WHEN 'critical' THEN 1 
                    WHEN 'high' THEN 2 
                END,
                created_at ASC
        """)
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_alert(row) for row in rows]
    
    def get_patient_alert_summary(self, patient_mrn: str) -> Dict[str, Any]:
        """Get alert summary for a patient"""
        alerts = self.get_alerts(patient_mrn=patient_mrn)
        
        by_severity = {}
        by_status = {}
        
        for alert in alerts:
            sev = alert.severity.value
            by_severity[sev] = by_severity.get(sev, 0) + 1
            
            stat = alert.status.value
            by_status[stat] = by_status.get(stat, 0) + 1
        
        active_critical = [
            a for a in alerts
            if a.status == AlertStatus.ACTIVE and
            a.severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]
        ]
        
        return {
            'patient_mrn': patient_mrn,
            'total_alerts': len(alerts),
            'by_severity': by_severity,
            'by_status': by_status,
            'active_critical_count': len(active_critical),
            'active_critical': [a.to_dict() for a in active_critical[:5]],
            'requires_attention': len(active_critical) > 0
        }
    
    def get_alert_history(self, alert_id: str) -> List[Dict[str, Any]]:
        """Get action history for an alert"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT action, actor, timestamp, details
            FROM alert_history
            WHERE alert_id = ?
            ORDER BY timestamp ASC
        """, (alert_id,))
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'action': row[0],
                'actor': row[1],
                'timestamp': row[2],
                'details': json.loads(row[3]) if row[3] else {}
            }
            for row in rows
        ]
    
    def _row_to_alert(self, row) -> Alert:
        """Convert database row to Alert object"""
        return Alert(
            id=row[0],
            alert_type=AlertType(row[1]),
            severity=AlertSeverity(row[2]),
            title=row[3],
            message=row[4],
            patient_mrn=row[5],
            source=row[6],
            status=AlertStatus(row[7]),
            created_at=row[8],
            acknowledged_at=row[9],
            acknowledged_by=row[10],
            resolved_at=row[11],
            resolved_by=row[12],
            escalated=bool(row[13]),
            escalation_count=row[14],
            last_escalation_at=row[15],
            notification_channels=[
                NotificationChannel(ch) for ch in json.loads(row[16] or "[]")
            ],
            notifications_sent=json.loads(row[17] or "[]"),
            metadata=json.loads(row[18] or "{}"),
            related_alerts=json.loads(row[19] or "[]")
        )
    
    def cleanup_old_alerts(self, days: int = 90) -> int:
        """Archive/delete alerts older than specified days"""
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            DELETE FROM alerts 
            WHERE created_at < ? 
            AND status IN ('resolved', 'expired')
        """, (cutoff,))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted


class AlertRules:
    """
    Rules engine for auto-generating alerts from clinical data.
    """
    
    def __init__(self, alert_manager: AlertManager):
        self.alert_manager = alert_manager
    
    def from_clinical_findings(
        self,
        patient_mrn: str,
        abnormal_labs: Optional[List[Dict]] = None,
        abnormal_vitals: Optional[List[Dict]] = None,
        risk_scores: Optional[List[Dict]] = None
    ) -> List[Alert]:
        """
        Generate alerts from clinical findings.
        
        Args:
            patient_mrn: Patient MRN
            abnormal_labs: List of abnormal lab results
            abnormal_vitals: List of abnormal vital signs
            risk_scores: List of elevated risk scores
            
        Returns:
            List of created alerts
        """
        alerts = []
        
        if abnormal_labs:
            for lab in abnormal_labs:
                severity = self._lab_severity(lab)
                alert = self.alert_manager.create_alert(
                    alert_type=AlertType.CRITICAL_LAB,
                    severity=severity,
                    title=f"Abnormal Lab: {lab.get('display', 'Unknown')}",
                    message=self._format_lab_message(lab),
                    patient_mrn=patient_mrn,
                    source="lab_system",
                    metadata={'lab_data': lab}
                )
                alerts.append(alert)
        
        if abnormal_vitals:
            for vital in abnormal_vitals:
                severity = self._vital_severity(vital)
                alert = self.alert_manager.create_alert(
                    alert_type=AlertType.ABNORMAL_VITAL,
                    severity=severity,
                    title=f"Abnormal Vital: {vital.get('display', 'Unknown')}",
                    message=self._format_vital_message(vital),
                    patient_mrn=patient_mrn,
                    source="vitals_monitor",
                    metadata={'vital_data': vital}
                )
                alerts.append(alert)
        
        if risk_scores:
            for score in risk_scores:
                if score.get('value', 0) > 0.7:
                    severity = AlertSeverity.HIGH if score.get('value', 0) > 0.85 else AlertSeverity.MEDIUM
                    alert = self.alert_manager.create_alert(
                        alert_type=AlertType.DETERIORATION,
                        severity=severity,
                        title=f"Elevated Risk: {score.get('name', 'Unknown')}",
                        message=f"Risk score {score.get('name')}: {score.get('value', 0):.1%}. "
                                f"Factors: {', '.join(score.get('factors', []))}",
                        patient_mrn=patient_mrn,
                        source="risk_engine",
                        metadata={'risk_score': score}
                    )
                    alerts.append(alert)
        
        return alerts
    
    def from_ai_insights(
        self,
        patient_mrn: str,
        insights: List[Dict]
    ) -> List[Alert]:
        """
        Generate alerts from AI tool insights.
        
        Args:
            patient_mrn: Patient MRN
            insights: List of AI insights
            
        Returns:
            List of created alerts
        """
        alerts = []
        
        for insight in insights:
            confidence = insight.get('confidence', 0.5)
            insight_type = insight.get('type', '').lower()
            
            if 'critical' in insight_type or confidence > 0.9:
                severity = AlertSeverity.HIGH
            elif 'warning' in insight_type or confidence > 0.8:
                severity = AlertSeverity.MEDIUM
            else:
                severity = AlertSeverity.LOW
            
            if confidence >= 0.7:
                alert = self.alert_manager.create_alert(
                    alert_type=AlertType.AI_INSIGHT,
                    severity=severity,
                    title=f"AI Insight: {insight.get('source', 'Unknown')}",
                    message=insight.get('content', 'No details available'),
                    patient_mrn=patient_mrn,
                    source=f"ai:{insight.get('source', 'unknown')}",
                    metadata={
                        'insight': insight,
                        'confidence': confidence,
                        'insight_type': insight_type
                    }
                )
                alerts.append(alert)
        
        return alerts
    
    def from_bayesian_result(
        self,
        patient_mrn: str,
        bayesian_result: Dict,
        clinical_question: Optional[str] = None
    ) -> Optional[Alert]:
        """
        Generate alert from Bayesian analysis result.
        
        Args:
            patient_mrn: Patient MRN
            bayesian_result: Bayesian analysis result
            clinical_question: Original clinical question
            
        Returns:
            Created alert or None if no alert needed
        """
        prob_safe = bayesian_result.get('prob_safe', 1.0)
        ci_low = bayesian_result.get('ci_low', 0)
        n_cases = bayesian_result.get('n_cases', 0)
        
        if prob_safe >= 0.85:
            return None
        
        if prob_safe < 0.5:
            severity = AlertSeverity.CRITICAL
            title = "Critical: Low Safety Probability"
        elif prob_safe < 0.7:
            severity = AlertSeverity.HIGH
            title = "High Risk: Reduced Safety Probability"
        else:
            severity = AlertSeverity.MEDIUM
            title = "Moderate Risk: Safety Review Recommended"
        
        message = (
            f"Bayesian safety analysis indicates {prob_safe:.0%} probability of safe outcome "
            f"(95% CI: {ci_low:.0%} - {bayesian_result.get('ci_high', 1):.0%}). "
            f"Based on {n_cases} similar historical cases."
        )
        
        if clinical_question:
            message += f"\n\nClinical question: {clinical_question}"
        
        return self.alert_manager.create_alert(
            alert_type=AlertType.BAYESIAN_RISK,
            severity=severity,
            title=title,
            message=message,
            patient_mrn=patient_mrn,
            source="bayesian_engine",
            metadata={
                'bayesian_result': bayesian_result,
                'clinical_question': clinical_question
            }
        )
    
    def from_imaging_findings(
        self,
        patient_mrn: str,
        imaging_results: List[Dict]
    ) -> List[Alert]:
        """
        Generate alerts from imaging findings.
        
        Args:
            patient_mrn: Patient MRN
            imaging_results: List of imaging study results
            
        Returns:
            List of created alerts
        """
        alerts = []
        
        critical_keywords = [
            'mass', 'tumor', 'nodule', 'hemorrhage', 'fracture',
            'pneumothorax', 'effusion', 'embolism', 'aneurysm',
            'obstruction', 'perforation', 'dissection'
        ]
        
        for img in imaging_results:
            findings = img.get('findings', '').lower()
            ai_analysis = img.get('ai_analysis', {})
            
            is_critical = any(kw in findings for kw in critical_keywords)
            ai_critical = ai_analysis.get('critical_finding', False)
            ai_confidence = ai_analysis.get('confidence', 0)
            
            if is_critical or (ai_critical and ai_confidence > 0.8):
                severity = AlertSeverity.CRITICAL if ai_critical else AlertSeverity.HIGH
                
                alert = self.alert_manager.create_alert(
                    alert_type=AlertType.IMAGING_FINDING,
                    severity=severity,
                    title=f"Critical Imaging: {img.get('modality', 'Unknown')} - {img.get('body_part', 'Unknown')}",
                    message=img.get('findings', 'Review imaging study for critical findings'),
                    patient_mrn=patient_mrn,
                    source=f"imaging:{img.get('source', 'unknown')}",
                    metadata={
                        'imaging': img,
                        'ai_analysis': ai_analysis
                    }
                )
                alerts.append(alert)
        
        return alerts
    
    def from_drug_interactions(
        self,
        patient_mrn: str,
        interactions: List[Dict]
    ) -> List[Alert]:
        """
        Generate alerts from drug interaction checks.
        
        Args:
            patient_mrn: Patient MRN
            interactions: List of detected drug interactions
            
        Returns:
            List of created alerts
        """
        alerts = []
        
        for interaction in interactions:
            severity_map = {
                'contraindicated': AlertSeverity.CRITICAL,
                'severe': AlertSeverity.HIGH,
                'moderate': AlertSeverity.MEDIUM,
                'minor': AlertSeverity.LOW
            }
            
            severity = severity_map.get(
                interaction.get('severity', '').lower(),
                AlertSeverity.MEDIUM
            )
            
            drugs = interaction.get('drugs', [])
            drug_names = ', '.join(drugs) if drugs else 'Unknown medications'
            
            alert = self.alert_manager.create_alert(
                alert_type=AlertType.DRUG_INTERACTION,
                severity=severity,
                title=f"Drug Interaction: {drug_names}",
                message=interaction.get('description', 'Potential drug interaction detected'),
                patient_mrn=patient_mrn,
                source="drug_interaction_checker",
                metadata={'interaction': interaction}
            )
            alerts.append(alert)
        
        return alerts
    
    def _lab_severity(self, lab: Dict) -> AlertSeverity:
        """Determine severity from lab result"""
        interpretation = lab.get('interpretation', '').upper()
        
        if interpretation in ['HH', 'LL', 'AA']:
            return AlertSeverity.CRITICAL
        elif interpretation in ['H', 'L', 'A']:
            value = lab.get('value')
            low = lab.get('reference_range_low')
            high = lab.get('reference_range_high')
            
            if value is not None and isinstance(value, (int, float)):
                if low and value < low * 0.5:
                    return AlertSeverity.CRITICAL
                if high and value > high * 2:
                    return AlertSeverity.CRITICAL
            
            return AlertSeverity.HIGH
        
        return AlertSeverity.MEDIUM
    
    def _vital_severity(self, vital: Dict) -> AlertSeverity:
        """Determine severity from vital sign"""
        critical_ranges = {
            'heart_rate': (30, 150),
            'systolic_bp': (70, 200),
            'diastolic_bp': (40, 120),
            'respiratory_rate': (8, 35),
            'oxygen_saturation': (85, 100),
            'temperature': (34, 40)
        }
        
        code = vital.get('code', '').lower()
        value = vital.get('value')
        
        if value is None or not isinstance(value, (int, float)):
            return AlertSeverity.MEDIUM
        
        for vital_type, (low, high) in critical_ranges.items():
            if vital_type in code:
                if value < low or value > high:
                    return AlertSeverity.CRITICAL
        
        return AlertSeverity.HIGH
    
    def _format_lab_message(self, lab: Dict) -> str:
        """Format lab result for alert message"""
        value = lab.get('value', 'N/A')
        unit = lab.get('unit', '')
        low = lab.get('reference_range_low')
        high = lab.get('reference_range_high')
        interp = lab.get('interpretation', '')
        
        msg = f"{lab.get('display', 'Lab')}: {value} {unit}"
        
        if low is not None and high is not None:
            msg += f" (Reference: {low}-{high} {unit})"
        
        if interp:
            interp_map = {
                'H': 'HIGH', 'HH': 'CRITICALLY HIGH',
                'L': 'LOW', 'LL': 'CRITICALLY LOW',
                'A': 'ABNORMAL', 'AA': 'CRITICALLY ABNORMAL'
            }
            msg += f" [{interp_map.get(interp.upper(), interp)}]"
        
        return msg
    
    def _format_vital_message(self, vital: Dict) -> str:
        """Format vital sign for alert message"""
        value = vital.get('value', 'N/A')
        unit = vital.get('unit', '')
        
        return f"{vital.get('display', 'Vital Sign')}: {value} {unit}"


def send_sms_notification(alert: Alert) -> bool:
    """Placeholder SMS notification handler"""
    print(f"[SMS PLACEHOLDER] Alert {alert.id}: {alert.title}")
    return True


def send_email_notification(alert: Alert) -> bool:
    """Placeholder email notification handler"""
    print(f"[EMAIL PLACEHOLDER] Alert {alert.id}: {alert.title}")
    return True


def send_pager_notification(alert: Alert) -> bool:
    """Placeholder pager notification handler"""
    print(f"[PAGER PLACEHOLDER] CRITICAL Alert {alert.id}: {alert.title}")
    return True


def create_alert_manager_with_defaults() -> AlertManager:
    """Create AlertManager with default notification handlers"""
    manager = AlertManager()
    manager.register_notification_handler(NotificationChannel.SMS, send_sms_notification)
    manager.register_notification_handler(NotificationChannel.EMAIL, send_email_notification)
    manager.register_notification_handler(NotificationChannel.PAGER, send_pager_notification)
    return manager
