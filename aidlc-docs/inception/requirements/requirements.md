# Requirements — ai-qa-test-engine

## Intent Analysis

- **User Request**: Build a flexible, feature-rich AI-powered QA test execution engine based on the existing test_translator project, with AgentCore deployment for scaling
- **Request Type**: New Project (greenfield, inspired by existing brownfield projects)
- **Scope Estimate**: System-wide — multiple packages, CLI, AgentCore deployment, multiple input formats
- **Complexity Estimate**: Complex — many features, dual execution modes, caching, multiple input formats

## Project Overview

**ai-qa-test-engine** is an AI-powered QA testing framework that:
1. Takes test specifications (Gherkin, Gauge, CSV) and translates them to executable test structures
2. Executes tests using Nova Act browser automation with natural language prompts
3. Supports local execution (developer workflow) and AgentCore deployment (scaled parallel execution)
4. Provides rich reporting with screenshots, artifacts, and drill-down capabilities

The project is a significant evolution of the existing `test_translator` with added flexibility, new features, and production deployment capabilities.

---

## Functional Requirements

### FR-01: Core Gherkin Execution Engine (Priority 1 — First Feature)

**Description**: Port and improve the test_translator's core execution engine.

**Requirements**:
- FR-01.1: Parse Gherkin `.feature` files using `gherkin-official` parser
- FR-01.2: Translate Gherkin AST to structured JSON using Strands Agent + Bedrock
- FR-01.3: Execute translated scenarios step-by-step using Nova Act
- FR-01.4: Support all Gherkin constructs: Background, Scenario, Scenario Outline, Examples, Data Tables
- FR-01.5: Support step types: instruction (act), extraction (expect.as_*), validation (expect.to_*), function_call
- FR-01.6: Variable substitution with `${variable_name}` syntax across steps
- FR-01.7: Variable validation — references must point to variables defined in earlier steps
- FR-01.8: Tag-to-URL mapping (GHERKIN_TAG_* env vars or config file)
- FR-01.9: Per-scenario workflow definition names for Nova Act traceability
- FR-01.10: Support local browser execution (headed and headless modes)

### FR-02: Custom Functions Utility (Priority 1)

**Description**: Bundled utility functions + user-supplied external functions.

**Requirements**:
- FR-02.1: Bundled utility functions directory within the project (e.g., `ai_qa_test_engine/functions/`)
- FR-02.2: Built-in functions for common operations (screenshot+Claude extraction, data formatting, etc.)
- FR-02.3: User-supplied custom functions file specified via config (path to external .py file)
- FR-02.4: When deployed to AgentCore, user functions loaded from S3
- FR-02.5: Support dot-notation for method calls (e.g., `user_service.create_user`)
- FR-02.6: Reserved parameter injection: `nova_act` (browser instance), `context` (variables dict)
- FR-02.7: Function call syntax in Gherkin: "I call 'function_name' with param1 value1 and store as 'var'"
- FR-02.8: Function validation before execution (check all referenced functions exist)

### FR-03: Excel Data Reading (Priority 2)

**Description**: Read Excel files for test data and inject as variables.

**Requirements**:
- FR-03.1: Reference Excel inline in Gherkin steps: `Given data from "TestData.xlsx" sheet "Login"`
- FR-03.2: Load specified sheet and make columns available as variables
- FR-03.3: Support row selection (e.g., by row number, by selection set, or iterate all rows)
- FR-03.4: Variables from Excel available for `${variable_name}` substitution in subsequent steps
- FR-03.5: Excel files stored locally in the test repo (local mode) or S3 (AgentCore mode)

### FR-04: Secrets Management (Priority 2)

**Description**: Secure credential handling for test execution.

**Requirements**:
- FR-04.1: Fetch secrets from AWS Secrets Manager at runtime
- FR-04.2: Local `.env` file fallback for development
- FR-04.3: Secrets injectable as variables using `${secret:secret_name}` or similar syntax
- FR-04.4: Secrets never logged or included in reports
- FR-04.5: Support for Playwright-style credential storage (browser context with saved auth state)

### FR-05: Screenshot + Claude Extraction (Priority 2)

**Description**: Use screenshots + Claude for data extraction as a custom function.

**Requirements**:
- FR-05.1: Implement as a built-in custom function (e.g., `extract_from_screenshot`)
- FR-05.2: Takes a screenshot of current page, sends to Claude (Bedrock), extracts specified data
- FR-05.3: User specifies what to extract via function parameters
- FR-05.4: Returns extracted text/data that can be stored as a variable
- FR-05.5: Callable from Gherkin steps like any other custom function

### FR-06: Common Steps / Include Mechanism (Priority 2)

**Description**: Reusable step groups referenced across feature files.

