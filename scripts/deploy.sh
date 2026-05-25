#!/bin/bash
# deploy.sh — Deploy AI QA Test Engine to AgentCore via CloudFormation
#
# Uses CodeBuild to build ARM64 containers in the cloud. No Docker needed locally.
# First deploy takes ~5-8 minutes (CodeBuild builds). Updates are faster.
#
# Prerequisites: AWS CLI configured with appropriate credentials
#
# Usage:
#   ./scripts/deploy.sh                          # Full deploy
#   ./scripts/deploy.sh --stack-name my-stack    # Custom stack name
#   ./scripts/deploy.sh --region us-west-2       # Custom region
#   ./scripts/deploy.sh --role-arn ARN           # Use pre-created IAM role
#   ./scripts/deploy.sh --test-bucket NAME       # Use pre-created S3 bucket

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
            echo "Usage: ./scripts/deploy.sh [options]"
            echo ""
            echo "  --stack-name NAME     CFN stack name (default: ai-qa-test-engine)"
            echo "  --region REGION       AWS region (default: us-east-1)"
            echo "  --role-arn ARN        Pre-created IAM role (skip creation)"
            echo "  --test-bucket NAME    Pre-created S3 bucket (skip creation)"
            exit 0 ;;
        *) echo "Unknown: $1. Use --help."; exit 1 ;;
    esac
done

echo "=============================================="
echo "AI QA Test Engine — AgentCore Deployment"
echo "=============================================="
echo "  Stack:   $STACK_NAME"
echo "  Region:  $REGION"
echo "  Method:  CFN + CodeBuild (no local Docker)"
echo ""

CFN_PARAMS="ProjectName=$STACK_NAME"
[ -n "$EXISTING_ROLE_ARN" ] && CFN_PARAMS="$CFN_PARAMS ExistingRoleArn=$EXISTING_ROLE_ARN"
[ -n "$EXISTING_TEST_BUCKET" ] && CFN_PARAMS="$CFN_PARAMS TestBucket=$EXISTING_TEST_BUCKET"

echo "🚀 Deploying (first deploy takes ~5-8 min for CodeBuild)..."
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
echo "📋 Stack Outputs:"
aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
    --output table
echo ""
echo "=============================================="
