#!/bin/bash
#
# verify_startup.sh - Verify Grok Doc Enterprise startup configuration
#
# This script verifies:
# 1. The app binds to 127.0.0.1 (localhost only)
# 2. local_inference.py can be imported successfully
# 3. No hallucinated imports or files exist
#
# Usage: ./tools/verify_startup.sh
#
# Exit codes:
#   0 - All checks passed
#   1 - One or more checks failed
#

set -e

# ── COLOR OUTPUT ───────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; FAILED=1; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

FAILED=0

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     Grok Doc Enterprise - Startup Verification Script      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# ── CHECK 1: Verify 127.0.0.1 binding in launch script ────────────
echo "1. Checking server binding configuration..."

if grep -q "server.address=127.0.0.1" launch_v2.sh 2>/dev/null; then
    pass "launch_v2.sh binds to 127.0.0.1"
else
    fail "launch_v2.sh does not bind to 127.0.0.1 - security risk"
fi

# ── CHECK 2: Verify local_inference.py can be imported ────────────
echo ""
echo "2. Checking local_inference.py import..."

# Set environment to skip auto-init during import check
export SKIP_AUTO_INIT=true

if python3 -c "from local_inference import grok_query, list_available_models; print('Import successful')" 2>/dev/null; then
    pass "local_inference.py imports successfully"
else
    fail "local_inference.py failed to import"
fi

# ── CHECK 3: Verify fail-fast error handling in app.py ────────────
echo ""
echo "3. Checking app.py fail-fast error handling..."

if grep -q "sys.exit(1)" app.py && grep -q "FATAL.*local_inference" app.py 2>/dev/null; then
    pass "app.py has fail-fast error handling for local_inference"
else
    fail "app.py missing fail-fast error handling for local_inference import"
fi

# ── CHECK 4: No hallucinated files ────────────────────────────────
echo ""
echo "4. Checking for hallucinated files..."

HALLUCINATED_FILES="induction_red_team.py phase_arbiter.py transformer_scribe.py"
FOUND_HALLUCINATED=0

for file in $HALLUCINATED_FILES; do
    if find . -name "$file" 2>/dev/null | grep -q .; then
        fail "Found hallucinated file: $file"
        FOUND_HALLUCINATED=1
    fi
done

if [ $FOUND_HALLUCINATED -eq 0 ]; then
    pass "No hallucinated files found"
fi

# ── CHECK 5: No hallucinated imports ──────────────────────────────
echo ""
echo "5. Checking for hallucinated imports..."

HALLUCINATED_IMPORTS="google.antigravity src.core.phase_arbiter src.agents.induction_red_team"
FOUND_HALLUCINATED_IMPORT=0

for import_name in $HALLUCINATED_IMPORTS; do
    if grep -r "$import_name" --include="*.py" . 2>/dev/null | grep -q .; then
        fail "Found hallucinated import: $import_name"
        FOUND_HALLUCINATED_IMPORT=1
    fi
done

if [ $FOUND_HALLUCINATED_IMPORT -eq 0 ]; then
    pass "No hallucinated imports found"
fi

# ── CHECK 6: No simulation header tokens ──────────────────────────
echo ""
echo "6. Checking for simulation header tokens..."

SIMULATION_TOKENS="!MAINTAIN_PERSISTENCE 2025_MODE SIMULATION_MODE TRIBUNAL"
FOUND_TOKEN=0

for token in $SIMULATION_TOKENS; do
    if grep -r "$token" --include="*.py" . 2>/dev/null | grep -q .; then
        fail "Found simulation token: $token"
        FOUND_TOKEN=1
    fi
done

if [ $FOUND_TOKEN -eq 0 ]; then
    pass "No simulation header tokens found"
fi

# ── CHECK 7: Required dependencies in requirements.txt ────────────
echo ""
echo "7. Checking required dependencies..."

REQUIRED_DEPS="anthropic google-generativeai blake3"
for dep in $REQUIRED_DEPS; do
    if grep -q "$dep" requirements.txt 2>/dev/null; then
        pass "Dependency found: $dep"
    else
        fail "Missing dependency: $dep"
    fi
done

# ── CHECK 8: router.py has route_request function ─────────────────
echo ""
echo "8. Checking router.py configuration..."

if grep -q "def route_request" src/core/router.py 2>/dev/null; then
    pass "src/core/router.py has route_request function"
else
    fail "src/core/router.py missing route_request function"
fi

# ── SUMMARY ───────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════════════"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All verification checks passed!${NC}"
    echo "════════════════════════════════════════════════════════════════"
    exit 0
else
    echo -e "${RED}Some verification checks failed. Please review above.${NC}"
    echo "════════════════════════════════════════════════════════════════"
    exit 1
fi
