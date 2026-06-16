"""Data models for AI QA Test Engine.

Ported from test_translator/translator/models.py with additions for
step-level result tracking (StepResult, ScenarioResult, RunSummary).
"""

import re
from dataclasses import dataclass, field
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, model_validator

# Pattern for matching ${variable_name} references
_VARIABLE_PATTERN = re.compile(r'\$\{([^}]+)\}')


class Extraction(BaseModel):
    """Extraction configuration for a test step.

    Used when a step needs to extract data from the UI using
    NovaActQa.expect().as_*() methods and store it for later use.
    """

    prompt: str
    extraction_key: str
    extraction_type: Literal["string", "number", "boolean"] = "string"


class Validation(BaseModel):
    """Validation configuration for a test step.

    Used when a step needs to extract data from the UI and compare it
    against an expected value using NovaActQa.expect().to_*() assertions.
    """

    prompt: str
    expected: str | float | bool | None = None
    comparison: Literal[
        "equal",
        "contain",
        "match",
        "greater_than",
        "less_than",
        "greater_or_equal",
        "less_or_equal",
        "true",
        "false",
    ]


class FunctionCall(BaseModel):
    """Function call configuration for a test step.

    Used when a step needs to call a custom Python function.
    """

    function_name: str
    parameters: dict[str, Any] = {}
    storage_key: Optional[str] = None


class TestStep(BaseModel):
    """Represents a single Gherkin step.

    Each step must have exactly one of: instruction, extraction, validation, or function_call.
    """

    original_keyword: str
    original_text: str
    instruction: Optional[str] = None
    extraction: Optional[Extraction] = None
    validation: Optional[Validation] = None
    function_call: Optional[FunctionCall] = None

    @model_validator(mode="after")
    def check_exactly_one_set(self) -> "TestStep":
        """Ensure exactly one of instruction, extraction, validation, or function_call is set (XOR)."""
        has_instruction = self.instruction is not None
        has_extraction = self.extraction is not None
        has_validation = self.validation is not None
        has_function_call = self.function_call is not None

        set_count = sum([has_instruction, has_extraction, has_validation, has_function_call])

        if set_count == 0:
            raise ValueError("One of instruction, extraction, validation, or function_call must be set")
        if set_count > 1:
            raise ValueError("Cannot set multiple fields - each step should be one action, extraction, validation, or function call")
        return self


class TestScenario(BaseModel):
    """Represents a Gherkin scenario."""

    name: str
    tags: List[str] = []
    steps: List[TestStep]

    @model_validator(mode="after")
    def validate_variable_references(self) -> "TestScenario":
        """Validate that all ${variable_name} references point to variables
        defined by extraction or function call steps earlier in the scenario.
        """
        defined_variables: set[str] = set()

        for step_idx, step in enumerate(self.steps, 1):
            texts_to_check: list[str] = []

            if step.instruction:
                texts_to_check.append(step.instruction)
            if step.extraction:
                texts_to_check.append(step.extraction.prompt)
            if step.validation:
                texts_to_check.append(step.validation.prompt)
                if isinstance(step.validation.expected, str):
                    texts_to_check.append(step.validation.expected)
            if step.function_call:
                for param_value in step.function_call.parameters.values():
                    if isinstance(param_value, str):
                        texts_to_check.append(param_value)

            # Validate references BEFORE registering this step's key
            # Note: variables from input_variables (runtime-loaded) won't be in defined_variables.
            # We skip strict validation — runtime will catch truly missing variables with a clear error.
            for text in texts_to_check:
                for match in _VARIABLE_PATTERN.finditer(text):
                    var_name = match.group(1)
                    if var_name in defined_variables:
                        continue
                    # Check dotted reference: ${stats.gravity} is valid if "stats" is defined
                    if "." in var_name:
                        base_name = var_name.split(".")[0]
                        if base_name in defined_variables:
                            continue
                    # Allow — may come from input_variables, env, or runtime context

            # Register variables defined by this step (after validation)
            if step.extraction:
                defined_variables.add(step.extraction.extraction_key)
            if step.function_call and step.function_call.storage_key:
                storage_key = step.function_call.storage_key
                # Support comma-separated keys for tuple unpack: "var1, var2"
                if "," in storage_key:
                    for k in storage_key.split(","):
                        defined_variables.add(k.strip())
                else:
                    defined_variables.add(storage_key)

        return self


class Feature(BaseModel):
    """Represents a Gherkin feature."""

    name: str
    description: str = ""
    base_url: str = ""
    tags: List[str] = []
    scenarios: List[TestScenario]

    # Metadata fields
    conversion_timestamp: str = ""
    source_file: str = ""
    bedrock_model_id: str = ""


# --- New models for result tracking ---


@dataclass
class StepResult:
    """Result of a single step execution."""

    step_number: int
    keyword: str
    original_text: str
    status: str  # "PASSED", "FAILED", "SKIPPED", "ERROR"
    duration_seconds: float
    error: str | None = None
    screenshot: str | None = None  # base64 PNG on failure
    extracted_value: Any = None
    prompt_sent: str | None = None  # The actual prompt/instruction sent to Nova Act
    screenshot_after: str | None = None  # base64 PNG after step (for detailed report)
    trajectory_file: str | None = None  # Path to Nova Act trajectory JSON (for detailed report)
    replayed_from_cache: bool = False  # True if step was replayed from trajectory cache
    attempt: int = 1  # Attempt number (1 = first try, 2+ = retries via stop-on-failure)
    is_retry: bool = False  # True if this result is from a stop-on-failure retry
    sub_actions: list[dict] | None = None  # Captured sub-actions from custom functions using nova_act


@dataclass
class ScenarioResult:
    """Result of a single scenario execution."""

    scenario_name: str
    feature_name: str
    status: str  # "PASSED", "FAILED", "ERROR"
    duration_seconds: float
    steps: list[StepResult] = field(default_factory=list)
    extracted_variables: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    workflow_definition_name: str | None = None
    workflow_run_id: str | None = None


@dataclass
class RunSummary:
    """Summary of an entire test run."""

    run_id: str
    timestamp: str
    total_scenarios: int
    passed: int
    failed: int
    errors: int
    total_duration_seconds: float
    status: str  # "PASSED", "FAILED"
    scenarios: list[ScenarioResult] = field(default_factory=list)
