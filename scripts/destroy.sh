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

echo ""
echo "🗑️  Emptying S3 buckets..."
aws s3 rm "s3://${TEST_BUCKET}" --recursive --region "$REGION" 2>/dev/null || true
aws s3 rm "s3://${DEPLOY_BUCKET}" --recursive --region "$REGION" 2>/dev/null || true
aws s3 rm "s3://${LOGS_BUCKET}" --recursive --region "$REGION" 2>/dev/null || true

# Handle versioned bucket (TestDataBucket now has versioning enabled)
aws s3api list-object-versions --bucket "$TEST_BUCKET" --region "$REGION" \
    --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}' --output json 2>/dev/null | \
    aws s3api delete-objects --bucket "$TEST_BUCKET" --region "$REGION" --delete file:///dev/stdin 2>/dev/null || true
aws s3api list-object-versions --bucket "$TEST_BUCKET" --region "$REGION" \
    --query '{Objects: DeleteMarkers[].{Key:Key,VersionId:VersionId}}' --output json 2>/dev/null | \
    aws s3api delete-objects --bucket "$TEST_BUCKET" --region "$REGION" --delete file:///dev/stdin 2>/dev/null || true

echo "  ✓ Buckets emptied"

echo ""
echo "🗑️  Deleting CloudFormation stack..."
aws cloudformation delete-stack --stack-name "$STACK_NAME" --region "$REGION"
echo "  Waiting for delete..."
aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" --region "$REGION" 2>/dev/null || {
    echo "  ⚠️  Delete may have failed. Retrying with --retain-resources for custom resources..."
    aws cloudformation delete-stack --stack-name "$STACK_NAME" --region "$REGION" \
        --retain-resources TriggerTestRunnerBuild TriggerOrchestratorBuild 2>/dev/null || true
    aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" --region "$REGION" 2>/dev/null || true
}
echo "  ✓ Stack deleted"

echo ""
echo "🗑️  Removing deploy bucket..."
aws s3 rb "s3://${DEPLOY_BUCKET}" --force --region "$REGION" 2>/dev/null || true
echo "  ✓ Deploy bucket removed"

echo ""
echo "✓ All resources destroyed."
echo "=============================================="
