#!/bin/bash
# tools/verify_startup.sh
# Verification script that imports src.local_inference and starts app.py briefly
# Checks that 127.0.0.1:8080 (or configured port) is listening

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "============================================="
echo "Startup Verification Script"
echo "============================================="

# Configuration
HOST="127.0.0.1"
PORT="${VERIFY_PORT:-8501}"  # Streamlit default port
TIMEOUT=30

echo ""
echo "Step 1: Verifying local_inference module import..."
echo "---------------------------------------------"

python3 << 'PYEOF'
import sys
sys.path.insert(0, '.')

try:
    from local_inference import init_inference_engine, get_current_model, list_available_models
    print("✓ local_inference module imported successfully")
    print(f"  Current model: {get_current_model()}")
    print(f"  Available models: {list(list_available_models().keys())[:5]}...")
except Exception as e:
    print(f"✗ Failed to import local_inference: {e}")
    sys.exit(1)

try:
    from src.config.hospital_config import get_config
    config = get_config()
    print("✓ Hospital configuration loaded")
except Exception as e:
    print(f"⚠ Warning: Could not load hospital config: {e}")

try:
    from llm_chain import MultiLLMChain
    print("✓ llm_chain module imported successfully")
except Exception as e:
    print(f"⚠ Warning: Could not import llm_chain: {e}")

print("")
print("Module verification complete.")
PYEOF

MODULE_STATUS=$?

if [ $MODULE_STATUS -ne 0 ]; then
    echo "✗ Module verification failed"
    exit 1
fi

echo ""
echo "Step 2: Verifying Streamlit app can start..."
echo "---------------------------------------------"

# Start Streamlit in background with timeout
timeout --preserve-status $TIMEOUT streamlit run app.py \
    --server.address $HOST \
    --server.port $PORT \
    --server.headless true \
    --browser.gatherUsageStats false \
    2>&1 &

APP_PID=$!

echo "Started app.py with PID $APP_PID"
echo "Waiting for server to start on $HOST:$PORT..."

# Wait for the port to be listening
WAITED=0
while [ $WAITED -lt $TIMEOUT ]; do
    if nc -z $HOST $PORT 2>/dev/null; then
        echo ""
        echo "✓ Server is listening on $HOST:$PORT"
        
        # Quick health check via curl if available
        if command -v curl &> /dev/null; then
            HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://$HOST:$PORT/_stcore/health" 2>/dev/null || echo "000")
            echo "  HTTP health check: $HTTP_CODE"
        fi
        
        # Kill the app
        kill $APP_PID 2>/dev/null || true
        wait $APP_PID 2>/dev/null || true
        
        echo ""
        echo "============================================="
        echo "✓ Startup verification PASSED"
        echo "============================================="
        exit 0
    fi
    
    sleep 1
    WAITED=$((WAITED + 1))
    printf "."
done

echo ""
echo "✗ Timeout waiting for server to start"

# Kill any remaining process
kill $APP_PID 2>/dev/null || true
wait $APP_PID 2>/dev/null || true

echo ""
echo "============================================="
echo "✗ Startup verification FAILED"
echo "============================================="
exit 1
