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
@click.option("--from-step", type=int, default=None, help="Resume from step N")
@click.option("--force-translate", is_flag=True, default=False, help="Force re-translation (bypass cache)")
@click.option("--tag", multiple=True, help="Tag-to-URL mapping (key=url)")
@click.option("--functions-file", type=click.Path(exists=True, path_type=Path), help="Custom functions Python file")
@click.option("--env-file", type=click.Path(exists=True, path_type=Path), default=None, help="Path to .env file")
@click.option("--tag-url-map-file", type=click.Path(exists=True, path_type=Path), default=None, help="Path to tag-url-mapping.json")
@click.option("--common-steps-dir", type=click.Path(exists=True, path_type=Path), default=None, help="Directory containing .steps files for @include")
def run(
    feature_dir,
    output_dir,
    browser_mode,
    stop_on_failure,
    from_step,
    force_translate,
    tag,
    functions_file,
    env_file,
    tag_url_map_file,
    common_steps_dir,
):
    """Execute tests from Gherkin feature files.

    Translates .feature files (with caching), then executes all scenarios
    using Nova Act browser automation. Generates HTML reports.

    Examples:

        ai-qa-test run --feature-dir ./features/

        ai-qa-test run --feature-dir ./features/ --browser-mode headless

        ai-qa-test run --feature-dir ./features/ --force-translate

        ai-qa-test run --feature-dir ./features/ --from-step 5
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
    if from_step:
        config_kwargs["from_step"] = from_step
    if force_translate:
        config_kwargs["force_translate"] = True
    if functions_file:
        config_kwargs["custom_functions_file"] = functions_file
    if tag_url_map_file:
        config_kwargs["tag_url_map_file"] = tag_url_map_file
    if common_steps_dir:
        config_kwargs["common_steps_dir"] = common_steps_dir

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


if __name__ == "__main__":
    cli()
