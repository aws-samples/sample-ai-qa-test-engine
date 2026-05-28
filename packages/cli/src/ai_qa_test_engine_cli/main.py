"""AI QA Test Engine — Command Line Interface.

Provides `run` and `translate` commands for local test execution.
Replaces the pytest-based runner from test_translator.
"""

import sys
from pathlib import Path

import click

from ai_qa_test_engine.config import AppConfig
from ai_qa_test_engine.services import TestExecutionService, TranslationService


@click.group()
@click.version_option(version="0.1.0", prog_name="ai-qa-test")
def cli():
    """AI QA Test Engine — AI-powered browser test automation."""
    pass


@cli.command()
@click.option("--feature-dir", type=click.Path(exists=True, path_type=Path), help="Directory containing .feature files")
@click.option("--output-dir", type=click.Path(path_type=Path), help="Directory for reports")
@click.option("--browser-mode", type=click.Choice(["headed", "headless"]), default=None, help="Browser mode")
@click.option("--stop-on-failure", is_flag=True, default=False, help="Stop and keep browser open on failure")
@click.option("--force-translate", is_flag=True, default=False, help="Force re-translation (bypass cache)")
@click.option("--video", is_flag=True, default=False, help="Enable video recording of browser session")
@click.option("--no-cache", is_flag=True, default=False, help="Disable trajectory replay cache (always use Nova Act)")
@click.option("--trajectory-strict", is_flag=True, default=False, help="Strict trajectory validation (fail on mismatch)")
@click.option("--tags", type=str, default=None, help="Filter scenarios by tag (e.g., '@smoke', 'not @slow', '@id:TC-001')")
@click.option("--tag", multiple=True, help="Tag-to-URL mapping (key=url)")
@click.option("--functions-file", multiple=True, type=click.Path(exists=True, path_type=Path), help="Custom functions file or directory (can specify multiple)")
@click.option("--env-file", type=click.Path(exists=True, path_type=Path), default=None, help="Path to .env file")
@click.option("--tag-url-map-file", type=click.Path(exists=True, path_type=Path), default=None, help="Path to tag-url-mapping.json")
@click.option("--common-steps-dir", type=click.Path(exists=True, path_type=Path), default=None, help="Directory containing .steps files for @include")
@click.option("--variables-file", type=click.Path(exists=True, path_type=Path), default=None, help="JSON file with input variables (pre-loaded as ${name})")
def run(
    feature_dir,
    output_dir,
    browser_mode,
    stop_on_failure,
    force_translate,
    video,
    no_cache,
    trajectory_strict,
    tags,
    tag,
    functions_file,
    env_file,
    tag_url_map_file,
    common_steps_dir,
    variables_file,
):
    """Execute tests from Gherkin feature files.

    Translates .feature files (with caching), then executes all scenarios
    using Nova Act browser automation. Generates HTML reports.

    Examples:

        ai-qa-test run --feature-dir ./features/

        ai-qa-test run --feature-dir ./features/ --browser-mode headless

        ai-qa-test run --feature-dir ./features/ --force-translate
    """
    # Build config from CLI args (overrides env/.env)
    config_kwargs = {}

    if feature_dir:
        config_kwargs["feature_dir"] = feature_dir
    if output_dir:
        config_kwargs["report_dir"] = output_dir
    if browser_mode:
        config_kwargs["browser_mode"] = browser_mode
    if stop_on_failure:
        config_kwargs["stop_on_failure"] = True
    if force_translate:
        config_kwargs["force_translate"] = True
    if video:
        config_kwargs["enable_video_recording"] = True
    if no_cache:
        config_kwargs["no_cache"] = True
    if trajectory_strict:
        config_kwargs["trajectory_strict"] = True
    if tags:
        config_kwargs["tag_filter"] = tags
    if functions_file:
        # First path goes into config (used by service for primary loading)
        config_kwargs["custom_functions_file"] = functions_file[0]
    if tag_url_map_file:
        config_kwargs["tag_url_map_file"] = tag_url_map_file
    if common_steps_dir:
        config_kwargs["common_steps_dir"] = common_steps_dir
    if variables_file:
        config_kwargs["input_variables_file"] = variables_file

    # Handle --tag key=value pairs
    if tag:
        import os
        for entry in tag:
            if "=" not in entry:
                click.echo(f"Error: Invalid tag format '{entry}', expected key=url", err=True)
                sys.exit(1)
            key, url = entry.split("=", 1)
            os.environ[f"GHERKIN_TAG_{key.upper()}"] = url

    try:
        config = AppConfig(_env_file=env_file, **config_kwargs)
    except Exception as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)

    # Run
    service = TestExecutionService(config)

    # Load additional function files/dirs beyond the first
    if len(functions_file) > 1:
        service.extra_function_paths = list(functions_file[1:])

    def log_callback(msg: str, level: str = "info"):
        if level == "error":
            click.echo(click.style(msg, fg="red"))
        elif level == "warning":
            click.echo(click.style(msg, fg="yellow"))
        else:
            click.echo(msg)

    summary = service.run(log_callback=log_callback)

    # Exit code
    sys.exit(0 if summary.status == "PASSED" else 1)


