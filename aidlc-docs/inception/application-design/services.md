# Services

## Service Layer Overview

The ai-qa-test-engine uses a pipeline-style service orchestration where the CLI (or AgentCore entrypoint) coordinates the core components in sequence.

---

## TestExecutionService

**Purpose**: Orchestrates the full test execution pipeline (translate → execute → report).

**Responsibilities**:
- Load configuration
- Discover feature files
- Check translation cache, translate if needed
- Execute scenarios (sequentially for local, parallel for AgentCore)
- Generate reports
- Handle stop-on-failure workflow

**Orchestration Flow**:
```
1. Config.from_cli(args)
2. Parser.parse(feature_files)
3. Parser.resolve_includes(parsed)
4. CacheManager.get_translation(feature) OR Translator.translate(parsed)
5. FunctionRegistry.load_bundled() + load_user_functions()
6. FunctionRegistry.validate(feature)
7. BrowserSession.create(config)
8. Executor.execute(scenario, browser, functions)
9. Reporter.generate_combined_report(results)
```

**Used by**: CLI `run` command, AgentCore Test Runner

---

## TranslationService

**Purpose**: Orchestrates translation-only pipeline (parse → translate → cache).

**Responsibilities**:
- Discover feature files
- Parse Gherkin AST
- Resolve includes
- Translate via Strands Agent
- Cache results

**Orchestration Flow**:
```
1. Config.from_cli(args)
2. Parser.parse(feature_files)
3. Parser.resolve_includes(parsed)
4. Translator.translate(parsed, tag_url_map)
5. CacheManager.put_translation(feature_path, translated)
```

**Used by**: CLI `translate` command, AgentCore Orchestrator (translate action)

---

## Service Interaction Diagram

```
+-------------------+
|       CLI         |
+-------------------+
         |
         | invokes
         v
+-------------------+     +-------------------+
| TestExecution     |---->| Translation       |
| Service           |     | Service           |
+-------------------+     +-------------------+
    |    |    |                    |
    |    |    |                    v
    |    |    |           +---------------+
    |    |    |           |  Translator   |
    |    |    |           +---------------+
    |    |    |                    |
    |    |    v                    v
    |    |  +---------------+  +---------------+
    |    |  | Cache Manager |  |    Parser     |
    |    |  +---------------+  +---------------+
    |    v
    |  +-------------------+
    |  | Functions Registry|
    |  +-------------------+
    v
+-------------------+     +-------------------+
|    Executor       |---->| Browser Backend   |
+-------------------+     +-------------------+
    |
    v
+-------------------+
|    Reporter       |
+-------------------+
```

---

## Package Dependencies

```
cli ──depends-on──> core
agentcore-runner ──depends-on──> core
agentcore-orchestrator ──depends-on──> core (translation + caching only)
```

The `core` package has NO dependencies on `cli` or `agentcore-*` packages. This ensures clean separation and testability.
