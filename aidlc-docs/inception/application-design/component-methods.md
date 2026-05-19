# Component Methods

## Package: core

### Parser

```python
class GherkinParser:
    def parse(self, file_path: Path) -> ParsedFeature:
        """Parse a .feature file into internal representation."""
    
    def resolve_includes(self, parsed: ParsedFeature, common_steps_dir: Path) -> ParsedFeature:
        """Expand @include directives with actual steps from common step files."""
    
    def expand_scenario_outlines(self, parsed: ParsedFeature) -> ParsedFeature:
        """Expand Scenario Outlines into concrete scenarios using Examples tables."""
```

### Translator

```python
class Translator:
    def __init__(self, config: TranslatorConfig):
        """Initialize with Bedrock model config."""
    
    def translate_feature(self, parsed: ParsedFeature, tag_url_map: dict) -> Feature:
        """Translate parsed feature to executable Feature model."""
    
    def translate_step(self, step_text: str, keyword: str) -> TestStep:
        """Translate a single Gherkin step to TestStep (used by agent internally)."""
```

### Executor

```python
class ScenarioExecutor:
    def __init__(self, browser: BrowserSession, functions: FunctionRegistry, config: ExecutorConfig):
        """Initialize with browser session and function registry."""
    
    def execute(self, scenario: TestScenario, base_url: str, from_step: int = 1) -> ScenarioResult:
        """Execute all steps in a scenario, optionally starting from a specific step."""
    
    def execute_step(self, step: TestStep, context: ExecutionContext) -> StepResult:
        """Execute a single step and return result."""
    
    def substitute_variables(self, text: str, variables: dict) -> str:
        """Replace ${variable_name} references with actual values."""
```

### Browser Backend

```python
class BrowserSession(Protocol):
    """Protocol for browser session abstraction."""
    
    def act(self, instruction: str) -> None:
        """Execute a browser action."""
    
    def expect(self, prompt: str) -> Expectation:
        """Create an expectation for extraction/validation."""
    
    def screenshot(self) -> bytes:
        """Take a screenshot of current page."""
    
    def close(self) -> None:
        """Close the browser session."""


class LocalBrowserSession:
    def __init__(self, config: BrowserConfig):
        """Create local browser session (headed or headless)."""
    
    def create(self, starting_url: str, workflow_name: str) -> BrowserSession:
        """Start Nova Act workflow and return session."""


class AgentCoreBrowserSession:
    def __init__(self, region: str):
        """Create AgentCore browser session."""
    
    def create(self, starting_url: str, workflow_name: str) -> BrowserSession:
        """Get CDP connection from AgentCore and return session."""
```

### Functions Registry

```python
class FunctionRegistry:
    def __init__(self):
        """Initialize empty registry."""
    
    def load_bundled(self, functions_dir: Path) -> None:
        """Load bundled utility functions from project directory."""
    
    def load_user_functions(self, file_path: Path) -> None:
        """Load user-supplied custom functions from external file."""
    
    def validate(self, feature: Feature) -> list[str]:
        """Validate all function calls in feature reference existing functions."""
    
    def call(self, name: str, params: dict, context: ExecutionContext) -> Any:
        """Execute a function by name with resolved parameters."""
    
    def get_function(self, name: str) -> Callable:
        """Get function by name, supporting dot-notation."""
```

### Cache Manager

```python
class CacheManager:
    def __init__(self, config: CacheConfig):
        """Initialize with cache configuration (local dir or S3)."""
    
    def get_translation(self, feature_path: Path) -> Feature | None:
        """Get cached translation for a feature file, or None if stale/missing."""
    
    def put_translation(self, feature_path: Path, feature: Feature) -> None:
        """Cache a translated feature."""
    
    def is_translation_stale(self, feature_path: Path) -> bool:
        """Check if cached translation is stale (source changed)."""
    
    def get_trajectory(self, scenario_name: str, step_index: int) -> TrajectoryData | None:
        """Get cached trajectory for a step (future: Feature 4)."""
    
    def put_trajectory(self, scenario_name: str, step_index: int, data: TrajectoryData) -> None:
        """Cache trajectory data for a step (future: Feature 4)."""
    
    def clear(self, scope: str = "all") -> None:
        """Clear cache (all, translations, trajectories)."""
```

### Reporter

```python
class Reporter:
    def __init__(self, config: ReportConfig):
        """Initialize with report configuration."""
    
    def generate_scenario_report(self, result: ScenarioResult) -> str:
        """Generate HTML report for a single scenario."""
    
    def generate_combined_report(self, results: list[ScenarioResult], run_id: str) -> Path:
        """Generate combined HTML dashboard for all scenarios in a run."""
    
    def generate_summary(self, results: list[ScenarioResult], run_id: str) -> RunSummary:
        """Generate JSON summary of run results."""
```

### Config

```python
class AppConfig:
    # Execution
    browser_mode: Literal["headed", "headless", "agentcore"]
    stop_on_failure: bool
    from_step: int | None
    
    # Paths
    feature_dir: Path
    output_dir: Path
    custom_functions_file: Path | None
    common_steps_dir: Path | None
    cache_dir: Path
    report_dir: Path
    
    # Translation
    translate_features: bool
    force_translate: bool
    bedrock_model_id: str | None
    tag_url_map: dict[str, str]
    
    # Nova Act
    workflow_definition_name: str
    nova_act_model_id: str
    
    @classmethod
    def from_cli(cls, **cli_args) -> "AppConfig":
        """Build config from CLI args + env vars + .env file."""
```

---

## Package: cli

### CLI App

```python
# Using click or typer for CLI framework

def run(
    feature_dir: Path,
    browser_mode: str = "headed",
    stop_on_failure: bool = False,
    from_step: int | None = None,
    force_translate: bool = False,
    tag: list[str] = [],
    output_dir: Path | None = None,
) -> None:
    """Execute tests from feature files."""

def translate(
    feature_dir: Path,
    output_dir: Path | None = None,
    tag: list[str] = [],
    model_id: str | None = None,
) -> None:
    """Translate feature files without executing."""
```
