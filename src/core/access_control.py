"""
Role-Based Access Control (RBAC) System for Grok Doc v2.5

Provides secure role-based permissions for clinical AI system access.
Integrates with audit logging for compliance tracking.
"""

import hashlib
import json
import sqlite3
import secrets
import functools
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict, Optional, List, Set, Any, Callable
from dataclasses import dataclass, field


DB_PATH = "audit.db"


class Permission(Enum):
    """Granular permissions for system access"""
    QUERY_CLINICAL = auto()
    QUERY_MEDICATION = auto()
    QUERY_LAB = auto()
    QUERY_IMAGING = auto()
    VIEW_PATIENT_DATA = auto()
    VIEW_ASSIGNED_PATIENTS = auto()
    VIEW_ALL_PATIENTS = auto()
    MODIFY_PATIENT_DATA = auto()
    SIGN_NOTES = auto()
    PRESCRIBE_MEDICATION = auto()
    ORDER_LABS = auto()
    ORDER_IMAGING = auto()
    VIEW_AUDIT_LOG = auto()
    EXPORT_AUDIT = auto()
    MANAGE_USERS = auto()
    MANAGE_CONFIG = auto()
    MANAGE_ALERTS = auto()
    ACCESS_ADMIN_DASHBOARD = auto()
    USE_CHAIN_ANALYSIS = auto()
    USE_ADVERSARIAL_STAGE = auto()
    USE_LITERATURE_STAGE = auto()
    DEMO_ACCESS_ONLY = auto()


class Role(Enum):
    """User roles with associated permission sets"""
    ADMIN = "admin"
    PHYSICIAN = "physician"
    NURSE = "nurse"
    PHARMACIST = "pharmacist"
    RESIDENT = "resident"
    GUEST = "guest"


ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: {
        Permission.QUERY_CLINICAL,
        Permission.QUERY_MEDICATION,
        Permission.QUERY_LAB,
        Permission.QUERY_IMAGING,
        Permission.VIEW_PATIENT_DATA,
        Permission.VIEW_ASSIGNED_PATIENTS,
        Permission.VIEW_ALL_PATIENTS,
        Permission.MODIFY_PATIENT_DATA,
        Permission.SIGN_NOTES,
        Permission.PRESCRIBE_MEDICATION,
        Permission.ORDER_LABS,
        Permission.ORDER_IMAGING,
        Permission.VIEW_AUDIT_LOG,
        Permission.EXPORT_AUDIT,
        Permission.MANAGE_USERS,
        Permission.MANAGE_CONFIG,
        Permission.MANAGE_ALERTS,
        Permission.ACCESS_ADMIN_DASHBOARD,
        Permission.USE_CHAIN_ANALYSIS,
        Permission.USE_ADVERSARIAL_STAGE,
        Permission.USE_LITERATURE_STAGE,
    },
    Role.PHYSICIAN: {
        Permission.QUERY_CLINICAL,
        Permission.QUERY_MEDICATION,
        Permission.QUERY_LAB,
        Permission.QUERY_IMAGING,
        Permission.VIEW_PATIENT_DATA,
        Permission.VIEW_ASSIGNED_PATIENTS,
        Permission.VIEW_ALL_PATIENTS,
        Permission.MODIFY_PATIENT_DATA,
        Permission.SIGN_NOTES,
        Permission.PRESCRIBE_MEDICATION,
        Permission.ORDER_LABS,
        Permission.ORDER_IMAGING,
        Permission.VIEW_AUDIT_LOG,
        Permission.USE_CHAIN_ANALYSIS,
        Permission.USE_ADVERSARIAL_STAGE,
        Permission.USE_LITERATURE_STAGE,
    },
    Role.NURSE: {
        Permission.QUERY_CLINICAL,
        Permission.QUERY_MEDICATION,
        Permission.QUERY_LAB,
        Permission.VIEW_PATIENT_DATA,
        Permission.VIEW_ASSIGNED_PATIENTS,
        Permission.ORDER_LABS,
        Permission.USE_CHAIN_ANALYSIS,
    },
    Role.PHARMACIST: {
        Permission.QUERY_MEDICATION,
        Permission.QUERY_LAB,
        Permission.VIEW_PATIENT_DATA,
        Permission.VIEW_ALL_PATIENTS,
        Permission.PRESCRIBE_MEDICATION,
        Permission.USE_CHAIN_ANALYSIS,
        Permission.USE_LITERATURE_STAGE,
    },
    Role.RESIDENT: {
        Permission.QUERY_CLINICAL,
        Permission.QUERY_MEDICATION,
        Permission.QUERY_LAB,
        Permission.QUERY_IMAGING,
        Permission.VIEW_PATIENT_DATA,
        Permission.VIEW_ASSIGNED_PATIENTS,
        Permission.VIEW_ALL_PATIENTS,
        Permission.MODIFY_PATIENT_DATA,
        Permission.SIGN_NOTES,
        Permission.ORDER_LABS,
        Permission.ORDER_IMAGING,
        Permission.USE_CHAIN_ANALYSIS,
        Permission.USE_ADVERSARIAL_STAGE,
        Permission.USE_LITERATURE_STAGE,
    },
    Role.GUEST: {
        Permission.DEMO_ACCESS_ONLY,
    },
}


