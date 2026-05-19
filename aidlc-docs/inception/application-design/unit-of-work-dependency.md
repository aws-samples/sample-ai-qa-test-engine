# Unit of Work Dependencies

## Dependency Matrix

| Unit | Depends On | Depended On By |
|------|-----------|----------------|
| core | (external packages only) | cli, agentcore-runner, agentcore-orchestrator |
| cli | core | (entry point — nothing depends on it) |
| agentcore-runner | core | agentcore-orchestrator (invokes it) |
| agentcore-orchestrator | core (translation/caching only) | (entry point) |

## Build Sequence (Feature 1)

```
1. core (no internal dependencies)
2. cli (depends on core)
3. sample-tests (validates both)
```

## Integration Points

### core ↔ cli
- CLI imports and calls `TestExecutionService` and `TranslationService` from core
- CLI constructs `AppConfig` from CLI args and passes to core services
- Core returns `RunSummary` / `ScenarioResult` which CLI formats for terminal output

### core ↔ agentcore-runner (Future)
- Runner imports `executor.py`, `functions.py`, `models.py` from core
- Runner provides AgentCore browser_session() CDP connection
- Runner wraps core's execute_scenario_impl with remote browser injection

### core ↔ agentcore-orchestrator (Future)
- Orchestrator imports `translator.py`, `cache.py`, `models.py` from core
- Orchestrator uses core's translation + caching in S3 mode
- Orchestrator decomposes features using core's models

## External Dependencies (Feature 1)

```
core:
  - nova-act >= latest
  - strands-agents >= 1.0
  - gherkin-official >= 28.0.0
  - pydantic >= 2.0
  - pydantic-settings >= 2.0
  - python-dotenv >= 1.0.0

cli:
  - ai-qa-test-engine (core, as workspace dependency)
  - click >= 8.0 (or typer >= 0.9)
```
