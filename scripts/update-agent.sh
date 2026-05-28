#!/bin/bash
# update-agent.sh — Rebuild and redeploy agent code (Developer team)
#
# Rebuilds container images via CodeBuild and updates AgentCore runtimes.
# No CloudFormation, no IAM changes, no admin needed.
#
# Typical cycle: ~2-3 minutes (CodeBuild rebuild + runtime update)
#
# Prerequisites:
#   - Infrastructure already deployed via deploy-infra.sh
#   - AWS CLI configured with developer credentials (ECR push, CodeBuild, AgentCore update)
#
# Usage:
#   ./scripts/update-agent.sh                          # Update both agents
#   ./scripts/update-agent.sh --runner-only            # Update test-runner only
#   ./scripts/update-agent.sh --orchestrator-only      # Update orchestrator only
#   ./scripts/update-agent.sh --stack-name my-stack    # Custom stack name
#   ./scripts/update-agent.sh --no-wait                # Don't wait for build completion
#   ./scripts/update-agent.sh --idle-timeout 1800      # Set idle session timeout (seconds)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ============================================================
# Configuration — edit these defaults or pass as CLI flags
# ============================================================
STACK_NAME="${STACK_NAME:-ai-qa-test-engine}"
REGION="${AWS_REGION:-us-east-1}"
IDLE_SESSION_TIMEOUT="${IDLE_SESSION_TIMEOUT:-900}"  # seconds (default: 15 min)
MAX_LIFETIME="${MAX_LIFETIME:-28800}"                # seconds (default: 8 hours)
# ============================================================

UPDATE_RUNNER=true
UPDATE_ORCHESTRATOR=true
WAIT_FOR_BUILD=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --stack-name) STACK_NAME="$2"; shift 2 ;;
        --region) REGION="$2"; shift 2 ;;
        --idle-timeout) IDLE_SESSION_TIMEOUT="$2"; shift 2 ;;
        --max-lifetime) MAX_LIFETIME="$2"; shift 2 ;;
        --runner-only) UPDATE_ORCHESTRATOR=false; shift ;;
        --orchestrator-only) UPDATE_RUNNER=false; shift ;;
        --no-wait) WAIT_FOR_BUILD=false; shift ;;
        --help)
            echo "Usage: ./scripts/update-agent.sh [options]"
            echo ""
            echo "Options:"
            echo "  --stack-name NAME       CFN stack name (default: ai-qa-test-engine)"
            echo "  --region REGION         AWS region (default: us-east-1)"
            echo "  --idle-timeout SECS     Idle session timeout in seconds (default: 900, range: 60-28800)"
            echo "  --max-lifetime SECS     Max session lifetime in seconds (default: 28800, range: 60-28800)"
            echo "  --runner-only           Only update the test-runner agent"
            echo "  --orchestrator-only     Only update the orchestrator agent"
            echo "  --no-wait               Don't wait for CodeBuild to finish"
            echo ""
            echo "This script rebuilds container images and updates AgentCore runtimes."
            echo "No CloudFormation or admin access needed."
            exit 0 ;;
        *) echo "Unknown option: $1. Use --help."; exit 1 ;;
    esac
done

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
DEPLOY_BUCKET="${STACK_NAME}-deploy-${ACCOUNT_ID}-${REGION}"

echo "=============================================="
echo "AI QA Test Engine — Agent Code Update"
echo "=============================================="
echo "  Stack:        $STACK_NAME"
echo "  Region:       $REGION"
echo "  Runner:       $UPDATE_RUNNER"
echo "  Orchestrator: $UPDATE_ORCHESTRATOR"
echo ""

# --- Helper: wait for CodeBuild ---
wait_for_build() {
    local build_id="$1"
    local project_name="$2"
    echo "  ⏳ Waiting for build: $project_name..."
    while true; do
        status=$(aws codebuild batch-get-builds --ids "$build_id" --region "$REGION" \
            --query 'builds[0].buildStatus' --output text)
        case "$status" in
            SUCCEEDED)
                echo "  ✓ Build succeeded: $project_name"
                return 0 ;;
            FAILED|FAULT|STOPPED|TIMED_OUT)
                echo "  ✗ Build $status: $project_name"
                echo "    View logs: https://${REGION}.console.aws.amazon.com/codesuite/codebuild/projects/${project_name}/build/${build_id}"
                return 1 ;;
            *)
                sleep 10 ;;
        esac
    done
}

