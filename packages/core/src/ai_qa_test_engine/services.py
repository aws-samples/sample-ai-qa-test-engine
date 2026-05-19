"""Service orchestration layer.

Provides TestExecutionService and TranslationService that coordinate
core components into complete pipelines. Replaces the pytest conftest.py
orchestration from test_translator.
"""

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional
from uuid import uuid4

from ai_qa_test_engine.cache import LocalCacheManager
from ai_qa_test_engine.config import AppConfig
from ai_qa_test_engine.executor import execute_scenario
from ai_qa_test_engine.function_registry import FunctionRegistry
from ai_qa_test_engine.models import Feature, RunSummary, ScenarioResult
from ai_qa_test_engine.reporter import (
    generate_combined_report,
    generate_scenario_html,
    write_report,
)
from ai_qa_test_engine.translator import translate_all_features


class TranslationService:
    """Orchestrates the translation pipeline: discover → parse → translate → cache."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.cache = LocalCacheManager(config.resolve_cache_dir())

    def translate(
        self,
        log_callback: Optional[Callable[[str, str], None]] = None,
    ) -> list[Path]:
        """Translate all feature files, using cache when possible.

        Args:
            log_callback: Optional callback for progress logging

        Returns:
            List of paths to translated JSON files (cached or freshly translated)
        """

        def log(msg: str, level: str = "info"):
            if log_callback:
                log_callback(msg, level)
            else:
                print(f"[{level.upper()}] {msg}")

        feature_dir = self.config.resolve_feature_dir()
        cache_dir = self.config.resolve_cache_dir()
        tag_url_map = self.config.get_tag_url_mapping()

        # Support both directory and single file
        if feature_dir.is_file():
            feature_files = [feature_dir]
            feature_dir = feature_dir.parent
        else:
            feature_files = sorted(feature_dir.glob("*.feature"))
        if not feature_files:
            log(f"No .feature files found in {feature_dir}", "warning")
            return []

        log(f"Found {len(feature_files)} .feature file(s) in {feature_dir}")

        # Check cache for each file
        stale_files = []
        fresh_files = []

        for f in feature_files:
            if self.config.force_translate or self.cache.is_stale(f):
                stale_files.append(f)
            else:
                fresh_files.append(f)
                log(f"  ✓ Cached (fresh): {f.name}")

        if not stale_files:
            log("All features are cached, no translation needed")
            return [self.cache._json_path(f) for f in feature_files]

        log(f"Translating {len(stale_files)} stale feature(s)...")

        # Translate stale files
        translated = translate_all_features(
            input_dir=feature_dir,
            output_dir=cache_dir,
            tag_url_map=tag_url_map,
            bedrock_model_id=self.config.bedrock_model_id,
        )

        # Update cache hashes for translated files
        for f in stale_files:
            json_path = cache_dir / f"{f.stem}.json"
            if json_path.exists():
                # Read the translated data and store with hash
                with open(json_path) as jf:
                    data = json.load(jf)
                self.cache.put(f, data)

        return [self.cache._json_path(f) for f in feature_files]


class TestExecutionService:
    """Orchestrates the full test pipeline: translate → validate → execute → report."""

    def __init__(self, config: AppConfig):
        self.config = config

    def run(
        self,
        log_callback: Optional[Callable[[str, str], None]] = None,
    ) -> RunSummary:
        """Execute the full test pipeline.

        Args:
            log_callback: Optional callback for progress logging

        Returns:
            RunSummary with all results
        """

        def log(msg: str, level: str = "info"):
            if log_callback:
                log_callback(msg, level)
            else:
                print(f"[{level.upper()}] {msg}")

        start_time = time.time()
        run_id = f"run-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:6]}"

        log(f"{'=' * 70}")
        log(f"AI QA Test Engine — Run {run_id}")
        log(f"{'=' * 70}")

        # Step 1: Translate (with caching)
        log("\n📝 Step 1: Translation")
        translation_service = TranslationService(self.config)
        json_files = translation_service.translate(log_callback=log_callback)

        if not json_files:
            return RunSummary(
                run_id=run_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                total_scenarios=0,
                passed=0,
                failed=0,
                errors=0,
                total_duration_seconds=time.time() - start_time,
                status="FAILED",
            )

        # Step 2: Load translated features
        log("\n📂 Step 2: Loading features")
        features: list[tuple[str, Feature]] = []
        for json_file in json_files:
            if not json_file.exists():
                continue
            with open(json_file) as f:
                data = json.load(f)
            feature = Feature.model_validate(data)
            features.append((json_file.stem, feature))
            log(f"  Loaded: {feature.name} ({len(feature.scenarios)} scenarios)")

        # Step 3: Load and validate functions
        log("\n🔧 Step 3: Loading functions")
        functions = FunctionRegistry()

        # Load bundled functions
        bundled_dir = Path(__file__).parent / "functions"
        functions.load_bundled(bundled_dir)

        # Load user functions
        user_funcs_path = self.config.resolve_custom_functions_file()
        if user_funcs_path and user_funcs_path.exists():
            functions.load_from_file(user_funcs_path)
            log(f"  Loaded user functions: {user_funcs_path.name}")

        # Validate function references
        for feature_name, feature in features:
            errors = functions.validate_feature(feature.model_dump())
            if errors:
                for err in errors:
                    log(f"  ✗ {err}", "error")
                raise RuntimeError(f"Function validation failed:\n" + "\n".join(errors))

        log("  ✓ All function references valid")

        # Step 4: Execute scenarios
        log("\n🚀 Step 4: Executing scenarios")
        all_results: list[ScenarioResult] = []

        for feature_name, feature in features:
            for scenario in feature.scenarios:
                result = execute_scenario(
                    scenario=scenario,
                    base_url=feature.base_url,
                    feature_name=feature_name,
                    config=self.config,
                    functions=functions,
                    log_callback=log_callback,
                )
                all_results.append(result)

                # Save extracted variables if any
                if result.extracted_variables:
                    self._save_extracted_variables(result, feature_name)

        # Step 5: Generate reports
        log("\n📊 Step 5: Generating reports")
        duration = time.time() - start_time

        summary = RunSummary(
            run_id=run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_scenarios=len(all_results),
            passed=sum(1 for r in all_results if r.status == "PASSED"),
            failed=sum(1 for r in all_results if r.status == "FAILED"),
            errors=sum(1 for r in all_results if r.status == "ERROR"),
            total_duration_seconds=duration,
            status="PASSED" if all(r.status == "PASSED" for r in all_results) else "FAILED",
            scenarios=all_results,
        )

        # Write combined report
        report_dir = self.config.resolve_report_dir()
        report_html = generate_combined_report(summary, all_results)
        report_path = report_dir / "report.html"
        write_report(report_html, report_path)
        log(f"  Report: {report_path}")

        # Write JSON summary
        summary_path = report_dir / "summary.json"
        summary_dict = {
            "run_id": summary.run_id,
            "timestamp": summary.timestamp,
            "total_scenarios": summary.total_scenarios,
            "passed": summary.passed,
            "failed": summary.failed,
            "errors": summary.errors,
            "total_duration_seconds": summary.total_duration_seconds,
            "status": summary.status,
        }
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        with open(summary_path, "w") as f:
            json.dump(summary_dict, f, indent=2)

        # Print summary
        log(f"\n{'=' * 70}")
        log(f"Run Complete: {summary.status}")
        log(f"  Total: {summary.total_scenarios} | Passed: {summary.passed} | "
            f"Failed: {summary.failed} | Errors: {summary.errors}")
        log(f"  Duration: {duration:.2f}s")
        log(f"  Report: {report_path}")
        log(f"{'=' * 70}")

        return summary

    def _save_extracted_variables(self, result: ScenarioResult, feature_name: str) -> None:
        """Save extracted variables to JSON file."""
        output_dir = self.config.resolve_extracted_variables_dir()
        output_dir.mkdir(parents=True, exist_ok=True)

        safe_name = re.sub(r"[^\w\s-]", "", result.scenario_name)
        safe_name = re.sub(r"[-\s]+", "_", safe_name).lower()

        filepath = output_dir / f"{safe_name}.json"
        output_data = {
            "feature": feature_name,
            "scenario": result.scenario_name,
            "variables": result.extracted_variables,
        }

        with open(filepath, "w") as f:
            json.dump(output_data, f, indent=2, default=str)
