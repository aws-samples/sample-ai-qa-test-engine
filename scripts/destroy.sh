#!/bin/bash
# destroy.sh — Delete all AgentCore resources created by deploy.sh
#
# Usage:
#   ./scripts/destroy.sh                          # Delete default stack
#   ./scripts/destroy.sh --stack-name my-stack    # Delete custom stack

set -euo pipefail

STACK_NAME="${STACK_NAME:-ai-qa-test-engine}"
REGION="${AWS_REGION:-us-east-1}"

FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --stack-name) STACK_NAME="$2"; shift 2 ;;
        --region) REGION="$2"; shift 2 ;;
        --force) FORCE=true; shift ;;
        --help)
            echo "Usage: ./scripts/destroy.sh [--stack-name NAME] [--region REGION] [--force]"
            exit 0 ;;
        *) echo "Unknown: $1"; exit 1 ;;
    esac
done

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
TEST_BUCKET="${STACK_NAME}-tests-${ACCOUNT_ID}-${REGION}"
DEPLOY_BUCKET="${STACK_NAME}-deploy-${ACCOUNT_ID}-${REGION}"
LOGS_BUCKET="${STACK_NAME}-access-logs-${ACCOUNT_ID}-${REGION}"

echo "=============================================="
echo "AI QA Test Engine — DESTROY"
echo "=============================================="
echo "  Stack:   $STACK_NAME"
echo "  Region:  $REGION"
echo ""
echo "  This will DELETE:"
echo "    • AgentCore runtimes (orchestrator + test runner)"
echo "    • ECR repositories + images"
echo "    • IAM roles"
echo "    • CodeBuild projects"
echo "    • Lambda function"
echo "    • S3 buckets: $TEST_BUCKET, $DEPLOY_BUCKET, $LOGS_BUCKET"
echo ""
if [ "$FORCE" != true ]; then
    read -p "  Are you sure? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo "  Aborted."
        exit 0
    fi
fi

# --- Helper: fully empty a bucket (including all object versions and delete markers) ---
empty_versioned_bucket() {
    local bucket="$1"
    # Remove current objects
    aws s3 rm "s3://${bucket}" --recursive --region "$REGION" 2>/dev/null || true
    # Remove all object versions
    aws s3api list-object-versions --bucket "$bucket" --region "$REGION" \
        --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}' --output json 2>/dev/null | \
        python3 -c "
import json, sys
data = json.load(sys.stdin)
if data and data.get('Objects'):
    print(json.dumps(data))
else:
    sys.exit(1)
" 2>/dev/null | \
        aws s3api delete-objects --bucket "$bucket" --region "$REGION" --delete file:///dev/stdin 2>/dev/null || true
    # Remove all delete markers
    aws s3api list-object-versions --bucket "$bucket" --region "$REGION" \
        --query '{Objects: DeleteMarkers[].{Key:Key,VersionId:VersionId}}' --output json 2>/dev/null | \
        python3 -c "
import json, sys
data = json.load(sys.stdin)
if data and data.get('Objects'):
    print(json.dumps(data))
else:
    sys.exit(1)
" 2>/dev/null | \
        aws s3api delete-objects --bucket "$bucket" --region "$REGION" --delete file:///dev/stdin 2>/dev/null || true
}

echo ""
echo "🗑️  Emptying S3 buckets (including versioned objects)..."
empty_versioned_bucket "$TEST_BUCKET"
empty_versioned_bucket "$DEPLOY_BUCKET"
empty_versioned_bucket "$LOGS_BUCKET"
echo "  ✓ Buckets emptied"

echo ""
echo "🗑️  Deleting CloudFormation stack..."
aws cloudformation delete-stack --stack-name "$STACK_NAME" --region "$REGION"
echo "  Waiting for delete..."
aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" --region "$REGION" 2>/dev/null || {
    echo "  ⚠️  Initial delete failed. Retrying with retained custom resources..."
    aws cloudformation delete-stack --stack-name "$STACK_NAME" --region "$REGION" \
        --retain-resources TriggerTestRunnerBuild TriggerOrchestratorBuild 2>/dev/null || true
    aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" --region "$REGION" 2>/dev/null || {
        echo "  ⚠️  Still failing. Force-deleting stack..."
        aws cloudformation delete-stack --stack-name "$STACK_NAME" --region "$REGION" \
            --deletion-mode FORCE_DELETE_STACK 2>/dev/null || true
        aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" --region "$REGION" 2>/dev/null || true
    }
}
echo "  ✓ Stack deleted"

# --- Clean up any ghost stack left in REVIEW_IN_PROGRESS state (from failed prior deploys) ---
GHOST_STATUS=$(aws cloudformation list-stacks --region "$REGION" \
    --stack-status-filter REVIEW_IN_PROGRESS CREATE_FAILED ROLLBACK_COMPLETE \
    --query "StackSummaries[?StackName=='${STACK_NAME}'].StackStatus" --output text 2>/dev/null || true)
if [ -n "$GHOST_STATUS" ]; then
    echo ""
    echo "🗑️  Cleaning up ghost stack (status: $GHOST_STATUS)..."
    aws cloudformation delete-stack --stack-name "$STACK_NAME" --region "$REGION" 2>/dev/null || true
    aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" --region "$REGION" 2>/dev/null || true
    echo "  ✓ Ghost stack removed"
fi

echo ""
echo "🗑️  Removing deploy bucket..."
aws s3 rb "s3://${DEPLOY_BUCKET}" --force --region "$REGION" 2>/dev/null || true
echo "  ✓ Deploy bucket removed"

echo "🗑️  Removing access logs bucket..."
aws s3 rb "s3://${LOGS_BUCKET}" --force --region "$REGION" 2>/dev/null || true
echo "  ✓ Access logs bucket removed"

echo ""
echo "✅ All resources destroyed. Ready for clean redeploy."
echo "=============================================="
