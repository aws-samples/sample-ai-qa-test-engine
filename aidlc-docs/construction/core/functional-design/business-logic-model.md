# Business Logic Model — Core Package

## Overview

The core package implements a pipeline: **Parse → Translate → Cache → Execute → Report**

All business logic is ported from test_translator. This document maps the existing logic and notes where modifications are needed.

---

## Pipeline Flow

```
Input: .feature file(s) + config
                |
                v
+---------------------------+
|  1. PARSE                 |  parser.py
|  - gherkin-official AST   |
|  - @include resolution    |
+---------------------------+
                |
                v
+---------------------------+
|  2. CACHE CHECK           |  cache.py
|  - content hash compare   |
|  - return cached if fresh |
+---------------------------+
                |  (stale or missing)
                v
+---------------------------+
|  3. TRANSLATE             |  translator.py
|  - Strands Agent + Bedrock|
|  - Classify steps         |
|  - Generate prompts       |
|  - Validate references    |
+---------------------------+
                |
                v
+---------------------------+
|  4. VALIDATE              |  functions.py
|  - Check function refs    |
|  - Load function modules  |
+---------------------------+
                |
                v
+---------------------------+
|  5. EXECUTE               |  executor.py + browser.py
|  - Create browser session |
|  - Iterate steps          |
|  - Dispatch by type       |
|  - Collect results        |
+---------------------------+
                |
                v
+---------------------------+
|  6. REPORT                |  reporter.py
|  - Per-scenario HTML      |
|  - Combined dashboard     |
|  - JSON summary           |
+---------------------------+
                |
                v
Output: HTML report + JSON summary + exit code
```

---

## Step Execution Logic (from test_translator — ported as-is)

This is the core loop from `utils/execution.py::execute_scenario_impl`:

```python
for step in scenario.steps:
    # Substitute variables in all text fields
    # Then dispatch based on step type:
    
    if step.function_call:
        # 1. Resolve parameters (substitute ${vars})
        # 2. Get function from registry
        # 3. Inject reserved params (nova_act, context)
        # 4. Call function
        # 5. Store result if storage_key specified
        
    elif step.instruction:
        # 1. Substitute variables in instruction text
        # 2. Call nova.act(instruction)
        
    elif step.extraction:
        # 1. Substitute variables in prompt
        # 2. Call nova.expect(prompt).as_{extraction_type}()
        # 3. Store extracted value in variables dict
        
    elif step.validation:
        # 1. Substitute variables in prompt and expected
        # 2. Call nova.expect(prompt).to_{comparison}(expected)
        # 3. Assert passes or raise AssertionError
```

**This logic is UNCHANGED from test_translator.** We port it directly.

---

## Variable Substitution (from test_translator — as-is)

```python
pattern = r'\$\{([^}]+)\}'

def substitute_variables(text: str, variables: dict) -> str:
    """Replace ${variable_name} with actual values."""
    def replacer(match):
        var_name = match.group(1)
        if var_name not in variables:
            raise KeyError(f"Variable '${{{var_name}}}' not found")
        return str(variables[var_name])
    return re.sub(pattern, replacer, text)
```

**Ported as-is.**

---

## Translation Logic (from test_translator — as-is)

The Strands Agent with `system_prompt.md` classifies each Gherkin step:

1. Parse .feature with gherkin-official → AST
2. Send AST to Strands Agent with structured_output_model=Feature
3. Agent classifies each step as instruction/extraction/validation/function_call
4. Agent generates Nova Act prompts
5. Pydantic model validates (XOR constraint, variable references)

**Ported as-is.** The system_prompt.md is unchanged.

---

## Modifications from test_translator

### Mod 1: Extract Browser Creation (NEW: browser.py)

**Current** (in executor): Browser created inline with NovaActQa constructor
**New**: Extracted to `browser.py` with mode switching

```python
class BrowserSessionFactory:
    def create(self, config: AppConfig, base_url: str, workflow_name: str) -> ContextManager:
        if config.browser_mode == "headed":
            return _local_session(base_url, workflow_name, headless=False)
        elif config.browser_mode == "headless":
            return _local_session(base_url, workflow_name, headless=True)
        elif config.browser_mode == "agentcore":
            return _agentcore_session(base_url, workflow_name)
```

### Mod 2: Add StepResult Collection (extends executor.py)

**Current**: Steps either pass or raise exception. No per-step result tracking.
**New**: Collect StepResult for each step (status, duration, screenshot on failure, error message)

```python
@dataclass
class StepResult:
    step_number: int
    keyword: str
    original_text: str
    status: Literal["PASSED", "FAILED", "ERROR"]
    duration_seconds: float
    error: str | None = None
    screenshot: str | None = None  # base64 PNG on failure
```

### Mod 3: Add from_step Support (extends executor.py)

**Current**: Always starts from step 1
**New**: Optional `from_step` parameter to skip steps 1..N-1

```python
def execute(self, scenario, base_url, from_step=1):
    for idx, step in enumerate(scenario.steps, 1):
        if idx < from_step:
            # Mark as SKIPPED in results
            continue
        # Execute normally
```

### Mod 4: Cache Manager (NEW: cache.py)

**Current**: conftest.py checks if JSON files exist, translates if missing
**New**: Proper cache with content-hash invalidation

```python
class LocalCacheManager:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
    
    def is_stale(self, source_path: Path) -> bool:
        """Compare SHA-256 of source vs stored hash."""
        cached_hash_file = self._hash_path(source_path)
        if not cached_hash_file.exists():
            return True
        stored_hash = cached_hash_file.read_text().strip()
        current_hash = self._compute_hash(source_path)
        return stored_hash != current_hash
    
    def get(self, source_path: Path) -> dict | None:
        """Return cached JSON or None."""
    
    def put(self, source_path: Path, data: dict) -> None:
        """Store translated JSON + source hash."""
```

### Mod 5: Reporter (NEW: reporter.py — ported from deploy_test_translator)

**Source**: `deploy_test_translator/app/test_runner/reporting.py` + `app/orchestrator/reporting.py`
**Adaptation**: Generate HTML locally (no S3), embed screenshots as base64

### Mod 6: Services Orchestration (NEW: services.py)

**Current**: conftest.py + test_runner.py handle orchestration via pytest
**New**: Standalone services that CLI calls

```python
class TestExecutionService:
    def run(self, config: AppConfig) -> RunSummary:
        """Full pipeline: discover → cache check → translate → validate → execute → report"""

class TranslationService:
    def translate(self, config: AppConfig) -> list[Path]:
        """Translate-only: discover → parse → translate → cache"""
```

### Mod 7: Config Extension (extends config.py)

**Current**: AppConfig reads from .env only
**New**: AppConfig supports CLI args override + new fields

New fields:
- `browser_mode: Literal["headed", "headless", "agentcore"]`
- `from_step: int | None`
- `cache_dir: Path`
- `report_dir: Path`
- `force_translate: bool`

---

## What is NOT Changed

- models.py — Feature, TestScenario, TestStep, Extraction, Validation, FunctionCall (as-is)
- system_prompt.md — AI translation prompt (as-is)
- Variable substitution logic (as-is)
- Step execution dispatch logic (as-is)
- Function call handling with reserved params (as-is)
- Gherkin parsing via gherkin-official (as-is)
- Tag-to-URL resolution (as-is)
- Workflow definition management (as-is)