# --- Helper: get runtime ID from stack outputs ---
get_runtime_id_from_arn() {
    local arn="$1"
    # ARN format: arn:aws:bedrock-agentcore:region:account:runtime/NAME
    echo "$arn" | grep -oP 'runtime/\K.*' || echo "$arn" | sed 's|.*/||'
}

# --- Step 1: Upload updated source ---
echo "📦 Uploading updated source..."

if [ "$UPDATE_RUNNER" = true ]; then
    cd "$PROJECT_ROOT/packages/agentcore-runner"
    rm -f /tmp/agentcore-runner.zip
    zip -r /tmp/agentcore-runner.zip main.py scenario_executor.py s3_utils.py pyproject.toml -x '*.pyc' --quiet
    cd "$PROJECT_ROOT/packages/core"
    zip -r /tmp/agentcore-runner.zip src/ pyproject.toml -x '*.pyc' '*__pycache__*' --quiet
    aws s3 cp /tmp/agentcore-runner.zip "s3://${DEPLOY_BUCKET}/source/agentcore-runner.zip" --quiet
    echo "  ✓ test-runner source uploaded"
fi

if [ "$UPDATE_ORCHESTRATOR" = true ]; then
    cd "$PROJECT_ROOT/packages/agentcore-orchestrator"
    rm -f /tmp/agentcore-orchestrator.zip
    zip -r /tmp/agentcore-orchestrator.zip main.py invoker.py s3_utils.py reporting.py pyproject.toml -x '*.pyc' --quiet
    aws s3 cp /tmp/agentcore-orchestrator.zip "s3://${DEPLOY_BUCKET}/source/agentcore-orchestrator.zip" --quiet
    echo "  ✓ orchestrator source uploaded"
fi

# --- Step 2: Trigger CodeBuild ---
echo ""
echo "🔨 Triggering CodeBuild..."

RUNNER_BUILD_ID=""
ORCHESTRATOR_BUILD_ID=""

if [ "$UPDATE_RUNNER" = true ]; then
    RUNNER_BUILD_ID=$(aws codebuild start-build \
        --project-name "${STACK_NAME}-test-runner-build" \
        --region "$REGION" \
        --query 'build.id' --output text)
    echo "  ✓ test-runner build started: $RUNNER_BUILD_ID"
fi

if [ "$UPDATE_ORCHESTRATOR" = true ]; then
    ORCHESTRATOR_BUILD_ID=$(aws codebuild start-build \
        --project-name "${STACK_NAME}-orchestrator-build" \
        --region "$REGION" \
        --query 'build.id' --output text)
    echo "  ✓ orchestrator build started: $ORCHESTRATOR_BUILD_ID"
fi

