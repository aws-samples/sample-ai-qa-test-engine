"""Scenario executor for AgentCore — uses browser_session for remote browser.

Uses ai-qa-test-engine core execution engine with AgentCore's CDP-based
remote browser instead of local Playwright.
"""

import logging
import os
import time
from pathlib import Path
from typing import Optional

from bedrock_agentcore.tools.browser_client import browser_session

logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def execute_scenario_agentcore(
    scenario_data: dict,
    base_url: str,
    feature_name: str,
    functions_file: Optional[Path] = None,
    input_variables: Optional[dict] = None,
    data_dir: Optional[Path] = None,
) -> dict:
    """Execute a single test scenario using ai-qa-test-engine with AgentCore browser.

    Args:
        scenario_data: Scenario dict (matching TestScenario model)
        base_url: Starting URL for the test
        feature_name: Name of the parent feature
        functions_file: Optional path to custom functions .py file
        input_variables: Optional dict of pre-loaded variables (from variables/ S3 dir)
        data_dir: Optional path to directory containing data files (Excel, CSV) downloaded from S3

    Returns:
        Result dict with status, duration, steps, errors
    """
    from ai_qa_test_engine.models import TestScenario
    from ai_qa_test_engine.config import AppConfig
    from ai_qa_test_engine.function_registry import FunctionRegistry
    from ai_qa_test_engine.executor import execute_scenario, _execute_step, substitute_variables
    from ai_qa_test_engine.browser import make_workflow_name
    from ai_qa_test_engine.models import StepResult
    from ai_qa_test_engine.nova_act_client import NovaActClient
    from ai_qa_test_engine.nova_act_qa import NovaActQa
    from nova_act import Workflow
    from unittest.mock import patch

    start_time = time.time()
    scenario = TestScenario.model_validate(scenario_data)
    scenario_name = scenario.name

    logger.info(f"{'=' * 60}")
    logger.info(f"Scenario: {scenario_name}")
    logger.info(f"Base URL: {base_url}")
    logger.info(f"Steps: {len(scenario.steps)}")
    logger.info(f"{'=' * 60}")

    # Load functions
    functions = FunctionRegistry()
    import ai_qa_test_engine
    bundled_dir = Path(ai_qa_test_engine.__file__).parent / "functions"
    functions.load_bundled(bundled_dir)
    if functions_file and functions_file.exists():
        if functions_file.is_dir():
            functions.load_from_directory(functions_file)
        else:
            functions.load_from_file(functions_file)

    # Build workflow name
    workflow_name = make_workflow_name(feature_name, scenario_name)

    # Collect logs
    log_messages = []

    def log_callback(message: str, level: str = "info"):
        log_messages.append({"level": level, "message": message})
        if level == "error":
            logger.error(f"  {message}")
        else:
            logger.info(f"  {message}")

    # Get workflow kwargs
    workflow_kwargs = NovaActClient.get_workflow_kwargs(
        workflow_definition_name=workflow_name
    )

    extracted_values = {}
    # Pre-load input variables (from variables/ S3 directory)
    if input_variables:
        extracted_values.update(input_variables)
        log_callback(f"Pre-loaded {len(input_variables)} input variable(s): {list(input_variables.keys())}")
    step_results = []
    errors = []

    # Set working directory to data_dir so relative file paths (Excel, CSV) resolve
    original_cwd = os.getcwd()
    if data_dir and data_dir.exists():
        os.chdir(data_dir)
        log_callback(f"Working directory set to: {data_dir}")

    try:
        # Get AgentCore browser session (CDP connection to remote browser)
        with browser_session(AWS_REGION) as client:
            cdp_endpoint_url, cdp_headers = client.generate_ws_headers()
            logger.info(f"Browser session obtained: {cdp_endpoint_url[:60]}...")

            # Start workflow and create NovaActQa with CDP params
            with Workflow(**workflow_kwargs) as workflow:
                with NovaActQa(
                    starting_page=base_url,
                    workflow=workflow,
                    headless=False,
                    cdp_endpoint_url=cdp_endpoint_url,
                    cdp_headers=cdp_headers,
                ) as nova:
                    for step_idx, step in enumerate(scenario.steps, 1):
                        keyword = step.original_keyword
                        text = step.original_text

                        log_callback(f"Step {step_idx}: {keyword} {text}")
                        step_start = time.time()

                        try:
                            result = _execute_step(
                                step, nova, extracted_values, functions, log_callback,
                            )
                            step_duration = time.time() - step_start

                            step_results.append({
                                "number": step_idx,
                                "keyword": keyword,
                                "original_text": text,
                                "status": "PASSED",
                                "duration_seconds": step_duration,
                            })
                            log_callback(f"  ✓ Step {step_idx} passed ({step_duration:.1f}s)")

                        except AssertionError as e:
                            step_duration = time.time() - step_start
                            error_msg = str(e)
                            log_callback(f"  ✗ Validation failed: {error_msg}", "error")

                            step_results.append({
                                "number": step_idx,
                                "keyword": keyword,
                                "original_text": text,
                                "status": "FAILED",
                                "duration_seconds": step_duration,
                                "error": error_msg,
                            })
                            errors.append(f"Step {step_idx}: {error_msg}")
                            break

                        except Exception as e:
                            step_duration = time.time() - step_start
                            error_msg = f"Step execution error: {e}"
                            log_callback(f"  ✗ Error: {error_msg}", "error")

                            step_results.append({
                                "number": step_idx,
                                "keyword": keyword,
                                "original_text": text,
                                "status": "ERROR",
                                "duration_seconds": step_duration,
                                "error": error_msg,
                            })
                            errors.append(error_msg)
                            break

    except Exception as e:
        errors.append(f"Browser session error: {type(e).__name__}: {e}")
        logger.error(f"Browser session error: {e}")
    finally:
        # Restore original working directory
        if data_dir:
            os.chdir(original_cwd)

    duration = time.time() - start_time

    # Determine status
    if errors:
        status = "FAILED" if any(s.get("status") == "FAILED" for s in step_results) else "ERROR"
    else:
        status = "PASSED"

    steps_passed = sum(1 for s in step_results if s.get("status") == "PASSED")
    steps_failed = sum(1 for s in step_results if s.get("status") in ("FAILED", "ERROR"))

    logger.info(f"Scenario {status}: {scenario_name} ({duration:.2f}s)")

    return {
        "status": status,
        "scenario_name": scenario_name,
        "duration_seconds": duration,
        "steps_total": len(scenario.steps),
        "steps_passed": steps_passed,
        "steps_failed": steps_failed,
        "errors": errors,
        "extracted_variables": extracted_values,
        "step_results": step_results,
        "log_messages": log_messages,
    }
