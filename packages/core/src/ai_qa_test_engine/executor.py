"""Test execution engine.

Ported from test_translator/utils/execution.py.
Modifications:
- Browser creation extracted to browser.py
- StepResult collection added for reporting
- from_step support added for resume-from-failure
- Uses FunctionRegistry instead of inline module loading
"""

import re
import time
from pathlib import Path
from typing import Any, Callable, Optional

from ai_qa_test_engine.browser import create_browser_session, make_workflow_name
from ai_qa_test_engine.config import AppConfig
from ai_qa_test_engine.function_registry import FunctionRegistry
from ai_qa_test_engine.models import (
    Feature,
    ScenarioResult,
    StepResult,
    TestScenario,
)


def substitute_variables(text: str, variables: dict) -> str:
    """Replace ${variable_name} references with actual values.

    Ported as-is from test_translator/utils/execution.py.

    Args:
        text: Text containing variable references
        variables: Dictionary of extracted variables

    Returns:
        Text with all variable references replaced

    Raises:
        KeyError: If a referenced variable is not found
    """
    if not text:
        return text

    pattern = r'\$\{([^}]+)\}'

    def replacer(match):
        var_name = match.group(1)
        if var_name not in variables:
            raise KeyError(f"Variable '${{{var_name}}}' not found in context")
        return str(variables[var_name])

    return re.sub(pattern, replacer, text)


def execute_scenario(
    scenario: TestScenario,
    base_url: str,
    feature_name: str,
    config: AppConfig,
    functions: FunctionRegistry,
    log_callback: Optional[Callable[[str, str], None]] = None,
) -> ScenarioResult:
    """Execute a single test scenario with Nova Act.

    This is the main execution entry point. It creates a browser session,
    iterates through steps, and collects results.

    Args:
        scenario: The test scenario to execute
        base_url: The base URL for the test
        feature_name: Name of the parent feature (for workflow naming)
        config: Application configuration
        functions: Loaded function registry
        log_callback: Optional callback for real-time logging

    Returns:
        ScenarioResult with step-level details
    """

    def log(message: str, level: str = "info"):
        if log_callback:
            log_callback(message, level)
        else:
            print(f"  [{level.upper()}] {message}")

    start_time = time.time()
    scenario_name = scenario.name
    steps = scenario.steps
    from_step = config.from_step or 1

    log(f"{'=' * 60}")
    log(f"Scenario: {scenario_name}")
    log(f"Base URL: {base_url}")
    log(f"Steps: {len(steps)} (starting from step {from_step})")
    log(f"{'=' * 60}")

    extracted_values: dict[str, Any] = {}
    step_results: list[StepResult] = []
    errors: list[str] = []

    # Generate workflow name
    workflow_name = make_workflow_name(feature_name, scenario_name)

    try:
        with create_browser_session(config, base_url, workflow_name) as nova:
            for step_idx, step in enumerate(steps, 1):
                keyword = step.original_keyword
                text = step.original_text

                # Skip steps before from_step
                if step_idx < from_step:
                    step_results.append(StepResult(
                        step_number=step_idx,
                        keyword=keyword,
                        original_text=text,
                        status="SKIPPED",
                        duration_seconds=0.0,
                    ))
                    continue

                log(f"Step {step_idx}: {keyword} {text}")
                step_start = time.time()

                try:
                    result = _execute_step(
                        step, nova, extracted_values, functions, log
                    )
                    step_duration = time.time() - step_start

                    step_results.append(StepResult(
                        step_number=step_idx,
                        keyword=keyword,
                        original_text=text,
                        status="PASSED",
                        duration_seconds=step_duration,
                        extracted_value=result,
                    ))
                    log(f"  ✓ Step {step_idx} passed ({step_duration:.1f}s)")

                except AssertionError as e:
                    step_duration = time.time() - step_start
                    error_msg = str(e)
                    log(f"  ✗ Validation failed: {error_msg}", "error")

                    # Capture screenshot on failure
                    screenshot = None
                    try:
                        page = nova.get_page()
                        if page:
                            screenshot_bytes = page.screenshot()
                            if screenshot_bytes:
                                import base64
                                screenshot = base64.b64encode(screenshot_bytes).decode()
                    except Exception:
                        pass

                    step_results.append(StepResult(
                        step_number=step_idx,
                        keyword=keyword,
                        original_text=text,
                        status="FAILED",
                        duration_seconds=step_duration,
                        error=error_msg,
                        screenshot=screenshot,
                    ))
                    errors.append(f"Step {step_idx} ({keyword} {text}): {error_msg}")

                    if config.stop_on_failure:
                        log(f"\n{'!' * 60}", "error")
                        log(f"STOPPED ON FAILURE (--stop-on-failure)", "error")
                        log(f"Failed at step {step_idx}: {keyword} {text}", "error")
                        log(f"Error: {error_msg}", "error")
                        log(f"To resume: ai-qa-test run --from-step {step_idx} ...", "error")
                        log(f"{'!' * 60}", "error")
                        # Keep browser open — don't break, just stop executing more steps
                        input("\nPress Enter to close browser and exit...")

                    # Stop on first failure
                    break

                except Exception as e:
                    step_duration = time.time() - step_start
                    error_msg = f"Step execution error: {e}"
                    log(f"  ✗ Error: {error_msg}", "error")

                    screenshot = None
                    try:
                        page = nova.get_page()
                        if page:
                            screenshot_bytes = page.screenshot()
                            if screenshot_bytes:
                                import base64
                                screenshot = base64.b64encode(screenshot_bytes).decode()
                    except Exception:
                        pass

                    step_results.append(StepResult(
                        step_number=step_idx,
                        keyword=keyword,
                        original_text=text,
                        status="ERROR",
                        duration_seconds=step_duration,
                        error=error_msg,
                        screenshot=screenshot,
                    ))
                    errors.append(error_msg)
                    break

    except Exception as e:
        errors.append(f"Browser session error: {type(e).__name__}: {e}")
        log(f"Browser session error: {type(e).__name__}: {e}", "error")

    duration = time.time() - start_time

    # Determine overall status
    if errors:
        status = "FAILED" if any(s.status == "FAILED" for s in step_results) else "ERROR"
    else:
        status = "PASSED"

    log(f"{'=' * 60}")
    log(f"Scenario {status}: {scenario_name} ({duration:.2f}s)")
    log(f"{'=' * 60}")

    return ScenarioResult(
        scenario_name=scenario_name,
        feature_name=feature_name,
        status=status,
        duration_seconds=duration,
        steps=step_results,
        extracted_variables=extracted_values,
        errors=errors,
    )