**Requirements**:
- FR-06.1: Custom `@include "step_group_name"` keyword in Gherkin steps
- FR-06.2: Step groups defined in separate files (e.g., `common_steps/login_flow.steps`)
- FR-06.3: Include resolves at translation time — expands into actual steps
- FR-06.4: Step groups can reference variables (passed in from calling context)
- FR-06.5: Nested includes supported (step group can include another step group)
- FR-06.6: Common steps stored in the test repo (local) or S3 (AgentCore)

### FR-07: Browser Mode Configuration (Priority 1)

**Description**: Support multiple browser execution modes.

**Requirements**:
- FR-07.1: Local browser — headed (visible window for debugging)
- FR-07.2: Local browser — headless (CI/CD, background execution)
- FR-07.3: AgentCore browser — remote browser via CDP (when deployed)
- FR-07.4: Configuration via CLI flag, env var, or config file
- FR-07.5: When running locally with failure stop (FR-08), browser stays open

### FR-08: Stop at Failure and Re-execute (Priority 2)

**Description**: Developer workflow for debugging failed tests.

**Requirements**:
- FR-08.1: CLI flag `--stop-on-failure` keeps browser open at point of failure
- FR-08.2: Print failed step number and context to terminal
- FR-08.3: User edits `.feature` file to fix the step
- FR-08.4: Re-run with `--from-step N` to resume execution from step N
- FR-08.5: Browser session preserved between stop and resume (same browser instance)
- FR-08.6: Only available in local headed mode (not headless, not AgentCore)

### FR-09: Trajectory Replay Caching (Priority 3)

**Description**: Cache and replay browser trajectories for static/repeatable steps.

**Requirements**:
- FR-09.1: Auto-detect: system records trajectories on first run
- FR-09.2: On subsequent runs, replay cached trajectory instead of using Nova Act
- FR-09.3: If trajectory replay fails, automatically fall back to Nova Act for that step
- FR-09.4: Explicit `@no-cache` annotation to force Nova Act for specific steps
- FR-09.5: Trajectory cache stored locally in git repo (local mode) or S3 (AgentCore mode)
- FR-09.6: Cache is committable to git — team members benefit from existing trajectories
- FR-09.7: Support mixed execution: steps 1,7,9 from cache, others via Nova Act
- FR-09.8: Cache invalidation when step text changes

### FR-10: Report Generation (Priority 1)

**Description**: Rich HTML reports with artifact integration.

**Requirements**:
- FR-10.1: Rich HTML dashboard with pass/fail/error counts, timing, overall status
- FR-10.2: Per-scenario drill-down with step details, screenshots, timing
- FR-10.3: Download/link Nova Act workflow artifacts (trajectory logs, recordings)
- FR-10.4: Collapsible sections for easy navigation
- FR-10.5: Error messages with context (step number, original Gherkin text, actual vs expected)
- FR-10.6: Report generated locally (HTML file) or uploaded to S3 (AgentCore mode)
- FR-10.7: Combined report across all features/scenarios in a run

### FR-11: AgentCore Deployment (Priority 2 — after most local features done)

**Description**: Deploy to AgentCore for scaled parallel execution.

**Requirements**:
- FR-11.1: Two-agent architecture: Orchestrator + Test Runner
- FR-11.2: Orchestrator reads `.feature` files from S3
- FR-11.3: Orchestrator manages translation caching in S3 (timestamp-based freshness)
- FR-11.4: Orchestrator decomposes features into scenario payloads
- FR-11.5: Orchestrator fans out parallel invocations to Test Runner (configurable concurrency)
- FR-11.6: Test Runner executes single scenario with AgentCore browser_session()
- FR-11.7: Test Runner uploads per-scenario results and HTML report to S3
- FR-11.8: Orchestrator collects results and generates combined report
- FR-11.9: Custom functions loaded from S3
- FR-11.10: S3 input structure matches existing deploy_test_translator pattern
- FR-11.11: AgentCore browser only when deployed (no browser packaging in container)

### FR-12: Translation Caching (Priority 1)

**Description**: Cache translated JSON to avoid re-translation on every run.

**Requirements**:
- FR-12.1: Local mode: cache translated JSON in local directory (e.g., `translated/`)
- FR-12.2: AgentCore mode: cache translated JSON in S3
- FR-12.3: Cache invalidation when source `.feature` file changes (timestamp or hash comparison)
- FR-12.4: Force re-translate option (CLI flag or config)
- FR-12.5: Cache files are git-committable — team members get pre-translated JSON
- FR-12.6: Multiple team members benefit without re-running translation

### FR-13: Gauge Testing Support (Priority 3 — after Gherkin is solid)

**Description**: Support Gauge test format (.md specification + .cpt concept files).

