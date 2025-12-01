#!/bin/bash
# remove_fake_imports.sh - Safely removes fake/hallucinated imports from Python files
# Creates .bak files before modification

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== Fake Import Removal Tool ==="
echo "Repository: $REPO_ROOT"
echo ""

# Define fake imports/patterns to remove
FAKE_PATTERNS=(
    "google.antigravity"
    "antigravity_sdk"
    "antigravity-sdk"
    "src.core.phase_arbiter"
    "src.agents.induction_red_team"
)

# Define header tokens to strip
HEADER_TOKENS=(
    "!MAINTAIN_PERSISTENCE"
    "2025_MODE"
    "SIMULATION_MODE"
    "TRIBUNAL"
)

# Counter for modifications
MODIFIED_COUNT=0

# Function to process a single file
process_file() {
    local file="$1"
    local modified=false
    
    # Create backup
    cp "$file" "$file.bak"
    
    # Check for fake imports
    for pattern in "${FAKE_PATTERNS[@]}"; do
        if grep -q "$pattern" "$file"; then
            echo "  Found fake import '$pattern' in $file"
            # Remove lines containing the pattern
            sed -i "/$pattern/d" "$file"
            modified=true
        fi
    done
    
    # Check for header tokens (only strip lines that are comments or at start)
    for token in "${HEADER_TOKENS[@]}"; do
        if grep -q "$token" "$file"; then
            echo "  Found header token '$token' in $file"
            # Remove lines containing the token that appear to be headers/comments
            sed -i "/^#.*$token/d" "$file"
            sed -i "/^\"\"\".*$token/d" "$file"
            sed -i "/^'''.*$token/d" "$file"
            modified=true
        fi
    done
    
    # If no modifications, remove backup
    if [ "$modified" = false ]; then
        rm "$file.bak"
    else
        echo "  Backup saved: $file.bak"
        MODIFIED_COUNT=$((MODIFIED_COUNT + 1))
    fi
}

echo "Scanning Python files..."
echo ""

# Find and process all Python files
while IFS= read -r -d '' file; do
    # Skip deprecated, __pycache__, and .git directories
    if [[ "$file" == *"deprecated"* ]] || [[ "$file" == *"__pycache__"* ]] || [[ "$file" == *".git"* ]]; then
        continue
    fi
    process_file "$file"
done < <(find . -name "*.py" -type f -print0)

echo ""
echo "=== Summary ==="
echo "Files modified: $MODIFIED_COUNT"

if [ $MODIFIED_COUNT -eq 0 ]; then
    echo "✓ No fake imports or header tokens found - repository is clean!"
else
    echo "⚠ Modified $MODIFIED_COUNT files. Check .bak files for originals."
fi

echo ""
echo "=== Verification Grep ==="
echo "Checking for remaining issues..."

# Final verification
ISSUES=0
for pattern in "${FAKE_PATTERNS[@]}"; do
    if grep -rn "$pattern" --include="*.py" . 2>/dev/null | grep -v "deprecated\|__pycache__\|\.bak"; then
        echo "⚠ Still found: $pattern"
        ISSUES=$((ISSUES + 1))
    fi
done

for token in "${HEADER_TOKENS[@]}"; do
    if grep -rn "$token" --include="*.py" . 2>/dev/null | grep -v "deprecated\|__pycache__\|\.bak"; then
        echo "⚠ Still found: $token"
        ISSUES=$((ISSUES + 1))
    fi
done

if [ $ISSUES -eq 0 ]; then
    echo "✓ All fake imports and header tokens removed!"
    exit 0
else
    echo "⚠ Found $ISSUES remaining issues - manual review needed"
    exit 1
fi
