"""HTML report generation.

Ported from deploy_test_translator/app/test_runner/reporting.py and
deploy_test_translator/app/orchestrator/reporting.py.
Adapted for local file output with embedded screenshots.
"""

from datetime import datetime, timezone
from pathlib import Path

from ai_qa_test_engine.models import RunSummary, ScenarioResult, StepResult


def generate_scenario_html(result: ScenarioResult) -> str:
    """Generate an HTML report for a single scenario execution.

    Args:
        result: Scenario result with step details

    Returns:
        HTML string
    """
    scenario_name = result.scenario_name
    feature_name = result.feature_name
    status = result.status
    duration = result.duration_seconds
    steps = result.steps
    errors = result.errors

    steps_passed = sum(1 for s in steps if s.status == "PASSED")
    steps_failed = sum(1 for s in steps if s.status in ("FAILED", "ERROR"))
    steps_total = len(steps)

    status_class = {"PASSED": "success", "FAILED": "failure", "ERROR": "error"}.get(status, "error")

    # Build step rows
    step_rows = []
    for step in steps:
        step_class = "step-success" if step.status == "PASSED" else (
            "step-skip" if step.status == "SKIPPED" else "step-error"
        )
        error_html = ""
        if step.error:
            safe_error = step.error.replace("<", "&lt;").replace(">", "&gt;")
            error_html = f'<br/><small class="error-text">{safe_error}</small>'

        safe_text = step.original_text.replace("<", "&lt;").replace(">", "&gt;")

        screenshot_html = ""
        if step.screenshot:
            screenshot_html = (
                f'<br/><a href="data:image/png;base64,{step.screenshot}" target="_blank">'
                f'<img src="data:image/png;base64,{step.screenshot}" class="screenshot"/></a>'
            )

        step_rows.append(
            f'<tr class="{step_class}">'
            f'<td>{step.step_number}</td>'
            f'<td><code>{step.keyword}</code></td>'
            f'<td>{safe_text}{error_html}</td>'
            f'<td><strong>{step.status}</strong></td>'
            f'<td>{step.duration_seconds:.1f}s</td>'
            f'<td>{screenshot_html}</td>'
            f'</tr>'
        )

    errors_section = ""
    if errors:
        error_items = "\n".join(
            f"<li>{e.replace('<', '&lt;').replace('>', '&gt;')}</li>" for e in errors
        )
        errors_section = f'<h2>Errors</h2><ul class="error-list">{error_items}</ul>'

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{feature_name} :: {scenario_name}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 20px; background: #f8f9fa; color: #212529; }}
  .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  h1 {{ border-bottom: 3px solid #ff9900; padding-bottom: 10px; font-size: 1.4em; }}
  .summary {{ background: #e8f4f8; padding: 15px; border-radius: 5px; margin: 15px 0; }}
  .summary p {{ margin: 4px 0; }}
  .success {{ color: #0f8a00; font-weight: bold; }}
  .failure {{ color: #d13212; font-weight: bold; }}
  .error {{ color: #d13212; font-weight: bold; }}
  table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
  th {{ background: #232f3e; color: white; padding: 10px; text-align: left; }}
  td {{ padding: 8px 10px; border: 1px solid #dee2e6; vertical-align: top; }}
  tr.step-success {{ background: #f1f8e9; }}
  tr.step-error {{ background: #fdecea; }}
  tr.step-skip {{ background: #f5f5f5; }}
  .error-text {{ color: #d13212; }}
  .error-list {{ color: #d13212; }}
  code {{ background: #f1f3f5; padding: 2px 5px; border-radius: 3px; font-size: 0.9em; }}
  .screenshot {{ max-width: 320px; border: 1px solid #ccc; border-radius: 4px; margin-top: 4px; }}
</style>
</head>
<body>
<div class="container">
  <h1>{feature_name} :: {scenario_name}</h1>
  <div class="summary">
    <p><strong>Status:</strong> <span class="{status_class}">{status}</span></p>
    <p><strong>Duration:</strong> {duration:.2f}s</p>
    <p><strong>Steps:</strong> {steps_passed}/{steps_total} passed, {steps_failed} failed</p>
    <p><strong>Generated:</strong> {timestamp}</p>
  </div>
  <h2>Step Details</h2>
  <table>
    <tr><th>#</th><th>Keyword</th><th>Step</th><th>Status</th><th>Duration</th><th>Screenshot</th></tr>
    {''.join(step_rows)}
  </table>
  {errors_section}
</div>
</body>
</html>"""


def generate_combined_report(summary: RunSummary, results: list[ScenarioResult]) -> str:
    """Generate combined HTML dashboard for all scenarios in a run.

    Args:
        summary: Run summary with aggregated stats
        results: List of scenario results

    Returns:
        HTML string
    """
    run_id = summary.run_id
    total = summary.total_scenarios
    passed = summary.passed
    failed = summary.failed
    errors = summary.errors
    duration = summary.total_duration_seconds
    overall_status = summary.status
    timestamp = summary.timestamp

    # Build scenario sections
    scenario_sections = []
    for r in results:
        status = r.status
        feature = r.feature_name
        scenario = r.scenario_name
        dur = r.duration_seconds
        errs = r.errors

        status_class = {"PASSED": "passed", "FAILED": "failed", "ERROR": "error"}.get(status, "error")

        # Build step table
        step_rows = ""
        for step in r.steps:
            s_class = "step-pass" if step.status == "PASSED" else (
                "step-skip" if step.status == "SKIPPED" else "step-fail"
            )
            s_text = step.original_text.replace("<", "&lt;")
            s_err = ""
            if step.error:
                s_err = f'<br><small class="err">{step.error[:200]}</small>'
            screenshot_html = ""
            if step.screenshot:
                screenshot_html = f'<img src="data:image/png;base64,{step.screenshot}" style="max-width:200px;margin-top:4px;border:1px solid #ccc;border-radius:3px;"/>'
            cache_icon = "⚡" if step.replayed_from_cache else ""
            step_rows += (
                f'<tr class="{s_class}">'
                f'<td>{step.step_number}</td>'
                f'<td>{step.keyword}</td>'
                f'<td>{s_text}{s_err}</td>'
                f'<td>{cache_icon}{step.status}</td>'
                f'<td>{step.duration_seconds:.1f}s</td>'
                f'<td>{screenshot_html}</td>'
                f'</tr>'
            )

        detail_html = (
            f'<table class="steps"><tr><th>#</th><th>Keyword</th><th>Step</th>'
            f'<th>Status</th><th>Time</th><th></th></tr>{step_rows}</table>'
        )

        errors_html = ""
        if errs:
            items = "".join(f"<li>{e[:200]}</li>" for e in errs)
            errors_html = f'<ul class="errors">{items}</ul>'

        scenario_sections.append(
            f'<details class="{status_class}">'
            f'<summary><span class="status-badge {status_class}">{status}</span> '
            f'{feature} :: {scenario} ({dur:.1f}s)</summary>'
            f'<div class="detail">{detail_html}{errors_html}</div>'
            f'</details>'
        )

    scenarios_html = "\n".join(scenario_sections)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Test Run Report — {run_id}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #f5f6f7; color: #1a1a1a; }}
  .container {{ max-width: 1000px; margin: 0 auto; }}
  h1 {{ margin-bottom: 5px; }}
  .meta {{ color: #666; margin-bottom: 20px; font-size: 0.9em; }}
  .dashboard {{ display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap; }}
  .stat {{ background: white; padding: 16px 24px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center; min-width: 100px; }}
  .stat .value {{ font-size: 2em; font-weight: bold; }}
  .stat .label {{ font-size: 0.85em; color: #666; margin-top: 4px; }}
  .stat.passed .value {{ color: #0f8a00; }}
  .stat.failed .value {{ color: #d13212; }}
  .stat.error .value {{ color: #e67e00; }}
  details {{ background: white; margin-bottom: 8px; border-radius: 6px; box-shadow: 0 1px 2px rgba(0,0,0,0.08); }}
  summary {{ padding: 12px 16px; cursor: pointer; font-weight: 500; }}
  summary:hover {{ background: #f9f9f9; }}
  .detail {{ padding: 12px 16px; border-top: 1px solid #eee; }}
  .status-badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; margin-right: 8px; }}
  .status-badge.passed {{ background: #e6f4e6; color: #0f8a00; }}
  .status-badge.failed {{ background: #fdecea; color: #d13212; }}
  .status-badge.error {{ background: #fff3e0; color: #e67e00; }}
  .steps {{ width: 100%; border-collapse: collapse; font-size: 0.9em; }}
  .steps th {{ background: #f5f5f5; padding: 6px 10px; text-align: left; }}
  .steps td {{ padding: 6px 10px; border-top: 1px solid #eee; }}
  .step-pass {{ }}
  .step-fail {{ background: #fef2f0; }}
  .step-skip {{ background: #f9f9f9; color: #999; }}
  .errors {{ color: #d13212; font-size: 0.9em; }}
  .err {{ color: #d13212; }}
  .overall-passed {{ color: #0f8a00; }}
  .overall-failed {{ color: #d13212; }}
</style>
</head>
<body>
<div class="container">
  <h1>Test Execution Report</h1>
  <div class="meta">Run: {run_id} | {timestamp} | Overall: <strong class="overall-{overall_status.lower()}">{overall_status}</strong></div>
  <div class="dashboard">
    <div class="stat passed"><div class="value">{passed}</div><div class="label">Passed</div></div>
    <div class="stat failed"><div class="value">{failed}</div><div class="label">Failed</div></div>
    <div class="stat error"><div class="value">{errors}</div><div class="label">Errors</div></div>
    <div class="stat"><div class="value">{total}</div><div class="label">Total</div></div>
    <div class="stat"><div class="value">{duration:.1f}s</div><div class="label">Duration</div></div>
  </div>
  <h2>Scenarios</h2>
  {scenarios_html}
</div>
</body>
</html>"""


def write_report(html: str, output_path: Path) -> Path:
    """Write HTML report to file.

    Args:
        html: HTML content
        output_path: Path to write the report

    Returns:
        Path to the written file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path
