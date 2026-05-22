"""Report generator — combined HTML dashboard + summary JSON."""

import logging
import re
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def build_summary(results: list[dict], run_id: str) -> dict:
    """Aggregate results into a summary dict."""
    total = len(results)
    passed = sum(1 for r in results if r.get("status") == "PASSED")
    failed = sum(1 for r in results if r.get("status") == "FAILED")
    errors = sum(1 for r in results if r.get("status") == "ERROR")
    total_duration = sum(r.get("duration_seconds", 0) for r in results)

    return {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_scenarios": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "total_duration_seconds": total_duration,
        "status": "PASSED" if failed == 0 and errors == 0 else "FAILED",
        "scenarios": [
            {
                "feature_name": r.get("feature_name", "unknown"),
                "scenario_name": r.get("scenario_name", "unknown"),
                "status": r.get("status", "UNKNOWN"),
                "duration_seconds": r.get("duration_seconds", 0),
                "steps_total": r.get("steps_total", 0),
                "steps_passed": r.get("steps_passed", 0),
                "steps_failed": r.get("steps_failed", 0),
                "errors": r.get("errors", []),
            }
            for r in results
        ],
    }


def build_combined_html(summary: dict, results: list[dict], scenario_reports: dict = None) -> str:
    """Generate combined HTML report with dashboard + collapsible scenario details."""
    if scenario_reports is None:
        scenario_reports = {}

    run_id = summary["run_id"]
    total = summary["total_scenarios"]
    passed = summary["passed"]
    failed = summary["failed"]
    errors = summary["errors"]
    duration = summary["total_duration_seconds"]
    overall_status = summary["status"]
    timestamp = summary["timestamp"]

    # Build scenario sections
    scenario_sections = []
    for r in results:
        status = r.get("status", "UNKNOWN")
        feature = r.get("feature_name", "unknown")
        scenario = r.get("scenario_name", "unknown")
        dur = r.get("duration_seconds", 0)
        step_results = r.get("step_results", [])
        errs = r.get("errors", [])

        status_class = {"PASSED": "passed", "FAILED": "failed", "ERROR": "error"}.get(status, "error")

        # Embed Test Runner report or build step table
        detail_html = ""
        scenario_key = f"{feature}_{scenario}"

        if scenario_key in scenario_reports:
            tr_report = scenario_reports[scenario_key]
            body_match = re.search(r'<body[^>]*>(.*)</body>', tr_report, re.DOTALL)
            if body_match:
                detail_html = f'<div class="embedded-report">{body_match.group(1)}</div>'
            else:
                detail_html = f'<div class="embedded-report">{tr_report}</div>'
        elif step_results:
            step_rows = ""
            for step in step_results:
                s_class = "step-pass" if step.get("status") == "PASSED" else "step-fail"
                s_text = step.get("original_text", "").replace("<", "&lt;")
                s_err = ""
                if step.get("error"):
                    s_err = f'<br><small class="err">{step["error"][:100]}</small>'
                step_rows += f'<tr class="{s_class}"><td>{step.get("number","")}</td><td>{step.get("keyword","")}</td><td>{s_text}{s_err}</td><td>{step.get("status","")}</td><td>{step.get("duration_seconds",0):.1f}s</td></tr>'
            detail_html = f'<table class="steps"><tr><th>#</th><th>Keyword</th><th>Step</th><th>Status</th><th>Time</th></tr>{step_rows}</table>'

        errors_html = ""
        if errs:
            items = "".join(f"<li>{e[:200]}</li>" for e in errs)
            errors_html = f'<ul class="errors">{items}</ul>'

        scenario_sections.append(
            f'<details class="{status_class}">'
            f'<summary><span class="status-badge {status_class}">{status}</span> {feature} :: {scenario} ({dur:.1f}s)</summary>'
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
  .detail {{ padding: 12px 16px; border-top: 1px solid #eee; }}
  .status-badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; margin-right: 8px; }}
  .status-badge.passed {{ background: #e6f4e6; color: #0f8a00; }}
  .status-badge.failed {{ background: #fdecea; color: #d13212; }}
  .status-badge.error {{ background: #fff3e0; color: #e67e00; }}
  .steps {{ width: 100%; border-collapse: collapse; font-size: 0.9em; }}
  .steps th {{ background: #f5f5f5; padding: 6px 10px; text-align: left; }}
  .steps td {{ padding: 6px 10px; border-top: 1px solid #eee; }}
  .step-fail {{ background: #fef2f0; }}
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
