# Unit of Work — Feature Mapping

## Feature 1 Requirements → Unit Mapping

| Requirement | Unit | Notes |
|-------------|------|-------|
| FR-01: Core Gherkin Execution | core | Main execution engine |
| FR-02: Custom Functions | core | FunctionRegistry + bundled functions |
| FR-07: Browser Mode Config | core | Browser backend abstraction |
| FR-10: Report Generation | core | Reporter module |
| FR-12: Translation Caching | core | Cache manager (local mode) |
| FR-15: CLI Interface | cli | Click/Typer commands |

## Feature 1 Deliverables per Unit

### Unit: core
- [ ] models.py — Port Feature, TestScenario, TestStep + add StepResult, RunSummary
- [ ] config.py — Port AppConfig + extend with browser_mode, cache_dir, from_step
- [ ] exceptions.py — Port ConfigurationError
- [ ] parser.py — Extract Gherkin parsing from translator, add @include stub
- [ ] translator.py — Port translate_all_features, translate_feature_to_json
- [ ] executor.py — Port execute_scenario_impl + extract browser, add from_step, collect StepResults
- [ ] browser.py — Browser session abstraction (headed/headless)
- [ ] functions.py — Port get_function_from_module + FunctionRegistry wrapper
- [ ] cache.py — Local file cache with content-hash invalidation
- [ ] reporter.py — HTML report generation (per-scenario + combined)
- [ ] services.py — TestExecutionService, TranslationService orchestration
- [ ] prompts/system_prompt.md — Port as-is

### Unit: cli
- [ ] main.py — `run` and `translate` commands with all CLI flags

### Sample Tests
- [ ] sample-tests/feature-01-core-execution/features/basic_navigation.feature
- [ ] sample-tests/feature-01-core-execution/features/extraction.feature
- [ ] sample-tests/feature-01-core-execution/features/validation.feature
- [ ] sample-tests/feature-01-core-execution/features/custom_functions.feature
- [ ] sample-tests/feature-01-core-execution/custom_functions.py
- [ ] sample-tests/feature-01-core-execution/tag-url-mapping.json

## Future Features → Unit Mapping

| Feature | Primary Unit | Notes |
|---------|-------------|-------|
| Feature 2: Excel + Secrets + Screenshot | core | New modules in core |
| Feature 3: @include + stop-on-failure | core + cli | Parser enhancement + CLI flag |
| Feature 4: Trajectory replay | core | Cache manager extension |
| Feature 5: AgentCore deployment | agentcore-runner + agentcore-orchestrator | New packages |
| Feature 6: Gauge support | core | New parser module |
| Feature 7: Mobile testing | core | New browser backend |
