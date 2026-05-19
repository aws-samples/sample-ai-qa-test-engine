# Components

## Package: core

The core package contains all execution logic, translation, models, and caching. It is the foundation that CLI and AgentCore packages depend on.

### Component: Parser
- **Purpose**: Parse test specification files into internal AST
- **Responsibilities**:
  - Parse Gherkin `.feature` files using gherkin-official
  - Resolve `@include` directives (expand common steps)
  - Handle Background, Scenario Outline, Examples, Data Tables
  - Future: Parse Gauge `.md`/`.cpt` files, CSV files
- **Interface**: `parse(file_path) → ParsedFeature`

### Component: Translator
- **Purpose**: Convert parsed AST to executable JSON test structure
- **Responsibilities**:
  - Use Strands Agent + Bedrock to classify steps (instruction/extraction/validation/function_call)
  - Generate Nova Act prompts from natural language steps
  - Resolve tag-to-URL mappings
  - Validate variable references across steps
  - Produce Feature/TestScenario/TestStep Pydantic models
- **Interface**: `translate(parsed_feature, config) → Feature`

### Component: Executor
- **Purpose**: Execute translated test scenarios step-by-step
- **Responsibilities**:
  - Iterate through scenario steps
  - Dispatch to appropriate handler (instruction → act, extraction → expect.as_*, validation → expect.to_*, function_call → call function)
  - Manage variable context (extracted values, function results)
  - Substitute `${variable_name}` references before execution
  - Handle errors, capture screenshots on failure
  - Support resume-from-step (--from-step N)
- **Interface**: `execute_scenario(scenario, browser, config) → ScenarioResult`

### Component: Browser Backend
- **Purpose**: Abstract browser interaction (local vs AgentCore)
- **Responsibilities**:
  - Create/manage Nova Act sessions (Workflow + NovaActQa)
  - Support headed, headless, and AgentCore browser modes
  - Manage browser lifecycle (start, stop, keep-open-on-failure)
  - Provide CDP connection for AgentCore mode
- **Interface**: `create_session(config) → BrowserSession`

### Component: Functions Registry
- **Purpose**: Load and execute custom functions
- **Responsibilities**:
  - Load bundled utility functions from project's `functions/` directory
  - Load user-supplied custom functions from external file
  - Validate function existence before execution
  - Resolve dot-notation function names
  - Inject reserved parameters (nova_act, context)
  - Execute functions with resolved parameters
- **Interface**: `load_functions(paths) → FunctionRegistry`, `registry.call(name, params, context) → result`

### Component: Cache Manager
- **Purpose**: Manage translation and trajectory caches
- **Responsibilities**:
  - Store/retrieve translated JSON (local dir or S3)
  - Store/retrieve trajectory recordings (local dir or S3)
  - Cache invalidation (content hash comparison)
  - Force-refresh capability
  - Git-friendly file format (deterministic JSON output)
- **Interface**: `get_cached(key) → data | None`, `put_cache(key, data)`, `is_stale(key, source) → bool`

### Component: Reporter
- **Purpose**: Generate test execution reports
- **Responsibilities**:
  - Generate rich HTML dashboard (pass/fail/error counts, timing)
  - Per-scenario drill-down with step details and screenshots
  - Link/embed Nova Act workflow artifacts
  - Collapsible sections for navigation
  - Combined report across all features in a run
- **Interface**: `generate_report(results, config) → ReportPath`

### Component: Models
- **Purpose**: Pydantic data models for the entire system
- **Responsibilities**:
  - Feature, TestScenario, TestStep, Extraction, Validation, FunctionCall
  - ScenarioResult, StepResult, RunSummary
  - Configuration models
  - Variable reference validation

### Component: Config
- **Purpose**: Unified configuration management
- **Responsibilities**:
  - Load from .env file, environment variables, CLI flags
  - Precedence: CLI > env vars > .env > defaults
  - Resolve paths (feature dir, output dir, functions file, cache dirs)
  - Tag-to-URL mapping resolution
- **Interface**: `load_config(cli_args) → AppConfig`

---

## Package: cli

The CLI package provides the command-line interface for local execution.

### Component: CLI App
- **Purpose**: Command-line entry point
- **Responsibilities**:
  - `run` command — execute tests from feature files
  - `translate` command — translate features without executing
  - Parse CLI arguments and flags
  - Configure and invoke core components
  - Display progress and results to terminal
  - Exit codes for CI/CD integration
- **Interface**: `ai-qa-test run [options]`, `ai-qa-test translate [options]`

---

## Package: agentcore-runner (Future — Feature 5)

The Test Runner agent for AgentCore deployment.

### Component: Runner Agent
- **Purpose**: Execute single scenario on AgentCore with remote browser
- **Responsibilities**:
  - HTTP entrypoint for AgentCore runtime
  - Parse scenario payload from orchestrator
  - Create AgentCore browser_session()
  - Inject CDP connection into execution engine
  - Upload results/reports to S3
  - Support translate action (for orchestrator)

---

## Package: agentcore-orchestrator (Future — Feature 5)

The Orchestrator agent for parallel test execution.

### Component: Orchestrator Agent
- **Purpose**: Fan out parallel test execution
- **Responsibilities**:
  - Read .feature files from S3
  - Manage translation cache in S3
  - Decompose features into scenario payloads
  - Fan out parallel invocations to Test Runner
  - Collect results and generate combined report
  - Upload combined report to S3
