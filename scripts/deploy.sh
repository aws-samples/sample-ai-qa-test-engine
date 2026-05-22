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
IMAGE_TAG=$(git -C "$PROJECT_ROOT" rev-parse --short HEAD 2>/dev/null || echo "latest")
DEPLOY_BUCKET="${STACK_NAME}-deploy-${ACCOUNT_ID}-${REGION}"
CREATE_ECR=false
EXISTING_ROLE_ARN=""
EXISTING_TEST_BUCKET=""

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --stack-name) STACK_NAME="$2"; shift 2 ;;
        --region) REGION="$2"; shift 2 ;;
        --create-ecr) CREATE_ECR=true; shift ;;
        --role-arn) EXISTING_ROLE_ARN="$2"; shift 2 ;;
        --test-bucket) EXISTING_TEST_BUCKET="$2"; shift 2 ;;
        --help)
            echo "Usage: ./scripts/deploy.sh [options]"
            echo ""
            echo "Options:"
            echo "  --stack-name NAME     CloudFormation stack name (default: ai-qa-test-engine)"
            echo "  --region REGION       AWS region (default: us-east-1)"
            echo "  --create-ecr          Create ECR repository if it doesn't exist"
            echo "  --role-arn ARN        Use pre-created IAM role (skip role creation)"
            echo "  --test-bucket NAME    Use pre-created S3 bucket (skip bucket creation)"
            echo ""
            echo "Examples:"
            echo "  ./scripts/deploy.sh --create-ecr                    # Full deploy (creates everything)"
            echo "  ./scripts/deploy.sh --role-arn arn:aws:iam::123:role/my-role --test-bucket my-bucket"
            exit 0 ;;
        *) echo "Unknown option: $1. Use --help for usage."; exit 1 ;;
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

DEPLOY_TIMESTAMP=$(date +%Y%m%d%H%M%S)
ORCHESTRATOR_S3_KEY="deploy/orchestrator-${DEPLOY_TIMESTAMP}.zip"
ORCHESTRATOR_ZIP="/tmp/${STACK_NAME}-orchestrator.zip"
zip -r "$ORCHESTRATOR_ZIP" main.py invoker.py s3_utils.py reporting.py pyproject.toml
echo "  ✓ Created: $ORCHESTRATOR_ZIP"

# Step 4: Create deploy bucket and upload orchestrator zip
echo ""
echo "☁️  Uploading to S3..."
aws s3 mb "s3://${DEPLOY_BUCKET}" --region "$REGION" 2>/dev/null || true
aws s3 cp "$ORCHESTRATOR_ZIP" "s3://${DEPLOY_BUCKET}/${ORCHESTRATOR_S3_KEY}"
echo "  ✓ Uploaded: s3://${DEPLOY_BUCKET}/${ORCHESTRATOR_S3_KEY}"

# Step 5: Deploy CloudFormation stack
echo ""
echo "🚀 Deploying CloudFormation stack..."

CFN_PARAMS="ProjectName=$STACK_NAME TestRunnerImageUri=${ECR_URI}:${IMAGE_TAG} OrchestratorCodeS3Bucket=$DEPLOY_BUCKET OrchestratorCodeS3Key=${ORCHESTRATOR_S3_KEY}"

if [ -n "$EXISTING_ROLE_ARN" ]; then
    CFN_PARAMS="$CFN_PARAMS ExistingRoleArn=$EXISTING_ROLE_ARN CreateResources=runtimes-only"
    echo "  Using existing role: $EXISTING_ROLE_ARN"
fi

if [ -n "$EXISTING_TEST_BUCKET" ]; then
    CFN_PARAMS="$CFN_PARAMS TestBucket=$EXISTING_TEST_BUCKET"
    echo "  Using existing bucket: $EXISTING_TEST_BUCKET"
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
