"""Unified configuration for AI QA Test Engine.

Extended with CLI args, browser mode, cache settings.
"""

import json
import os
from pathlib import Path
from typing import Dict, Literal, Optional

from dotenv import load_dotenv
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from ai_qa_test_engine.exceptions import ConfigurationError


def _validate_app_config(func):
    """Decorator that formats Pydantic validation errors into user-friendly messages.

    Ported from test_translator/config/decorators.py.
    """

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            errors = e.errors()
            error_messages = []

            for error in errors:
                if error["type"] == "missing":
                    error_messages.append(f"Missing required environment variable: {error['loc'][0]}")
                elif error["type"] == "extra_forbidden":
                    error_messages.append(f"Invalid environment variable name: {str(error['loc'][0]).upper()}")
                else:
                    error_messages.append(f"Validation error: {error['msg']}")

            max_message_length = max(len(msg) for msg in error_messages) if error_messages else 0
            width = max(70, max_message_length + 4)
            border = "*" * width
            title = "Environment Configuration Error"

            formatted_message = (
                "\n"
                f"{border}\n"
                f"* {title.center(width - 4)} *\n"
                f"{border}\n"
                + "\n".join(f"* {msg:<{width - 4}} *" for msg in error_messages)
                + "\n"
                f"{border}\n"
            )

            raise ConfigurationError(formatted_message)

    return wrapper


