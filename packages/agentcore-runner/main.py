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

        if action == "translate":
            return _handle_translate(payload)
        else:
            return _handle_execute(payload)

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
        local_path = f"/tmp/custom_functions_{run_id}.py"
        functions_path = download_file(bucket, key, local_path)
        logger.info(f"Custom functions downloaded: {functions_path}")

    # Execute scenario
    result = execute_scenario_agentcore(
        scenario_data=scenario_data,
        base_url=base_url,
        feature_name=feature_name,
        functions_file=Path(functions_path) if functions_path else None,
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


if __name__ == "__main__":
    app.run()