@dataclass
class User:
    """User with role and department information"""
    user_id: str
    username: str
    role: Role
    department: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    npi_number: Optional[str] = None
    supervising_physician_id: Optional[str] = None
    assigned_patients: Set[str] = field(default_factory=set)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    last_login: Optional[str] = None
    is_active: bool = True
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission"""
        if not self.is_active:
            return False
        return permission in ROLE_PERMISSIONS.get(self.role, set())
    
    def has_any_permission(self, permissions: List[Permission]) -> bool:
        """Check if user has any of the specified permissions"""
        return any(self.has_permission(p) for p in permissions)
    
    def has_all_permissions(self, permissions: List[Permission]) -> bool:
        """Check if user has all specified permissions"""
        return all(self.has_permission(p) for p in permissions)
    
    def can_access_patient(self, mrn: str) -> bool:
        """Check if user can access a specific patient's data"""
        if not self.is_active:
            return False
        if self.has_permission(Permission.VIEW_ALL_PATIENTS):
            return True
        if self.has_permission(Permission.VIEW_ASSIGNED_PATIENTS):
            return mrn in self.assigned_patients
        return False
    
    def get_permissions(self) -> Set[Permission]:
        """Get all permissions for this user"""
        if not self.is_active:
            return set()
        return ROLE_PERMISSIONS.get(self.role, set()).copy()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary (excludes sensitive data)"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "role": self.role.value,
            "department": self.department,
            "email": self.email,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "last_login": self.last_login,
        }


@dataclass
class Session:
    """User session with token management"""
    session_id: str
    user_id: str
    token: str
    created_at: str
    expires_at: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_valid: bool = True
    
    def is_expired(self) -> bool:
        """Check if session has expired"""
        if not self.is_valid:
            return True
        expires = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
        return datetime.now(expires.tzinfo) > expires


class AccessControlError(Exception):
    """Base exception for access control errors"""
    pass


class PermissionDeniedError(AccessControlError):
    """Raised when a user lacks required permissions"""
    def __init__(self, user_id: str, required_permission: Permission, action: str = ""):
        self.user_id = user_id
        self.required_permission = required_permission
        self.action = action
        message = f"Permission denied for user {user_id}: requires {required_permission.name}"
        if action:
            message += f" to {action}"
        super().__init__(message)


class SessionExpiredError(AccessControlError):
    """Raised when a session has expired"""
    pass


class InvalidSessionError(AccessControlError):
    """Raised when a session is invalid"""
    pass


def _init_access_control_db():
    """Initialize access control tables in the audit database"""
    conn = sqlite3.connect(DB_PATH)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS access_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user_id TEXT NOT NULL,
            username TEXT,
            role TEXT,
            action TEXT NOT NULL,
            resource TEXT,
            permission_required TEXT,
            granted BOOLEAN NOT NULL,
            denial_reason TEXT,
            ip_address TEXT,
            session_id TEXT,
            prev_hash TEXT NOT NULL,
            entry_hash TEXT NOT NULL,
            UNIQUE(entry_hash)
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            token_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            is_valid BOOLEAN DEFAULT 1
        )
    """)
    
    conn.execute("CREATE INDEX IF NOT EXISTS idx_access_user ON access_attempts(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_access_timestamp ON access_attempts(timestamp)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_access_granted ON access_attempts(granted)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_session_user ON sessions(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_session_token ON sessions(token_hash)")
    
    conn.commit()
    conn.close()


def _get_last_access_hash() -> str:
    """Get the hash of the most recent access attempt entry"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute(
            "SELECT entry_hash FROM access_attempts ORDER BY id DESC LIMIT 1"
        )
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else "GENESIS_ACCESS_BLOCK"
    except sqlite3.OperationalError:
        return "GENESIS_ACCESS_BLOCK"


