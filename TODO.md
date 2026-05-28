# TODO

## CLI Improvements
- [ ] Support multiple `--feature-dir` paths (run specific files without running entire directory)
- [ ] Add `--work-dir` flag to set base directory for all output (translated, trajectories, reports, recordings, extracted_variables)
- [ ] Unify `CACHE_DIR` and `TRANSLATED_FEATURE_DIR` config (they're redundant)
- [ ] Document `--feature-dir` accepts both a directory and a single file in README

## Execution
- [ ] Per-scenario input variables (different vars per scenario via JSON keyed by scenario_id)
- [ ] Global variables (`${global.name}`) vs scenario-scoped (`${name}`)
- [ ] Run-ID-based output directories (preserve history instead of overwriting reports)
- [ ] Fix Pydantic validation warning for `${variable}` references that come from input variables file
- [ ] Local parallel execution (run multiple scenarios concurrently with `--parallel N`)
- [ ] Improve HTML dashboard (charts, trend over time, collapsible step details, screenshots inline)
- [ ] Attach to existing browser session and continue from step N (CDP connect to locally open browser)

## AgentCore Deployment
- [ ] Save extracted variables as separate file in S3 (not just embedded in result.json)
- [ ] Trajectory cache in S3 (shared across runs in AgentCore mode)
- [ ] Custom functions directory support in S3 (currently only single file)
- [ ] Presigned URL for HTML report (view without S3 console access)

## Documentation
- [ ] Document CLI usage patterns in README (single file, directory, multiple files)
- [ ] Add examples showing `--tags` with multiple feature files
- [ ] Document .env file format with all available variables

## Future Features
- [ ] Feature 6: Gauge support (.md + .cpt test format)
- [ ] Feature 7: Mobile testing (AWS Device Farm integration)
- [ ] CI/CD pipeline (auto-deploy on git push)
- [ ] Reduce trajectory replay `wait_before_replay_ms` from 5000 to 1000-2000ms
