# Porting Checklist — test_translator → ai-qa-test-engine

## Purpose
Exhaustive checklist of EVERY feature/capability in test_translator to ensure nothing is missed during code generation.

---

## Source Files → Port Status

| # | Source File | Target | Port Status |
|---|------------|--------|-------------|
| 1 | `translator/models.py` | `core/models.py` | [ ] |
| 2 | `translator/agent.py` | `core/translator.py` | [ ] |
| 3 | `translator/main.py` | `cli/main.py` (absorbed) | [ ] |
| 4 | `translator/system_prompt.md` | `core/prompts/system_prompt.md` | [ ] |
| 5 | `translator/__init__.py` | `core/__init__.py` (exports) | [ ] |
| 6 | `utils/execution.py` | `core/executor.py` | [ ] |
| 7 | `utils/function_helpers.py` | `core/functions.py` | [ ] |
| 8 | `config/app_config.py` | `core/config.py` | [ ] |
| 9 | `config/decorators.py` | `core/config.py` (inline) | [ ] |
| 10 | `config/exceptions.py` | `core/exceptions.py` | [ ] |
| 11 | `config/__init__.py` | `core/__init__.py` | [ ] |
| 12 | `tests/conftest.py` | `core/services.py` (logic absorbed) | [ ] |
| 13 | `tests/test_runner.py` | `core/executor.py` (logic absorbed) | [ ] |
| 14 | `custom_functions_sample.py` | `sample-tests/custom_functions.py` | [ ] |
| 15 | `.env.example` | `sample-tests/.env.example` | [ ] |
| 16 | `features/destination_selection.feature` | `sample-tests/` | [ ] |
| 17 | `features/consumer_connection_ford_smoke_tests.feature` | `sample-tests/` (reference) | [ ] |

---

## Feature Capabilities Checklist

### Gherkin Parsing & Translation
| # | Capability | Source Location | Port Status |
|---|-----------|----------------|-------------|
| 1 | Parse .feature files via gherkin-official | `translator/agent.py::parse_gherkin_file` | [ ] |
| 2 | Translate AST to JSON via Strands Agent | `translator/agent.py::translate_feature_to_json` | [ ] |
| 3 | Structured output with Feature Pydantic model | `translator/agent.py` (structured_output_model=Feature) | [ ] |
| 4 | System prompt for step classification | `translator/system_prompt.md` | [ ] |
| 5 | Batch translate all features in directory | `translator/agent.py::translate_all_features` | [ ] |
| 6 | Save translated JSON to output directory | `translator/agent.py::save_feature_json` | [ ] |
| 7 | Resolve test URL from feature tags | `translator/agent.py::resolve_test_url` | [ ] |
| 8 | Tag-to-URL mapping from env vars (GHERKIN_TAG_*) | `config/app_config.py::get_tag_url_mapping` | [ ] |
| 9 | Default URL fallback | `config/app_config.py::default_test_url` | [ ] |
| 10 | CLI for standalone translation | `translator/main.py` (fire CLI) | [ ] |
| 11 | CLI --tag key=value overrides | `translator/main.py::_build_tag_url_map` | [ ] |

### Gherkin Constructs Supported
| # | Construct | Handled By | Port Status |
|---|-----------|-----------|-------------|
| 12 | Background steps (prepend to all scenarios) | system_prompt.md + agent | [ ] |
| 13 | Scenario Outline + Examples (expand to N scenarios) | system_prompt.md + agent | [ ] |
| 14 | Data Tables (action input or validation data) | system_prompt.md + agent | [ ] |
| 15 | Tags (@tag on feature/scenario) | system_prompt.md + models | [ ] |
| 16 | Given/When/Then/And/But keywords | models.py::TestStep.original_keyword | [ ] |
| 17 | Negation handling (should not → comparison "false") | system_prompt.md | [ ] |
| 18 | Complex step splitting (multi-validation → separate steps) | system_prompt.md | [ ] |

### Step Types & Execution
| # | Capability | Source Location | Port Status |
|---|-----------|----------------|-------------|
| 19 | Instruction steps → nova.act() | `utils/execution.py` | [ ] |
| 20 | Extraction steps → nova.expect().as_*() | `utils/execution.py` | [ ] |
| 21 | Validation steps → nova.expect().to_*() | `utils/execution.py` | [ ] |
| 22 | Function call steps → custom function execution | `utils/execution.py` | [ ] |
| 23 | XOR constraint (exactly one type per step) | `translator/models.py::TestStep.check_exactly_one_set` | [ ] |

