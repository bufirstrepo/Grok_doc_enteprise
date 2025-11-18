# Contributing to Grok Doc

Thank you for your interest in contributing to Grok Doc!

## Areas Where We Need Help

- [ ] EHR integration modules (Epic, Cerner, Allscripts)
- [ ] Additional clinical specialties (cardiology, oncology)
- [ ] Multi-language support
- [ ] Clinical validation studies
- [ ] Performance optimizations
- [ ] Documentation improvements

## How to Contribute

1. **Fork the repository**
2. **Create a feature branch:** `git checkout -b feature/your-feature-name`
3. **Make your changes**
4. **Test thoroughly:** Ensure zero-cloud architecture is maintained
5. **Commit:** `git commit -m "Add: your feature description"`
6. **Push:** `git push origin feature/your-feature-name`
7. **Open a Pull Request**

## Code Standards

- Follow PEP 8 for Python code
- Maintain zero-cloud architecture (no external API calls)
- All patient data handling must be HIPAA-compliant
- Include docstrings for all functions
- Add type hints where appropriate

## Testing

Before submitting:
```bash
python data_builder.py  # Verify database generation
streamlit run app.py    # Manual UI testing
```

## Questions?

Open an issue or contact [@ohio_dino](https://twitter.com/ohio_dino)