**Requirements**:
- FR-13.1: Parse Gauge `.md` specification files
- FR-13.2: Parse Gauge `.cpt` concept files (reusable step implementations)
- FR-13.3: Translate Gauge specs to the same internal JSON format as Gherkin
- FR-13.4: Execute using the same execution engine
- FR-13.5: Same reporting, caching, and deployment capabilities as Gherkin

### FR-14: Mobile Testing with AWS Device Farm (Priority 3 — after browser testing is solid)

**Description**: Extend to mobile testing using AWS Device Farm.

**Requirements**:
- FR-14.1: Design execution engine for extensibility to mobile
- FR-14.2: Support Device Farm session creation and management
- FR-14.3: Mobile-specific step types (tap, swipe, etc.)
- FR-14.4: Same Gherkin syntax with mobile-specific annotations

### FR-15: CLI Interface (Priority 1)

**Description**: Command-line interface for all operations.

**Requirements**:
- FR-15.1: `run` command — execute tests from feature files
- FR-15.2: `translate` command — translate features without executing
- FR-15.3: `--browser-mode` flag (headed/headless/agentcore)
- FR-15.4: `--stop-on-failure` flag for debug workflow
- FR-15.5: `--from-step N` flag for resuming from a specific step
- FR-15.6: `--force-translate` flag to bypass cache
- FR-15.7: `--feature-dir` and `--output-dir` options
- FR-15.8: `--tag key=url` for tag-to-URL mappings
- FR-15.9: Configuration via `.env` file, env vars, or CLI flags (CLI > env > .env > defaults)

---

## Non-Functional Requirements

### NFR-01: Performance
- Translation should be cached to avoid repeated Bedrock calls
- Trajectory replay should be significantly faster than Nova Act execution
- Local execution should start within 5 seconds (excluding browser launch)

### NFR-02: Extensibility
- Plugin-like architecture for input formats (Gherkin, Gauge, CSV, future formats)
- Custom function system allows arbitrary Python code injection
- Browser backend abstraction (local, AgentCore, future: Device Farm)

### NFR-03: Developer Experience
- Clear error messages with step context (which step failed, original Gherkin text)
- Debug mode with browser visible and stop-on-failure
- Fast feedback loop (resume from failure point)
- Git-friendly caches (translation JSON, trajectory recordings)

### NFR-04: Reliability
- Graceful handling of Nova Act failures (retry, screenshot on failure)
- Trajectory replay fallback to Nova Act on failure
- Proper cleanup of browser sessions on error

### NFR-05: Compatibility
- Python 3.13 + uv + pyproject.toml
- Must work on macOS and Linux
- AgentCore deployment on AWS (us-east-1)

---

## Architecture Decisions

### AD-01: Monorepo with Separate Packages
- `core` — execution engine, translation, models, caching
- `cli` — command-line interface
- `agentcore-runner` — Test Runner agent for AgentCore deployment
- `agentcore-orchestrator` — Orchestrator agent for AgentCore deployment

### AD-02: Dual Execution Mode
- **Local mode**: Git repo with features, local browser, local file caches
- **AgentCore mode**: S3 input/output, AgentCore browser, S3 caches

### AD-03: Incremental Feature Development Order
1. Core Gherkin execution engine (local, headed browser) + custom functions + translation caching + reports
2. Excel data reading + secrets management + screenshot+Claude extraction
3. Common steps (@include) + stop-on-failure + browser mode config
4. Trajectory replay caching
5. AgentCore deployment (orchestrator + test runner)
6. Gauge testing support
7. Mobile testing (Device Farm)

### AD-04: Caching Strategy
- Translation cache: local dir (git-committable) or S3
- Trajectory cache: local dir (git-committable) or S3
- Cache key: hash of source content (not timestamp) for git-friendliness

---

## Sample Test Repository Structure (User's Repo)

```
my-qa-tests/                          # User's git repo
├── features/                         # Gherkin .feature files
│   ├── login.feature
│   ├── checkout.feature
│   └── search.feature
├── common_steps/                     # Reusable step groups
│   ├── login_flow.steps
│   └── navigation.steps
├── data/                             # Test data
│   ├── TestData.xlsx
│   └── users.xlsx
├── custom_functions.py               # User's custom functions
├── translated/                       # Translation cache (git-committed)
│   ├── login.json
│   ├── checkout.json
│   └── search.json
├── trajectories/                     # Trajectory cache (git-committed)
│   ├── login__login_flow/
│   └── checkout__place_order/
├── reports/                          # Generated reports (gitignored)
│   └── report.html
├── tag-url-mapping.json              # Tag to URL mappings
├── .env                              # Local config (secrets, settings)
└── .gitignore
```

---

## Constraints

- Must preserve all existing test_translator functionality (no regression)
- Nova Act SDK is required for browser automation
- Strands Agents SDK required for Gherkin translation
- AgentCore SDK required for deployment
- One feature developed and tested at a time before moving to next
- Sample tests use Nova Act's next-dot gym for validation
