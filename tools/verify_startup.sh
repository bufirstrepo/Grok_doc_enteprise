#!/bin/bash
# Verify App Startup and Imports

echo "Verifying App Startup..."

# 1. Check for duplicate lines in app.py
echo "Checking for duplicates in app.py..."
DUPLICATES=$(uniq -d src/app.py 2>/dev/null)
if [ -n "$DUPLICATES" ]; then
    echo "❌ Duplicates found in app.py"
    exit 1
else
    echo "✓ No duplicates found in app.py"
fi

# 2. Verify Imports
echo "Verifying imports..."
python3 -c "from local_inference import init_inference_engine; print('✓ local_inference ok')" || exit 1
python3 -c "import flask; print('✓ flask ok')" || echo "⚠️ flask missing (optional)"
python3 -c "import sqlcipher3; print('✓ sqlcipher3 ok')" || echo "⚠️ sqlcipher3 missing (optional)"

# 3. Verify Startup (Dry Run)
# We can't easily run streamlit in headless mode without it staying open, 
# but we can import app to check for syntax errors.
echo "Checking app.py syntax..."
python3 -m py_compile app.py || exit 1
echo "✓ app.py syntax ok"

echo "All checks passed!"
