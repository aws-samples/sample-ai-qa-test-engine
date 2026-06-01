"""
Test Runner Agent — AgentCore Runtime Entrypoint

Executes a single test scenario using ai-qa-test-engine core
with AgentCore browser_session for remote browser automation.

Payload (execute):
{
    "scenario": { ... TestScenario JSON ... },
    "base_url": "https://...",
    "feature_name": "destination_selection",
    "scenario_name": "view_destination_details",
    "custom_functions_s3": {
        "bucket": "my-bucket",
        "key": "path/to/custom_functions.py"
    },
    "output_s3": {
        "bucket": "my-results-bucket",
        "prefix": "results/run-id/scenarios/feature_scenario"
    },
    "run_id": "run-20260520-170000"
}

Payload (translate):
{
    "action": "translate",
    "feature_content": "Feature: ...",
    "feature_name": "login.feature",
    "tag_url_map": {"@myapp": "https://..."},
    "bedrock_model_id": null
}
"""

import json
import logging
import os
import time
from pathlib import Path

from bedrock_agentcore.runtime import BedrockAgentCoreApp

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = BedrockAgentCoreApp()


@app.entrypoint
def handler(payload):
    """Handle requests — supports 'execute' (default) and 'translate' actions."""
    logger.info("=" * 80)
    logger.info("AI QA Test Engine — Test Runner Agent")
    logger.info("=" * 80)

    try:
        # Parse payload
        if isinstance(payload, str):
            payload = json.loads(payload)

        # Handle agentcore invoke wrapping: {"prompt": "<json-string>"}
        if isinstance(payload, dict) and "prompt" in payload and "scenario" not in payload and "action" not in payload:
            prompt_val = payload["prompt"]
            if isinstance(prompt_val, str):
                try:
                    payload = json.loads(prompt_val)
                except json.JSONDecodeError:
                    pass
            elif isinstance(prompt_val, dict):
                payload = prompt_val

        # Route by action
        action = payload.get("action", "execute")

        # Phase 1: signal HealthyBusy to the platform so the idle timeout
        # doesn't kill the session during long-running handlers (sleeps,
        # browser automation, custom functions). The handler still blocks
        # synchronously - this only changes /ping status.
        task_id = app.add_async_task(f"handler_{action}")
        logger.info(f"BUSY: marked task busy, action={action}, task_id={task_id}")
        try:
            if action == "translate":
                return _handle_translate(payload)
            else:
                return _handle_execute(payload)
        finally:
            app.complete_async_task(task_id)
            logger.info(f"DONE: marked task complete, task_id={task_id}")

    except Exception as e:
        logger.error(f"Handler failed: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "ERROR", "errors": [str(e)]}


def _handle_translate(payload):
    """Translate a .feature file content to JSON using ai-qa-test-engine translator."""
    import tempfile
    import shutil

    from ai_qa_test_engine.translator import translate_all_features

    logger.info("Action: TRANSLATE")

    feature_content = payload.get("feature_content")
    feature_name = payload.get("feature_name", "input.feature")
    tag_url_map = payload.get("tag_url_map", {})
    bedrock_model_id = payload.get("bedrock_model_id")

    if not feature_content:
        raise ValueError("Missing 'feature_content' in payload")

    # Write feature to temp file
    tmp_input = tempfile.mkdtemp(prefix="translate_in_")
    tmp_output = tempfile.mkdtemp(prefix="translate_out_")

    try:
        if not feature_name.endswith(".feature"):
            feature_name += ".feature"

        input_path = os.path.join(tmp_input, feature_name)
        with open(input_path, "w") as f:
            f.write(feature_content)

        # Translate
        translated = translate_all_features(
            input_dir=Path(tmp_input),
            output_dir=Path(tmp_output),
            tag_url_map=tag_url_map,
            bedrock_model_id=bedrock_model_id,
        )

        if not translated:
            raise RuntimeError("Translation produced no output")

        # Return the first translated feature
        result_data = translated[0] if isinstance(translated, list) else translated

        logger.info(f"Translation complete: {len(result_data.get('scenarios', []))} scenarios")
        return {
            "status": "SUCCESS",
            "action": "translate",
            "feature_name": feature_name,
            "translated": result_data,
        }

    finally:
        shutil.rmtree(tmp_input, ignore_errors=True)
        shutil.rmtree(tmp_output, ignore_errors=True)


def _handle_execute(payload):
    """Execute a single test scenario using ai-qa-test-engine with AgentCore browser."""
    from s3_utils import download_file, upload_string
    from scenario_executor import execute_scenario_agentcore

    logger.info("Action: EXECUTE")

    scenario_data = payload.get("scenario")
    base_url = payload.get("base_url")
    feature_name = payload.get("feature_name", "unknown_feature")
    scenario_name = payload.get("scenario_name", "unknown_scenario")
    custom_functions_s3 = payload.get("custom_functions_s3")
    input_variables_s3 = payload.get("input_variables_s3")
    scenario_id_for_vars = payload.get("scenario_id_for_vars")
    output_s3 = payload.get("output_s3")
    run_id = payload.get("run_id", "manual")

    if not scenario_data:
        raise ValueError("Missing 'scenario' in payload")
    if not base_url:
        raise ValueError("Missing 'base_url' in payload")

    logger.info(f"Feature: {feature_name}")
    logger.info(f"Scenario: {scenario_name}")
    logger.info(f"Base URL: {base_url}")
    logger.info(f"Run ID: {run_id}")

    # Download custom functions from S3 if specified
    functions_path = None
    if custom_functions_s3:
        bucket = custom_functions_s3["bucket"]
        key = custom_functions_s3["key"]
        local_path = f"/tmp/custom_functions_{run_id}.py"  # nosec B108 — isolated microVM, /tmp is only writable fs
        functions_path = download_file(bucket, key, local_path)
        logger.info(f"Custom functions downloaded: {functions_path}")

    # Load input variables from S3 if specified
    input_variables = {}
    if input_variables_s3:
        input_variables = _load_input_variables(input_variables_s3, scenario_id_for_vars, feature_name)
        if input_variables:
            logger.info(f"Input variables loaded: {list(input_variables.keys())}")

    # Download data files (Excel, CSV) from S3 if specified
    data_files_s3 = payload.get("data_files_s3")
    data_dir = None
    if data_files_s3:
        data_dir = _download_data_files(data_files_s3)
        if data_dir:
            logger.info(f"Data files downloaded to: {data_dir}")

    # Execute scenario
    result = execute_scenario_agentcore(
        scenario_data=scenario_data,
        base_url=base_url,
        feature_name=feature_name,
        functions_file=Path(functions_path) if functions_path else None,
        input_variables=input_variables,
        data_dir=Path(data_dir) if data_dir else None,
    )

    # Add metadata
    result["feature_name"] = feature_name
    result["run_id"] = run_id

    # Upload results to S3
    if output_s3:
        output_bucket = output_s3["bucket"]
        output_prefix = output_s3["prefix"]

        # Upload result JSON
        result_key = f"{output_prefix}/result.json"
        upload_string(
            json.dumps(result, indent=2, default=str),
            output_bucket,
            result_key,
        )
        result["result_s3_key"] = result_key

        # Generate and upload HTML report
        html_report = f"<html><body><h1>{feature_name}</h1><pre>{json.dumps(result, indent=2, default=str)}</pre></body></html>"
        report_key = f"{output_prefix}/report.html"
        upload_string(html_report, output_bucket, report_key, content_type="text/html; charset=utf-8")
        result["report_s3_key"] = report_key

        logger.info(f"Results uploaded to s3://{output_bucket}/{output_prefix}/")

    # Clean up
    if functions_path:
        try:
            os.remove(functions_path)
        except OSError:
            pass

    logger.info(f"Scenario complete: {result['status']}")
    return result


def _download_data_files(data_files_s3: dict) -> str:
    """Download data files (Excel, CSV) from S3 to a local temp directory.

    Returns the local directory path where files were downloaded.
    The scenario executor should use this as the working directory for
    resolving relative file paths (e.g., 'TestData.xlsx').
    """
    from s3_utils import download_file
    import tempfile

    data_dir = tempfile.mkdtemp(prefix="data_files_")
    bucket = data_files_s3["bucket"]

    for file_info in data_files_s3.get("files", []):
        key = file_info["key"]
        filename = file_info["filename"]
        local_path = os.path.join(data_dir, filename)
        try:
            download_file(bucket, key, local_path)
            logger.info(f"  Downloaded: {filename}")
        except Exception as e:
            logger.warning(f"  Failed to download {filename}: {e}")

    return data_dir


def _load_input_variables(input_variables_s3: dict, scenario_id: str, feature_name: str) -> dict:
    """Load input variables from S3 for a specific scenario.

    Supports two layouts:
    1. Directory with per-scenario files: variables/_global.json + variables/<scenario_id>.json
    2. Single file: variables.json (flat dict applied to all scenarios)

    Merge order: _global.json + <feature_name>.json + <scenario_id>.json (most specific wins)
    """
    from s3_utils import download_file
    import json as _json

    variables = {}

    if "prefix" in input_variables_s3:
        # Directory layout: download _global.json + scenario-specific file
        bucket = input_variables_s3["bucket"]
        prefix = input_variables_s3["prefix"]

        # Load _global.json
        try:
            global_path = f"/tmp/vars_global_{scenario_id}.json"  # nosec B108 — isolated microVM
            download_file(bucket, f"{prefix}_global.json", global_path)
            with open(global_path) as f:
                variables.update(_json.load(f))
            os.remove(global_path)
        except Exception:
            pass

        # Load feature-level file
        try:
            feat_path = f"/tmp/vars_feat_{scenario_id}.json"  # nosec B108 — isolated microVM
            download_file(bucket, f"{prefix}{feature_name}.json", feat_path)
            with open(feat_path) as f:
                variables.update(_json.load(f))
            os.remove(feat_path)
        except Exception:
            pass

        # Load scenario-specific file
        if scenario_id:
            try:
                scen_path = f"/tmp/vars_scen_{scenario_id}.json"  # nosec B108 — isolated microVM
                download_file(bucket, f"{prefix}{scenario_id}.json", scen_path)
                with open(scen_path) as f:
                    variables.update(_json.load(f))
                os.remove(scen_path)
            except Exception:
                pass

    elif "key" in input_variables_s3:
        # Single file layout: download and apply to all
        bucket = input_variables_s3["bucket"]
        key = input_variables_s3["key"]
        try:
            local_path = f"/tmp/vars_{scenario_id}.json"  # nosec B108 — isolated microVM
            download_file(bucket, key, local_path)
            with open(local_path) as f:
                variables = _json.load(f)
            os.remove(local_path)
        except Exception:
            pass

    return variables


if __name__ == "__main__":
    app.run()