def _compute_access_hash(entry: Dict) -> str:
    """Compute SHA-256 hash of access attempt entry"""
    hash_data = {
        "timestamp": entry["timestamp"],
        "user_id": entry["user_id"],
        "action": entry["action"],
        "granted": entry["granted"],
        "prev_hash": entry["prev_hash"]
    }
    canonical_json = json.dumps(hash_data, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()


def log_access_attempt(
    user_id: str,
    action: str,
    granted: bool,
    username: Optional[str] = None,
    role: Optional[str] = None,
    resource: Optional[str] = None,
    permission_required: Optional[Permission] = None,
    denial_reason: Optional[str] = None,
    ip_address: Optional[str] = None,
    session_id: Optional[str] = None
) -> Dict:
    """
    Log an access attempt to the audit trail.
    
    Args:
        user_id: User attempting access
        action: Action being attempted
        granted: Whether access was granted
        username: Username of the user
        role: Role of the user
        resource: Resource being accessed
        permission_required: Permission needed for action
        denial_reason: Reason for denial if not granted
        ip_address: IP address of request
        session_id: Session ID if available
        
    Returns:
        Dict containing the logged entry with hash
    """
    _init_access_control_db()
    
    timestamp = datetime.utcnow().isoformat() + "Z"
    prev_hash = _get_last_access_hash()
    
    entry = {
        "timestamp": timestamp,
        "user_id": user_id,
        "username": username,
        "role": role,
        "action": action,
        "resource": resource,
        "permission_required": permission_required.name if permission_required else None,
        "granted": granted,
        "denial_reason": denial_reason,
        "ip_address": ip_address,
        "session_id": session_id,
        "prev_hash": prev_hash
    }
    
    entry_hash = _compute_access_hash(entry)
    entry["hash"] = entry_hash
    
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            INSERT INTO access_attempts
            (timestamp, user_id, username, role, action, resource, 
             permission_required, granted, denial_reason, ip_address, 
             session_id, prev_hash, entry_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp, user_id, username, role, action, resource,
            entry["permission_required"], granted, denial_reason,
            ip_address, session_id, prev_hash, entry_hash
        ))
        conn.commit()
    except sqlite3.IntegrityError as e:
        pass
    finally:
        conn.close()
    
    return entry


