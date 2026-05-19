# Application Design — ai-qa-test-engine

## Design Philosophy

**PORT FIRST, MODIFY MINIMALLY.** The existing test_translator is proven, working code. We take it as-is into the new monorepo structure and only modify what's strictly needed for:
1. Package restructuring (import paths)
2. New features that don't exist yet
3. Configuration flexibility (CLI args, dual-mode caching)

This minimizes design effort and bugs.

## Source Mapping: test_translator → ai-qa-test-engine

| test_translator file | New location (core package) | Changes needed |
|---------------------|---------------------------|----------------|
| `translator/models.py` | `models.py` | As-is (Feature, TestScenario, TestStep, etc.) |
| `translator/agent.py` | `translator.py` | As-is (translate_all_features, translate_feature_to_json) |
| `translator/system_prompt.md` | `prompts/system_prompt.md` | As-is |
| `translator/main.py` | Absorbed into CLI | CLI wraps translate_all_features() |
| `utils/execution.py` | `executor.py` | Minimal changes: extract browser creation, add from_step support |
| `utils/function_helpers.py` | `functions.py` | As-is + add registry wrapper |
| `config/app_config.py` | `config.py` | Extend with CLI args, cache dirs, browser mode |
| `config/decorators.py` | `config.py` (inline) | As-is |
| `config/exceptions.py` | `exceptions.py` | As-is |
| `tests/conftest.py` | Not needed (CLI replaces pytest runner) | — |
| `tests/test_runner.py` | Absorbed into executor/CLI | Logic reused in execute pipeline |
| `custom_functions_sample.py` | `sample-tests/` | Moved to sample tests |

### From deploy_test_translator (Reference for AgentCore — Feature 5, later):

**NOTE**: This is a REFERENCE, not a direct copy. The patterns (browser_session injection, fan-out, S3 I/O, reporting) will be adapted. The deployment mechanism (boto3, Terraform, CFN, or AgentCore CLI) is TBD when Feature 5 is built.

| deploy_test_translator pattern | What we take from it | Decision deferred |
|-------------------------------|---------------------|-------------------|
| `scenario_executor.py` — browser_session() + monkey-patch | CDP injection pattern for remote browser | — |
| `orchestrator/main.py` — fan-out pattern | Parallel invocation architecture | — |
| `orchestrator/cache.py` — S3 timestamp cache | S3 caching pattern (adapt to content-hash) | — |
| `orchestrator/invoker.py` — async semaphore | Concurrency control pattern | — |
| `orchestrator/reporting.py` — combined HTML | Combined report generation pattern | — |
| `agentcore.json` + CDK | Deployment infrastructure | **TBD: boto3 vs Terraform vs CFN vs AgentCore CLI** |
| `Dockerfile` | Container build for Test Runner | — |
| `scripts/sync-examples.sh` | Not needed (core is a package dependency, not vendored) | — |

## Monorepo Structure

