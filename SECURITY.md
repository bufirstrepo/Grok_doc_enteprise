# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

**DO NOT open public issues for security vulnerabilities.**

Instead:
1. DM [@ohio_dino](https://twitter.com/ohio_dino) on Twitter
2. Include: description, reproduction steps, potential impact

We will respond within 48 hours and work with you on a fix.

## Security Considerations for Deployment

### PHI Protection
- All patient data stays on local hardware
- No external API calls in production mode
- Network isolation via WiFi lock

### Audit Trail
- SHA-256 cryptographic hashing
- Blockchain-style chain linking
- Tamper detection via `verify_audit_integrity()`

### Access Control
- Physician PIN required for e-signature
- Recommend adding: LDAP/AD integration, 2FA

### Known Limitations
- WiFi check can be spoofed (add certificate pinning for production)
- PIN is not stored/verified (implement proper auth system)
- No rate limiting on endpoints

## Security Best Practices for Production

1. **Enable SSL/TLS**
```bash
   streamlit run app.py \
     --server.sslCertFile=/path/to/cert.pem \
     --server.sslKeyFile=/path/to/key.pem
```

2. **Encrypt Database at Rest**
   Use hospital encryption tools for audit.db

3. **Firewall Configuration**
   - Block all external traffic
   - Whitelist only hospital network

4. **Regular Audits**
```python
   from audit_log import verify_audit_integrity
   verify_audit_integrity()  # Run daily
```
