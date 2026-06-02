"""Scenario executor for AgentCore — uses browser_session for remote browser.

Uses ai-qa-test-engine core's shared step execution loop with AgentCore's
CDP-based remote browser instead of local Playwright.
"""

import base64
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
    trajectory_cache_dir: Optional[Path] = None,
) -> dict:
    """Execute a single test scenario using ai-qa-test-engine with AgentCore browser.

    Args:
        scenario_data: Scenario dict (matching TestScenario model)
        base_url: Starting URL for the test
        feature_name: Name of the parent feature
        functions_file: Optional path to custom functions .py file
        input_variables: Optional dict of pre-loaded variables (from variables/ S3 dir)
        data_dir: Optional path to directory containing data files (Excel, CSV) downloaded from S3
        trajectory_cache_dir: Optional path to trajectory cache directory for replay

    Returns:
        Result dict with status, duration, steps, errors, detailed_report_html
    """
    from ai_qa_test_engine.models import TestScenario, StepResult, ScenarioResult, RunSummary
    from ai_qa_test_engine.function_registry import FunctionRegistry
    from ai_qa_test_engine.browser import make_workflow_name
    from ai_qa_test_engine.nova_act_client import NovaActClient
    from ai_qa_test_engine.nova_act_qa import NovaActQa
    from ai_qa_test_engine.trajectory import TrajectoryCache
    from ai_qa_test_engine.step_loop import execute_steps
    from ai_qa_test_engine.detailed_report import generate_detailed_report
    from nova_act import Workflow
    from datetime import datetime, timezone
    from uuid import uuid4

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

    # Initialize trajectory cache
    traj_cache = None
    if trajectory_cache_dir:
        traj_cache = TrajectoryCache(trajectory_cache_dir)
        logger.info(f"Trajectory cache: {trajectory_cache_dir}")

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

    step_results: list[StepResult] = []
    errors: list[str] = []

    # Set working directory to data_dir so relative file paths (Excel, CSV) resolve
    original_cwd = os.getcwd()
    if data_dir and data_dir.exists():
        os.chdir(data_dir)
        log_callback(f"Working directory set to: {data_dir}")

    try:
        # Get AgentCore browser session (CDP connection to remote browser)
        # Use custom browser identifier if set (VPC mode creates a dedicated browser)
        browser_id = os.environ.get("BROWSER_IDENTIFIER")
        browser_kwargs = {"region": AWS_REGION}
        if browser_id:
            browser_kwargs["identifier"] = browser_id
        with browser_session(**browser_kwargs) as client:
            cdp_endpoint_url, cdp_headers = client.generate_ws_headers()
            logger.info(f"Browser session obtained: {cdp_endpoint_url[:60]}...")

            # Start workflow and create NovaActQa with CDP params
            with Workflow(**workflow_kwargs) as workflow:
                with NovaActQa(
                    starting_page=base_url,
                    workflow=workflow,
                    headless=False,
                    replayable=True,  # Enable trajectory recording for replay cache
                    cdp_endpoint_url=cdp_endpoint_url,
                    cdp_headers=cdp_headers,
                ) as nova:
                    # Get max_steps from env var (set by config or payload)
                    _max_steps = int(os.environ.get("MAX_STEPS", "30"))

                    # Use shared step execution loop (same code as local executor)
                    step_results, errors = execute_steps(
                        scenario=scenario,
                        nova=nova,
                        extracted_values=extracted_values,
                        functions=functions,
                        log=log_callback,
                        traj_cache=traj_cache,
                        feature_name=feature_name,
                        max_steps=_max_steps,
                    )

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
        status = "FAILED" if any(s.status == "FAILED" for s in step_results) else "ERROR"
    else:
        status = "PASSED"

    steps_passed = sum(1 for s in step_results if s.status == "PASSED")
    steps_failed = sum(1 for s in step_results if s.status in ("FAILED", "ERROR"))

    logger.info(f"Scenario {status}: {scenario_name} ({duration:.2f}s)")

    # Generate detailed HTML report
    detailed_report_html = None
    try:
        run_id = f"run-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:6]}"
        scenario_result = ScenarioResult(
            scenario_name=scenario_name,
            feature_name=feature_name,
            status=status,
            duration_seconds=duration,
            steps=step_results,
            extracted_variables=extracted_values,
            errors=errors,
        )
        run_summary = RunSummary(
            run_id=run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_scenarios=1,
            passed=1 if status == "PASSED" else 0,
            failed=1 if status == "FAILED" else 0,
            errors=1 if status == "ERROR" else 0,
            total_duration_seconds=duration,
            status=status,
            scenarios=[scenario_result],
        )
        detailed_report_html = generate_detailed_report(run_summary, [scenario_result])
        logger.info("Detailed report generated")
    except Exception as e:
        logger.warning(f"Failed to generate detailed report: {e}")

    # Build step_results as dicts for JSON serialization
    step_results_dicts = []
    for sr in step_results:
        d = {
            "number": sr.step_number,
            "keyword": sr.keyword,
            "original_text": sr.original_text,
            "status": sr.status,
            "duration_seconds": sr.duration_seconds,
            "replayed_from_cache": sr.replayed_from_cache or False,
        }
        if sr.error:
            d["error"] = sr.error
        step_results_dicts.append(d)

    return {
        "status": status,
        "scenario_name": scenario_name,
        "duration_seconds": duration,
        "steps_total": len(scenario.steps),
        "steps_passed": steps_passed,
        "steps_failed": steps_failed,
        "errors": errors,
        "extracted_variables": extracted_values,
        "step_results": step_results_dicts,
        "log_messages": log_messages,
        "detailed_report_html": detailed_report_html,
    }
