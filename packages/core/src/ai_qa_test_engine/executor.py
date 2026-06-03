"""Test execution engine.

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
    ScenarioResult,
    StepResult,
    TestScenario,
)
from ai_qa_test_engine.trajectory import TrajectoryCache


def store_variable(variables: dict, key: str, value: Any) -> None:
    """Store a value in the variables dict, supporting dotted nested paths.

    - Simple key ("order_id") → variables["order_id"] = value
    - Dotted key ("dealer.email") → variables["dealer"]["email"] = value
      (auto-creates intermediate dicts)
    """
    if "." not in key:
        variables[key] = value
        return

    parts = key.split(".")
    obj = variables
    for part in parts[:-1]:
        if part not in obj or not isinstance(obj[part], dict):
            obj[part] = {}
        obj = obj[part]
    obj[parts[-1]] = value


def substitute_variables(text: str, variables: dict) -> str:
    """Replace ${variable_name} references with actual values.

    Supports:
    - Simple: ${name} → variables["name"]
    - Dotted (nested): ${user.name} → variables["user"]["name"]
    - Dotted (nested from extraction): ${dealer.email} → variables["dealer"]["email"]
    - Dict return: ${stats.gravity} → variables["stats"]["gravity"]
    - Array index: ${items.0.title} → variables["items"][0]["title"]

    Args:
        text: Text containing variable references
        variables: Dictionary of extracted variables (nested)

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

        # Direct lookup (handles simple keys and legacy flat dotted keys)
        if var_name in variables:
            return str(variables[var_name])

        # Dotted path traversal for nested objects/arrays
        if "." in var_name:
            parts = var_name.split(".")
            obj = variables.get(parts[0])
            if obj is not None:
                for part in parts[1:]:
                    if isinstance(obj, dict):
                        obj = obj.get(part)
                    elif isinstance(obj, (list, tuple)) and part.isdigit():
                        idx = int(part)
                        obj = obj[idx] if idx < len(obj) else None
                    else:
                        obj = None
                        break
                if obj is not None:
                    return str(obj)

        raise KeyError(f"Variable '${{{var_name}}}' not found in context")

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
    workflow_definition_name: str | None = None
    workflow_run_id: str | None = None

    # Pre-load input variables from JSON file if specified
    if config.input_variables_file:
        import json as _json
        vars_path = config._resolve_path(config.input_variables_file)
        if vars_path.exists():
            try:
                with open(vars_path, encoding="utf-8") as f:
                    input_vars = _json.load(f)
            except (UnicodeDecodeError, ValueError):
                with open(vars_path, encoding="utf-8-sig") as f:
                    try:
                        input_vars = _json.load(f)
                    except (UnicodeDecodeError, ValueError):
                        with open(vars_path, encoding="cp1252") as f:
                            input_vars = _json.load(f)
            extracted_values.update(input_vars)
            log(f"Pre-loaded {len(input_vars)} variable(s) from {vars_path.name}")

    # Initialize trajectory cache (unless --no-cache)
    traj_cache = None
    if not config.no_cache:
        cache_dir = config.resolve_trajectory_cache_dir()
        traj_cache = TrajectoryCache(cache_dir)
        log(f"Trajectory cache: {cache_dir}")

    # Generate workflow name
    workflow_name = make_workflow_name(feature_name, scenario_name)

    try:
        with create_browser_session(config, base_url, workflow_name) as nova:
            # Capture workflow metadata for end-of-run summary
            workflow_definition_name = getattr(nova, '_workflow_definition_name', None)
            workflow_run_id = getattr(nova, '_workflow_run_id', None)

            # Set strict mode flag on the nova instance for downstream use
            nova._strict_mode = config.strict_mode

            from ai_qa_test_engine.step_loop import execute_steps
            step_results, errors = execute_steps(
                scenario=scenario,
                nova=nova,
                extracted_values=extracted_values,
                functions=functions,
                log=log,
                traj_cache=traj_cache,
                feature_name=feature_name,
                trajectory_strict=config.trajectory_strict,
                max_steps=config.max_steps,
                from_step=from_step,
            )

            # Handle stop-on-failure if there was a failure
            if errors and config.stop_on_failure:
                # Find the failed step
                failed_step_result = next(
                    (s for s in step_results if s.status == "FAILED"), None
                )
                if failed_step_result:
                    failed_idx = failed_step_result.step_number
                    failed_keyword = failed_step_result.keyword
                    failed_text = failed_step_result.original_text
                    failed_error = failed_step_result.error or ""

                    retried = _handle_stop_on_failure(
                        step_idx=failed_idx,
                        scenario_name=scenario.name,
                        keyword=failed_keyword,
                        text=failed_text,
                        error_msg=failed_error,
                        nova=nova,
                        extracted_values=extracted_values,
                        functions=functions,
                        config=config,
                        feature_name=feature_name,
                        steps=list(scenario.steps),
                        step_results=step_results,
                        errors=errors,
                        log=log,
                    )
                    # If retry succeeded, errors list was cleared by handler

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
        workflow_definition_name=workflow_definition_name,
        workflow_run_id=workflow_run_id,
    )