# --- Step 3: Wait for builds ---
if [ "$WAIT_FOR_BUILD" = true ]; then
    echo ""
    echo "⏳ Waiting for builds to complete..."

    if [ -n "$RUNNER_BUILD_ID" ]; then
        wait_for_build "$RUNNER_BUILD_ID" "${STACK_NAME}-test-runner-build" || exit 1
    fi
    if [ -n "$ORCHESTRATOR_BUILD_ID" ]; then
        wait_for_build "$ORCHESTRATOR_BUILD_ID" "${STACK_NAME}-orchestrator-build" || exit 1
    fi

    # --- Step 4: Update AgentCore runtimes ---
    echo ""
    echo "🚀 Updating AgentCore runtimes..."

    # Get runtime ARNs and role from stack outputs
    STACK_OUTPUTS=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs' --output json)

    ROLE_ARN=$(echo "$STACK_OUTPUTS" | python3 -c "
import json, sys
outputs = json.load(sys.stdin)
for o in outputs:
    if o['OutputKey'] == 'ExecutionRoleArn':
        print(o['OutputValue'])
        break
")

    if [ "$UPDATE_RUNNER" = true ]; then
        RUNNER_ARN=$(echo "$STACK_OUTPUTS" | python3 -c "
import json, sys
outputs = json.load(sys.stdin)
for o in outputs:
    if o['OutputKey'] == 'TestRunnerArn':
        print(o['OutputValue'])
        break
")
        RUNNER_ECR=$(echo "$STACK_OUTPUTS" | python3 -c "
import json, sys
outputs = json.load(sys.stdin)
for o in outputs:
    if o['OutputKey'] == 'TestRunnerECRUri':
        print(o['OutputValue'])
        break
")
        RUNNER_ID=$(echo "$RUNNER_ARN" | sed 's|.*/||')
        # Preserve existing env vars
        RUNNER_ENV=$(aws bedrock-agentcore-control get-agent-runtime --agent-runtime-id "$RUNNER_ID" --region "$REGION" --query 'environmentVariables' --output json 2>/dev/null)
        ENV_ARGS=()
        if [ "$RUNNER_ENV" != "null" ] && [ -n "$RUNNER_ENV" ]; then
            ENV_ARGS=(--environment-variables "$RUNNER_ENV")
        fi
        aws bedrock-agentcore-control update-agent-runtime \
            --agent-runtime-id "$RUNNER_ID" \
            --agent-runtime-artifact "{\"containerConfiguration\":{\"containerUri\":\"${RUNNER_ECR}:latest\"}}" \
            --network-configuration '{"networkMode":"PUBLIC"}' \
            --lifecycle-configuration "{\"idleRuntimeSessionTimeout\":${IDLE_SESSION_TIMEOUT},\"maxLifetime\":${MAX_LIFETIME}}" \
            "${ENV_ARGS[@]}" \
            --role-arn "$ROLE_ARN" \
            --region "$REGION" \
            --output text --query 'agentRuntimeArn' > /dev/null
        echo "  ✓ test-runner runtime updated (idle_timeout=${IDLE_SESSION_TIMEOUT}s)"
    fi

    if [ "$UPDATE_ORCHESTRATOR" = true ]; then
        ORCHESTRATOR_ARN=$(echo "$STACK_OUTPUTS" | python3 -c "
import json, sys
outputs = json.load(sys.stdin)
for o in outputs:
    if o['OutputKey'] == 'OrchestratorArn':
        print(o['OutputValue'])
        break
")
        ORCHESTRATOR_ECR=$(echo "$STACK_OUTPUTS" | python3 -c "
import json, sys
outputs = json.load(sys.stdin)
for o in outputs:
    if o['OutputKey'] == 'OrchestratorECRUri':
        print(o['OutputValue'])
        break
")
        ORCHESTRATOR_ID=$(echo "$ORCHESTRATOR_ARN" | sed 's|.*/||')
        # Preserve existing env vars (e.g., TEST_RUNNER_ARN set by CFN)
        ORCH_ENV=$(aws bedrock-agentcore-control get-agent-runtime --agent-runtime-id "$ORCHESTRATOR_ID" --region "$REGION" --query 'environmentVariables' --output json 2>/dev/null)
        ENV_ARGS=()
        if [ "$ORCH_ENV" != "null" ] && [ -n "$ORCH_ENV" ]; then
            ENV_ARGS=(--environment-variables "$ORCH_ENV")
        fi
        aws bedrock-agentcore-control update-agent-runtime \
            --agent-runtime-id "$ORCHESTRATOR_ID" \
            --agent-runtime-artifact "{\"containerConfiguration\":{\"containerUri\":\"${ORCHESTRATOR_ECR}:latest\"}}" \
            --network-configuration '{"networkMode":"PUBLIC"}' \
            --lifecycle-configuration "{\"idleRuntimeSessionTimeout\":${IDLE_SESSION_TIMEOUT},\"maxLifetime\":${MAX_LIFETIME}}" \
            "${ENV_ARGS[@]}" \
            --role-arn "$ROLE_ARN" \
            --region "$REGION" \
            --output text --query 'agentRuntimeArn' > /dev/null
        echo "  ✓ orchestrator runtime updated (idle_timeout=${IDLE_SESSION_TIMEOUT}s)"
    fi
else
    echo ""
    echo "⚠️  --no-wait: Builds triggered but not waiting. Run update again or check console."
fi

echo ""
echo "=============================================="
echo "✅ Agent update complete!"
echo ""
echo "Test with:"
echo "  aws bedrock-agentcore invoke-agent-runtime \\"
echo "    --agent-runtime-arn <OrchestratorArn> \\"
echo "    --payload '{\"action\":\"run_tests\",\"s3_prefix\":\"s3://bucket/tests/\"}'"
echo "=============================================="
