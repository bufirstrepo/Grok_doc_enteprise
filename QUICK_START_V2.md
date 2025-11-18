# Grok Doc v2.0 - Quick Start Guide

## 🚀 Get Running in 5 Minutes

### Prerequisites
- Python 3.9+
- 80GB+ VRAM GPU (or use smaller model)
- Hospital WiFi network

### Install

```bash
git clone https://github.com/bufirstrepo/Grok_doc_enteprise.git
cd Grok_doc_enteprise
pip install -r requirements.txt
python data_builder.py  # Generate sample database
```

### Launch

```bash
./launch_v2.sh
# Or manually:
streamlit run app.py
```

Access at: `http://localhost:8501`

---

## 🎯 Your First Query

1. **Enter patient info:**
   - MRN: `12345678`
   - Age: `72`
   - Gender: `Male`
   - Question: `"72M septic shock on vancomycin, Cr 2.9→1.8. Safe trough?"`

2. **Choose mode:**
   - **⚡ Fast Mode**: Quick answer (~2s)
   - **🔗 Chain Mode**: Deep reasoning (~8s)

3. **Review & sign** the recommendation

---

## 🔗 Multi-LLM Chain (v2.0)

**When to use Chain Mode:**
- High-risk medications (vancomycin, warfarin, aminoglycosides)
- Complex cases with comorbidities
- Low Bayesian confidence (< 70%)
- Need complete audit trail

**What happens:**
1. **Kinetics Model** → PK/PD calculations
2. **Adversarial Model** → Risk analysis (devil's advocate)
3. **Literature Model** → Evidence-based validation
4. **Arbiter Model** → Final synthesized recommendation

**Output:**
- Final recommendation with confidence score
- Complete reasoning chain (4 steps)
- Cryptographic hash verification
- Full audit trail for regulatory compliance

---

## ⚡ Fast Mode (v1.0)

**When to use Fast Mode:**
- Straightforward clinical questions
- Time-sensitive decisions
- High Bayesian confidence (> 90%)
- Low-risk scenarios

**What happens:**
1. Vector search → 100 similar cases
2. Bayesian safety analysis
3. Single LLM call with evidence
4. Recommendation with confidence

---

## 🔒 Audit Trail

Every decision is logged with:
- Patient context + query
- AI recommendation
- Physician signature
- Analysis mode (Fast vs Chain)
- Cryptographic hash (tamper-evident)

**Verify integrity:**
```bash
python -c "from audit_log import verify_audit_integrity; print(verify_audit_integrity())"
```

---

## 🛠️ Common Commands

```bash
# Launch with custom port
./launch_v2.sh --port 8080

# Disable WiFi check (dev only)
./launch_v2.sh --no-wifi-check

# Run tests
python -m unittest test_v2.py

# Export audit trail
python -c "from audit_log import export_audit_trail; export_audit_trail('audit.json')"

# Verify chain integrity
python -c "from llm_chain import MultiLLMChain; print('Chain OK')"
```

---

## 📊 Performance Tips

**For faster inference:**
- Use AWQ-quantized models (4-bit)
- Enable tensor parallelism: `--tensor-parallel-size 4`
- Use vLLM for batching

**For better accuracy:**
- Use Chain Mode for critical decisions
- Increase case database size (50k+ cases)
- Update to latest clinical guidelines

---

##⚠️ Troubleshooting

**"Model not found"**
```bash
export GROK_MODEL_PATH="/path/to/your/model"
```

**"FAISS index not found"**
```bash
python data_builder.py
```

**"WiFi check failed"**
```python
# In app.py, set:
REQUIRE_WIFI_CHECK = False
```

**"Chain verification failed"**
```python
# Check audit logs for tampering
from audit_log import verify_audit_integrity
result = verify_audit_integrity()
print(result)
```

---

## 📞 Get Help

- **Issues**: https://github.com/bufirstrepo/Grok_doc_enteprise/issues
- **Docs**: See README.md and MULTI_LLM_CHAIN.md
- **Contact**: [@ohio_dino](https://twitter.com/ohio_dino)

---

**Quick Reference:**
- Fast Mode = 1 LLM call (~2s)
- Chain Mode = 4 LLM calls (~8s)
- Both modes use Bayesian analysis + case retrieval
- All decisions logged with e-signature
- 100% on-premises, zero cloud