### Variable System
| # | Capability | Source Location | Port Status |
|---|-----------|----------------|-------------|
| 24 | ${variable_name} substitution in instructions | `utils/execution.py::substitute_variables` | [ ] |
| 25 | ${variable_name} substitution in extraction prompts | `utils/execution.py` | [ ] |
| 26 | ${variable_name} substitution in validation prompts | `utils/execution.py` | [ ] |
| 27 | ${variable_name} substitution in validation expected values | `utils/execution.py` | [ ] |
| 28 | ${variable_name} substitution in function parameters | `utils/execution.py` | [ ] |
| 29 | Variable reference validation (must be defined earlier) | `translator/models.py::TestScenario.validate_variable_references` | [ ] |
| 30 | Extracted variables saved to JSON file | `tests/test_runner.py` (end of test) | [ ] |

### Custom Functions
| # | Capability | Source Location | Port Status |
|---|-----------|----------------|-------------|
| 31 | Load functions from Python file | `utils/execution.py` (importlib) | [ ] |
| 32 | Dot-notation function names (service.method) | `utils/function_helpers.py::get_function_from_module` | [ ] |
| 33 | Reserved param: nova_act (browser instance injection) | `utils/execution.py` (inspect.signature) | [ ] |
| 34 | Reserved param: context (variables dict injection) | `utils/execution.py` (inspect.signature) | [ ] |
| 35 | Function validation before execution | `utils/execution.py::validate_function_calls_from_data` | [ ] |
| 36 | Function result storage (storage_key) | `utils/execution.py` | [ ] |
| 37 | Parameter type preservation (str, int, float, bool) | system_prompt.md + models | [ ] |

### Browser & Nova Act Integration
| # | Capability | Source Location | Port Status |
|---|-----------|----------------|-------------|
| 38 | NovaActQa wrapper (act, expect, screenshot) | External: nova_act_qa package | [ ] |
| 39 | Nova Act Workflow context manager | `utils/execution.py` (Workflow()) | [ ] |
| 40 | Per-scenario workflow definition names | `tests/test_runner.py` (workflow_name) | [ ] |
| 41 | Workflow definition auto-creation | `tests/test_runner.py` (NovaActClient.get_workflow_kwargs) | [ ] |
| 42 | Headless mode support | `config/app_config.py::headless` | [ ] |
| 43 | tty=False for non-interactive execution | `utils/execution.py` (nova_kwargs) | [ ] |
| 44 | ignore_https_errors=True | `utils/execution.py` (nova_kwargs) | [ ] |

### Video Recording
| # | Capability | Source Location | Port Status |
|---|-----------|----------------|-------------|
| 45 | Enable/disable video recording | `config/app_config.py::enable_video_recording` | [ ] |
| 46 | Video recording directory config | `config/app_config.py::video_recording_dir` | [ ] |
| 47 | Pass record_video + logs_directory to NovaActQa | `utils/execution.py` (nova_kwargs) | [ ] |

### Configuration
| # | Capability | Source Location | Port Status |
|---|-----------|----------------|-------------|
| 48 | Pydantic Settings with .env file | `config/app_config.py` | [ ] |
| 49 | Environment variable aliases (HEADLESS, FEATURE_DIR, etc.) | `config/app_config.py` | [ ] |
| 50 | Path resolution (relative to project root) | `config/app_config.py::resolve_*` methods | [ ] |
| 51 | Validation error formatting (decorator) | `config/decorators.py::validate_app_config` | [ ] |
| 52 | ConfigurationError exception | `config/exceptions.py` | [ ] |

### Test Execution Orchestration
| # | Capability | Source Location | Port Status |
|---|-----------|----------------|-------------|
| 53 | Auto-translate if no JSON files exist | `tests/conftest.py::pytest_sessionstart` | [ ] |
| 54 | Force re-translate (TRANSLATE_FEATURES=true) | `tests/conftest.py::pytest_sessionstart` | [ ] |
| 55 | Discover all JSON feature files | `tests/conftest.py::collect_feature_scenarios` | [ ] |
| 56 | Parametrize one test per scenario | `tests/conftest.py::pytest_generate_tests` | [ ] |
| 57 | Execute all scenarios sequentially | `tests/test_runner.py::test_feature` | [ ] |
| 58 | Save extracted variables per scenario | `tests/test_runner.py` (JSON output) | [ ] |

### Programmatic API (execute_feature)
| # | Capability | Source Location | Port Status |
|---|-----------|----------------|-------------|
| 59 | execute_feature() for non-pytest consumers | `utils/execution.py::execute_feature` | [ ] |
| 60 | TestResult dataclass (success, summary, duration, errors) | `utils/execution.py::TestResult` | [ ] |
| 61 | log_callback for real-time streaming | `utils/execution.py::execute_feature` | [ ] |

---

## Total: 61 capabilities to port

When code generation begins, each capability will be checked off as it's implemented. This ensures zero regression from test_translator.
