"""Detailed HTML report with Nova Act trajectory data.

Generates a single-page HTML report showing:
- Each Gherkin step with its original text
- All Nova Act sub-steps (think → action → screenshot) for that step
- Inline embedded screenshots at each trajectory step

This is a "deep dive" report for debugging and understanding
exactly what the AI did at each point.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from ai_qa_test_engine.models import RunSummary, ScenarioResult, StepResult


def _load_trajectory(trajectory_file: str | None) -> dict | None:
    """Load trajectory JSON and return the full data dict.

    Args:
        trajectory_file: Path to trajectory JSON file

    Returns:
        Full trajectory dict (with 'prompt', 'steps', 'metadata'), or None if unavailable
    """
    if not trajectory_file:
        return None

    path = Path(trajectory_file)
    if not path.exists():
        return None

    try:
        with open(path) as f:
            data = json.load(f)
        return data
    except (json.JSONDecodeError, OSError):
        return None


def _format_action(call: dict) -> tuple[str, str | None]:
    """Format a single program call into a human-readable action string.

    Args:
        call: A dict with 'name' and 'kwargs'

    Returns:
        Tuple of (formatted action description, bounding box string or None)
    """
    name = call.get("name", "unknown")
    kwargs = call.get("kwargs", {})

    if name == "think":
        return ("", None)  # Think is rendered separately
    elif name == "agentClick":
        box = kwargs.get("box", "")
        return (f"Click at {box}", box)
    elif name == "agentType":
        text = kwargs.get("text", "")
        box = kwargs.get("box", "")
        # Truncate long text
        display = text[:80] + "..." if len(text) > 80 else text
        return (f'Type: "{display}"', box or None)
    elif name == "scroll":
        direction = kwargs.get("direction", "down")
        return (f"Scroll {direction}", None)
    elif name == "waitForPageToSettle":
        return ("Wait for page to settle", None)
    elif name == "takeObservation":
        return ("Observe page state", None)
    elif name == "return":
        return ("✓ Task complete", None)
    elif name == "agentHover":
        box = kwargs.get("box", "")
        return (f"Hover at {box}", box)
    elif name == "pressKey":
        key = kwargs.get("key", "")
        return (f"Press key: {key}", None)
    elif name == "selectOption":
        box = kwargs.get("box", "")
        return ("Select option", box or None)
    else:
        # Generic fallback
        params = ", ".join(f"{k}={v}" for k, v in kwargs.items() if k != "value")
        return (f"{name}({params})" if params else name, None)


def _draw_boxes_on_image(image_data_url: str, boxes: list[tuple[int, int, int, int]]) -> str:
    """Draw red bounding boxes directly onto the image and return a new data URL.

    Args:
        image_data_url: Original image as a data URL (data:image/jpeg;base64,...)
        boxes: List of (left, top, right, bottom) in pixel coordinates

    Returns:
        New data URL with boxes drawn on the image
    """
    import base64
    import io

    try:
        from PIL import Image, ImageDraw

        # Decode the image
        header, b64_data = image_data_url.split(",", 1)
        img_bytes = base64.b64decode(b64_data)
        img = Image.open(io.BytesIO(img_bytes))

        # Draw red rectangles
        draw = ImageDraw.Draw(img)
        for left, top, right, bottom in boxes:
            # Draw 3px border by drawing multiple rectangles
            for offset in range(3):
                draw.rectangle(
                    [left - offset, top - offset, right + offset, bottom + offset],
                    outline="red",
                )

        # Encode back to base64
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        encoded = base64.b64encode(buf.getvalue()).decode()
        return f"data:image/jpeg;base64,{encoded}"

    except ImportError:
        # PIL not available, return original
        return image_data_url
    except Exception:
        return image_data_url


def _parse_box(box_str: str) -> tuple[int, int, int, int] | None:
    """Parse a bounding box string like '<box>32,547,55,640</box>' into (left, top, right, bottom) in pixels.

    Nova Act format: <box>top, left, bottom, right</box> in viewport pixel coordinates.
    We convert to (left, top, right, bottom) for canvas rendering.

    Args:
        box_str: Raw box string from trajectory

    Returns:
        Tuple of (left, top, right, bottom) in pixels or None if parsing fails
    """
    if not box_str:
        return None
    import re
    match = re.search(r'(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)', box_str)
    if match:
        # Nova Act format: top, left, bottom, right
        top = int(match.group(1))
        left = int(match.group(2))
        bottom = int(match.group(3))
        right = int(match.group(4))
        # Return as (left, top, right, bottom) for canvas strokeRect(x, y, w, h)
        return (left, top, right, bottom)
    return None


def _render_trajectory_steps(trajectory_steps: list[dict]) -> str:
    """Render trajectory steps as HTML.

    Args:
        trajectory_steps: List of trajectory step dicts from the JSON

    Returns:
        HTML string for the trajectory steps
    """
    if not trajectory_steps:
        return '<p class="no-trajectory">No trajectory data available</p>'

    html_parts = []
    for i, traj_step in enumerate(trajectory_steps, 1):
        calls = traj_step.get("program", {}).get("calls", [])
        image = traj_step.get("image", "")
        url = traj_step.get("active_url", "")

        # Extract think and actions (with bounding boxes)
        think_text = ""
        actions = []  # list of (action_str, box_coords_or_None)
        for call in calls:
            if call.get("name") == "think":
                think_text = call.get("kwargs", {}).get("value", "")
            else:
                action_str, box_str = _format_action(call)
                if action_str:
                    box_coords = _parse_box(box_str) if box_str else None
                    actions.append((action_str, box_coords))

        # Collect all bounding boxes for overlay on screenshot
        all_boxes = [coords for _, coords in actions if coords is not None]

        # Build the trajectory step HTML
        html_parts.append(f'<div class="traj-step">')
        html_parts.append(f'  <div class="traj-step-header">Sub-step {i}</div>')

        if url:
            safe_url = url.replace("<", "&lt;").replace(">", "&gt;")
            html_parts.append(f'  <div class="traj-url">🔗 {safe_url}</div>')

        if think_text:
            safe_think = think_text.replace("<", "&lt;").replace(">", "&gt;")
            html_parts.append(f'  <div class="traj-think">')
            html_parts.append(f'    <span class="traj-label">💭 Think:</span>')
            html_parts.append(f'    <span class="traj-think-text">{safe_think}</span>')
            html_parts.append(f'  </div>')

        if actions:
            html_parts.append(f'  <div class="traj-actions">')
            html_parts.append(f'    <span class="traj-label">⚡ Actions:</span>')
            html_parts.append(f'    <ul class="traj-action-list">')
            for action_str, _ in actions:
                safe_action = action_str.replace("<", "&lt;").replace(">", "&gt;")
                html_parts.append(f'      <li>{safe_action}</li>')
            html_parts.append(f'    </ul>')
            html_parts.append(f'  </div>')

        if image:
            html_parts.append(f'  <div class="traj-screenshot">')
            html_parts.append(f'    <span class="traj-label">📸 Screenshot:</span>')

            if all_boxes:
                # Draw red boxes directly onto the image (persists in lightbox)
                annotated_image = _draw_boxes_on_image(image, all_boxes)
                html_parts.append(
                    f'    <img src="{annotated_image}" class="traj-img"'
                    f' onclick="openLightbox(this.src)"/>'
                )
            else:
                html_parts.append(
                    f'    <img src="{image}" class="traj-img" loading="lazy"'
                    f' onclick="openLightbox(this.src)"/>'
                )

            html_parts.append(f'  </div>')

        html_parts.append(f'</div>')

    return "\n".join(html_parts)


def _render_gherkin_step(step: StepResult) -> str:
    """Render a single Gherkin step with its trajectory.

    Args:
        step: The step result

    Returns:
        HTML string for the step
    """
    status_class = {
        "PASSED": "step-passed",
        "FAILED": "step-failed",
        "ERROR": "step-error",
        "SKIPPED": "step-skipped",
    }.get(step.status, "step-error")

    status_icon = {
        "PASSED": "✓",
        "FAILED": "✗",
        "ERROR": "⚠",
        "SKIPPED": "⊘",
    }.get(step.status, "?")

    safe_text = step.original_text.replace("<", "&lt;").replace(">", "&gt;")

    # Use <details> to make step content collapsible (open by default for failed steps)
    open_attr = ' open' if step.status in ("FAILED", "ERROR") else ''
    html = f'<details class="gherkin-step {status_class}"{open_attr}>'
    html += f'  <summary class="gherkin-step-header">'
    html += f'    <span class="step-status-icon">{status_icon}{"⚡" if step.replayed_from_cache else ""}</span>'
    html += f'    <code class="step-keyword">{step.keyword}</code>'
    html += f'    <span class="step-text">{safe_text}</span>'
    html += f'    <span class="step-duration">{step.duration_seconds:.1f}s</span>'
    html += f'    <span class="step-badge {status_class}">{step.status}</span>'
    html += f'  </summary>'

    if step.error:
        safe_error = step.error.replace("<", "&lt;").replace(">", "&gt;")
        html += f'  <div class="step-error-msg">Error: {safe_error}</div>'

    # Load and render trajectory
    trajectory_data = _load_trajectory(step.trajectory_file)
    if trajectory_data:
        # Show the prompt sent to Nova Act
        prompt = trajectory_data.get("prompt", "")
        if prompt:
            safe_prompt = prompt.replace("<", "&lt;").replace(">", "&gt;")
            html += f'  <div class="step-prompt">🎯 Prompt: <code>{safe_prompt}</code></div>'

        trajectory_steps = trajectory_data.get("steps", [])
        if trajectory_steps:
            html += f'  <div class="trajectory-container">'
            html += _render_trajectory_steps(trajectory_steps)
            html += f'  </div>'
    elif step.status == "SKIPPED":
        pass  # No trajectory for skipped steps
    elif step.screenshot:
        # Fallback: show failure screenshot if no trajectory
        html += f'  <div class="trajectory-container">'
        html += f'    <div class="traj-step">'
        html += f'      <div class="traj-screenshot">'
        html += f'        <span class="traj-label">📸 Failure Screenshot:</span>'
        html += (
            f'        <img src="data:image/png;base64,{step.screenshot}" class="traj-img" '
            f'onclick="openLightbox(this.src)"/>'
        )
        html += f'      </div>'
        html += f'    </div>'
        html += f'  </div>'
    else:
        # No trajectory available — note the step type
        html += f'  <div class="trajectory-container">'
        html += f'    <p class="no-trajectory">No trajectory recorded (validation/extraction steps use act_get which does not produce a trajectory)</p>'
        html += f'  </div>'

    html += f'</details>'
    return html


def _render_scenario(result: ScenarioResult) -> str:
    """Render a full scenario with all its steps.

    Args:
        result: Scenario result

    Returns:
        HTML string for the scenario
    """
    status_class = {
        "PASSED": "scenario-passed",
        "FAILED": "scenario-failed",
        "ERROR": "scenario-error",
    }.get(result.status, "scenario-error")

    steps_html = "\n".join(_render_gherkin_step(step) for step in result.steps)

    # Per-scenario workflow info
    wf_html = ""
    if result.workflow_definition_name or result.workflow_run_id:
        wf_html = '<div class="scenario-workflow">'
        if result.workflow_definition_name:
            wf_html += f'<span>Workflow: <code>{result.workflow_definition_name}</code></span>'
        if result.workflow_run_id:
            wf_html += f'<span>Run ID: <code>{result.workflow_run_id}</code></span>'
        wf_html += '</div>'

    return f"""
    <details class="scenario-detail {status_class}" {'open' if result.status != 'PASSED' else ''}>
      <summary class="scenario-summary">
        <span class="scenario-badge {status_class}">{result.status}</span>
        <span class="scenario-feature">{result.feature_name}</span> ::
        <span class="scenario-name">{result.scenario_name}</span>
        <span class="scenario-duration">({result.duration_seconds:.1f}s)</span>
      </summary>
      <div class="scenario-body">
        {wf_html}
        {steps_html}
      </div>
    </details>
    """


def generate_detailed_report(summary: RunSummary, results: list[ScenarioResult]) -> str:
    """Generate a detailed HTML report with full Nova Act trajectory data.

    This is a single-page HTML file showing every Gherkin step with
    the complete AI reasoning (think), actions taken, and screenshots
    at each sub-step.

    Args:
        summary: Run summary with aggregated stats
        results: List of scenario results

    Returns:
        Complete HTML string
    """
    scenarios_html = "\n".join(_render_scenario(r) for r in results)
    timestamp = summary.timestamp or datetime.now(timezone.utc).isoformat()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Detailed Test Report — {summary.run_id}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    margin: 0; padding: 20px;
    background: #f0f2f5; color: #1a1a2e;
    line-height: 1.5;
  }}
  .container {{ max-width: 1200px; margin: 0 auto; }}

  /* Header */
  .report-header {{
    background: linear-gradient(135deg, #232f3e 0%, #1a2332 100%);
    color: white; padding: 24px 32px; border-radius: 12px;
    margin-bottom: 24px;
  }}
  .report-header h1 {{ margin: 0 0 8px 0; font-size: 1.5em; }}
  .report-meta {{ color: #adb5bd; font-size: 0.9em; }}
  .report-meta span {{ margin-right: 20px; }}

  /* Stats bar */
  .stats-bar {{
    display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap;
  }}
  .stat-card {{
    background: white; padding: 16px 24px; border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08); text-align: center;
    min-width: 100px; flex: 1;
  }}
  .stat-card .value {{ font-size: 2em; font-weight: 700; }}
  .stat-card .label {{ font-size: 0.8em; color: #6c757d; text-transform: uppercase; letter-spacing: 0.5px; }}
  .stat-card.passed .value {{ color: #0f8a00; }}
  .stat-card.failed .value {{ color: #d13212; }}
  .stat-card.error .value {{ color: #e67e00; }}

  /* Scenario */
  .scenario-detail {{
    background: white; margin-bottom: 16px; border-radius: 10px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    border-left: 4px solid #adb5bd;
  }}
  .scenario-detail.scenario-passed {{ border-left-color: #0f8a00; }}
  .scenario-detail.scenario-failed {{ border-left-color: #d13212; }}
  .scenario-detail.scenario-error {{ border-left-color: #e67e00; }}

  .scenario-summary {{
    padding: 16px 20px; cursor: pointer; font-weight: 500;
    display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  }}
  .scenario-summary:hover {{ background: #f8f9fa; }}
  .scenario-badge {{
    display: inline-block; padding: 3px 10px; border-radius: 4px;
    font-size: 0.75em; font-weight: 700; text-transform: uppercase;
  }}
  .scenario-badge.scenario-passed {{ background: #e6f4e6; color: #0f8a00; }}
  .scenario-badge.scenario-failed {{ background: #fdecea; color: #d13212; }}
  .scenario-badge.scenario-error {{ background: #fff3e0; color: #e67e00; }}
  .scenario-feature {{ color: #6c757d; }}
  .scenario-name {{ font-weight: 600; }}
  .scenario-duration {{ color: #6c757d; font-size: 0.9em; margin-left: auto; }}

  .scenario-body {{ padding: 0 20px 20px 20px; }}

  /* Gherkin Step */
  .gherkin-step {{
    margin-bottom: 16px; border: 1px solid #e9ecef;
    border-radius: 8px; overflow: hidden;
  }}
  .gherkin-step.step-passed {{ border-color: #c3e6c3; }}
  .gherkin-step.step-failed {{ border-color: #f5c6cb; }}
  .gherkin-step.step-error {{ border-color: #ffdab9; }}
  .gherkin-step.step-skipped {{ border-color: #e2e3e5; opacity: 0.7; }}

  .gherkin-step-header {{
    padding: 12px 16px; display: flex; align-items: center; gap: 10px;
    background: #f8f9fa; cursor: pointer;
    flex-wrap: wrap; list-style: none;
  }}
  .gherkin-step-header::-webkit-details-marker {{ display: none; }}
  .gherkin-step-header:hover {{ background: #eef0f2; }}
  .step-status-icon {{ font-size: 1.2em; }}
  .step-keyword {{
    background: #232f3e; color: #ff9900; padding: 2px 8px;
    border-radius: 4px; font-size: 0.85em; font-weight: 600;
  }}
  .step-text {{ font-size: 0.95em; }}
  .step-duration {{ color: #6c757d; font-size: 0.85em; margin-left: auto; }}
  .step-badge {{
    font-size: 0.7em; padding: 2px 6px; border-radius: 3px;
    font-weight: 600; text-transform: uppercase;
  }}
  .step-badge.step-passed {{ background: #e6f4e6; color: #0f8a00; }}
  .step-badge.step-failed {{ background: #fdecea; color: #d13212; }}
  .step-badge.step-error {{ background: #fff3e0; color: #e67e00; }}
  .step-badge.step-skipped {{ background: #e2e3e5; color: #6c757d; }}

  .step-error-msg {{
    padding: 8px 16px; background: #fdecea; color: #d13212;
    font-size: 0.9em; border-bottom: 1px solid #f5c6cb;
  }}

  /* Trajectory */
  .trajectory-container {{
    padding: 12px 16px;
  }}
  .no-trajectory {{ color: #6c757d; font-style: italic; }}

  .traj-step {{
    margin-bottom: 14px; padding: 12px 16px;
    background: #f8f9fc; border-radius: 6px;
    border: 1px solid #e9ecef;
  }}
  .traj-step:last-child {{ margin-bottom: 0; }}

  .traj-step-header {{
    font-weight: 600; font-size: 0.8em; color: #6c757d;
    text-transform: uppercase; letter-spacing: 0.5px;
    margin-bottom: 8px; padding-bottom: 4px;
    border-bottom: 1px solid #e9ecef;
  }}

  .traj-url {{
    font-size: 0.8em; color: #6c757d; margin-bottom: 6px;
    word-break: break-all;
  }}

  .traj-label {{
    font-weight: 600; font-size: 0.85em; color: #495057;
    display: block; margin-bottom: 4px;
  }}

  .traj-think {{
    margin-bottom: 10px; padding: 10px 12px;
    background: #e8f4fd; border-radius: 4px;
    border-left: 3px solid #0073bb;
  }}
  .traj-think-text {{
    font-size: 0.9em; color: #1a3a4a; display: block;
    white-space: pre-wrap;
  }}

  .traj-actions {{ margin-bottom: 10px; }}
  .traj-action-list {{
    margin: 4px 0 0 0; padding-left: 20px;
    font-size: 0.9em; color: #333;
  }}
  .traj-action-list li {{ margin-bottom: 3px; }}

  .traj-screenshot {{ margin-top: 8px; }}
  .traj-img {{
    max-width: 100%; max-height: 400px;
    border: 1px solid #dee2e6; border-radius: 6px;
    margin-top: 6px; cursor: pointer;
    transition: box-shadow 0.2s;
    display: block;
  }}
  .traj-img:hover {{ box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}

  /* Footer */
  .report-footer {{
    text-align: center; padding: 20px;
    color: #6c757d; font-size: 0.85em;
  }}

  /* Prompt */
  .step-prompt {{
    padding: 8px 16px; background: #f0f7ff; border-bottom: 1px solid #d0e3f7;
    font-size: 0.9em;
  }}
  .step-prompt code {{
    background: #e1edf9; padding: 2px 6px; border-radius: 3px;
  }}

  /* Workflow info (per-scenario) */
  .scenario-workflow {{
    padding: 8px 12px; margin-bottom: 12px;
    background: #f0f2f5; border-radius: 4px;
    font-size: 0.8em; color: #495057;
    display: flex; gap: 20px; flex-wrap: wrap;
  }}
  .scenario-workflow code {{
    background: #e1e5ea; padding: 2px 6px; border-radius: 3px; font-size: 0.95em;
  }}

  /* Lightbox */
  .lightbox-overlay {{
    display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    background: rgba(0,0,0,0.85); z-index: 9999;
    justify-content: center; align-items: center; cursor: pointer;
  }}
  .lightbox-overlay.active {{ display: flex; }}
  .lightbox-overlay img {{
    max-width: 95%; max-height: 95%; border-radius: 8px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5);
  }}
</style>
</head>
<body>
<div class="container">
  <div class="report-header">
    <h1>🔍 Detailed Test Execution Report</h1>
    <div class="report-meta">
      <span>Run: {summary.run_id}</span>
      <span>Generated: {timestamp}</span>
      <span>Status: <strong>{summary.status}</strong></span>
    </div>
  </div>

  <div class="stats-bar">
    <div class="stat-card passed"><div class="value">{summary.passed}</div><div class="label">Passed</div></div>
    <div class="stat-card failed"><div class="value">{summary.failed}</div><div class="label">Failed</div></div>
    <div class="stat-card error"><div class="value">{summary.errors}</div><div class="label">Errors</div></div>
    <div class="stat-card"><div class="value">{summary.total_scenarios}</div><div class="label">Total</div></div>
    <div class="stat-card"><div class="value">{summary.total_duration_seconds:.1f}s</div><div class="label">Duration</div></div>
  </div>

  <h2>Scenarios</h2>
  {scenarios_html}

  <div class="report-footer">
    AI QA Test Engine — Detailed Trajectory Report
  </div>
</div>

<!-- Lightbox overlay -->
<div class="lightbox-overlay" id="lightbox" onclick="closeLightbox()">
  <img id="lightbox-img" src="" alt="Enlarged screenshot"/>
</div>
<script>
function openLightbox(src) {{
  document.getElementById('lightbox-img').src = src;
  document.getElementById('lightbox').classList.add('active');
}}
function closeLightbox() {{
  document.getElementById('lightbox').classList.remove('active');
}}
document.addEventListener('keydown', function(e) {{
  if (e.key === 'Escape') closeLightbox();
}});
</script>
</body>
</html>"""
