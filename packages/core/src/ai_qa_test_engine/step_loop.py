"""Shared step execution loop.

Extracted from executor.py to be reused by both the local executor
and the AgentCore runner — eliminating code duplication that caused
bugs to be fixed in one place but not the other.
"""

import base64
import time
from typing import Any, Callable, Optional

from ai_qa_test_engine.executor import _execute_step, substitute_variables
from ai_qa_test_engine.function_registry import FunctionRegistry
from ai_qa_test_engine.models import StepResult, TestScenario
from ai_qa_test_engine.trajectory import TrajectoryCache


def execute_steps(
    *,
    scenario: TestScenario,
    nova: Any,
    extracted_values: dict,
    functions: FunctionRegistry,
    log: Callable[[str, str], None],
    traj_cache: Optional[TrajectoryCache] = None,
    feature_name: str = "",
    trajectory_strict: bool = False,
    max_steps: int = 30,
    from_step: int = 1,
) -> tuple[list[StepResult], list[str]]:
    """Execute all steps in a scenario, collecting results and errors.

    This is the shared loop used by both the local executor and AgentCore runner.
    The caller is responsible for creating the browser/nova session and passing it in.

    Args:
        scenario: The test scenario containing steps
        nova: An active NovaActQa instance (already connected to a browser)
        extracted_values: Mutable dict for storing extracted variables
        functions: Loaded function registry
        log: Logging callback (message, level)
        traj_cache: Optional trajectory cache for replay
        feature_name: Feature name for cache keying
        trajectory_strict: Whether to enforce strict trajectory replay
        max_steps: Default max steps per act() call
        from_step: Start execution from this step number (1-indexed)

    Returns:
        Tuple of (step_results, errors)
    """
    step_results: list[StepResult] = []
    errors: list[str] = []
    scenario_name = scenario.name

    for step_idx, step in enumerate(scenario.steps, 1):
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

        log(f"Step {step_idx}: {keyword} {text}", "info")
        step_start = time.time()

        try:
            result = _execute_step(
                step, nova, extracted_values, functions, log,
                traj_cache=traj_cache,
                feature_name=feature_name,
                scenario_name=scenario_name,
                step_index=step_idx,
                trajectory_strict=trajectory_strict,
                max_steps=max_steps,
            )
            step_duration = time.time() - step_start

            # Capture trajectory file path from ActResult (instruction steps)
            # or from act_get fallback (stored on nova instance)
            trajectory_file = None
            was_replayed = False
            sub_actions = None
            if hasattr(result, 'trajectory_file_path') and result.trajectory_file_path:
                trajectory_file = result.trajectory_file_path
            elif hasattr(nova, '_last_trajectory_file') and nova._last_trajectory_file:
                trajectory_file = nova._last_trajectory_file
                # Check if this was an actual cache replay (set by replay path)
                was_replayed = getattr(nova, '_last_was_replay', False)
                nova._last_trajectory_file = None  # Reset after capture
                nova._last_was_replay = False

            # Pick up sub-actions from custom function calls
            if hasattr(nova, '_last_sub_actions') and nova._last_sub_actions:
                sub_actions = nova._last_sub_actions
                nova._last_sub_actions = None

            step_results.append(StepResult(
                step_number=step_idx,
                keyword=keyword,
                original_text=text,
                status="PASSED",
                duration_seconds=step_duration,
                extracted_value=result,
                trajectory_file=trajectory_file,
                replayed_from_cache=was_replayed,
                sub_actions=sub_actions,
            ))
            cache_icon = "⚡" if was_replayed else ""
            log(f"  ✓{cache_icon} Step {step_idx} passed ({step_duration:.1f}s)", "info")

        except AssertionError as e:
            step_duration = time.time() - step_start
            error_msg = str(e)
            log(f"  ✗ Validation failed: {error_msg}", "error")

            # Capture screenshot on failure
            screenshot = _capture_screenshot(nova)

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
            break

        except Exception as e:
            step_duration = time.time() - step_start
            error_msg = f"Step execution error: {e}"
            log(f"  ✗ Error: {error_msg}", "error")

            screenshot = _capture_screenshot(nova)

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

    return step_results, errors


def _capture_screenshot(nova: Any) -> Optional[str]:
    """Attempt to capture a screenshot from the browser, returning base64 or None."""
    try:
        page = nova.get_page()
        if page:
            screenshot_bytes = page.screenshot()
            if screenshot_bytes:
                return base64.b64encode(screenshot_bytes).decode()
    except Exception:
        pass
    return None