class AppConfig(BaseSettings):
    """Unified configuration for test execution and translation.

    Loads from .env file, environment variables, and supports CLI overrides.
    Precedence: CLI args (set via constructor) > env vars > .env file > defaults.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # --- Test Execution Settings ---
    translate_features: bool = Field(
        default=False,
        description="Auto-translate Gherkin features before running tests",
    )

    workflow_definition_name: str = Field(
        default="nova-act-examples",
        alias="NOVA_ACT_WORKFLOW_DEFINITION_NAME",
        description="Nova Act Workflow definition name",
    )

    headless: bool = Field(
        default=False,
        alias="HEADLESS",
        description="Run browser in headless mode",
    )

    browser_mode: Literal["headed", "headless", "agentcore"] = Field(
        default="headed",
        alias="BROWSER_MODE",
        description="Browser execution mode",
    )

    stop_on_failure: bool = Field(
        default=False,
        alias="STOP_ON_FAILURE",
        description="Stop execution and keep browser open on failure",
    )

    from_step: Optional[int] = Field(
        default=None,
        alias="FROM_STEP",
        description="Resume execution from this step number",
    )

    # --- Translation Settings ---
    bedrock_model_id: str | None = Field(
        default=None,
        alias="BEDROCK_MODEL_ID",
        description="Bedrock model ID for test translation",
    )

    force_translate: bool = Field(
        default=False,
        alias="FORCE_TRANSLATE",
        description="Force re-translation even if cache is fresh",
    )

    feature_dir: Path = Field(
        default=Path("features"),
        alias="FEATURE_DIR",
        description="Directory containing Gherkin .feature files",
    )

    extracted_variables_dir: Path = Field(
        default=Path("extracted_variables"),
        alias="EXTRACTED_VARIABLES_DIR",
        description="Directory for storing extracted variable JSON files",
    )

    custom_functions_file: Path | None = Field(
        default=None,
        alias="CUSTOM_FUNCTIONS_FILE",
        description="Path to Python file containing custom test functions",
    )

    default_test_url: str | None = Field(
        default=None,
        alias="DEFAULT_TEST_URL",
        description="Default URL when no tag mapping exists",
    )

    tag_url_map_file: Path | None = Field(
        default=None,
        alias="TAG_URL_MAP_FILE",
        description="Path to JSON file with tag-to-URL mappings",
    )

    # --- Cache Settings ---
    cache_dir: Path = Field(
        default=Path("translated"),
        alias="CACHE_DIR",
        description="Directory for translation cache (git-committable)",
    )

    # --- Report Settings ---
    report_dir: Path = Field(
        default=Path("reports"),
        alias="REPORT_DIR",
        description="Directory for generated HTML reports",
    )

    # --- Video Recording Settings ---
    enable_video_recording: bool = Field(
        default=False,
        alias="ENABLE_VIDEO_RECORDING",
        description="Enable video recording of test executions",
    )

    video_recording_dir: Path = Field(
        default=Path("./recordings"),
        alias="VIDEO_RECORDING_DIR",
        description="Directory to store video recordings",
    )

    # --- Trajectory Cache Settings ---
    trajectory_cache_dir: Path = Field(
        default=Path("trajectories"),
        alias="TRAJECTORY_CACHE_DIR",
        description="Directory for trajectory replay cache (git-committable)",
    )

    no_cache: bool = Field(
        default=False,
        alias="NO_CACHE",
        description="Disable trajectory replay cache (always use Nova Act)",
    )

    tag_filter: str | None = Field(
        default=None,
        alias="TAG_FILTER",
        description="Filter scenarios by tag expression (e.g., '@smoke', 'not @slow')",
    )

    trajectory_strict: bool = Field(
        default=False,
        alias="TRAJECTORY_STRICT",
        description="Strict mode for trajectory replay validation (raise on mismatch)",
    )

    # --- Input Variables ---
    input_variables_file: Path | None = Field(
        default=None,
        alias="INPUT_VARIABLES_FILE",
        description="JSON file with pre-loaded variables available as ${name} in steps",
    )
    common_steps_dir: Path | None = Field(
        default=None,
        alias="COMMON_STEPS_DIR",
        description="Directory containing reusable step group files",
    )

    @_validate_app_config
    def __init__(self, _env_file: str | Path | None = None, **data):
        """Initialize config, loading .env if present."""
        env_path = Path(_env_file) if _env_file else Path(".env")
        if env_path.exists():
            load_dotenv(env_path, override=False)
        super().__init__(**data)

    def get_tag_url_mapping(self) -> Dict[str, str]:
        """Build tag-to-URL mapping from JSON file and/or GHERKIN_TAG_* env vars."""
        tag_url_map: dict[str, str] = {}

        # Load from JSON file if specified
        if self.tag_url_map_file:
            map_path = self._resolve_path(self.tag_url_map_file)
            if map_path.exists():
                with open(map_path) as f:
                    file_map = json.load(f)
                # Normalize keys (strip @ prefix, lowercase)
                for key, value in file_map.items():
                    normalized = key.lstrip("@").lower()
                    tag_url_map[normalized] = value

        # Load from GHERKIN_TAG_* env vars (override file)
        for key, value in os.environ.items():
            if key.startswith("GHERKIN_TAG_"):
                tag_name = key.replace("GHERKIN_TAG_", "").lower()
                tag_url_map[tag_name] = value

        # Default URL fallback
        if self.default_test_url:
            tag_url_map["default"] = self.default_test_url

        return tag_url_map

    def _resolve_path(self, path: Path) -> Path:
        """Resolve a path relative to CWD if not absolute."""
        if path.is_absolute():
            return path
        return Path.cwd() / path

    def resolve_feature_dir(self) -> Path:
        return self._resolve_path(self.feature_dir)

    def resolve_extracted_variables_dir(self) -> Path:
        return self._resolve_path(self.extracted_variables_dir)

    def resolve_custom_functions_file(self) -> Path | None:
        if self.custom_functions_file is None:
            return None
        return self._resolve_path(self.custom_functions_file)

    def resolve_cache_dir(self) -> Path:
        return self._resolve_path(self.cache_dir)

    def resolve_report_dir(self) -> Path:
        return self._resolve_path(self.report_dir)

    def resolve_video_recording_dir(self) -> Path:
        return self._resolve_path(self.video_recording_dir)

    def resolve_trajectory_cache_dir(self) -> Path:
        return self._resolve_path(self.trajectory_cache_dir)