```
ai-qa-test-engine/
├── packages/
│   ├── core/                              # Core engine (mostly ported from test_translator)
│   │   ├── src/
│   │   │   └── ai_qa_test_engine/
│   │   │       ├── __init__.py
│   │   │       ├── models.py             # ← translator/models.py (as-is)
│   │   │       ├── config.py             # ← config/app_config.py (extended)
│   │   │       ├── exceptions.py         # ← config/exceptions.py (as-is)
│   │   │       ├── parser.py             # NEW: Gherkin parsing + @include resolution
│   │   │       ├── translator.py         # ← translator/agent.py (as-is)
│   │   │       ├── executor.py           # ← utils/execution.py (minor mods)
│   │   │       ├── browser.py            # NEW: Browser backend abstraction
│   │   │       ├── functions.py          # ← utils/function_helpers.py (extended)
│   │   │       ├── cache.py              # NEW: Local + S3 cache manager
│   │   │       ├── reporter.py           # ← deploy_test_translator reporting (ported)
│   │   │       ├── services.py           # NEW: Orchestration (thin wrappers)
│   │   │       └── prompts/
│   │   │           └── system_prompt.md  # ← translator/system_prompt.md (as-is)
│   │   ├── pyproject.toml
│   │   └── README.md
│   ├── cli/                              # CLI entry point
│   │   ├── src/
│   │   │   └── ai_qa_test_engine_cli/
│   │   │       ├── __init__.py
│   │   │       └── main.py              # Click/Typer CLI
│   │   ├── pyproject.toml
│   │   └── README.md
│   ├── agentcore-runner/                 # (Future: Feature 5)
│   └── agentcore-orchestrator/           # (Future: Feature 5)
├── sample-tests/
│   └── feature-01-core-execution/
│       ├── features/
│       │   ├── basic_navigation.feature
│       │   ├── extraction.feature
│       │   ├── validation.feature
│       │   └── custom_functions.feature
│       ├── custom_functions.py           # ← custom_functions_sample.py
│       ├── translated/                   # Cache (git-committed)
│       └── tag-url-mapping.json
├── pyproject.toml                        # uv workspace root
├── README.md
└── .gitignore
```

## What's NEW vs What's PORTED

### Ported As-Is (minimal import path changes only):
- **models.py** — Feature, TestScenario, TestStep, Extraction, Validation, FunctionCall
- **translator.py** — translate_all_features, translate_feature_to_json, load_agent_prompt, parse_gherkin_file
- **system_prompt.md** — AI translation prompt
- **executor.py** — execute_scenario_impl (core loop: instruction/extraction/validation/function_call dispatch)
- **functions.py** — get_function_from_module, dot-notation support, reserved param injection
- **config.py** — AppConfig with pydantic-settings (extended, not rewritten)
- **exceptions.py** — ConfigurationError

### New Code (Feature 1):
- **parser.py** — Wraps gherkin-official parsing + @include resolution (currently inline in translator/agent.py, extracted as standalone)
- **browser.py** — Thin abstraction over NovaActQa creation (currently inline in executor, extracted for mode switching)
- **cache.py** — Local file cache with content-hash invalidation (new, replaces the "check if JSON exists" logic in conftest.py)
- **reporter.py** — HTML report generation (ported from deploy_test_translator/reporting.py, adapted for local use)
- **services.py** — Thin orchestration: discover files → check cache → translate → execute → report
- **cli/main.py** — Click/Typer CLI replacing the pytest-based runner

### Modified (minimal changes to existing logic):
- **executor.py** — Extract browser creation into browser.py, add `from_step` parameter, add StepResult collection for reporting
- **config.py** — Add CLI arg support, cache_dir, report_dir, browser_mode, from_step
- **functions.py** — Add FunctionRegistry class wrapping existing get_function_from_module

## Key Principle

> **If test_translator already does it correctly, we copy it. We don't redesign it.**
> 
> The only reasons to change existing code:
> 1. Import paths (package restructuring)
> 2. Extract a concern into its own module (e.g., browser creation out of executor)
> 3. Add a new parameter/feature that doesn't exist yet
> 4. Replace pytest-specific code with CLI-driven execution

## Component Interactions (same as test_translator, just restructured)

The execution flow is identical to test_translator's `execute_scenario_impl`:

```python
# This is essentially the same loop from utils/execution.py
for step in scenario.steps:
    if step.function_call:
        # Call custom function (same logic as test_translator)
    elif step.instruction:
        # nova.act(instruction) — same
    elif step.extraction:
        # nova.expect(prompt).as_*() — same
    elif step.validation:
        # nova.expect(prompt).to_*() — same
```

The difference is HOW we get to this loop:
- **test_translator**: pytest → conftest.py → test_runner.py → execute_scenario_impl
- **ai-qa-test-engine**: CLI → services.py → executor.py (same execute_scenario_impl logic)
