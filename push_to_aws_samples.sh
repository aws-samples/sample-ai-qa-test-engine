#!/bin/bash
set -e

echo "=== Pushing ai-qa-test-engine to aws-samples/sample-ai-qa-test-engine ==="

cd /Users/dedhiaj/projects/ai-qa-test-engine

# Step 1: Check if 'origin' remote exists and update it, or add it
REMOTE_URL="git@github.com:aws-samples/sample-ai-qa-test-engine.git"
if git remote get-url origin &>/dev/null; then
    echo "Updating existing 'origin' remote..."
    git remote set-url origin "$REMOTE_URL"
else
    echo "Adding 'origin' remote..."
    git remote add origin "$REMOTE_URL"
fi

echo "Remote set to: $(git remote get-url origin)"

# Step 2: Scan for secrets (required by aws-samples policy)
echo ""
echo "=== Scanning for secrets ==="
if command -v git-secrets &>/dev/null; then
    git secrets --scan
    echo "✅ No secrets found"
else
    echo "⚠️  git-secrets not installed. Install it before pushing:"
    echo "    brew install git-secrets"
    echo "    git secrets --install"
    echo "    git secrets --register-aws"
    echo ""
    echo "Continuing anyway, but you MUST install git-secrets for aws-samples compliance."
fi

# Step 3: Make sure all code is committed
echo ""
echo "=== Checking git status ==="
if [ -n "$(git status --porcelain)" ]; then
    echo "Uncommitted changes found. Staging and committing..."
    git add .
    git commit -m "Initial commit for aws-samples publication"
else
    echo "All changes already committed."
fi

# Step 4: Push to aws-samples (force to overwrite template placeholder)
echo ""
echo "=== Pushing to aws-samples ==="
git push origin main --force

echo ""
echo "✅ Done! Your code is now at:"
echo "   https://github.com/aws-samples/sample-ai-qa-test-engine"
echo ""
echo "=== Next Step: Make the repo PUBLIC ==="
echo "Go to: https://console.harmony.a2z.com/open-sourcerer"
echo "Find your repo and request public release."
