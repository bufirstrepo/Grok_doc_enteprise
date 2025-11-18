#!/bin/bash
#
# Grok Doc v2.0 - One-Time Setup Script
#
# This script performs initial setup:
# 1. Checks system requirements
# 2. Installs Python dependencies
# 3. Downloads the LLM model (optional)
# 4. Generates case database
# 5. Runs tests to verify installation
#
# Usage:
#   ./setup.sh                # Full setup with model download
#   ./setup.sh --skip-model   # Skip model download
#

set -e  # Exit on error

# ── CONFIGURATION ─────────────────────────────────────────────────
PYTHON_MIN_VERSION="3.9"
MODEL_PATH="${GROK_MODEL_PATH:-/models/llama-3.1-70b-instruct-awq}"
MODEL_HF_REPO="meta-llama/Meta-Llama-3.1-70B-Instruct-AWQ"

# ── COLOR OUTPUT ───────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

step() {
    echo -e "\n${BLUE}==>${NC} $1"
}

# ── PARSE ARGUMENTS ───────────────────────────────────────────────
SKIP_MODEL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-model)
            SKIP_MODEL=true
            shift
            ;;
        --help)
            echo "Grok Doc v2.0 Setup Script"
            echo ""
            echo "Usage: ./setup.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --skip-model    Skip LLM model download (~140GB)"
            echo "  --help          Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  GROK_MODEL_PATH  Target path for model (default: /models/llama-3.1-70b-instruct-awq)"
            exit 0
            ;;
        *)
            error "Unknown option: $1. Use --help for usage."
            ;;
    esac
done

# ── HEADER ────────────────────────────────────────────────────────
clear
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║           🩺  Grok Doc v2.0 Setup Script                  ║"
echo "║                                                            ║"
echo "║  Multi-LLM Clinical AI • On-Premises • HIPAA-Compliant   ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# ── STEP 1: SYSTEM CHECKS ─────────────────────────────────────────
step "Step 1/5: Checking system requirements"

# Check Python
if ! command -v python3 &> /dev/null; then
    error "Python 3 is not installed. Please install Python $PYTHON_MIN_VERSION+"
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
info "✓ Python $PYTHON_VERSION found"

# Check GPU
if command -v nvidia-smi &> /dev/null; then
    GPU_COUNT=$(nvidia-smi --list-gpus | wc -l)
    TOTAL_VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | awk '{sum+=$1} END {print sum/1024}')
    info "✓ Found $GPU_COUNT GPU(s) with ${TOTAL_VRAM}GB total VRAM"

    if (( $(echo "$TOTAL_VRAM < 80" | bc -l) )); then
        warn "Recommended: 80GB+ VRAM for Llama-3.1-70B"
        warn "Consider using Llama-3.1-8B for your hardware"
    fi
else
    warn "nvidia-smi not found. GPU inference may not be available."
fi

# Check disk space
AVAILABLE_GB=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')
if [ "$AVAILABLE_GB" -lt 200 ]; then
    warn "Low disk space: ${AVAILABLE_GB}GB available. Model requires ~140GB."
fi

# ── STEP 2: INSTALL DEPENDENCIES ──────────────────────────────────
step "Step 2/5: Installing Python dependencies"

if [ ! -f "requirements.txt" ]; then
    error "requirements.txt not found. Are you in the project directory?"
fi

info "Installing packages..."
pip install -r requirements.txt --quiet

info "✓ Dependencies installed"

# ── STEP 3: DOWNLOAD MODEL ────────────────────────────────────────
step "Step 3/5: LLM Model Setup"

if [ "$SKIP_MODEL" = true ]; then
    warn "Skipping model download (--skip-model flag)"
    warn "Set GROK_MODEL_PATH to your model location before running"
elif [ -d "$MODEL_PATH" ]; then
    info "✓ Model already exists at $MODEL_PATH"
else
    echo ""
    echo "┌────────────────────────────────────────────────────────┐"
    echo "│  Model Download                                        │"
    echo "│                                                        │"
    echo "│  Model: $MODEL_HF_REPO                                │"
    echo "│  Size: ~140GB                                          │"
    echo "│  Path: $MODEL_PATH                                    │"
    echo "│                                                        │"
    echo "│  This will take 15-60 minutes depending on your       │"
    echo "│  internet connection.                                 │"
    echo "└────────────────────────────────────────────────────────┘"
    echo ""

    read -p "Download model now? (y/N): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        info "Downloading model to $MODEL_PATH..."

        # Check if huggingface-cli is installed
        if ! command -v huggingface-cli &> /dev/null; then
            info "Installing huggingface-hub..."
            pip install huggingface-hub[cli] --quiet
        fi

        # Download model
        huggingface-cli download "$MODEL_HF_REPO" \
            --local-dir "$MODEL_PATH" \
            --local-dir-use-symlinks False

        info "✓ Model downloaded successfully"

        # Verify model files
        if [ -f "$MODEL_PATH/config.json" ]; then
            info "✓ Model verified (config.json found)"
        else
            warn "Model download may be incomplete (config.json not found)"
        fi
    else
        warn "Skipping model download. Remember to set GROK_MODEL_PATH before running."
    fi
fi

# ── STEP 4: GENERATE CASE DATABASE ────────────────────────────────
step "Step 4/5: Generating sample case database"

if [ -f "case_index.faiss" ] && [ -f "cases_17k.jsonl" ]; then
    info "✓ Case database already exists"
else
    info "Creating sample database (17k cases)..."
    info "This may take 2-3 minutes..."

    python3 data_builder.py

    if [ $? -eq 0 ]; then
        info "✓ Case database generated"
        info "  - case_index.faiss: $(du -h case_index.faiss | cut -f1)"
        info "  - cases_17k.jsonl: $(du -h cases_17k.jsonl | cut -f1)"
    else
        warn "Case database generation failed. You can run data_builder.py manually later."
    fi
fi

# ── STEP 5: RUN TESTS ──────────────────────────────────────────────
step "Step 5/5: Running tests"

info "Running test suite..."

python3 -m unittest test_v2.py -v

if [ $? -eq 0 ]; then
    info "✓ All tests passed"
else
    warn "Some tests failed. System may still work, but review errors."
fi

# ── SETUP COMPLETE ─────────────────────────────────────────────────
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║  ✅ Setup Complete!                                       ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

info "Next steps:"
echo ""
echo "  1. Set model path (if not downloaded):"
echo "     export GROK_MODEL_PATH=\"/path/to/your/model\""
echo ""
echo "  2. Launch Grok Doc v2.0:"
echo "     ./launch_v2.sh"
echo ""
echo "  3. Access web interface:"
echo "     http://localhost:8501"
echo ""
echo "  4. Configure for production:"
echo "     - Update WiFi keywords in app.py"
echo "     - Enable SSL/TLS"
echo "     - Integrate LDAP/AD authentication"
echo "     - Set up firewall rules"
echo ""

info "Documentation:"
echo "  - README.md           - Complete documentation"
echo "  - QUICK_START_V2.md   - Quick reference guide"
echo "  - MULTI_LLM_CHAIN.md  - Architecture details"
echo "  - SECURITY.md         - Security best practices"
echo ""

echo "For help: https://github.com/bufirstrepo/Grok_doc_enteprise/issues"
echo ""