@cli.command()
@click.option("--feature-dir", type=click.Path(exists=True, path_type=Path), help="Directory containing .feature files")
@click.option("--output-dir", type=click.Path(path_type=Path), help="Directory for translated JSON")
@click.option("--tag", multiple=True, help="Tag-to-URL mapping (key=url)")
@click.option("--model-id", type=str, default=None, help="Bedrock model ID for translation")
@click.option("--force", is_flag=True, default=False, help="Force re-translation (bypass cache)")
@click.option("--env-file", type=click.Path(exists=True, path_type=Path), default=None, help="Path to .env file")
@click.option("--tag-url-map-file", type=click.Path(exists=True, path_type=Path), default=None, help="Path to tag-url-mapping.json")
def translate(feature_dir, output_dir, tag, model_id, force, env_file, tag_url_map_file):
    """Translate Gherkin feature files to JSON without executing.

    Useful for pre-translating features to commit to git cache.

    Examples:

        ai-qa-test translate --feature-dir ./features/

        ai-qa-test translate --feature-dir ./features/ --force

        ai-qa-test translate --feature-dir ./features/ --model-id us.amazon.nova-2-lite-v1:0
    """
    config_kwargs = {}

    if feature_dir:
        config_kwargs["feature_dir"] = feature_dir
    if output_dir:
        config_kwargs["cache_dir"] = output_dir
        config_kwargs["translated_feature_dir"] = output_dir
    if model_id:
        config_kwargs["bedrock_model_id"] = model_id
    if force:
        config_kwargs["force_translate"] = True
    if tag_url_map_file:
        config_kwargs["tag_url_map_file"] = tag_url_map_file

    # Handle --tag key=value pairs
    if tag:
        import os
        for entry in tag:
            if "=" not in entry:
                click.echo(f"Error: Invalid tag format '{entry}', expected key=url", err=True)
                sys.exit(1)
            key, url = entry.split("=", 1)
            os.environ[f"GHERKIN_TAG_{key.upper()}"] = url

    try:
        config = AppConfig(_env_file=env_file, **config_kwargs)
    except Exception as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)

    service = TranslationService(config)

    def log_callback(msg: str, level: str = "info"):
        if level == "error":
            click.echo(click.style(msg, fg="red"))
        else:
            click.echo(msg)

    try:
        json_files = service.translate(log_callback=log_callback)
        click.echo(f"\n✓ Translation complete: {len(json_files)} feature(s)")
    except Exception as e:
        click.echo(f"\n✗ Translation failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--feature-dir", type=click.Path(exists=True, path_type=Path), help="Directory containing .feature files")
