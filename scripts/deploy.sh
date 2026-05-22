#!/bin/bash
# deploy.sh — Deploy AI QA Test Engine to AgentCore via CloudFormation
#
# Both agents deploy as CodeZip (no Docker needed).
# Uses native AWS::BedrockAgentCore::Runtime CFN resources.
#
# Prerequisites:
#   - AWS CLI configured with appropriate credentials
#   - zip command available
#
# Usage:
#   ./scripts/deploy.sh                          # Deploy (creates role + bucket)
#   ./scripts/deploy.sh --stack-name my-stack    # Custom stack name
#   ./scripts/deploy.sh --region us-west-2       # Custom region
#   ./scripts/deploy.sh --role-arn ARN           # Use pre-created IAM role
#   ./scripts/deploy.sh --test-bucket NAME       # Use pre-created S3 bucket

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Defaults
STACK_NAME="${STACK_NAME:-ai-qa-test-engine}"
REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
DEPLOY_BUCKET="${STACK_NAME}-deploy-${ACCOUNT_ID}-${REGION}"
EXISTING_ROLE_ARN=""
EXISTING_TEST_BUCKET=""

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --stack-name) STACK_NAME="$2"; shift 2 ;;
        --region) REGION="$2"; shift 2 ;;
        --role-arn) EXISTING_ROLE_ARN="$2"; shift 2 ;;
        --test-bucket) EXISTING_TEST_BUCKET="$2"; shift 2 ;;
        --help)
            echo "Usage: ./scripts/deploy.sh [options]"
            echo ""
            echo "Options:"
            echo "  --stack-name NAME     CloudFormation stack name (default: ai-qa-test-engine)"
            echo "  --region REGION       AWS region (default: us-east-1)"
            echo "  --role-arn ARN        Use pre-created IAM role (skip role creation)"
            echo "  --test-bucket NAME    Use pre-created S3 bucket (skip bucket creation)"
            echo ""
            echo "Examples:"
            echo "  ./scripts/deploy.sh                                     # Full deploy (creates role + bucket)"
            echo "  ./scripts/deploy.sh --role-arn arn:aws:iam::123:role/r --test-bucket my-bucket"
            exit 0 ;;
        *) echo "Unknown option: $1. Use --help for usage."; exit 1 ;;
    esac
done

DEPLOY_TIMESTAMP=$(date +%Y%m%d%H%M%S)

echo "=============================================="
echo "AI QA Test Engine — AgentCore Deployment"
echo "=============================================="
echo "  Stack:    $STACK_NAME"
echo "  Region:   $REGION"
echo "  Account:  $ACCOUNT_ID"
echo "  Deploy:   CodeZip via CloudFormation (no Docker)"
if [ -n "$EXISTING_ROLE_ARN" ]; then
    echo "  Role:     $EXISTING_ROLE_ARN (pre-created)"
else
    echo "  Role:     (will be created by CFN)"
fi
if [ -n "$EXISTING_TEST_BUCKET" ]; then
    echo "  Bucket:   $EXISTING_TEST_BUCKET (pre-created)"
else
    echo "  Bucket:   (will be created by CFN)"
fi
echo ""

# Step 1: Create deploy bucket for code zips
echo "☁️  Ensuring deploy bucket exists..."
aws s3 mb "s3://${DEPLOY_BUCKET}" --region "$REGION" 2>/dev/null || true
echo "  ✓ Bucket: $DEPLOY_BUCKET"

# Step 2: Package and upload Test Runner
echo ""
echo "📦 Packaging Test Runner..."
cd "$PROJECT_ROOT/packages/agentcore-runner"

RUNNER_S3_KEY="deploy/test-runner-${DEPLOY_TIMESTAMP}.zip"
RUNNER_ZIP="/tmp/${STACK_NAME}-test-runner.zip"
zip -r "$RUNNER_ZIP" main.py scenario_executor.py s3_utils.py pyproject.toml
aws s3 cp "$RUNNER_ZIP" "s3://${DEPLOY_BUCKET}/${RUNNER_S3_KEY}" --quiet
echo "  ✓ Uploaded: s3://${DEPLOY_BUCKET}/${RUNNER_S3_KEY}"

# Step 3: Package and upload Orchestrator
echo ""
echo "📦 Packaging Orchestrator..."
cd "$PROJECT_ROOT/packages/agentcore-orchestrator"

ORCHESTRATOR_S3_KEY="deploy/orchestrator-${DEPLOY_TIMESTAMP}.zip"
ORCHESTRATOR_ZIP="/tmp/${STACK_NAME}-orchestrator.zip"
zip -r "$ORCHESTRATOR_ZIP" main.py invoker.py s3_utils.py reporting.py pyproject.toml
aws s3 cp "$ORCHESTRATOR_ZIP" "s3://${DEPLOY_BUCKET}/${ORCHESTRATOR_S3_KEY}" --quiet
echo "  ✓ Uploaded: s3://${DEPLOY_BUCKET}/${ORCHESTRATOR_S3_KEY}"

# Step 4: Deploy CloudFormation stack
echo ""
echo "🚀 Deploying CloudFormation stack..."

CFN_PARAMS="ProjectName=$STACK_NAME"
CFN_PARAMS="$CFN_PARAMS TestRunnerCodeS3Bucket=$DEPLOY_BUCKET TestRunnerCodeS3Key=${RUNNER_S3_KEY}"
CFN_PARAMS="$CFN_PARAMS OrchestratorCodeS3Bucket=$DEPLOY_BUCKET OrchestratorCodeS3Key=${ORCHESTRATOR_S3_KEY}"

if [ -n "$EXISTING_ROLE_ARN" ]; then
    CFN_PARAMS="$CFN_PARAMS ExistingRoleArn=$EXISTING_ROLE_ARN"
    echo "  Using existing role"
fi

if [ -n "$EXISTING_TEST_BUCKET" ]; then
    CFN_PARAMS="$CFN_PARAMS TestBucket=$EXISTING_TEST_BUCKET"
    echo "  Using existing bucket"
fi

aws cloudformation deploy \
    --template-file "$PROJECT_ROOT/infra/cfn-template.yaml" \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides $CFN_PARAMS \
    --no-fail-on-empty-changeset

echo ""
echo "✓ Deployment complete!"
echo ""

# Step 5: Show outputs
echo "📋 Stack Outputs:"
aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
    --output table

echo ""
echo "=============================================="
echo "Next steps:"
echo "  1. Upload test files to S3:"
echo "     aws s3 sync ./my-tests/ s3://<bucket>/my-project/tests/"
echo ""
echo "  2. Invoke the Orchestrator (see InvokeExample output above)"
echo "=============================================="
