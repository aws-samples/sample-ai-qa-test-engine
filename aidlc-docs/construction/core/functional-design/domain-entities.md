# Domain Entities — Core Package

## Entities Ported from test_translator (unchanged)

### Feature
```python
class Feature(BaseModel):
    name: str
    description: str
    base_url: str                    # Resolved from tags
    tags: list[str] = []
    scenarios: list[TestScenario]
    # Metadata
    conversion_timestamp: str
    source_file: str
    bedrock_model_id: str
```

### TestScenario
```python
class TestScenario(BaseModel):
    name: str
    tags: list[str] = []
    steps: list[TestStep]
    # model_validator: validate_variable_references
```

### TestStep
```python
class TestStep(BaseModel):
    original_keyword: str            # Given/When/Then/And/But
    original_text: str               # Original Gherkin text
    instruction: str | None = None   # Nova Act act() prompt
    extraction: Extraction | None = None
    validation: Validation | None = None
    function_call: FunctionCall | None = None
    # model_validator: check_exactly_one_set (XOR)
```

### Extraction
```python
class Extraction(BaseModel):
    prompt: str                      # Nova Act expect() prompt
    extraction_key: str              # Variable name to store
    extraction_type: Literal["string", "number", "boolean"] = "string"
```

### Validation
```python
class Validation(BaseModel):
    prompt: str                      # Nova Act expect() prompt
    expected: str | float | bool | None = None
    comparison: Literal[
        "equal", "contain", "match",
        "greater_than", "less_than", "greater_or_equal", "less_or_equal",
        "true", "false"
    ]
```

### FunctionCall
```python
class FunctionCall(BaseModel):
    function_name: str               # e.g., "calculate_discount" or "service.method"
    parameters: dict[str, Any] = {}
    storage_key: str | None = None   # Variable name to store result
```

---

## New Entities (Feature 1)

### StepResult
```python
@dataclass
class StepResult:
    step_number: int
    keyword: str
    original_text: str
    status: Literal["PASSED", "FAILED", "SKIPPED", "ERROR"]
    duration_seconds: float
    error: str | None = None
    screenshot: str | None = None    # base64 PNG
    extracted_value: Any = None      # For extraction steps
```

### ScenarioResult
```python
@dataclass
class ScenarioResult:
    scenario_name: str
    feature_name: str
    status: Literal["PASSED", "FAILED", "ERROR"]
    duration_seconds: float
    steps: list[StepResult]
    extracted_variables: dict[str, Any]
    errors: list[str]
```

### RunSummary
```python
@dataclass
class RunSummary:
    run_id: str
    timestamp: str
    total_scenarios: int
    passed: int
    failed: int
    errors: int
    total_duration_seconds: float
    status: Literal["PASSED", "FAILED"]
    scenarios: list[ScenarioResult]
```

### CacheEntry
```python
@dataclass
class CacheEntry:
    source_hash: str                 # SHA-256 of source .feature file
    translated_json: dict            # The Feature dict
    cached_at: str                   # ISO timestamp
```

### AppConfig (extended from test_translator)
```python
class AppConfig(BaseSettings):
    # --- Ported from test_translator ---
    translate_features: bool = False
    workflow_definition_name: str = "nova-act-examples"
    headless: bool = False
    bedrock_model_id: str | None = None
    feature_dir: Path = Path("features")
    translated_feature_dir: Path = Path("features_translated")
    custom_functions_file: Path = Path("custom_functions.py")
    default_test_url: str | None = None
    enable_video_recording: bool = False
    
    # --- New for ai-qa-test-engine ---
    browser_mode: Literal["headed", "headless", "agentcore"] = "headed"
    from_step: int | None = None
    stop_on_failure: bool = False
    force_translate: bool = False
    cache_dir: Path = Path("translated")      # Git-committable cache
    report_dir: Path = Path("reports")
    common_steps_dir: Path | None = None      # Future: Feature 3
    tag_url_map_file: Path | None = None      # Alternative to env vars
```

---

## Entity Relationships

```
Feature 1──* TestScenario 1──* TestStep
                                    |
                          exactly one of:
                    +-------+-------+-------+
                    |       |       |       |
              instruction extraction validation function_call

RunSummary 1──* ScenarioResult 1──* StepResult

AppConfig ──used-by──> all components
CacheEntry ──stored-in──> cache_dir (one per .feature file)
```
