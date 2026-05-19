# Component Dependencies

## Dependency Matrix

| Component | Depends On | Depended On By |
|-----------|-----------|----------------|
| Parser | Models | Translator, TranslationService |
| Translator | Parser, Models, Config | TestExecutionService, TranslationService |
| Executor | Models, Browser Backend, Functions Registry, Config | TestExecutionService |
| Browser Backend | Config | Executor |
| Functions Registry | Models | Executor |
| Cache Manager | Config, Models | TestExecutionService, TranslationService |
| Reporter | Models, Config | TestExecutionService |
| Models | (none) | All components |
| Config | (none) | All components |
| CLI App | TestExecutionService, TranslationService, Config | (entry point) |

## Communication Patterns

### Synchronous (Direct Call)
All component interactions are synchronous function calls within the same process (local mode).

### Data Flow

```
Feature File (.feature)
    |
    v [Parser]
ParsedFeature (internal AST)
    |
    v [Translator]
Feature (Pydantic model - JSON serializable)
    |
    v [Cache Manager - store/retrieve]
    |
    v [Executor]
ScenarioResult (per scenario)
    |
    v [Reporter]
HTML Report + JSON Summary
```

### Variable Context Flow

```
Executor creates ExecutionContext
    |
    v [Step 1: extraction] → stores variable in context
    |
    v [Step 2: function_call] → reads variable, stores result
    |
    v [Step 3: instruction] → substitutes ${var} from context
    |
    v [Step 4: validation] → substitutes ${var} in expected value
```

## Package-Level Dependencies

```
+------------------+
|       cli        |  (entry point)
+------------------+
         |
         | depends on
         v
+------------------+
|       core       |  (all business logic)
+------------------+
         ^
         | depends on
         |
+------------------+     +------------------+
| agentcore-runner |     | agentcore-orch   |
+------------------+     +------------------+
```

## External Dependencies

| Component | External Dependency | Purpose |
|-----------|-------------------|---------|
| Parser | gherkin-official | Gherkin AST parsing |
| Translator | strands-agents, bedrock | AI translation |
| Executor | nova-act | Browser automation |
| Browser Backend (local) | nova-act | NovaActQa wrapper |
| Browser Backend (agentcore) | bedrock-agentcore | browser_session() CDP |
| Functions Registry | (none - dynamic import) | Load user Python files |
| Cache Manager | boto3 (AgentCore mode only) | S3 operations |
| Reporter | (none - generates HTML) | HTML generation |
| Config | pydantic-settings, python-dotenv | Settings management |
| CLI App | click or typer | CLI framework |
