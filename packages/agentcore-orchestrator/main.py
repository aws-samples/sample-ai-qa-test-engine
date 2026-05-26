"""
Orchestrator Agent — AgentCore Runtime Entrypoint

Reads test cases from S3, manages translation caching, fans out parallel
invocations to the Test Runner agent, and produces combined reports.

Payload:
{
    "input_bucket": "my-test-cases-bucket",
    "input_prefix": "project-a/tests/",
    "output_bucket": "my-test-results-bucket",
    "output_prefix": "project-a/results",
    "test_runner_arn": "arn:aws:bedrock-agentcore:us-east-1:...:runtime/...",
    "max_concurrency": 10,
    "force_retranslate": false,
    "bedrock_model_id": null
}
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from uuid import uuid4

from bedrock_agentcore.runtime import BedrockAgentCoreApp

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = BedrockAgentCoreApp()


@app.entrypoint
def handler(payload):
    """Orchestrate parallel test execution."""
    from s3_utils import download_string, upload_string, list_objects, get_last_modified
    from invoker import invoke_test_runners
    from reporting import build_summary, build_combined_html

    logger.info("=" * 80)
    logger.info("AI QA Test Engine — Orchestrator Agent")
    logger.info("=" * 80)

    start_time = time.time()

    try:
        # Parse payload
        if isinstance(payload, str):
            payload = json.loads(payload)

        # Handle agentcore invoke wrapping
        if isinstance(payload, dict) and "prompt" in payload and "input_bucket" not in payload:
            prompt_val = payload["prompt"]
            if isinstance(prompt_val, str):
                try:
                    payload = json.loads(prompt_val)
                except json.JSONDecodeError:
                    pass
            elif isinstance(prompt_val, dict):
                payload = prompt_val

        input_bucket = payload.get("input_bucket")
        input_prefix = payload.get("input_prefix", "").rstrip("/") + "/"
        output_bucket = payload.get("output_bucket")
        output_prefix = payload.get("output_prefix", "").rstrip("/")
        test_runner_arn = payload.get("test_runner_arn")
        max_concurrency = payload.get("max_concurrency", 10)
        force_retranslate = payload.get("force_retranslate", False)
        bedrock_model_id = payload.get("bedrock_model_id")

        if not input_bucket:
            raise ValueError("Missing 'input_bucket' in payload")
        if not output_bucket:
            raise ValueError("Missing 'output_bucket' in payload")
        if not test_runner_arn:
            raise ValueError("Missing 'test_runner_arn' in payload")

        # Generate run ID
        run_id = f"run-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:6]}"
        logger.info(f"Run ID: {run_id}")
        logger.info(f"Input: s3://{input_bucket}/{input_prefix}")
        logger.info(f"Output: s3://{output_bucket}/{output_prefix}/{run_id}/")
        logger.info(f"Test Runner: {test_runner_arn}")
        logger.info(f"Max concurrency: {max_concurrency}")

        # Step 1: Load tag-url-mapping.json
        tag_url_map = {}
        tag_map_key = f"{input_prefix}tag-url-mapping.json"
        try:
            tag_map_content = download_string(input_bucket, tag_map_key)
            tag_url_map = json.loads(tag_map_content)
            logger.info(f"Loaded tag-url-mapping: {len(tag_url_map)} mappings")
        except Exception as e:
            logger.warning(f"No tag-url-mapping.json found: {e}")

        # Step 2: Check translation cache
        features_prefix = f"{input_prefix}features/"
        translated_prefix = f"{input_prefix}translated/"

        cache_status = _check_cache(
            input_bucket, features_prefix, translated_prefix, force_retranslate,
            list_objects, get_last_modified,
        )

        if not cache_status:
            raise ValueError(f"No .feature files found in s3://{input_bucket}/{features_prefix}")

        # Step 3: Translate stale features
        _translate_stale(
            input_bucket, cache_status, tag_url_map, translated_prefix,
            test_runner_arn, bedrock_model_id, download_string, upload_string,
        )

        # Step 4: Load translated features and decompose into scenarios
        features = _load_translated(input_bucket, cache_status, download_string)

        # Check for custom functions
        custom_functions_s3 = None
        custom_funcs_key = f"{input_prefix}custom-functions/custom_functions.py"
        try:
            if get_last_modified(input_bucket, custom_funcs_key):
                custom_functions_s3 = {"bucket": input_bucket, "key": custom_funcs_key}
                logger.info(f"Custom functions found: {custom_funcs_key}")
        except Exception:
            pass

        scenarios = _decompose(features, run_id, custom_functions_s3, output_bucket, output_prefix)
        logger.info(f"Total scenarios to execute: {len(scenarios)}")

        # Step 5: Fan out parallel invocations
        results = invoke_test_runners(
            scenarios=scenarios,
            test_runner_arn=test_runner_arn,
            max_concurrency=max_concurrency,
        )

        # Step 6: Generate reports
        summary = build_summary(results, run_id)

        # Download individual scenario HTML reports
        scenario_reports = {}
        for r in results:
            report_key = r.get("report_s3_key")
            if report_key:
                try:
                    html = download_string(output_bucket, report_key)
                    key = f"{r.get('feature_name', '')}_{r.get('scenario_name', '')}"
                    scenario_reports[key] = html
                except Exception:
                    pass

        combined_html = build_combined_html(summary, results, scenario_reports)

        # Step 7: Upload reports to S3
        summary_key = f"{output_prefix}/{run_id}/summary.json"
        report_key = f"{output_prefix}/{run_id}/combined-report.html"

        upload_string(json.dumps(summary, indent=2), output_bucket, summary_key)
        upload_string(combined_html, output_bucket, report_key, content_type="text/html; charset=utf-8")

        logger.info(f"Summary: s3://{output_bucket}/{summary_key}")
        logger.info(f"Report: s3://{output_bucket}/{report_key}")

        duration = time.time() - start_time

        return {
            "status": summary["status"],
            "run_id": run_id,
            "total_scenarios": summary["total_scenarios"],
            "passed": summary["passed"],
            "failed": summary["failed"],
            "errors": summary["errors"],
            "total_duration_seconds": duration,
            "summary_s3_key": summary_key,
            "report_s3_key": report_key,
            "output_location": f"s3://{output_bucket}/{output_prefix}/{run_id}/",
        }

    except Exception as e:
        logger.error(f"Orchestrator failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "ERROR",
            "errors": [str(e)],
            "total_duration_seconds": time.time() - start_time,
        }


def _check_cache(bucket, features_prefix, translated_prefix, force_retranslate, list_objects, get_last_modified):
    """Check which features need (re)translation."""
    feature_files = list_objects(bucket, features_prefix, suffix=".feature")
    logger.info(f"Found {len(feature_files)} .feature files")

    cache_status = {}
    for feat in feature_files:
        feature_key = feat["key"]
        feature_name = os.path.basename(feature_key).replace(".feature", "")
        cached_json_key = f"{translated_prefix}{feature_name}.json"

        needs_translation = force_retranslate
        if not needs_translation:
            cached_modified = get_last_modified(bucket, cached_json_key)
            if cached_modified is None or cached_modified < feat["last_modified"]:
                needs_translation = True

        cache_status[feature_key] = {
            "needs_translation": needs_translation,
            "cached_json_key": cached_json_key,
            "feature_name": feature_name,
        }

    stale = sum(1 for v in cache_status.values() if v["needs_translation"])
    logger.info(f"Cache: {stale} need translation, {len(cache_status) - stale} cached")
    return cache_status


def _translate_stale(bucket, cache_status, tag_url_map, translated_prefix, test_runner_arn, bedrock_model_id, download_string, upload_string):
    """Translate stale features by calling Test Runner's translate action."""
    from invoker import _invoke_runtime

    stale = {k: v for k, v in cache_status.items() if v["needs_translation"]}
    if not stale:
        logger.info("All features cached, no translation needed")
        return

    for feature_key, info in stale.items():
        feature_name = info["feature_name"]
        cached_json_key = info["cached_json_key"]

        logger.info(f"Translating: {feature_name}...")
        feature_content = download_string(bucket, feature_key)

        translate_payload = {
            "action": "translate",
            "feature_content": feature_content,
            "feature_name": f"{feature_name}.feature",
            "tag_url_map": tag_url_map,
        }
        if bedrock_model_id:
            translate_payload["bedrock_model_id"] = bedrock_model_id

        result = _invoke_runtime(test_runner_arn, translate_payload)

        if result.get("status") == "SUCCESS" and "translated" in result:
            translated_json = json.dumps(result["translated"], indent=2)
            upload_string(translated_json, bucket, cached_json_key)
            scenarios_count = len(result["translated"].get("scenarios", []))
            logger.info(f"  ✓ Cached: {feature_name} ({scenarios_count} scenarios)")
        else:
            logger.error(f"  ✗ Translation failed: {result.get('errors', [])}")