def _execute_step(step, nova, extracted_values: dict, functions: FunctionRegistry, log,
                  traj_cache: Optional['TrajectoryCache'] = None,
                  feature_name: str = "",
                  scenario_name: str = "",
                  step_index: int = 0,
                  trajectory_strict: bool = False,
                  max_steps: int = 30) -> Any:
    """Execute a single step. Returns extracted/computed value if any.

    Core dispatch logic ported as-is from test_translator/utils/execution.py.
    Extended with trajectory replay: checks cache before act(), saves after.
    max_steps controls the Nova Act step budget per act() call.
    Per-step override: @max-steps:N annotation in the step text.
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

        # Wrap nova_act with capture to record sub-actions from custom functions
        from ai_qa_test_engine.function_capture import capture_function_actions
        with capture_function_actions(nova) as captured:
            # Call via registry (handles reserved param injection)
            result = functions.call(
                func_name,
                resolved_params,
                nova_act=nova,
                context={'variables': extracted_values},
            )

        # Store captured sub-actions for the step_loop to attach to StepResult
        if captured.sub_actions:
            nova._last_sub_actions = captured.sub_actions
            log(f"  → Captured {len(captured.sub_actions)} sub-action(s) from function")
        else:
            nova._last_sub_actions = None

        if storage_key:
            # Support multiple storage keys: "username, password" unpacks tuple/list
            if "," in storage_key:
                keys = [k.strip() for k in storage_key.split(",")]
                if isinstance(result, (tuple, list)) and len(result) == len(keys):
                    for k, v in zip(keys, result):
                        store_variable(extracted_values, k, v)
                    log(f"  → Stored as: {', '.join(keys)}")
                else:
                    # Mismatch — store full result under first key, warn
                    store_variable(extracted_values, keys[0], result)
                    log(f"  → Warning: expected {len(keys)} values but got {type(result).__name__}, stored under {keys[0]}")
            else:
                store_variable(extracted_values, storage_key, result)
                log(f"  → Stored as: {storage_key}")

        log(f"  → Result: {result}")
        return result

    elif step.instruction:
        instruction = substitute_variables(step.instruction, extracted_values)

        # QA strict mode: prepend guardrail prompt to prevent wandering
        if hasattr(nova, '_strict_mode') and nova._strict_mode:
            instruction = (
                "You are a QA tester executing a single test step. "
                "Do exactly what is described below — nothing more. "
                "Do not navigate to other pages or click links not mentioned. "
                "If an element cannot be found on the current page, stop and return immediately. "
                "If an error or validation message appears after your action, do not attempt to correct it — stop and return. "
                f"\nTask: {instruction}"
            )

        log(f"  → Action: {instruction}")

        step_text = step.original_text

        # Check trajectory cache for replay (skip if @no-cache)
        # Key on resolved instruction so variable steps cache correctly when value is same
        if traj_cache and not traj_cache.is_step_no_cache(step_text):
            cached_path = traj_cache.get_trajectory_path(
                feature_name, scenario_name, step_index, instruction
            )
            if cached_path:
                from ai_qa_test_engine.trajectory import replay_cached_trajectory
                log(f"  → Replaying from cache: {cached_path.name}")
                replayed = replay_cached_trajectory(nova, cached_path, strict=trajectory_strict)
                if replayed:
                    log(f"  → Replay successful (no AI model call)")
                    # Store trajectory path for detailed report access
                    nova._last_trajectory_file = str(cached_path)
                    nova._last_was_replay = True
                    return None  # Replay doesn't return ActResult

        # No cache hit or replay failed — execute via Nova Act
        # Check for per-step @max-steps:N override
        step_max_steps = max_steps
        import re as _re
        max_steps_match = _re.search(r'@max-steps:(\d+)', step_text, _re.IGNORECASE)
        if max_steps_match:
            step_max_steps = int(max_steps_match.group(1))
            log(f"  → max_steps override: {step_max_steps}")

        result = nova.act(instruction, max_steps=step_max_steps)

        # Save trajectory to cache keyed on resolved instruction
        if traj_cache and not traj_cache.is_step_no_cache(step_text):
            if hasattr(result, 'trajectory_file_path') and result.trajectory_file_path:
                traj_cache.save_trajectory(
                    feature_name=feature_name,
                    scenario_name=scenario_name,
                    step_index=step_index,
                    step_text=instruction,  # Key on resolved text
                    trajectory_file_path=result.trajectory_file_path,
                )
                log(f"  → Trajectory saved to cache")

        return result

    elif step.extraction:
        extraction = step.extraction
        prompt = substitute_variables(extraction.prompt, extracted_values)
        extraction_type = extraction.extraction_type
        extraction_key = extraction.extraction_key

        log(f"  → Extract ({extraction_type}): {prompt}")
        log(f"  → Store as: {extraction_key}")

        value = getattr(nova.expect(prompt), f"as_{extraction_type}")()
        store_variable(extracted_values, extraction_key, value)
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


def _handle_stop_on_failure(
    step_idx: int,
    scenario_name: str,
    keyword: str,
    text: str,
    error_msg: str,
    nova,
    extracted_values: dict,
    functions: FunctionRegistry,
    config: AppConfig,
    feature_name: str,
    steps: list,
    step_results: list,
    errors: list,
    log,
) -> bool:
    """Handle stop-on-failure: interactive debug loop with menu.

    Flow (loops until all remaining steps pass or user aborts):
    1. Show failure info and debug menu
    2. User picks: Retry / Save Report / Show Variables / Screenshot / Abort
    3. On Retry: re-translate, detect changes, resume from changed step
    4. If retry fails: loop back to menu (preserving all attempts in step_results)

    Returns True if all remaining steps passed, False if user aborted.
    """
    from ai_qa_test_engine.translator import translate_all_features
    from ai_qa_test_engine.models import Feature
    from ai_qa_test_engine.debug_menu import (
        show_debug_menu, display_variables,
        RETRY, SAVE_REPORT, SHOW_VARIABLES, TAKE_SCREENSHOT, ABORT,
    )

    current_fail_idx = step_idx
    current_keyword = keyword
    current_text = text
    current_error = error_msg

    # Track attempt counts per step number
    attempt_counts: dict[int, int] = {step_idx: 1}  # First failure = attempt 1

    while True:
        # Show menu
        choice = show_debug_menu(
            step_number=current_fail_idx,
            keyword=current_keyword,
            text=current_text,
            error_msg=current_error,
            log=log,
        )

        if choice == ABORT:
            log("\n  Aborted by user.", "error")
            return False

        elif choice == SHOW_VARIABLES:
            display_variables(extracted_values, log)
            continue

        elif choice == TAKE_SCREENSHOT:
            import base64 as _b64
            try:
                page = nova.get_page()
                if page:
                    screenshot_bytes = page.screenshot()
                    if screenshot_bytes:
                        # Save to reports dir
                        from pathlib import Path
                        reports_dir = Path("reports")
                        reports_dir.mkdir(exist_ok=True)
                        screenshot_path = reports_dir / f"debug_screenshot_step{current_fail_idx}.png"
                        screenshot_path.write_bytes(screenshot_bytes)
                        log(f"  📸 Screenshot saved: {screenshot_path}", "info")
                    else:
                        log("  ⚠️  Could not capture screenshot", "error")
                else:
                    log("  ⚠️  No page available", "error")
            except Exception as e:
                log(f"  ⚠️  Screenshot failed: {e}", "error")
            continue

        elif choice == SAVE_REPORT:
            try:
                from ai_qa_test_engine.detailed_report import generate_detailed_report
                from ai_qa_test_engine.models import ScenarioResult, RunSummary
                from datetime import datetime, timezone
                from uuid import uuid4
                from pathlib import Path

                run_id = f"debug-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:6]}"
                duration = sum(s.duration_seconds for s in step_results)
                status = "FAILED"

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
                    passed=0,
                    failed=1,
                    errors=0,
                    total_duration_seconds=duration,
                    status=status,
                    scenarios=[scenario_result],
                )
                html = generate_detailed_report(run_summary, [scenario_result])

                reports_dir = Path("reports")
                reports_dir.mkdir(exist_ok=True)
                report_path = reports_dir / f"{run_id}_partial.html"
                report_path.write_text(html, encoding="utf-8")
                log(f"  📊 Partial report saved: {report_path}", "info")
            except Exception as e:
                log(f"  ⚠️  Report generation failed: {e}", "error")
            continue

        elif choice == RETRY:
            # Re-translate and retry
            log(f"\n  🔄 Re-translating feature file...")
            feature_dir = config.resolve_feature_dir()
            cache_dir = config.resolve_cache_dir()
            tag_url_map = config.get_tag_url_mapping()

            try:
                translated = translate_all_features(
                    input_dir=feature_dir if feature_dir.is_dir() else feature_dir.parent,
                    output_dir=cache_dir,
                    tag_url_map=tag_url_map,
                    bedrock_model_id=config.bedrock_model_id,
                    common_steps_dir=config.common_steps_dir,
                )

                if not translated:
                    log("  Re-translation produced no output", "error")
                    continue

                # Find the correct feature
                feature_data = None
                for t in translated:
                    if t.get("source_file", "").replace(".feature", "") in feature_name or \
                       t.get("name", "") == scenario_name.split("::")[0]:
                        feature_data = t
                        break
                if feature_data is None:
                    feature_data = translated[-1]

                feature = Feature.model_validate(feature_data)

                # Find matching scenario
                updated_scenario = None
                for sc in feature.scenarios:
                    if sc.name == scenario_name:
                        updated_scenario = sc
                        break
                if updated_scenario is None and len(feature.scenarios) == 1:
                    updated_scenario = feature.scenarios[0]
                if updated_scenario is None:
                    log("  Could not find updated scenario after re-translation", "error")
                    continue

                # Detect first changed step
                first_changed = current_fail_idx
                for i in range(len(updated_scenario.steps)):
                    if i >= len(steps):
                        first_changed = i + 1
                        break
                    old_text = steps[i].original_text
                    new_text = updated_scenario.steps[i].original_text
                    if old_text != new_text:
                        first_changed = i + 1
                        log(f"  Change detected at step {first_changed}: '{old_text}' → '{new_text}'")
                        break
                else:
                    first_changed = current_fail_idx
                    log(f"  No text changes detected, resuming from failed step {current_fail_idx}")

                log(f"  Resuming execution from step {first_changed}...")

                # Mark the last failed step result as a failed attempt (don't remove it)
                # This preserves retry history in the report
                if step_results and step_results[-1].status == "FAILED":
                    step_results[-1].is_retry = False  # It's the original attempt, not a retry result
                # Remove the error so we can retry cleanly
                if errors:
                    errors.pop()

                # Execute from first_changed step onwards
                retry_failed = False
                for retry_idx in range(first_changed - 1, len(updated_scenario.steps)):
                    retry_step = updated_scenario.steps[retry_idx]
                    step_num = retry_idx + 1

                    # Track attempt number
                    attempt_counts[step_num] = attempt_counts.get(step_num, 0) + 1
                    attempt_num = attempt_counts[step_num]

                    log(f"  Step {step_num} (attempt {attempt_num}): {retry_step.original_keyword} {retry_step.original_text}")
                    step_start = time.time()

                    try:
                        result = _execute_step(retry_step, nova, extracted_values, functions, log)
                        step_duration = time.time() - step_start
                        step_results.append(StepResult(
                            step_number=step_num,
                            keyword=retry_step.original_keyword,
                            original_text=retry_step.original_text,
                            status="PASSED",
                            duration_seconds=step_duration,
                            extracted_value=result,
                            attempt=attempt_num,
                            is_retry=attempt_num > 1,
                        ))
                        log(f"  ✓ Step {step_num} passed ({step_duration:.1f}s)")
                    except (AssertionError, Exception) as e:
                        step_duration = time.time() - step_start
                        err_msg = str(e)
                        log(f"  ✗ Step {step_num} failed (attempt {attempt_num}): {err_msg}", "error")

                        # Capture screenshot on failure
                        screenshot = None
                        try:
                            page = nova.get_page()
                            if page:
                                screenshot_bytes = page.screenshot()
                                if screenshot_bytes:
                                    import base64 as _b64
                                    screenshot = _b64.b64encode(screenshot_bytes).decode()
                        except Exception:
                            pass

                        step_results.append(StepResult(
                            step_number=step_num,
                            keyword=retry_step.original_keyword,
                            original_text=retry_step.original_text,
                            status="FAILED",
                            duration_seconds=step_duration,
                            error=err_msg,
                            screenshot=screenshot,
                            attempt=attempt_num,
                            is_retry=attempt_num > 1,
                        ))
                        errors.append(f"Step {step_num} (attempt {attempt_num}): {err_msg}")
                        current_fail_idx = step_num
                        current_keyword = retry_step.original_keyword
                        current_text = retry_step.original_text
                        current_error = err_msg
                        retry_failed = True
                        break

                # Update steps list with new versions
                for i in range(len(updated_scenario.steps)):
                    if i < len(steps):
                        steps[i] = updated_scenario.steps[i]

                if not retry_failed:
                    return True
                # Loop back to menu

            except Exception as e:
                log(f"  Retry failed: {e}", "error")
                continue
