#!/bin/bash
#
# Grok Doc v2.0 - Automated Launch Script
#
# This script automatically:
# 1. Checks system requirements
# 2. Loads the LLM model
# 3. Generates case database if needed
# 4. Launches the Streamlit UI
#
# Usage:
#   ./launch_v2.sh                    # Launch with default settings
#   ./launch_v2.sh --port 8080        # Launch on custom port
#   ./launch_v2.sh --no-wifi-check    # Disable WiFi verification (dev mode)
#

set -e  # Exit on error

# ── CONFIGURATION ─────────────────────────────────────────────────
DEFAULT_PORT=8501
MODEL_PATH="${GROK_MODEL_PATH:-/models/llama-3.1-70b-instruct-awq}"
MIN_VRAM_GB=80
CASE_INDEX="case_index.faiss"
CASES_FILE="cases_17k.jsonl"

# ── COLOR OUTPUT ───────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

# ── PARSE ARGUMENTS ───────────────────────────────────────────────
PORT=$DEFAULT_PORT
NO_WIFI_CHECK=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --no-wifi-check)
            NO_WIFI_CHECK=true
            shift
            ;;
        --help)
            echo "Grok Doc v2.0 Launch Script"
            echo ""
            echo "Usage: ./launch_v2.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --port PORT          Set Streamlit port (default: 8501)"
            echo "  --no-wifi-check      Disable hospital WiFi verification (dev only)"
            echo "  --help               Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  GROK_MODEL_PATH      Path to LLM model (default: /models/llama-3.1-70b-instruct-awq)"
            exit 0
            ;;
        *)
            error "Unknown option: $1. Use --help for usage."
            ;;
    esac
done

# ── HEADER ────────────────────────────────────────────────────────
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║           🩺  Grok Doc v2.0 Launch Script                 ║"
echo "║                                                            ║"
echo "║  Multi-LLM Clinical AI • On-Premises • HIPAA-Compliant   ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# ── SYSTEM CHECKS ─────────────────────────────────────────────────
info "Running system checks..."

# Check Python version
if ! command -v python3 &> /dev/null; then
    error "Python 3 is not installed. Please install Python 3.9+"
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.9"
if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    error "Python $REQUIRED_VERSION+ required. Found: $PYTHON_VERSION"
fi

info "✓ Python $PYTHON_VERSION found"

# Check GPU availability
if ! command -v nvidia-smi &> /dev/null; then
    warn "nvidia-smi not found. GPU inference may not be available."
else
    GPU_COUNT=$(nvidia-smi --list-gpus | wc -l)
    TOTAL_VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | awk '{sum+=$1} END {print sum/1024}')

    info "✓ Found $GPU_COUNT GPU(s) with ${TOTAL_VRAM}GB total VRAM"

    if (( $(echo "$TOTAL_VRAM < $MIN_VRAM_GB" | bc -l) )); then
        warn "Recommended VRAM: ${MIN_VRAM_GB}GB+. You have: ${TOTAL_VRAM}GB."
        warn "Consider using a smaller model (e.g., Llama-3.1-8B)"
    fi
fi

# Check if model exists
if [ ! -d "$MODEL_PATH" ]; then
    warn "Model not found at $MODEL_PATH"
    warn "Please download the model first:"
    echo ""
    echo "    huggingface-cli download meta-llama/Meta-Llama-3.1-70B-Instruct-AWQ \\"
    echo "      --local-dir $MODEL_PATH"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    info "✓ Model found at $MODEL_PATH"
fi

# Check dependencies
info "Checking Python dependencies..."
if ! python3 -c "import streamlit" &> /dev/null; then
    warn "Streamlit not installed. Installing dependencies..."
    pip install -r requirements.txt
fi

info "✓ Dependencies OK"

# ── GENERATE CASE DATABASE ───────────────────────────────────────
if [ ! -f "$CASE_INDEX" ] || [ ! -f "$CASES_FILE" ]; then
    warn "Case database not found. Generating sample database..."
    info "This may take 2-3 minutes..."

    python3 data_builder.py

    if [ $? -eq 0 ]; then
        info "✓ Case database generated"
    else
        error "Failed to generate case database"
    fi
else
    info "✓ Case database found ($CASES_FILE)"
fi

# ── WIFI CHECK CONFIGURATION ──────────────────────────────────────
if [ "$NO_WIFI_CHECK" = true ]; then
    warn "WiFi check DISABLED (development mode)"
    warn "⚠️  DO NOT use in production - PHI protection disabled!"
    export REQUIRE_WIFI_CHECK=false
else
    info "Hospital WiFi verification enabled"
fi

# ── LAUNCH STREAMLIT ──────────────────────────────────────────────
info "Starting Grok Doc v2.0 on port $PORT..."
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║  🚀 Grok Doc v2.0 is starting...                          ║"
echo "║                                                            ║"
echo "║  Access at: http://localhost:$PORT                       ║"
echo "║                                                            ║"
echo "║  Features:                                                ║"
echo "║    • ⚡ Fast Mode (v1.0) - Single LLM (~2s)               ║"
echo "║    • 🔗 Chain Mode (v2.0) - Multi-LLM chain (~8s)         ║"
echo "║                                                            ║"
echo "║  Press Ctrl+C to stop                                     ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Export model path for app
export GROK_MODEL_PATH="$MODEL_PATH"

# Launch Streamlit
streamlit run app.py \
    --server.port=$PORT \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.serverAddress=localhost \
    --browser.gatherUsageStats=false

# ── CLEANUP ───────────────────────────────────────────────────────
info "Grok Doc v2.0 stopped"