def _load_translated(bucket, cache_status, download_string):
    """Load all translated feature JSONs from S3."""
    features = []
    for feature_key, info in cache_status.items():
        try:
            content = download_string(bucket, info["cached_json_key"])
            feature_data = json.loads(content)
            feature_data["_feature_name"] = info["feature_name"]
            features.append(feature_data)
        except Exception as e:
            logger.error(f"Failed to load {info['cached_json_key']}: {e}")
    return features


def _decompose(features, run_id, custom_functions_s3, output_bucket, output_prefix):
    """Break features into individual scenario payloads."""
    import re
    payloads = []

    for feature_data in features:
        feature_name = feature_data.get("_feature_name", "unknown")
        base_url = feature_data.get("base_url", "")

        for idx, scenario in enumerate(feature_data.get("scenarios", [])):
            scenario_name = scenario.get("name", f"scenario_{idx}")
            tags = scenario.get("tags", [])

            # Generate canonical scenario ID
            scenario_id = _make_scenario_id(feature_name, scenario_name, tags)

            payload = {
                "scenario": scenario,
                "base_url": base_url,
                "feature_name": feature_name,
                "scenario_name": scenario_name,
                "scenario_id": scenario_id,
                "run_id": run_id,
            }

            if custom_functions_s3:
                payload["custom_functions_s3"] = custom_functions_s3

            payload["output_s3"] = {
                "bucket": output_bucket,
                "prefix": f"{output_prefix}/{run_id}/scenarios/{scenario_id}",
            }

            payloads.append(payload)

    logger.info(f"Decomposed {len(features)} features into {len(payloads)} scenarios")
    return payloads


def _make_scenario_id(feature_name, scenario_name, tags=None):
    """Generate canonical scenario ID (same logic as core scenario_id module)."""
    import re
    # Check for @id:XXX tag
    if tags:
        for tag in tags:
            tag_clean = tag.lstrip("@")
            if tag_clean.startswith("id:") or tag_clean.startswith("id="):
                val = tag_clean[3:]
                return re.sub(r"[^\w]+", "_", val).strip("_").lower()

    # Fallback: feature__scenario slug
    def slugify(text, max_len=0):
        s = re.sub(r"[^\w]+", "_", text).strip("_").lower()
        return s[:max_len].rstrip("_") if max_len else s

    parts = [slugify(feature_name, 30), slugify(scenario_name, 40)]
    return "__".join(parts)


if __name__ == "__main__":
    app.run()
