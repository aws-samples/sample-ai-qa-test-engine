"""Interactive debug menu for stop-on-failure mode.

Provides a cross-platform arrow-key menu using prompt_toolkit (bundled with
Python via IPython or available standalone). Falls back to numbered input
if prompt_toolkit is unavailable.
"""

import json
import sys
from typing import Any, Callable, Optional


# Menu choices
RETRY = "retry"
SAVE_REPORT = "save_report"
SHOW_VARIABLES = "show_variables"
SAVE_VARIABLES = "save_variables"
RELOAD_VARIABLES = "reload_variables"
TAKE_SCREENSHOT = "take_screenshot"
ABORT = "abort"

MENU_CHOICES = [
    (RETRY, "▶ Retry (re-translate and resume)"),
    (SAVE_REPORT, "📊 Save report (export progress so far)"),
    (SHOW_VARIABLES, "🔍 Show current variables"),
    (SAVE_VARIABLES, "💾 Save variables to file"),
    (RELOAD_VARIABLES, "🔄 Reload input variables (re-read JSON file)"),
    (TAKE_SCREENSHOT, "📸 Take screenshot of current page"),
    (ABORT, "🛑 Abort"),
]


def show_debug_menu(
    step_number: int,
    keyword: str,
    text: str,
    error_msg: str,
    log: Callable[[str, str], None],
) -> str:
    """Show the interactive debug menu and return the user's choice.

    Args:
        step_number: The step that failed
        keyword: Step keyword (Given/When/Then)
        text: Step text
        error_msg: Error message from the failure
        log: Log callback

    Returns:
        One of the choice constants: RETRY, SAVE_REPORT, SHOW_VARIABLES, TAKE_SCREENSHOT, ABORT
    """
    log(f"\n{'!' * 60}", "error")
    log(f"  STOPPED ON FAILURE", "error")
    log(f"  Step {step_number}: {keyword} {text}", "error")
    log(f"  Error: {error_msg}", "error")
    log(f"{'!' * 60}", "error")
    log("", "info")
    log("  Browser is open — inspect the page state.", "info")
    log("  Edit your .feature file before selecting Retry.", "info")
    log("", "info")

    try:
        return _show_menu_questionary()
    except (ImportError, Exception):
        pass

    try:
        return _show_menu_prompt_toolkit()
    except (ImportError, Exception):
        pass

    # Final fallback: numbered menu
    return _show_menu_fallback()


def _show_menu_questionary() -> str:
    """Use questionary for cross-platform arrow-key menu."""
    import questionary

    choices = [
        questionary.Choice(title=label, value=key)
        for key, label in MENU_CHOICES
    ]
    result = questionary.select(
        "What would you like to do?",
        choices=choices,
        use_arrow_keys=True,
        use_shortcuts=False,
    ).ask()

    if result is None:  # Ctrl+C
        return ABORT
    return result


def _show_menu_prompt_toolkit() -> str:
    """Use prompt_toolkit directly (available if questionary isn't installed)."""
    from prompt_toolkit import prompt
    from prompt_toolkit.formatted_text import FormattedText

    print("\n  What would you like to do?\n")
    for i, (key, label) in enumerate(MENU_CHOICES, 1):
        print(f"    {i}. {label}")
    print()

    while True:
        try:
            answer = prompt("  Enter choice (1-7): ").strip()
            idx = int(answer) - 1
            if 0 <= idx < len(MENU_CHOICES):
                return MENU_CHOICES[idx][0]
        except (ValueError, EOFError, KeyboardInterrupt):
            return ABORT


def _show_menu_fallback() -> str:
    """Simple numbered fallback — works everywhere."""
    print("\n  What would you like to do?\n")
    for i, (key, label) in enumerate(MENU_CHOICES, 1):
        print(f"    {i}. {label}")
    print()

    while True:
        try:
            answer = input("  Enter choice (1-7): ").strip()
            if answer.lower() in ("q", "quit", "abort"):
                return ABORT
            idx = int(answer) - 1
            if 0 <= idx < len(MENU_CHOICES):
                return MENU_CHOICES[idx][0]
            print("  Invalid choice. Enter 1-7.")
        except (ValueError, EOFError, KeyboardInterrupt):
            return ABORT


def display_variables(extracted_values: dict, log: Callable[[str, str], None]) -> None:
    """Pretty-print the current variable state as formatted JSON."""
    print("\n  ┌─────────────────────────────────────")
    print("  │ Current Variables")
    print("  ├─────────────────────────────────────")

    if not extracted_values:
        print("  │  (none)")
    else:
        formatted = json.dumps(extracted_values, indent=2, ensure_ascii=False, default=str)
        for line in formatted.splitlines():
            print(f"  │  {line}")

    print("  └─────────────────────────────────────")


def save_variables(extracted_values: dict, output_dir: Any) -> str:
    """Save current variables to a JSON file and return the path.

    Args:
        extracted_values: Current variable state
        output_dir: Path to output directory (typically config.resolve_report_dir())

    Returns:
        Absolute path string of the saved file
    """
    from pathlib import Path
    from datetime import datetime, timezone

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    filepath = out_dir / f"variables_{timestamp}.json"
    filepath.write_text(
        json.dumps(extracted_values, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return str(filepath.resolve())


def _truncate(s: str, max_len: int) -> str:
    """Truncate a string with ellipsis if too long."""
    if len(s) <= max_len:
        return s
    return s[:max_len - 3] + "..."
