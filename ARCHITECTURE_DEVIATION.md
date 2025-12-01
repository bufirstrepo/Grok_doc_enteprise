# Architectural Deviation Report

## ⚠️ Critical Deviation: Cloud-Hybrid vs Air-Gapped

**Requirement Source**: DevOps / MLOps Engineer Role
**Requirement**: "Air-gapped deployment... hardware qualification (GPU servers in the data center)"

**Current Architecture**: Cloud-Hybrid (Grok Doc v6.5)
**Implementation**: 
- PHI stays on-prem (masked)
- Inference logic runs in cloud (xAI, Azure, Anthropic)
- Requires outbound HTTPS (443) access

### Justification for Deviation
1. **Capability**: Local 70B models cannot match reasoning capability of Grok/GPT-4 for complex clinical synthesis.
2. **Cost**: On-prem H100 GPU clusters are cost-prohibitive for many hospitals.
3. **Speed**: Cloud inference provides lower latency than typical on-prem hardware.

### Risk Mitigation
1. **PHI Masking**: All data stripped of identifiers before cloud transmission (Safe Harbor).
2. **BAA**: Business Associate Agreements required with all cloud vendors.
3. **Audit Trail**: Full logging of what was sent and received.

### Approval Required
This deviation requires explicit sign-off from:
- [ ] Chief Medical Officer
- [ ] Chief Information Security Officer (CISO)
- [ ] Legal Counsel
