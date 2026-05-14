#!/bin/bash

# Pre-commit hook to prevent accidentally committing .env files and secrets
# Install: Copy to .git/hooks/pre-commit and make executable

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check for .env files in staging area
echo "🔍 Checking for .env files in commit..."

# Get list of files staged for commit
STAGED_FILES=$(git diff --cached --name-only)

# Patterns that indicate secrets
SECRET_PATTERNS=(
    "^\.env"              # .env files
    "\.env\."             # .env.* files
    "credentials"         # credentials files
    "secrets"             # secrets files
    "private_key"         # private keys
    "password"            # passwords
    "api_key"             # api keys
    "token"               # tokens
)

ERROR_FOUND=false

# Check each staged file
for file in $STAGED_FILES; do
    # Skip if file no longer exists (deleted)
    if [ ! -f "$file" ]; then
        continue
    fi
    
    # Check filename against patterns
    for pattern in "${SECRET_PATTERNS[@]}"; do
        if [[ "$file" =~ $pattern ]]; then
            echo -e "${RED}❌ ERROR: Secret file detected in commit: $file${NC}"
            ERROR_FOUND=true
        fi
    done
    
    # Check file contents for secret patterns
    if grep -qE "(api_key|password|secret|token).*=" "$file" 2>/dev/null; then
        echo -e "${RED}⚠️  WARNING: Potential secret in file: $file${NC}"
        ERROR_FOUND=true
    fi
done

if [ "$ERROR_FOUND" = true ]; then
    echo ""
    echo -e "${RED}❌ COMMIT BLOCKED: Secrets detected in files${NC}"
    echo ""
    echo "🔧 How to fix:"
    echo "  1. Remove the secret files from staging:"
    echo "     git reset <file>"
    echo "  2. Add them to .gitignore (if not already there):"
    echo "     echo '.env' >> .gitignore"
    echo "  3. Verify they're not tracked:"
    echo "     git rm --cached <file>"
    echo "  4. Retry the commit:"
    echo "     git commit -m '...'"
    echo ""
    echo "📚 For more help, see: config/SECRET-MANAGEMENT.md"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ Pre-commit check passed - no secrets detected${NC}"
exit 0
