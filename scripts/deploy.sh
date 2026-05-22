#!/bin/bash
# deploy.sh — Deploy AI QA Test Engine to AgentCore via CloudFormation
#
# Prerequisites:
#   - AWS CLI configured with appropriate credentials
#   - Docker installed (for building Test Runner container)
#   - ECR repository created (or use --create-ecr flag)
#
# Usage:
#   ./scripts/deploy.sh                          # Deploy with defaults
#   ./scripts/deploy.sh --stack-name my-stack    # Custom stack name
#   ./scripts/deploy.sh --region us-west-2       # Custom region
#   ./scripts/deploy.sh --create-ecr             # Create ECR repo if needed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Defaults
STACK_NAME="${STACK_NAME:-ai-qa-test-engine}"
REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="${STACK_NAME}-test-runner"
IMAGE_TAG="latest"
DEPLOY_BUCKET="${STACK_NAME}-deploy-${ACCOUNT_ID}-${REGION}"
CREATE_ECR=false

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --stack-name) STACK_NAME="$2"; shift 2 ;;
        --region) REGION="$2"; shift 2 ;;
        --create-ecr) CREATE_ECR=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

echo "=============================================="
echo "AI QA Test Engine — AgentCore Deployment"
echo "=============================================="
echo "  Stack:    $STACK_NAME"
echo "  Region:   $REGION"
echo "  Account:  $ACCOUNT_ID"
echo "  ECR Repo: $ECR_REPO"
echo ""

# Step 1: Create ECR repository if needed
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO}"

if [ "$CREATE_ECR" = true ]; then
    echo "📦 Creating ECR repository..."
    aws ecr create-repository \
        --repository-name "$ECR_REPO" \
        --region "$REGION" \
        --image-scanning-configuration scanOnPush=true \
        2>/dev/null || echo "  (already exists)"
fi

# Step 2: Build and push Test Runner container
echo ""
echo "🐳 Building Test Runner container..."
cd "$PROJECT_ROOT/packages/agentcore-runner"

# Login to ECR
aws ecr get-login-password --region "$REGION" | \
    docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# Build
docker build -t "${ECR_REPO}:${IMAGE_TAG}" .

# Tag and push
docker tag "${ECR_REPO}:${IMAGE_TAG}" "${ECR_URI}:${IMAGE_TAG}"
docker push "${ECR_URI}:${IMAGE_TAG}"
echo "  ✓ Pushed: ${ECR_URI}:${IMAGE_TAG}"

# Step 3: Package Orchestrator code zip
echo ""
echo "📦 Packaging Orchestrator..."
cd "$PROJECT_ROOT/packages/agentcore-orchestrator"

ORCHESTRATOR_ZIP="/tmp/${STACK_NAME}-orchestrator.zip"
zip -r "$ORCHESTRATOR_ZIP" main.py invoker.py s3_utils.py reporting.py pyproject.toml
echo "  ✓ Created: $ORCHESTRATOR_ZIP"

# Step 4: Create deploy bucket and upload orchestrator zip
echo ""
echo "☁️  Uploading to S3..."
aws s3 mb "s3://${DEPLOY_BUCKET}" --region "$REGION" 2>/dev/null || true
aws s3 cp "$ORCHESTRATOR_ZIP" "s3://${DEPLOY_BUCKET}/deploy/orchestrator.zip"
echo "  ✓ Uploaded: s3://${DEPLOY_BUCKET}/deploy/orchestrator.zip"

# Step 5: Deploy CloudFormation stack
echo ""
echo "🚀 Deploying CloudFormation stack..."
aws cloudformation deploy \
    --template-file "$PROJECT_ROOT/infra/cfn-template.yaml" \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        ProjectName="$STACK_NAME" \
        TestRunnerImageUri="${ECR_URI}:${IMAGE_TAG}" \
        OrchestratorCodeS3Bucket="$DEPLOY_BUCKET" \
        OrchestratorCodeS3Key="deploy/orchestrator.zip" \
    --no-fail-on-empty-changeset

echo ""
echo "✓ Deployment complete!"
echo ""

# Step 6: Show outputs
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
echo "  2. Invoke the Orchestrator:"
echo "     aws bedrock-agentcore invoke-agent-runtime \\"
echo "       --agent-runtime-arn <orchestrator-arn> \\"
echo "       --payload '{\"input_bucket\":\"<bucket>\",\"input_prefix\":\"my-project/tests/\",\"output_bucket\":\"<bucket>\",\"output_prefix\":\"my-project/results\",\"test_runner_arn\":\"<test-runner-arn>\",\"max_concurrency\":10}'"
echo "=============================================="