class SessionManager:
    """Manages user sessions with secure token handling"""
    
    DEFAULT_SESSION_DURATION_HOURS = 8
    
    def __init__(self, session_duration_hours: int = DEFAULT_SESSION_DURATION_HOURS):
        self.session_duration = timedelta(hours=session_duration_hours)
        _init_access_control_db()
    
    def create_session(
        self,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Session:
        """
        Create a new session for a user.
        
        Args:
            user: User object
            ip_address: Client IP address
            user_agent: Client user agent string
            
        Returns:
            Session object with token
        """
        session_id = secrets.token_urlsafe(32)
        token = secrets.token_urlsafe(64)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        now = datetime.utcnow()
        created_at = now.isoformat() + "Z"
        expires_at = (now + self.session_duration).isoformat() + "Z"
        
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT INTO sessions
            (session_id, user_id, token_hash, created_at, expires_at, 
             ip_address, user_agent, is_valid)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id, user.user_id, token_hash, created_at, 
            expires_at, ip_address, user_agent, True
        ))
        conn.commit()
        conn.close()
        
        user.last_login = created_at
        
        log_access_attempt(
            user_id=user.user_id,
            action="session_created",
            granted=True,
            username=user.username,
            role=user.role.value,
            ip_address=ip_address,
            session_id=session_id
        )
        
        return Session(
            session_id=session_id,
            user_id=user.user_id,
            token=token,
            created_at=created_at,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
            is_valid=True
        )
    
    def validate_token(self, token: str) -> Optional[str]:
        """
        Validate a session token and return user_id if valid.
        
        Args:
            token: Session token to validate
            
        Returns:
            User ID if valid, None otherwise
        """
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute("""
            SELECT session_id, user_id, expires_at, is_valid
            FROM sessions
            WHERE token_hash = ?
        """, (token_hash,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        session_id, user_id, expires_at, is_valid = result
        
        if not is_valid:
            return None
        
        expires = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if datetime.now(expires.tzinfo) > expires:
            self.invalidate_session(session_id)
            return None
        
        return user_id
    
    def invalidate_session(self, session_id: str) -> bool:
        """
        Invalidate a session by ID.
        
        Args:
            session_id: Session ID to invalidate
            
        Returns:
            True if session was invalidated, False if not found
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute("""
            UPDATE sessions SET is_valid = 0 WHERE session_id = ?
        """, (session_id,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        if affected > 0:
            log_access_attempt(
                user_id="system",
                action="session_invalidated",
                granted=True,
                session_id=session_id
            )
        
        return affected > 0
    
    def invalidate_user_sessions(self, user_id: str) -> int:
        """
        Invalidate all sessions for a user.
        
        Args:
            user_id: User ID whose sessions should be invalidated
            
        Returns:
            Number of sessions invalidated
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute("""
            UPDATE sessions SET is_valid = 0 
            WHERE user_id = ? AND is_valid = 1
        """, (user_id,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        if affected > 0:
            log_access_attempt(
                user_id=user_id,
                action="all_sessions_invalidated",
                granted=True,
                resource=f"{affected} sessions"
            )
        
        return affected
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions from the database.
        
        Returns:
            Number of sessions cleaned up
        """
        now = datetime.utcnow().isoformat() + "Z"
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute("""
            DELETE FROM sessions WHERE expires_at < ? OR is_valid = 0
        """, (now,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return affected


def require_permission(*permissions: Permission, log_attempts: bool = True):
    """
    Decorator to require specific permissions for a function.
    
    The decorated function must receive a 'user' keyword argument
    or have 'user' as its first positional argument.
    
    Args:
        *permissions: One or more permissions required (user needs ANY of them)
        log_attempts: Whether to log access attempts
    
    Example:
        @require_permission(Permission.QUERY_CLINICAL)
        def query_patient(user: User, mrn: str, question: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            user = kwargs.get('user')
            if user is None and args:
                user = args[0] if isinstance(args[0], User) else None
            
            if user is None:
                raise AccessControlError("No user context provided")
            
            has_required = user.has_any_permission(list(permissions))
            
            if log_attempts:
                log_access_attempt(
                    user_id=user.user_id,
                    action=func.__name__,
                    granted=has_required,
                    username=user.username,
                    role=user.role.value,
                    permission_required=permissions[0] if permissions else None,
                    denial_reason=None if has_required else "Insufficient permissions"
                )
            
            if not has_required:
                raise PermissionDeniedError(
                    user_id=user.user_id,
                    required_permission=permissions[0],
                    action=func.__name__
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_all_permissions(*permissions: Permission, log_attempts: bool = True):
    """
    Decorator requiring ALL specified permissions.
    
    Args:
        *permissions: All permissions required
        log_attempts: Whether to log access attempts
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            user = kwargs.get('user')
            if user is None and args:
                user = args[0] if isinstance(args[0], User) else None
            
            if user is None:
                raise AccessControlError("No user context provided")
            
            has_all = user.has_all_permissions(list(permissions))
            
            if log_attempts:
                log_access_attempt(
                    user_id=user.user_id,
                    action=func.__name__,
                    granted=has_all,
                    username=user.username,
                    role=user.role.value,
                    permission_required=permissions[0] if permissions else None,
                    denial_reason=None if has_all else "Missing required permissions"
                )
            
            if not has_all:
                missing = [p for p in permissions if not user.has_permission(p)]
                raise PermissionDeniedError(
                    user_id=user.user_id,
                    required_permission=missing[0] if missing else permissions[0],
                    action=func.__name__
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_patient_access(log_attempts: bool = True):
    """
    Decorator to verify user can access a specific patient.
    
    The decorated function must have 'user' and 'mrn' arguments.
    
    Example:
        @require_patient_access()
        def get_patient_data(user: User, mrn: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            user = kwargs.get('user')
            mrn = kwargs.get('mrn')
            
            if user is None and args:
                user = args[0] if isinstance(args[0], User) else None
            if mrn is None and len(args) > 1:
                mrn = args[1] if isinstance(args[1], str) else None
            
            if user is None:
                raise AccessControlError("No user context provided")
            if mrn is None:
                raise AccessControlError("No patient MRN provided")
            
            can_access = user.can_access_patient(mrn)
            
            if log_attempts:
                log_access_attempt(
                    user_id=user.user_id,
                    action=func.__name__,
                    granted=can_access,
                    username=user.username,
                    role=user.role.value,
                    resource=f"patient:{mrn}",
                    permission_required=Permission.VIEW_PATIENT_DATA,
                    denial_reason=None if can_access else "Patient not assigned to user"
                )
            
            if not can_access:
                raise PermissionDeniedError(
                    user_id=user.user_id,
                    required_permission=Permission.VIEW_PATIENT_DATA,
                    action=f"access patient {mrn}"
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_oversight_logging(log_attempts: bool = True):
    """
    Decorator for functions requiring additional oversight (e.g., for residents).
    
    Logs extra information when the user is a resident or other supervised role.
    
    Example:
        @require_oversight_logging()
        @require_permission(Permission.SIGN_NOTES)
        def sign_clinical_note(user: User, note_id: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            user = kwargs.get('user')
            if user is None and args:
                user = args[0] if isinstance(args[0], User) else None
            
            if user is None:
                raise AccessControlError("No user context provided")
            
            result = func(*args, **kwargs)
            
            if user.role == Role.RESIDENT:
                log_access_attempt(
                    user_id=user.user_id,
                    action=f"{func.__name__}_oversight",
                    granted=True,
                    username=user.username,
                    role=user.role.value,
                    resource=f"supervising_physician:{user.supervising_physician_id}",
                    denial_reason=None
                )
            
            return result
        return wrapper
    return decorator


def get_access_log(
    user_id: Optional[str] = None,
    granted_only: Optional[bool] = None,
    limit: int = 100,
    since: Optional[str] = None
) -> List[Dict]:
    """
    Retrieve access attempt logs.
    
    Args:
        user_id: Filter by specific user
        granted_only: If True, only granted; if False, only denied
        limit: Maximum entries to return
        since: ISO timestamp to filter from
        
    Returns:
        List of access log entries
    """
    _init_access_control_db()
    
    query = "SELECT * FROM access_attempts WHERE 1=1"
    params: List[Any] = []
    
    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)
    
    if granted_only is not None:
        query += " AND granted = ?"
        params.append(granted_only)
    
    if since:
        query += " AND timestamp >= ?"
        params.append(since)
    
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(query, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return results


def get_denied_access_summary(hours: int = 24) -> Dict[str, Any]:
    """
    Get summary of denied access attempts.
    
    Args:
        hours: Number of hours to look back
        
    Returns:
        Summary statistics of denied access attempts
    """
    _init_access_control_db()
    
    since = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + "Z"
    
    conn = sqlite3.connect(DB_PATH)
    
    cursor = conn.execute("""
        SELECT COUNT(*) FROM access_attempts 
        WHERE granted = 0 AND timestamp >= ?
    """, (since,))
    total_denied = cursor.fetchone()[0]
    
    cursor = conn.execute("""
        SELECT user_id, COUNT(*) as count FROM access_attempts 
        WHERE granted = 0 AND timestamp >= ?
        GROUP BY user_id ORDER BY count DESC LIMIT 10
    """, (since,))
    by_user = {row[0]: row[1] for row in cursor.fetchall()}
    
    cursor = conn.execute("""
        SELECT action, COUNT(*) as count FROM access_attempts 
        WHERE granted = 0 AND timestamp >= ?
        GROUP BY action ORDER BY count DESC LIMIT 10
    """, (since,))
    by_action = {row[0]: row[1] for row in cursor.fetchall()}
    
    conn.close()
    
    return {
        "period_hours": hours,
        "total_denied": total_denied,
        "by_user": by_user,
        "by_action": by_action
    }


def create_demo_user() -> User:
    """Create a demo guest user for testing"""
    return User(
        user_id="demo_guest",
        username="demo",
        role=Role.GUEST,
        department="Demo",
        full_name="Demo User",
        is_active=True
    )


def create_test_users() -> Dict[str, User]:
    """Create a set of test users for development"""
    return {
        "admin": User(
            user_id="admin_001",
            username="admin",
            role=Role.ADMIN,
            department="IT",
            full_name="System Administrator",
            email="admin@hospital.org"
        ),
        "physician": User(
            user_id="phys_001",
            username="dr_smith",
            role=Role.PHYSICIAN,
            department="Internal Medicine",
            full_name="Dr. Jane Smith",
            npi_number="1234567890",
            email="jsmith@hospital.org"
        ),
        "nurse": User(
            user_id="nurse_001",
            username="nurse_jones",
            role=Role.NURSE,
            department="ICU",
            full_name="Robert Jones, RN",
            assigned_patients={"MRN001", "MRN002", "MRN003"}
        ),
        "pharmacist": User(
            user_id="pharm_001",
            username="pharm_chen",
            role=Role.PHARMACIST,
            department="Pharmacy",
            full_name="Dr. Wei Chen, PharmD"
        ),
        "resident": User(
            user_id="res_001",
            username="dr_patel",
            role=Role.RESIDENT,
            department="Internal Medicine",
            full_name="Dr. Anil Patel",
            supervising_physician_id="phys_001",
            assigned_patients={"MRN001", "MRN004"}
        ),
        "guest": create_demo_user()
    }


_init_access_control_db()