@click.option("--functions-file", type=click.Path(exists=True, path_type=Path), help="Custom functions Python file")
@click.option("--tag-url-map-file", type=click.Path(exists=True, path_type=Path), default=None, help="Path to tag-url-mapping.json")
@click.option("--env-file", type=click.Path(exists=True, path_type=Path), default=None, help="Path to .env file")
@click.option("--force-translate", is_flag=True, default=False, help="Force re-translation before validating")
def validate(feature_dir, functions_file, tag_url_map_file, env_file, force_translate):
    """Validate feature files without executing (check variables + functions).

    Translates features (if needed), then checks:
    - All ${variable} references point to earlier extraction/function steps
    - All function_call steps reference functions that exist in the loaded modules

    No browser is launched. Fast pre-flight check.

    Examples:

        ai-qa-test validate --feature-dir ./features/ --functions-file ./custom_functions.py

        ai-qa-test validate --feature-dir ./features/ --force-translate
    """
    import json

    from ai_qa_test_engine.function_registry import FunctionRegistry
    from ai_qa_test_engine.models import Feature

    config_kwargs = {}
    if feature_dir:
        config_kwargs["feature_dir"] = feature_dir
    if functions_file:
        config_kwargs["custom_functions_file"] = functions_file
    if tag_url_map_file:
        config_kwargs["tag_url_map_file"] = tag_url_map_file
    if force_translate:
        config_kwargs["force_translate"] = True

    try:
        config = AppConfig(_env_file=env_file, **config_kwargs)
    except Exception as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)

    # Step 1: Translate (uses cache)
    click.echo("📝 Translating features...")
    service = TranslationService(config)
    try:
        json_files = service.translate()
    except Exception as e:
        click.echo(f"✗ Translation failed: {e}", err=True)
        sys.exit(1)

    if not json_files:
        click.echo("No features found to validate.")
        sys.exit(1)

    # Step 2: Load translated JSON and validate models (variable references)
    click.echo("\n🔍 Validating variable references...")
    var_errors = 0
    for json_file in json_files:
        if not json_file.exists():
            continue
        try:
            with open(json_file) as f:
                data = json.load(f)
            Feature.model_validate(data)  # Pydantic validates variable refs
            click.echo(f"  ✓ {json_file.name}: variable references OK")
        except Exception as e:
            click.echo(click.style(f"  ✗ {json_file.name}: {e}", fg="red"))
            var_errors += 1

    # Step 3: Load functions and validate function references
    click.echo("\n🔍 Validating function references...")
    functions = FunctionRegistry()
    bundled_dir = Path(__file__).parent / "../../core/src/ai_qa_test_engine/functions"
    # Use the actual bundled dir from the installed package
    import ai_qa_test_engine
    pkg_dir = Path(ai_qa_test_engine.__file__).parent / "functions"
    functions.load_bundled(pkg_dir)

    user_funcs = config.resolve_custom_functions_file()
    if user_funcs and user_funcs.exists():
        functions.load_from_file(user_funcs)
        click.echo(f"  Loaded user functions: {user_funcs.name}")

    func_errors = 0
    for json_file in json_files:
        if not json_file.exists():
            continue
        with open(json_file) as f:
            data = json.load(f)
        errors = functions.validate_feature(data)
        if errors:
            for err in errors:
                click.echo(click.style(f"  ✗ {json_file.name}: {err}", fg="red"))
            func_errors += len(errors)
        else:
            click.echo(f"  ✓ {json_file.name}: function references OK")

    # Summary
    total_errors = var_errors + func_errors
    click.echo(f"\n{'=' * 50}")
    if total_errors == 0:
        click.echo(click.style("✓ All validations passed!", fg="green"))
        sys.exit(0)
    else:
        click.echo(click.style(f"✗ {total_errors} validation error(s) found", fg="red"))
        sys.exit(1)


if __name__ == "__main__":
    cli()