def _execute_step(step, nova, extracted_values: dict, functions: FunctionRegistry, log) -> Any:
    """Execute a single step. Returns extracted/computed value if any.

    Core dispatch logic ported as-is from test_translator/utils/execution.py.
    """
    if step.function_call:
        func_name = step.function_call.function_name
        parameters = step.function_call.parameters
        storage_key = step.function_call.storage_key

        log(f"  → Call function: {func_name}")
        if parameters:
            log(f"  → Parameters: {parameters}")

        # Substitute variables in parameters
        resolved_params = {}
        for key, value in parameters.items():
            if isinstance(value, str):
                resolved_params[key] = substitute_variables(value, extracted_values)
            else:
                resolved_params[key] = value

        # Call via registry (handles reserved param injection)
        result = functions.call(
            func_name,
            resolved_params,
            nova_act=nova,
            context={'variables': extracted_values},
        )

        if storage_key:
            extracted_values[storage_key] = result
            log(f"  → Stored as: {storage_key}")

        log(f"  → Result: {result}")
        return result

    elif step.instruction:
        instruction = substitute_variables(step.instruction, extracted_values)
        log(f"  → Action: {instruction}")
        nova.act(instruction)
        return None

    elif step.extraction:
        extraction = step.extraction
        prompt = substitute_variables(extraction.prompt, extracted_values)
        extraction_type = extraction.extraction_type
        extraction_key = extraction.extraction_key

        log(f"  → Extract ({extraction_type}): {prompt}")
        log(f"  → Store as: {extraction_key}")

        value = getattr(nova.expect(prompt), f"as_{extraction_type}")()
        extracted_values[extraction_key] = value
        log(f"  → Extracted: {value}")
        return value

    elif step.validation:
        validation = step.validation
        prompt = substitute_variables(validation.prompt, extracted_values)
        expected = validation.expected
        if isinstance(expected, str):
            expected = substitute_variables(expected, extracted_values)
        comparison = validation.comparison

        log(f"  → Validate ({comparison}): {prompt}")
        if comparison not in ("true", "false"):
            log(f"  → Expected: {expected}")

        # Map comparison to Nova Act QA method name
        if comparison in ("equal", "contain", "match", "greater_than", "less_than", "greater_or_equal", "less_or_equal"):
            method_name = f"to_{comparison}"
        else:
            method_name = f"to_be_{comparison}"

        expectation = nova.expect(prompt)
        assert_method = getattr(expectation, method_name)

        if comparison in ("true", "false"):
            actual = assert_method()
        else:
            actual = assert_method(expected)

        log(f"  → Actual: {actual}")
        return actual

    return None
