"""Capture sub-actions from custom functions that use nova_act.

When a custom function receives `nova_act` as a parameter and calls
`.act()` or `.expect()` on it, this module records each call —
including the instruction, trajectory, and a screenshot — so they
can be included in the detailed report as sub-steps.

Usage:
    with capture_function_actions(nova) as captured:
        result = functions.call(func_name, params, nova_act=nova)
    # captured.sub_actions is a list of dicts with action details
"""

import base64
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CapturedAction:
    """A single captured sub-action from a custom function."""
    action_type: str  # "act" or "expect"
    instruction: str
    duration_seconds: float = 0.0
    trajectory_file: str | None = None
    screenshot: str | None = None  # base64 PNG after action
    result: str | None = None  # String repr of result (for expect)
    think_text: str | None = None  # Thinking/reasoning from trajectory


@dataclass
class FunctionCapture:
    """Collects all sub-actions captured during a function call."""
    sub_actions: list[dict] = field(default_factory=list)


@contextmanager
def capture_function_actions(nova: Any):
    """Context manager that monkey-patches nova.act/expect to record sub-actions.

    Yields a FunctionCapture object. On exit, restores original methods.

    Usage:
        with capture_function_actions(nova) as captured:
            result = my_custom_function(nova_act=nova, ...)
        # captured.sub_actions contains recorded actions
    """
    capture = FunctionCapture()

    # Save originals
    original_act = nova.act
    original_expect = nova.expect

    def recording_act(instruction: str, **kwargs) -> Any:
        start = time.time()
        result = original_act(instruction, **kwargs)
        duration = time.time() - start

        # Capture screenshot after action
        screenshot_b64 = _capture_screenshot(nova)

        # Extract trajectory file path
        traj_file = None
        if hasattr(result, 'trajectory_file_path') and result.trajectory_file_path:
            traj_file = str(result.trajectory_file_path)

        capture.sub_actions.append({
            "action_type": "act",
            "instruction": instruction,
            "duration_seconds": round(duration, 2),
            "trajectory_file": traj_file,
            "screenshot": screenshot_b64,
        })

        return result

    def recording_expect(prompt: str) -> Any:
        """Wrap expect — capture the prompt but return the expectation object as-is.

        We can't easily intercept the chained .as_string() / .to_be_true() calls,
        so we record the prompt and capture a screenshot at the expect() call time.
        """
        screenshot_b64 = _capture_screenshot(nova)

        capture.sub_actions.append({
            "action_type": "expect",
            "instruction": prompt,
            "duration_seconds": 0.0,  # Updated if we can measure
            "screenshot": screenshot_b64,
        })

        return original_expect(prompt)

    # Monkey-patch
    nova.act = recording_act
    nova.expect = recording_expect

    try:
        yield capture
    finally:
        # Restore originals
        nova.act = original_act
        nova.expect = original_expect


def _capture_screenshot(nova: Any) -> str | None:
    """Attempt to capture a screenshot, returning base64 or None."""
    try:
        page = nova.get_page()
        if page:
            screenshot_bytes = page.screenshot()
            if screenshot_bytes:
                return base64.b64encode(screenshot_bytes).decode()
    except Exception:
        pass
    return None
