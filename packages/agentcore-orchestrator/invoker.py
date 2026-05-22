"""Test Runner invoker — parallel invocation via AgentCore runtime."""

import asyncio
import json
import logging
import os

import boto3

logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def invoke_test_runners(
    scenarios: list[dict],
    test_runner_arn: str,
    max_concurrency: int = 10,
) -> list[dict]:
    """Invoke Test Runner agent for each scenario in parallel.

    Args:
        scenarios: List of scenario payloads
        test_runner_arn: ARN of the Test Runner runtime
        max_concurrency: Maximum parallel invocations

    Returns:
        List of result dicts (one per scenario)
    """
    logger.info(f"Invoking {len(scenarios)} scenarios (max_concurrency={max_concurrency})")
    results = asyncio.run(_invoke_all(scenarios, test_runner_arn, max_concurrency))
    return results


async def _invoke_all(scenarios, test_runner_arn, max_concurrency):
    """Async fan-out of Test Runner invocations."""
    semaphore = asyncio.Semaphore(max_concurrency)
    tasks = []

    for idx, payload in enumerate(scenarios):
        task = asyncio.create_task(_invoke_one(semaphore, payload, test_runner_arn, idx))
        tasks.append(task)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    final_results = []
    for idx, result in enumerate(results):
        if isinstance(result, Exception):
            final_results.append({
                "status": "ERROR",
                "feature_name": scenarios[idx].get("feature_name", "unknown"),
                "scenario_name": scenarios[idx].get("scenario_name", "unknown"),
                "errors": [str(result)],
                "duration_seconds": 0,
                "steps_total": 0,
                "steps_passed": 0,
                "steps_failed": 0,
            })
        else:
            final_results.append(result)

    return final_results


async def _invoke_one(semaphore, payload, test_runner_arn, idx):
    """Invoke a single Test Runner instance."""
    async with semaphore:
        feature_name = payload.get("feature_name", "unknown")
        scenario_name = payload.get("scenario_name", "unknown")
        logger.info(f"[{idx}] Invoking: {feature_name}::{scenario_name}")

        try:
            result = await asyncio.to_thread(_invoke_runtime, test_runner_arn, payload)
            logger.info(f"[{idx}] Completed: {feature_name}::{scenario_name} → {result.get('status', 'UNKNOWN')}")
            return result
        except Exception as e:
            logger.error(f"[{idx}] Failed: {feature_name}::{scenario_name} → {e}")
            raise


def _invoke_runtime(test_runner_arn: str, payload: dict) -> dict:
    """Synchronous invocation of an AgentCore runtime."""
    # Support local testing via env var
    local_url = os.environ.get("LOCAL_TEST_RUNNER_URL")
    if local_url:
        import requests
        response = requests.post(
            local_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=300,
        )
        return response.json()

    from botocore.config import Config
    config = Config(read_timeout=300, connect_timeout=10, retries={"max_attempts": 0})
    client = boto3.client("bedrock-agentcore", region_name=AWS_REGION, config=config)

    response = client.invoke_agent_runtime(
        agentRuntimeArn=test_runner_arn,
        payload=json.dumps(payload),
    )

    response_body = response.get("response", "") or response.get("body", "")
    if hasattr(response_body, "read"):
        response_body = response_body.read()
    if isinstance(response_body, bytes):
        response_body = response_body.decode("utf-8")

    try:
        return json.loads(response_body)
    except json.JSONDecodeError:
        return {
            "status": "ERROR",
            "errors": [f"Invalid response: {response_body[:200]}"],
            "feature_name": payload.get("feature_name", "unknown"),
            "scenario_name": payload.get("scenario_name", "unknown"),
        }
