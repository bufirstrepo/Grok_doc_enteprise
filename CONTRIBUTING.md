# Contributing to Grok Doc

Thank you for your interest in contributing to Grok Doc! This document provides guidelines for contributing to the project.

---

## 🎯 Vision

Grok Doc aims to provide **safe, transparent, on-premises clinical AI** that:
- Never sends PHI to the cloud
- Provides complete audit trails for regulatory compliance
- Uses adversarial multi-LLM reasoning to reduce errors
- Integrates seamlessly into hospital workflows

---

## 🤝 Ways to Contribute

### Code Contributions
- Bug fixes
- New features (see roadmap below)
- Performance optimizations
- Test coverage improvements
- Documentation improvements

### Non-Code Contributions
- Clinical validation studies
- Medical literature reviews
- Hospital deployment guides
- Translation to other languages
- Community support

---

## 🚀 Getting Started

### 1. Fork and Clone

```bash
git fork https://github.com/bufirstrepo/Grok_doc_enteprise
git clone https://github.com/YOUR_USERNAME/Grok_doc_enteprise.git
cd Grok_doc_enteprise
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies + dev tools
pip install -r requirements.txt
pip install pytest black flake8 mypy

# Run tests to verify setup
python -m unittest test_v2.py
```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
# Or
git checkout -b fix/bug-description
```

---

## 📝 Development Guidelines

### Code Style

We follow **PEP 8** with these specifics:
- Line length: 100 characters
- Indentation: 4 spaces (no tabs)
- Docstrings: Google style
- Type hints: Required for all functions

**Format code before committing:**
```bash
black *.py
flake8 --max-line-length=100 *.py
```

### Type Hints

All new functions must include type hints:

```python
def run_chain(
    self,
    patient_context: Dict,
    query: str,
    retrieved_evidence: List[Dict],
    bayesian_result: Dict
) -> Dict:
    """Execute the full 4-LLM decision chain."""
    ...
```

### Testing

- All new features must include unit tests
- Maintain >80% test coverage
- Use `unittest.mock` for LLM calls (don't call real models in tests)

**Run tests:**
```bash
python -m unittest test_v2.py -v
```

### Documentation

- Update README.md for user-facing changes
- Update MULTI_LLM_CHAIN.md for architecture changes
- Add docstrings to all new functions/classes
- Update CHANGELOG.md with your changes

---

## 🏗️ Architecture Principles

### Zero-Cloud Requirement
**CRITICAL**: All contributions must maintain zero-cloud architecture:
- ❌ No external API calls (OpenAI, Anthropic, etc.)
- ❌ No cloud storage (S3, GCS, etc.)
- ❌ No telemetry/analytics to external services
- ✅ All inference happens locally
- ✅ All data stays on hospital hardware

### HIPAA Compliance
- Never log PHI in plain text
- Always use cryptographic hashing for audit trails
- Maintain immutable audit logs
- Require physician e-signature before logging

### Clinical Safety
- Multi-LLM chain must preserve adversarial validation
- Hash chain integrity must be verifiable
- Never skip safety checks for performance
- All recommendations labeled as "decision support" not "autonomous"

---

## 🎨 Contribution Types

### Bug Fixes

1. Create an issue describing the bug
2. Reference the issue in your PR: `Fixes #123`
3. Include test that reproduces the bug
4. Verify fix doesn't break existing tests

### New Features

Before starting major features, open an issue to discuss:
- Is this aligned with project vision?
- How does it maintain HIPAA compliance?
- What's the testing strategy?

**Roadmap (PRs welcome):**
- [ ] EHR integration (Epic, Cerner)
- [ ] Additional clinical specialties (cardiology, oncology)
- [ ] Multi-language support (Spanish, Mandarin)
- [ ] Advanced Bayesian models (hierarchical, multi-level)
- [ ] Chain visualization UI (flowchart of reasoning)
- [ ] FHIR format export
- [ ] Reinforcement learning from physician overrides
- [ ] Parallel chain execution

### Documentation

- Fix typos
- Clarify confusing sections
- Add examples
- Improve deployment guides

---

## 🔬 Testing Guidelines

### Unit Tests

```python
# Test single function in isolation
def test_hash_computation(self):
    chain = MultiLLMChain()
    hash1 = chain._compute_step_hash("Test", "prompt", "response", "prev")
    self.assertIsNotNone(hash1)
```

### Integration Tests

```python
# Test full workflow with mocked LLM
@patch('llm_chain.grok_query')
def test_full_chain(self, mock_grok):
    mock_grok.return_value = "Test response"
    result = run_multi_llm_decision(...)
    self.assertEqual(len(result['chain_steps']), 4)
```

### Clinical Validation Tests

For medical accuracy, we need:
- Retrospective case reviews
- Pharmacist validation
- Comparison to clinical guidelines
- IRB-approved prospective studies

---

## 📤 Submitting a Pull Request

### Checklist

Before submitting, ensure:
- [ ] Code follows PEP 8 style (run `black` and `flake8`)
- [ ] All tests pass (`python -m unittest test_v2.py`)
- [ ] New features have tests (>80% coverage)
- [ ] Documentation updated (README, docstrings, etc.)
- [ ] CHANGELOG.md updated
- [ ] No PHI in code/tests (use synthetic data only)
- [ ] Zero-cloud architecture maintained
- [ ] Hash chain integrity preserved (if touching llm_chain.py)

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement

## Testing
- [ ] Unit tests added/updated
- [ ] All tests pass locally
- [ ] Manual testing performed

## HIPAA Compliance
- [ ] No PHI in code
- [ ] No external API calls
- [ ] Audit trail maintained

## Checklist
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
```

---

## 🚫 What We Won't Accept

- Cloud-based features (violates zero-cloud architecture)
- Removing safety checks (adversarial model, hash verification)
- Proprietary code without clear licensing
- Features that skip physician review
- Changes that break audit trail integrity

---

## 📜 License

By contributing, you agree that your contributions will be licensed under the same MIT license with clinical use restrictions. See [LICENSE](LICENSE) for details.

**Commercial/Clinical Use:** Requires written authorization even for contributors.

---

## 🏥 Clinical Deployment

If you're deploying Grok Doc in a hospital:
1. Open an issue to share your experience
2. Document any deployment challenges
3. Share anonymized usage statistics (if permitted by IRB)
4. Contribute hospital-specific integration guides

---

## 💬 Communication

- **GitHub Issues**: Bug reports, feature requests
- **Pull Requests**: Code review and discussion
- **Twitter**: [@ohio_dino](https://twitter.com/ohio_dino) for general questions
- **Email**: For partnership/commercial inquiries

---

## 🌟 Recognition

Contributors will be recognized in:
- CHANGELOG.md (for significant contributions)
- README.md acknowledgments
- GitHub contributors page

---

## ❓ Questions?

Not sure where to start? Open an issue with the label `question` or reach out on Twitter.

Thank you for helping make clinical AI safer and more transparent!

---

**Last Updated**: 2025-11-18
