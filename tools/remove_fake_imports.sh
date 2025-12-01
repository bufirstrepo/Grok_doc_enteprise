#!/bin/bash
# tools/remove_fake_imports.sh
# Safe repo-wide removal of fake import lines and header tokens
# Creates .bak backups before modification

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "============================================="
echo "Fake Import and Header Token Removal Tool"
echo "============================================="
echo ""
echo "This script removes the following patterns:"
echo "  - google.antigravity imports"
echo "  - antigravity-sdk references"
echo "  - !MAINTAIN_PERSISTENCE headers"
echo "  - 2025_MODE headers"
echo "  - SIMULATION_MODE headers"
echo ""

# Patterns to remove (lines containing these will be deleted)
PATTERNS=(
    "google\.antigravity"
    "antigravity-sdk"
    "!MAINTAIN_PERSISTENCE"
    "2025_MODE"
    "SIMULATION_MODE"
    "from src\.core\.phase_arbiter"
    "from src\.agents\.induction_red_team"
    "import phase_arbiter"
    "import induction_red_team"
)

# Find Python files
echo "Scanning Python files..."
FILES=$(find . -name "*.py" -type f ! -path "./.git/*" ! -path "./deprecated/*" ! -path "./__pycache__/*")

MODIFIED_FILES=()
BACKUP_FILES=()

for pattern in "${PATTERNS[@]}"; do
    echo "  Checking for pattern: $pattern"
    
    for file in $FILES; do
        if grep -q "$pattern" "$file" 2>/dev/null; then
            # Create backup if not already done
            if [[ ! -f "${file}.bak" ]]; then
                cp "$file" "${file}.bak"
                BACKUP_FILES+=("${file}.bak")
                echo "    Created backup: ${file}.bak"
            fi
            
            # Remove lines containing the pattern
            sed -i "/$pattern/d" "$file"
            
            if [[ ! " ${MODIFIED_FILES[*]} " =~ " ${file} " ]]; then
                MODIFIED_FILES+=("$file")
            fi
            echo "    Removed from: $file"
        fi
    done
done

echo ""
echo "============================================="
echo "Summary"
echo "============================================="
echo "Files modified: ${#MODIFIED_FILES[@]}"
echo "Backup files created: ${#BACKUP_FILES[@]}"

if [ ${#MODIFIED_FILES[@]} -gt 0 ]; then
    echo ""
    echo "Modified files:"
    for f in "${MODIFIED_FILES[@]}"; do
        echo "  - $f"
    done
fi

if [ ${#BACKUP_FILES[@]} -gt 0 ]; then
    echo ""
    echo "Backup files (.bak) for review:"
    for f in "${BACKUP_FILES[@]}"; do
        echo "  - $f"
    done
    echo ""
    echo "To remove backups after verification:"
    echo "  find . -name '*.bak' -type f -delete"
fi

echo ""
echo "Done. Please verify the changes before committing."
