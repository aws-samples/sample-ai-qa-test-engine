# TODO

## CLI Improvements
- [ ] Support multiple `--feature-dir` paths (run specific files without running entire directory)
- [ ] Add `--work-dir` flag to set base directory for all output (translated, trajectories, reports, recordings, extracted_variables)
- [ ] Document `--feature-dir` accepts both a directory and a single file in README
- [ ] PII masking in execution logs (mask secrets, passwords, emails in log output)

## Execution
- [ ] Support tags on Examples blocks in Scenario Outlines (update translator prompt to merge Outline tags + Examples-level tags into expanded scenarios)
- [ ] Per-scenario input variables (different vars per scenario via JSON keyed by scenario_id)
- [ ] Global variables (`${global.name}`) vs scenario-scoped (`${name}`)
- [ ] Run-ID-based output directories (preserve history instead of overwriting reports)
- [ ] Fix Pydantic validation warning for `${variable}` references that come from input variables file
- [ ] Local parallel execution (run multiple scenarios concurrently with `--parallel N`)
- [ ] Attach to existing browser session and continue from step N (CDP connect to locally open browser)

## AgentCore Deployment
- [ ] Save extracted variables as separate file in S3 (not just embedded in result.json)
- [ ] Trajectory cache in S3 (shared across runs in AgentCore mode)
- [ ] Custom functions directory support in S3 (currently only single file)
- [ ] Presigned URL for HTML report (view without S3 console access)

## Documentation
- [ ] Document CLI usage patterns in README (single file, directory, multiple files)
- [ ] Document screenshot extraction usage (prompt format, store as, model config)
- [ ] Auto-inference for screenshot extraction (detect IDs, VINs, emails without explicit prompt)
- [ ] User-defined model support for screenshot extraction (configure vision model via env/CLI)

## Gherkin Spec Gaps
- [ ] Doc Strings support (triple-quoted multi-line step arguments — need model, prompt, and executor changes)
- [ ] Rule keyword (Gherkin 6+ grouping of scenarios under business rules — parser supports it, translator/models don't)
- [ ] Multiple named Examples blocks (translator prompt doesn't explicitly handle naming/tagging per block)
- [ ] `*` (star) step keyword (generic step — valid Gherkin, not mentioned in translator prompt)
- [ ] Scenario descriptions (free-text between Scenario line and first step — parser has it, translator ignores it)
- [ ] i18n / localized keywords (parser supports natively, translator prompt is English-only)

## Future Features
- [ ] Feature 6: Gauge support (.md + .cpt test format)
- [ ] Feature 7: Mobile testing (AWS Device Farm integration)
- [ ] CI/CD pipeline (auto-deploy on git push)
