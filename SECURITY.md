# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.0.x   | :white_check_mark: |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

---

## Reporting a Vulnerability

We take the security of Grok Doc seriously, especially given its use in clinical settings with protected health information (PHI).

### How to Report

**DO NOT** open a public GitHub issue for security vulnerabilities.

Instead, please email security details to:
- **Email**: [security contact - to be added]
- **Twitter DM**: [@ohio_dino](https://twitter.com/ohio_dino)

Include in your report:
1. Description of the vulnerability
2. Steps to reproduce
3. Potential impact (especially PHI exposure risks)
4. Suggested fix (if you have one)

### What to Expect

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 5 business days
- **Fix Timeline**: Critical issues within 7 days, others within 30 days
- **Disclosure**: Coordinated disclosure after fix is released

---

## Security Architecture

### 🔒 Core Security Features

#### 1. Zero-Cloud Architecture
- **All inference happens locally** on hospital hardware
- No external API calls to OpenAI, Anthropic, etc.
- No cloud storage (S3, GCS, Azure Blob, etc.)
- No telemetry or analytics to external services

**Verification:**
```bash
# Check for external network calls
grep -r "requests\|urllib\|httplib" *.py | grep -v "captive.apple.com"
# Should only show local WiFi check
```

#### 2. Network Isolation
- **Hospital WiFi enforcement**: App checks SSID before operation
- Captive portal detection to prevent public WiFi usage
- No data leaves hospital network perimeter

**Configuration (`app.py`):**
```python
HOSPITAL_SSID_KEYWORDS = ["hospital", "clinical", "healthcare", "medical"]
REQUIRE_WIFI_CHECK = True  # Never disable in production
```

**For production, add:**
- Certificate pinning
- MAC address whitelist
- VPN tunnel verification
- Firewall rules blocking external traffic

#### 3. Immutable Audit Trail
- **Blockchain-style logging** with SHA-256 hash chaining
- Every decision linked to previous via `prev_hash`
- Tamper detection via `verify_audit_integrity()`
- Complete provenance for regulatory audits

**Integrity Check:**
```python
from audit_log import verify_audit_integrity
result = verify_audit_integrity()
if not result['valid']:
    print(f"Tampering detected at entry {result['tampered_index']}")
```

#### 4. Cryptographic Verification (v2.0)
- Multi-LLM chain steps are hash-chained
- Each step includes: `step_name`, `prompt`, `response`, `prev_hash`
- Chain verification before logging decision
- Genesis hash: `"GENESIS_CHAIN"`

**Verification:**
```python
from llm_chain import MultiLLMChain
chain = MultiLLMChain()
# ... run chain ...
assert chain.verify_chain() == True
```

#### 5. Physician E-Signature
- **Required** before any decision is logged
- PIN-based authentication (4-6 digits minimum)
- Signed decisions are immutable
- Signature included in audit hash

---

## 🛡️ Threat Model

### In Scope

1. **PHI Exposure**
   - Patient data leaving hospital network
   - Audit logs containing identifiable information
   - Model outputs with PHI

2. **Audit Trail Tampering**
   - Modification of past decisions
   - Hash chain manipulation
   - Database injection attacks

3. **Unauthorized Access**
   - Non-hospital devices accessing system
   - Bypassing WiFi checks
   - Privilege escalation

4. **Model Manipulation**
   - Prompt injection attacks
   - Adversarial inputs to bias recommendations
   - Cache poisoning

### Out of Scope

- Physical access to hospital servers (assumed secured by hospital IT)
- Social engineering of physicians (hospital policy issue)
- DDoS attacks (hospital network team responsibility)
- Zero-day OS/kernel exploits (use latest patches)

---

## 🔐 Security Best Practices

### For Hospital Deployment

#### 1. Network Security

```bash
# Firewall: Block all outbound traffic except
# - Hospital internal network
# - Model download (one-time, from trusted source)

iptables -A OUTPUT -d 10.0.0.0/8 -j ACCEPT        # Internal
iptables -A OUTPUT -d 192.168.0.0/16 -j ACCEPT    # Internal
iptables -A OUTPUT -j DROP                         # Block all else
```

#### 2. Database Encryption

```bash
# Encrypt audit.db at rest
# Using SQLCipher:
pip install pysqlcipher3

# Update audit_log.py to use encrypted connection
import sqlcipher.dbapi2 as sqlite3
conn = sqlite3.connect('audit.db')
conn.execute("PRAGMA key = 'your-encryption-key'")
```

#### 3. Access Control

```python
# Integrate with hospital LDAP/AD
import ldap

def authenticate_physician(username, pin):
    conn = ldap.initialize('ldap://hospital.internal')
    try:
        conn.simple_bind_s(f"uid={username},ou=physicians,dc=hospital,dc=org", pin)
        return True
    except ldap.INVALID_CREDENTIALS:
        return False
```

#### 4. SSL/TLS

```bash
# Generate self-signed cert (or use hospital CA)
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365

# Launch with TLS
streamlit run app.py \
  --server.sslCertFile=cert.pem \
  --server.sslKeyFile=key.pem \
  --server.port=443
```

#### 5. Monitoring

```python
# Log all access attempts
import logging

logging.basicConfig(
    filename='access.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logging.info(f"Query from MRN {mrn} by {doctor_name}")
```

---

## ⚠️ Known Limitations

### Current Version (2.0)

1. **WiFi Check Bypass**
   - `REQUIRE_WIFI_CHECK=False` disables protection
   - **Mitigation**: Remove this option in production builds

2. **PIN Security**
   - PINs stored in plaintext in code (for demo)
   - **Mitigation**: Integrate with hospital AD/LDAP

3. **No Rate Limiting**
   - System can be overwhelmed with queries
   - **Mitigation**: Add rate limiting (e.g., 10 queries/minute/physician)

4. **Model Security**
   - Model weights not integrity-checked
   - **Mitigation**: Verify SHA-256 of downloaded model

5. **Audit Log Backups**
   - No automatic backup of `audit.db`
   - **Mitigation**: Hospital should backup to encrypted storage

---

## 🔍 Security Audits

### Self-Assessment Checklist

Before production deployment:

- [ ] WiFi check enabled and tested
- [ ] Firewall blocks external traffic
- [ ] Audit database encrypted at rest
- [ ] SSL/TLS enabled for web interface
- [ ] LDAP/AD authentication integrated
- [ ] Model integrity verified (SHA-256 hash)
- [ ] Audit log backup configured
- [ ] Access logs monitored
- [ ] Incident response plan documented
- [ ] HIPAA compliance reviewed by legal team

### Penetration Testing

Recommended annual penetration testing to verify:
- Network isolation
- Authentication bypass attempts
- SQL injection in audit logging
- Prompt injection attacks
- Hash chain manipulation

---

## 📋 Compliance

### HIPAA

Grok Doc is designed to facilitate HIPAA compliance:
- ✅ **§ 164.308(a)(1)**: Audit controls (immutable logging)
- ✅ **§ 164.308(a)(5)**: Automatic logoff (session timeout)
- ✅ **§ 164.310(d)**: Workstation security (network isolation)
- ✅ **§ 164.312(a)(1)**: Access control (WiFi check + e-signature)
- ✅ **§ 164.312(b)**: Audit trails (blockchain-style logging)
- ✅ **§ 164.312(e)(1)**: Transmission security (SSL/TLS)

**Note**: Hospitals must perform their own HIPAA risk assessment.

### FDA

For hospitals considering FDA submission:
- Complete audit trail for algorithm transparency
- Hash chain prevents post-hoc modification of decisions
- Physician-in-the-loop design (decision support, not autonomous)
- Clinical validation data can be extracted from audit logs

---

## 🆘 Incident Response

### If PHI Exposure Suspected

1. **Immediate Actions:**
   - Disconnect system from network
   - Preserve audit logs
   - Document suspected exposure

2. **Investigation:**
   - Review access logs
   - Check audit trail integrity
   - Identify affected patient records

3. **Notification:**
   - Hospital compliance officer
   - Affected patients (if required)
   - HHS Office for Civil Rights (if >500 patients)

4. **Remediation:**
   - Apply security patches
   - Reset authentication credentials
   - Enhanced monitoring

### If Audit Tampering Detected

```python
from audit_log import verify_audit_integrity

result = verify_audit_integrity()
if not result['valid']:
    # Tampering detected!
    print(f"Compromised at entry {result['tampered_index']}")

    # Actions:
    # 1. Preserve database for forensics
    # 2. Review all decisions after tampered entry
    # 3. Notify compliance team
    # 4. Investigate access logs
```

---

## 📞 Security Contact

- **General Security**: [To be added]
- **Critical Vulnerabilities**: Direct message [@ohio_dino](https://twitter.com/ohio_dino)
- **Hospital Deployment Security**: Open issue with `security` label (no PHI!)

---

## 🏆 Security Recognition

We appreciate responsible disclosure. Security researchers who report valid vulnerabilities will be:
- Acknowledged in CHANGELOG.md (if desired)
- Listed in Hall of Fame (coming soon)
- Eligible for bounties (if program launched)

---

**Last Updated**: 2025-11-18
**Version**: 2.0
