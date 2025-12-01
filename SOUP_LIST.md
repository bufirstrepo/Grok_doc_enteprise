# Software of Unknown Provenance (SOUP) - IEC 62304

| Library | Version | Vendor | Purpose | Known CVEs | Mitigation |
|---------|---------|--------|---------|-----------|------------|
| openai | ≥1.0.0 | OpenAI Inc | xAI/Azure API client | None known | Vendor-managed, BAA signed |
| anthropic | ≥0.18.0 | Anthropic PBC | Claude API client | None known | Vendor-managed, BAA signed |
| google-generativeai | ≥0.3.0 | Google LLC | Gemini API client | None known | Vendor-managed |
| streamlit | 1.38.0 | Streamlit Inc | Web UI framework | None critical | Regular updates |
| pandas | 2.2.2 | NumFOCUS | Data processing | None | Widely validated |
| pyjwt | 2.8.0 | Python JWT | Authentication | CVE-2022-29217 | Mitigated in v2.4+ |
| cryptography | 43.0.1 | PyCA | Encryption | None | Security-focused library |

## Risk Assessment
All third-party libraries are evaluated for:
1. Known security vulnerabilities (CVE database)
2. Vendor reputation and support
3. BAA availability (for PHI handling)
4. Update frequency and patch responsiveness

## Cybersecurity Monitoring
Monthly CVE scans automated via `pip-audit`
