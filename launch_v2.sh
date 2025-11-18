#!/bin/bash
# Grok Doc v2.0 Launch Script
# Automates testing, committing, and deploying v2.0

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Grok Doc v2.0 Launch Script${NC}"
echo -e "${BLUE}  Multi-LLM Decision Chain Release${NC}"
echo -e "${BLUE}════════════════════════════════════════════════${NC}"
echo ""

# Check we're in the right directory
if [ ! -f "app.py" ]; then
    echo -e "${RED}✗ Error: app.py not found. Run this from the repo root.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Repository root detected${NC}"

# Step 1: Verify required files exist
echo ""
echo -e "${YELLOW}Step 1: Verifying v2.0 files...${NC}"

REQUIRED_FILES=(
    "llm_chain.py"
    "MULTI_LLM_CHAIN.md"
    "test_v2.py"
    "app.py"
    "README.md"
    "CHANGELOG.md"
)

MISSING_FILES=0
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}  ✓ $file${NC}"
    else
        echo -e "${RED}  ✗ MISSING: $file${NC}"
        MISSING_FILES=$((MISSING_FILES + 1))
    fi
done

if [ $MISSING_FILES -gt 0 ]; then
    echo -e "${RED}✗ Missing $MISSING_FILES file(s). Create them before launching.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All required files present${NC}"

# Step 2: Run tests
echo ""
echo -e "${YELLOW}Step 2: Running test suite...${NC}"

if python test_v2.py; then
    echo -e "${GREEN}✓ All tests passed${NC}"
else
    echo -e "${RED}✗ Tests failed. Fix errors before launching.${NC}"
    exit 1
fi

# Step 3: Check git status
echo ""
echo -e "${YELLOW}Step 3: Checking git status...${NC}"

if ! git diff --quiet; then
    echo -e "${YELLOW}  ⚠ Uncommitted changes detected${NC}"
    git status --short
else
    echo -e "${GREEN}  ✓ No uncommitted changes${NC}"
fi

# Step 4: Confirm launch
echo ""
echo -e "${YELLOW}════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Ready to launch v2.0?${NC}"
echo -e "${YELLOW}════════════════════════════════════════════════${NC}"
echo ""
echo "This will:"
echo "  1. Stage all v2.0 files"
echo "  2. Commit with detailed message"
echo "  3. Tag as v2.0.0"
echo "  4. Push to GitHub"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Launch cancelled${NC}"
    exit 0
fi

# Step 5: Stage files
echo ""
echo -e "${YELLOW}Step 4: Staging files...${NC}"

git add llm_chain.py
git add MULTI_LLM_CHAIN.md
git add test_v2.py
git add DEPLOY_V2.md 2>/dev/null || echo "  (DEPLOY_V2.md not found, skipping)"
git add app.py
git add README.md
git add CHANGELOG.md

echo -e "${GREEN}✓ Files staged${NC}"

# Step 6: Commit
echo ""
echo -e "${YELLOW}Step 5: Committing v2.0...${NC}"

git commit -m "Release v2.0: Multi-LLM Decision Chain

Major Features:
- 4-stage LLM reasoning chain (Kinetics → Adversarial → Literature → Arbiter)
- Cryptographic verification of complete reasoning chain
- Toggle between Fast Mode (v1.0) and Chain Mode (v2.0)
- Enhanced UI with chain breakdown and verification
- Complete technical documentation

Technical Changes:
- Added llm_chain.py: Core multi-LLM orchestrator
- Updated app.py: v2.0 UI with mode toggle
- Enhanced audit logging with chain metadata
- Comprehensive test suite

Documentation:
- MULTI_LLM_CHAIN.md: Technical architecture
- Updated README.md: v2.0 features and usage
- CHANGELOG.md: Complete version history
- Test suite with 4 verification tests

This is the core innovation that makes Grok Doc legally defensible 
and clinically robust through transparent, multi-model reasoning."

echo -e "${GREEN}✓ Committed${NC}"

# Step 7: Tag
echo ""
echo -e "${YELLOW}Step 6: Creating v2.0.0 tag...${NC}"

git tag -a v2.0.0 -m "Multi-LLM Decision Chain Release

Major Features:
- 4-stage specialized LLM chain
- Adversarial risk analysis
- Evidence-based synthesis
- Cryptographic verification

See CHANGELOG.md for complete details."

echo -e "${GREEN}✓ Tagged as v2.0.0${NC}"

# Step 8: Push
echo ""
echo -e "${YELLOW}Step 7: Pushing to GitHub...${NC}"

git push origin main
git push origin --tags

echo -e "${GREEN}✓ Pushed to GitHub${NC}"

# Step 9: Summary
echo ""
echo -e "${GREEN}════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ v2.0 Successfully Launched!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. Create GitHub Release:"
echo "   https://github.com/bufirstrepo/Grok_doc_revision/releases/new"
echo "   - Tag: v2.0.0"
echo "   - Title: Grok Doc v2.0 - Multi-LLM Decision Chain"
echo ""
echo "2. Record demo video showing:"
echo "   - Fast Mode (v1.0)"
echo "   - Chain Mode (v2.0) with all 4 steps"
echo "   - Chain verification"
echo ""
echo "3. Tweet the announcement:"
echo "   🚀 Grok Doc v2.0 is LIVE"
echo "   "
echo "   Introducing the Multi-LLM Decision Chain:"
echo "   • 4 specialized models analyze every decision"
echo "   • Kinetics → Adversarial → Literature → Arbiter"
echo "   • Cryptographically verified reasoning trail"
echo "   "
echo "   github.com/bufirstrepo/Grok_doc_revision"
echo "   "
echo "   @elonmusk @xai"
echo ""
echo "4. Verify deployment:"
echo "   - Visit: https://github.com/bufirstrepo/Grok_doc_revision"
echo "   - Check all files are visible"
echo "   - Verify README displays correctly"
echo "   - Test fresh clone works"
echo ""
echo -e "${BLUE}════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Congratulations on shipping v2.0! 🎉${NC}"
echo -e "${BLUE}════════════════════════════════════════════════${NC}"
