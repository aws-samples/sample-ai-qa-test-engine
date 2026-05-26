#!/bin/bash
# deploy-infra.sh — One-time infrastructure deployment (Admin team)
#
# Creates: ECR repos, CodeBuild projects, IAM roles, S3 bucket,
#          AgentCore runtimes, and builds initial container images.
#
# Run this ONCE (or when infra changes). For agent code updates, use update-agent.sh.
#
# Prerequisites:
#   - AWS CLI configured with admin-level credentials
#   - CAPABILITY_NAMED_IAM permissions
#
# Usage:
#   ./scripts/deploy-infra.sh                          # Full infra deploy
#   ./scripts/deploy-infra.sh --stack-name my-stack    # Custom stack name
#   ./scripts/deploy-infra.sh --region us-west-2       # Custom region
#   ./scripts/deploy-infra.sh --role-arn ARN           # Use pre-created IAM role
#   ./scripts/deploy-infra.sh --test-bucket NAME       # Use pre-created S3 bucket

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

STACK_NAME="${STACK_NAME:-ai-qa-test-engine}"
REGION="${AWS_REGION:-us-east-1}"
EXISTING_ROLE_ARN=""
EXISTING_TEST_BUCKET=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --stack-name) STACK_NAME="$2"; shift 2 ;;
        --region) REGION="$2"; shift 2 ;;
        --role-arn) EXISTING_ROLE_ARN="$2"; shift 2 ;;
        --test-bucket) EXISTING_TEST_BUCKET="$2"; shift 2 ;;
        --help)
            echo "Usage: ./scripts/deploy-infra.sh [options]"
            echo ""
            echo "Options:"
            echo "  --stack-name NAME     CFN stack name (default: ai-qa-test-engine)"
            echo "  --region REGION       AWS region (default: us-east-1)"
            echo "  --role-arn ARN        Pre-created IAM role ARN (skip role creation)"
            echo "  --test-bucket NAME    Pre-created S3 bucket name (skip bucket creation)"
            echo ""
            echo "This script deploys the full infrastructure stack via CloudFormation."
            echo "Run ONCE or when infra changes. For code updates, use update-agent.sh."
            exit 0 ;;
        *) echo "Unknown option: $1. Use --help."; exit 1 ;;
    esac
done

echo "=============================================="
echo "AI QA Test Engine — Infrastructure Deployment"
echo "=============================================="
echo "  Stack:   $STACK_NAME"
echo "  Region:  $REGION"
echo "  Role:    ${EXISTING_ROLE_ARN:-<will be created>}"
echo "  Bucket:  ${EXISTING_TEST_BUCKET:-<will be created>}"
echo "  Method:  CloudFormation + CodeBuild"
echo ""

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
DEPLOY_BUCKET="${STACK_NAME}-deploy-${ACCOUNT_ID}-${REGION}"

# Create deploy bucket for source uploads
echo "📦 Preparing deploy bucket: s3://${DEPLOY_BUCKET}"
aws s3 mb "s3://${DEPLOY_BUCKET}" --region "$REGION" 2>/dev/null || true

# Upload agent source zips (needed for initial CodeBuild)
echo "📦 Uploading agent source for initial build..."

cd "$PROJECT_ROOT/packages/agentcore-runner"
zip -r /tmp/agentcore-runner.zip main.py scenario_executor.py s3_utils.py pyproject.toml -x '*.pyc' --quiet
cd "$PROJECT_ROOT/packages/core"
zip -r /tmp/agentcore-runner.zip src/ pyproject.toml -x '*.pyc' '*__pycache__*' --quiet
aws s3 cp /tmp/agentcore-runner.zip "s3://${DEPLOY_BUCKET}/source/agentcore-runner.zip" --quiet

cd "$PROJECT_ROOT/packages/agentcore-orchestrator"
zip -r /tmp/agentcore-orchestrator.zip main.py invoker.py s3_utils.py reporting.py pyproject.toml -x '*.pyc' --quiet
aws s3 cp /tmp/agentcore-orchestrator.zip "s3://${DEPLOY_BUCKET}/source/agentcore-orchestrator.zip" --quiet
echo "  ✓ Source uploaded to s3://${DEPLOY_BUCKET}/source/"

# Build CFN parameters
CFN_PARAMS="ProjectName=$STACK_NAME SourceBucket=$DEPLOY_BUCKET"
[ -n "$EXISTING_ROLE_ARN" ] && CFN_PARAMS="$CFN_PARAMS ExistingRoleArn=$EXISTING_ROLE_ARN"
[ -n "$EXISTING_TEST_BUCKET" ] && CFN_PARAMS="$CFN_PARAMS TestBucket=$EXISTING_TEST_BUCKET"

# Deploy CloudFormation stack
cd "$PROJECT_ROOT"
echo ""
echo "🚀 Deploying CloudFormation stack (first deploy takes ~5-8 min)..."
aws cloudformation deploy \
    --template-file "$PROJECT_ROOT/infra/cfn-template.yaml" \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides $CFN_PARAMS \
    --no-fail-on-empty-changeset

echo ""
echo "✅ Infrastructure deployment complete!"
echo ""
echo "📋 Stack Outputs:"
aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
    --output table

echo ""
echo "=============================================="
echo "Next steps:"
echo "  • Agent developers can now use ./scripts/update-agent.sh to push code changes"
echo "  • No CFN or admin access needed for code updates"
echo "=============================================="
