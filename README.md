# AI QA Test Engine

AI-powered QA test execution engine using Nova Act browser automation. Translates Gherkin feature files into executable tests using AI, then runs them with natural language browser automation.

## Quick Start

```bash
# Install (from workspace root)
uv sync

# Run sample tests
cd examples/01-basic-navigation/
ai-qa-test run --feature-dir . --tag-url-map-file ./tag-url-mapping.json

# Translate only (no execution)
ai-qa-test translate --feature-dir . --tag-url-map-file ./tag-url-mapping.json
```

### Windows

The CLI (`ai-qa-test run`, `translate`, `validate`) works natively on Windows with Python 3.11+ and uv. No WSL needed for running tests.

For the bash scripts (`scripts/test-cli.sh`, `scripts/deploy-infra.sh`, `scripts/update-agent.sh`), use one of:
- **Windows 11**: WSL2 with WSLg (GUI browser support built-in) — `wsl --install`
- **Windows 10**: WSL2 + headless mode (`--browser-mode headless`)
- **Git Bash**: Works for deploy/update scripts, limited for test-cli.sh (no mkfifo)

```powershell
# Windows native setup
uv sync
cd sample-tests\feature-01-core-execution\
ai-qa-test run --feature-dir .\features\ --browser-mode headed
```

## Features

| Feature | Description | Example |
|---------|-------------|---------|
| **Gherkin Execution** | Parse and execute .feature files with Nova Act | [`01-basic-navigation/`](examples/01-basic-navigation/) |
| **Background Steps** | Shared steps prepended to every scenario | [`02-extraction-validation/`](examples/02-extraction-validation/) |
| **Scenario Outline** | Data-driven tests with Examples table | [`04-data-driven/scenario_outline.feature`](examples/04-data-driven/scenario_outline.feature) |
| **Data Tables** | Tabular data in steps | [`04-data-driven/data_tables.feature`](examples/04-data-driven/data_tables.feature) |
| **Variable Extraction** | Extract values from page, use in later steps | [`02-extraction-validation/extraction.feature`](examples/02-extraction-validation/extraction.feature) |
| **Variable Substitution** | Reference extracted values with `${name}` | [`02-extraction-validation/extraction.feature`](examples/02-extraction-validation/extraction.feature) |
| **Input Variables** | Pre-load variables from JSON file | [`04-data-driven/input_variables.feature`](examples/04-data-driven/input_variables.feature) |
| **Output Variables** | Save extracted variables to JSON after scenario | [`02-extraction-validation/`](examples/02-extraction-validation/) |
| **Custom Functions** | Call Python functions from Gherkin steps | [`03-custom-functions/functions.feature`](examples/03-custom-functions/functions.feature) |
| **Multi-value Return (dict)** | Functions returning dict auto-unpack to `${key.field}` | [`03-custom-functions/multi_value.feature`](examples/03-custom-functions/multi_value.feature) |
| **Multi-value Return (tuple)** | Comma-separated storage keys unpack tuple/list | [`03-custom-functions/multi_value.feature`](examples/03-custom-functions/multi_value.feature) |
| **Reserved Params** | Functions can access browser and context | [`03-custom-functions/custom_functions.py`](examples/03-custom-functions/custom_functions.py) |
| **Translation Caching** | Cache Gherkin→JSON translation (content-hash) | All examples (automatic) |
| **Tag-to-URL Mapping** | Map `@tags` to starting URLs | [`01-basic-navigation/tag-url-mapping.json`](examples/01-basic-navigation/tag-url-mapping.json) |
| **Excel Data** | Load test data from .xlsx files | [`05-excel-secrets/excel_data.feature`](examples/05-excel-secrets/excel_data.feature) |
| **Secrets (env)** | Fetch secrets from .env for local dev | [`05-excel-secrets/secrets.feature`](examples/05-excel-secrets/secrets.feature) |
| **Secrets (AWS SM)** | Fetch secrets from AWS Secrets Manager | [`05-excel-secrets/secrets.feature`](examples/05-excel-secrets/secrets.feature) |
| **Secure Typing** | Type credentials via Playwright (not Nova Act) | [`05-excel-secrets/secrets.feature`](examples/05-excel-secrets/secrets.feature) |
| **Screenshot Extraction** | Extract data from screenshots using AI vision | [`05-excel-secrets/screenshot_extract.feature`](examples/05-excel-secrets/screenshot_extract.feature) |
| **@include Steps** | Reuse common step sequences from .steps files | [`06-include-reuse/`](examples/06-include-reuse/) |
| **Stop on Failure** | Pause on failure, edit .feature, retry | [`07-stop-on-failure/`](examples/07-stop-on-failure/) |
| **Browser Modes** | Headed, headless, or AgentCore (remote) | `--browser-mode headed` / `headless` |
| **HTML Reports** | Rich dashboard with step details + screenshots | Auto-generated at `reports/report.html` |
| **CLI** | Command-line interface for all operations | `ai-qa-test run --feature-dir ./features/` |
| **Validate Command** | Check variables + functions without running browser | `ai-qa-test validate --feature-dir ./features/` |
| **Video Recording** | Record browser session video | `--video` flag or `ENABLE_VIDEO_RECORDING=true` |
| **Force Re-translate** | Bypass cache and re-translate all features | `--force-translate` |
| **Trajectory Replay** | Cache browser trajectories, replay without AI model calls | [`08-trajectory-replay/`](examples/08-trajectory-replay/) |
| **@no-cache Annotation** | Skip trajectory cache for specific steps | [`08-trajectory-replay/trajectory.feature`](examples/08-trajectory-replay/trajectory.feature) |
| **@id Tag** | Assign explicit scenario IDs for stable naming | [`02-extraction-validation/extraction.feature`](examples/02-extraction-validation/extraction.feature) |
| **Tag Filtering** | Run specific scenarios by tag (`--tags @smoke`, `not @slow`) | [`02-extraction-validation/extraction.feature`](examples/02-extraction-validation/extraction.feature) |
| **Trajectory Strict** | Validate URL/screenshot/DOM during replay | `--trajectory-strict` fails on page state mismatch |
| **AgentCore Deploy** | Parallel execution at scale with S3 I/O | `./scripts/deploy-infra.sh` + `./scripts/update-agent.sh` |
| **Screenshot on Fail** | Auto-captures screenshot when a step fails | Embedded in HTML report |

## AgentCore Deployment (Parallel Execution at Scale)

Deploy the engine to AWS AgentCore for parallel test execution with S3 I/O.

### Architecture

```
User → Orchestrator Agent → N × Test Runner Agents (parallel)
         ↕ S3                    ↕ S3 + AgentCore Browser
```

- **Orchestrator**: Reads .feature files from S3, manages translation cache, fans out scenarios to Test Runners, collects results, generates combined HTML report
- **Test Runner**: Executes a single scenario using AgentCore's remote browser (CDP), uploads results to S3

### S3 Structure

```
s3://my-bucket/
├── my-project/tests/
│   ├── features/              ← .feature files
│   ├── translated/            ← translation cache (auto-managed)
│   ├── tag-url-mapping.json
│   └── custom-functions/
│       └── custom_functions.py
└── my-project/results/
    └── run-20260520-123456/
        ├── summary.json
        ├── combined-report.html
        └── scenarios/...
```

### Two-Team Deployment Model

The deployment is split into two scripts for separation of concerns:

| Script | Who | When | What |
|--------|-----|------|------|
| `scripts/deploy-infra.sh` | Admin team | One-time (or infra changes) | Creates ECR, CodeBuild, IAM roles, S3, AgentCore runtimes via CFN |
| `scripts/update-agent.sh` | Developer team | Every code change | Rebuilds containers + updates runtimes (no CFN, no admin) |

### Step 1: Admin — Pre-create IAM Role (Optional)

If your org requires pre-created roles, hand your admin `infra/iam-policy-reference.json`. They create the role and give you the ARN.

### Step 2: Admin — Deploy Infrastructure (One-Time)

```bash
# With pre-created role
./scripts/deploy-infra.sh --role-arn arn:aws:iam::123456789012:role/my-role

# Or let CFN create the role
./scripts/deploy-infra.sh
```

This creates all infrastructure and builds the initial container images (~5-8 min).

### Step 3: Admin — Grant Developer Permissions

Attach `infra/iam-developer-policy.json` to the developer team's IAM role. This gives them permission to rebuild containers and update runtimes without any IAM or CFN access.

### Step 4: Developer — Update Agent Code (Ongoing)

```bash
# Update both agents (~2-3 min)
./scripts/update-agent.sh

# Update only the test runner
./scripts/update-agent.sh --runner-only

# Update only the orchestrator
./scripts/update-agent.sh --orchestrator-only

# Fire and forget (don't wait for build)
./scripts/update-agent.sh --no-wait

# Set custom idle timeout (default: 900s / 15 min)
./scripts/update-agent.sh --idle-timeout 1800
```

No CloudFormation, no admin involvement. Just rebuilds the container and tells AgentCore to pick up the new image.

### Step 5: Invoke

```bash
# Upload tests to S3
aws s3 sync ./my-tests/ s3://<bucket>/my-project/tests/

# Invoke orchestrator (payload must be base64-encoded for AWS CLI)
PAYLOAD=$(echo '{"input_bucket":"<bucket>","input_prefix":"my-project/tests/","output_bucket":"<bucket>","output_prefix":"my-project/results","max_concurrency":10}' | base64)
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn <orchestrator-arn> \
  --payload "$PAYLOAD" \
  --cli-read-timeout 300 \
  --region us-east-1 /tmp/result.json

# Run only @smoke scenarios
PAYLOAD=$(echo '{"input_bucket":"<bucket>","input_prefix":"my-project/tests/","output_bucket":"<bucket>","output_prefix":"my-project/results","tag_filter":"@smoke"}' | base64)

# Exclude @negative-test scenarios
PAYLOAD=$(echo '{"input_bucket":"<bucket>","input_prefix":"my-project/tests/","output_bucket":"<bucket>","output_prefix":"my-project/results","tag_filter":"not @negative-test"}' | base64)

# Combine tags (AND/OR)
# tag_filter supports: "@smoke", "not @slow", "@smoke and @login", "@smoke or @regression"
```

> **Important — `--cli-read-timeout`**: The AWS CLI's default socket read timeout is ~60s. For invocations expected to run longer than 60 seconds (most real test runs), pass `--cli-read-timeout 300` (or higher, up to 900). Without this, the CLI will retry on its own when its read timeout fires — even though the agent is still working — and you'll see duplicate executions.

### Tag-to-URL Mapping Format

The `tag-url-mapping.json` file in your test S3 prefix maps Gherkin `@tags` to starting URLs:

```json
{
  "@MyApp": "https://my-app.example.com",
  "@Staging": "https://staging.example.com",
  "default": "https://default.example.com"
}
```

Keys are matched case-insensitively, with or without the `@` prefix — so `@MyApp`, `myapp`, or `MyApp` all resolve to the same URL.

### Lifecycle Configuration (Idle Timeout)

Each AgentCore Runtime has two lifecycle settings:

| Setting | Default | Range | What it controls |
|---------|---------|-------|------------------|
| `idleRuntimeSessionTimeout` | 900s (15 min) | 60s–28800s | Time the platform considers a session "idle" before terminating |
| `maxLifetime` | 28800s (8 hr) | 60s–28800s | Maximum total session age regardless of activity |

**Important**: A handler that blocks synchronously (e.g., `time.sleep(120)`, browser automation, long custom functions) is considered "idle" by the platform unless you explicitly signal otherwise. Both agents in this project use `add_async_task` / `complete_async_task` to mark themselves as `HealthyBusy` during long operations, which prevents the platform from killing the session during sync work.

To override the default timeout for a runtime:

```bash
aws bedrock-agentcore-control update-agent-runtime \
  --agent-runtime-id <runtime-id> \
  --agent-runtime-artifact '{"containerConfiguration":{"containerUri":"<ecr-uri>:latest"}}' \
  --network-configuration '{"networkMode":"PUBLIC"}' \
  --lifecycle-configuration '{"idleRuntimeSessionTimeout":1800,"maxLifetime":28800}' \
  --role-arn <execution-role-arn> \
  --region us-east-1
```

**Synchronous request limit**: regardless of session lifecycle, a single synchronous `InvokeAgentRuntime` HTTP request is bounded by **15 minutes** (AWS service quota, not adjustable). Use multiple invocations (or a future async polling pattern) for runs that exceed this.

### IAM Reference Files

| File | Audience | Purpose |
|------|----------|---------|
| `infra/iam-policy-reference.json` | Admin | AgentCore execution role (what the runtime assumes at runtime) |
| `infra/iam-developer-policy.json` | Admin | Developer permissions (what devs need for `update-agent.sh`) |
| `infra/cfn-template.yaml` | Admin | Full infrastructure definition |

## Project Structure

```
ai-qa-test-engine/
├── packages/
│   ├── core/                    # Execution engine, translation, caching, reporting
│   ├── cli/                     # Command-line interface
│   ├── agentcore-runner/        # AgentCore Test Runner agent
│   └── agentcore-orchestrator/  # AgentCore Orchestrator agent
├── examples/                    # Syntax reference + runnable examples
│   ├── 01-basic-navigation/
│   ├── 02-extraction-validation/
│   ├── 03-custom-functions/
│   ├── 04-data-driven/
│   ├── 05-excel-secrets/
│   ├── 06-include-reuse/
│   ├── 07-stop-on-failure/
│   └── 08-trajectory-replay/
├── infra/                       # CloudFormation template
├── scripts/                     # deploy-infra.sh, update-agent.sh, destroy.sh, test-cli.sh
└── pyproject.toml               # uv workspace
```

## CLI Reference

### `ai-qa-test run`

Execute tests from Gherkin feature files.

```bash
ai-qa-test run --feature-dir ./features/ [options]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--feature-dir` | PATH | required | Directory containing .feature files |
| `--output-dir` | PATH | `./reports` | Directory for HTML reports |
| `--browser-mode` | `headed`/`headless` | `headed` | Browser visibility mode |
| `--stop-on-failure` | flag | off | Pause on failure, keep browser open for debugging |
| `--force-translate` | flag | off | Bypass translation cache, re-translate all features |
| `--video` | flag | off | Record browser session video |
| `--no-cache` | flag | off | Disable trajectory replay (always use Nova Act) |
| `--trajectory-strict` | flag | off | Fail if page state differs during trajectory replay |
| `--max-steps` | INT | 30 | Max steps per act() call. Override per-step with `@max-steps:N` |
| `--tags` | STRING | — | Filter scenarios by tag (`@smoke`, `not @slow`, `@id:TC-001`) |
| `--tag` | KEY=URL | — | Tag-to-URL mapping (repeatable) |
| `--functions-file` | PATH | — | Custom functions .py file or directory (repeatable) |
| `--env-file` | PATH | `.env` | Path to environment file |
| `--tag-url-map-file` | PATH | — | Path to tag-url-mapping.json |
| `--common-steps-dir` | PATH | — | Directory containing .steps files for @include |
| `--variables-file` | PATH | — | JSON file with pre-loaded input variables |

### `ai-qa-test translate`

Translate Gherkin features to JSON without executing.

```bash
ai-qa-test translate --feature-dir ./features/ [options]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--feature-dir` | PATH | required | Directory containing .feature files |
| `--output-dir` | PATH | `./translated` | Directory for translated JSON output |
| `--tag` | KEY=URL | — | Tag-to-URL mapping (repeatable) |
| `--model-id` | STRING | — | Bedrock model ID for translation |
| `--force` | flag | off | Force re-translation (bypass cache) |
| `--env-file` | PATH | `.env` | Path to environment file |
| `--tag-url-map-file` | PATH | — | Path to tag-url-mapping.json |

### `ai-qa-test validate`

Check variable references and function calls without running browser.

```bash
ai-qa-test validate --feature-dir ./features/ [options]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--feature-dir` | PATH | required | Directory containing .feature files |
| `--functions-file` | PATH | — | Custom functions .py file |
| `--tag-url-map-file` | PATH | — | Path to tag-url-mapping.json |
| `--env-file` | PATH | `.env` | Path to environment file |
| `--force-translate` | flag | off | Force re-translation before validating |

## Environment Variables

All CLI options can also be set via environment variables (in `.env` or exported):

| Variable | CLI Equivalent | Description |
|----------|---------------|-------------|
| `FEATURE_DIR` | `--feature-dir` | Feature files directory |
| `REPORT_DIR` | `--output-dir` | Reports output directory |
| `BROWSER_MODE` | `--browser-mode` | `headed` or `headless` |
| `STOP_ON_FAILURE` | `--stop-on-failure` | `true`/`false` |
| `FORCE_TRANSLATE` | `--force-translate` | `true`/`false` |
| `ENABLE_VIDEO_RECORDING` | `--video` | `true`/`false` |
| `NO_CACHE` | `--no-cache` | `true`/`false` |
| `TRAJECTORY_STRICT` | `--trajectory-strict` | `true`/`false` |
| `MAX_STEPS` | `--max-steps` | Max steps per act() call (default: 30) |
| `CUSTOM_FUNCTIONS_FILE` | `--functions-file` | Path to .py file or directory |
| `TAG_URL_MAP_FILE` | `--tag-url-map-file` | Path to mapping JSON |
| `COMMON_STEPS_DIR` | `--common-steps-dir` | Path to .steps directory |
| `INPUT_VARIABLES_FILE` | `--variables-file` | Path to variables JSON |
| `DEFAULT_TEST_URL` | — | Fallback URL when no tag matches |
| `GHERKIN_TAG_<NAME>` | `--tag NAME=url` | Per-tag URL mapping (e.g., `GHERKIN_TAG_MYAPP=https://...`) |
| `BEDROCK_MODEL_ID` | `--model-id` | Bedrock model for translation |
| `NOVA_ACT_API_KEY` | — | Nova Act API key (skips WorkflowDefinition) |

## Scripts Reference

### `scripts/deploy-infra.sh` (Admin — one-time)

```bash
./scripts/deploy-infra.sh [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--stack-name NAME` | `ai-qa-test-engine` | CloudFormation stack name |
| `--region REGION` | `us-east-1` | AWS region |
| `--role-arn ARN` | — | Pre-created IAM role (skip role creation) |
| `--test-bucket NAME` | — | Pre-created S3 bucket (skip bucket creation) |

### `scripts/update-agent.sh` (Developer — ongoing)

```bash
./scripts/update-agent.sh [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--stack-name NAME` | `ai-qa-test-engine` | CloudFormation stack name |
| `--region REGION` | `us-east-1` | AWS region |
| `--runner-only` | — | Only update the test-runner agent |
| `--orchestrator-only` | — | Only update the orchestrator agent |
| `--no-wait` | — | Don't wait for CodeBuild to finish |
| `--idle-timeout SECS` | `900` | Idle session timeout (60–28800) |
| `--max-lifetime SECS` | `28800` | Max session lifetime (60–28800) |

Environment variable overrides: `STACK_NAME`, `AWS_REGION`, `IDLE_SESSION_TIMEOUT`, `MAX_LIFETIME`

### `scripts/destroy.sh`

```bash
./scripts/destroy.sh [--stack-name NAME] [--region REGION]
```

Removes all AWS resources (ECR, CodeBuild, runtimes, S3 bucket, IAM roles).

## Orchestrator Payload Reference

The orchestrator accepts a JSON payload with these fields:

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `input_bucket` | yes | — | S3 bucket containing test features |
| `input_prefix` | yes | — | S3 prefix for test files (e.g., `my-project/tests/`) |
| `output_bucket` | yes | — | S3 bucket for results |
| `output_prefix` | yes | — | S3 prefix for results (e.g., `my-project/results`) |
| `test_runner_arn` | no | `TEST_RUNNER_ARN` env var | Override test runner ARN (set automatically by CFN) |
| `max_concurrency` | no | `10` | Max parallel test runner invocations |
| `force_retranslate` | no | `false` | Force re-translation of all features |
| `bedrock_model_id` | no | — | Override Bedrock model for translation |
| `tag_filter` | no | — | Filter scenarios by tag (e.g., `@smoke`, `not @slow`) |

**Minimal payload** (test_runner_arn comes from env var):
```json
{
  "input_bucket": "my-bucket",
  "input_prefix": "my-project/tests/",
  "output_bucket": "my-bucket",
  "output_prefix": "my-project/results"
}
```

**Full payload:**
```json
{
  "input_bucket": "my-bucket",
  "input_prefix": "my-project/tests/",
  "output_bucket": "my-bucket",
  "output_prefix": "my-project/results",
  "max_concurrency": 5,
  "tag_filter": "@smoke",
  "force_retranslate": true,
  "bedrock_model_id": null
}
```

## Scenario IDs

Each scenario gets a canonical ID used for workflow names, S3 paths, and extracted variable files.

**Option 1: Explicit `@id` tag (recommended for stable IDs)**

```gherkin
@id:TC-LOGIN-001
Scenario: Successful login
  Given I am on the login page
  ...
```

The ID `TC-LOGIN-001` is used everywhere: workflow definition, S3 result path, extracted variables key.

**Option 2: Auto-generated (fallback)**

Without `@id`, the ID is derived from: `{filename}__{feature_slug}__{scenario_slug}`

Example: `extraction__data_extraction__extract_and_verify_destination_name`

**Extracted variables output format:**

```json
// extracted_variables/data_extraction.json
{
  "feature": "Data Extraction",
  "scenarios": {
    "tc_ext_001": {
      "scenario_name": "Extract and verify destination name",
      "scenario_id": "tc_ext_001",
      "variables": {"destination_name": "Proxima Centauri b"}
    },
    "tc_ext_002": {
      "scenario_name": "Extract multiple values",
      "scenario_id": "tc_ext_002",
      "variables": {"destination_name": "Proxima Centauri b", "mass_info": "1.27 Earth masses"}
    }
  }
}
```

## Tag Filtering (Run Specific Scenarios)

Filter which scenarios to execute using Gherkin tags:

```bash
# Run only @smoke scenarios
ai-qa-test run --feature-dir ./examples/02-extraction-validation/ --tags "@smoke"

# Run by scenario ID
ai-qa-test run --feature-dir ./examples/02-extraction-validation/ --tags "@id:TC-EXT-001"

# Exclude slow tests
ai-qa-test run --feature-dir ./features/ --tags "not @slow"

# Combine with AND/OR
ai-qa-test run --feature-dir ./features/ --tags "@smoke and @login"
ai-qa-test run --feature-dir ./features/ --tags "@smoke or @regression"
```

Tag your scenarios in Gherkin:
```gherkin
@smoke @id:TC-NAV-001
Scenario: Navigate to destinations page
  Given I am on the home page
  ...

@regression @id:TC-EXT-002
Scenario: Extract multiple values
  ...
```

Also works in AgentCore mode — add `"tag_filter": "@smoke"` to the orchestrator payload.

## Writing Tests

```gherkin
@MyApp
Feature: User Login
  Scenario: Successful login
    Given I am on the login page
    When I enter "user@example.com" in the email field
    And I enter "password123" in the password field
    And I click the "Sign In" button
    Then I should see the dashboard
    And the welcome message should contain "user@example.com"
```

## Development

```bash
# Setup
uv sync

# Run from source
uv run ai-qa-test run --feature-dir ./sample-tests/feature-01-core-execution/features/
```

## Custom Functions

Custom functions are Python functions loaded from a file via `--functions-file`. They can return single values, dicts (auto-unpacked), or tuples (positional unpack).

### Single value return

```python
# custom_functions.py
def calculate_tax(amount, rate=0.08):
    return amount * rate
```

```gherkin
When I call 'calculate_tax' with amount 100 and store as "tax"
Then the tax should equal "${tax}"   # tax = 8.0
```

### Dict return (auto-unpacked to ${key.field})

```python
def get_user_profile(user_id):
    return {"name": "Alice", "email": "alice@example.com", "role": "admin"}
```

```gherkin
When I call 'get_user_profile' with user_id "123" and store as "user"
Then I should see "${user.name}" on the page       # Alice
And the email field should show "${user.email}"    # alice@example.com
And the role should be "${user.role}"              # admin
```

### Tuple/list return (positional unpack with comma-separated keys)

```python
def get_credentials(env="staging"):
    return ("testuser@example.com", "s3cret!")
```

```gherkin
When I call 'get_credentials' with env "staging" and store as "username, password"
And I enter "${username}" for username
And I enter "${password}" for password
```

### Accessing browser and context

Functions can declare `nova_act` and `context` parameters to access the browser session and extracted variables:

```python
def take_screenshot_and_extract(prompt, nova_act, context):
    """Uses browser to screenshot, then extracts data."""
    page = nova_act.get_page()
    screenshot = page.screenshot()
    # ... process screenshot ...
    return extracted_value
```

### Loading functions

Functions can be specified via CLI in three ways:

```bash
# Single file
ai-qa-test run --functions-file ./custom_functions.py

# Directory (loads all .py files, enables cross-file imports)
ai-qa-test run --functions-file ./my_functions/

# Multiple sources
ai-qa-test run --functions-file ./helpers.py --functions-file ./main_functions.py
```

**Directory mode** adds the directory to `sys.path`, so files can import each other:

```
my_functions/
├── helpers.py          # def multiply(a, b): return a * b
└── main_functions.py   # from helpers import multiply
```

You can also set `CUSTOM_FUNCTIONS_FILE=./my_functions/` in `.env`.

## Variable Storage & Resolution

Variables come from multiple sources and are stored in a unified nested dictionary. Dotted keys create nested structures, ensuring input variables and extracted variables use the same path — no ambiguity.

| Storage Pattern | Example | How Stored | How Read |
|---|---|---|---|
| Simple key | `store as "order_id"` | `variables["order_id"] = "ORD-123"` | `${order_id}` |
| Dotted key | `store as "dealer.email"` | `variables["dealer"]["email"] = "x@y.com"` | `${dealer.email}` |
| Tuple unpack | `store as "username, password"` | `variables["username"]`, `variables["password"]` | `${username}`, `${password}` |
| Dict return | `store as "stats"` (func returns dict) | `variables["stats"] = {"gravity": "1.1g"}` | `${stats.gravity}` |
| Input variables | `--variables-file` with `{"target": {"destination": "X"}}` | `variables["target"] = {"destination": "X"}` | `${target.destination}` |

**Key behaviors:**
- Extraction with a dotted key (e.g., `dealer.email`) overwrites the same path in input variables — single source of truth
- Tuple unpack keys are always flat (no dot traversal)
- Dict returns store the whole dict under the key — access fields via `${key.field}`
- Resolution order: direct key lookup first, then dotted path traversal

## Trajectory Replay (Speed Up Repeated Runs)

On first run, the engine records browser actions (clicks, scrolls) as trajectory JSON files. On subsequent runs, cached action steps replay without calling the AI model — saving time and API costs.

**How it works:**
1. First run: Nova Act executes normally, trajectories saved to `trajectories/` dir
2. Second run: Action steps replay from cache (no AI call), validation steps still use AI (they read page content)
3. Cache key: based on the resolved instruction text — if variables change, cache misses automatically

**CLI flags:**
```bash
# Normal run (cache enabled by default)
ai-qa-test run --feature-dir ./features/

# Disable cache (always use Nova Act)
ai-qa-test run --feature-dir ./features/ --no-cache

# Strict validation during replay (fail if page state differs)
ai-qa-test run --feature-dir ./features/ --trajectory-strict
```

**Per-step control:** Add `@no-cache` to any step to skip replay for that step:
```gherkin
When I click the submit button @no-cache
```

**Requires:** `nova-act-samples` on PYTHONPATH for replay (falls back to Nova Act if not available).

## Max Steps (Control Nova Act Step Budget)

Nova Act has a default limit of 30 steps per `act()` call. For complex interactions (multi-page forms, long wizards), you can increase this.

**Global default (all steps):**
```bash
ai-qa-test run --feature-dir ./features/ --max-steps 50
```

Or via environment variable:
```
MAX_STEPS=50
```

**Per-step override (specific steps only):**
```gherkin
Scenario: Complete multi-page registration
  Given I am on the registration page
  When I fill out the entire registration wizard @max-steps:60
  Then I should see the confirmation page
```

The `@max-steps:60` annotation overrides the global default just for that one step. Other steps still use the global value (default 30).

**AgentCore mode:** Set `MAX_STEPS` as an environment variable on the runtime, or pass in the orchestrator payload.

## Stop on Failure (Interactive Debugging)

When a step fails, the browser stays open so you can inspect the page, edit the `.feature` file to fix the step, then press Enter to re-translate and resume.

```bash
ai-qa-test run --feature-dir ./features/ --stop-on-failure
```

**Flow:**
1. Step fails → browser stays open, terminal shows error
2. You edit the `.feature` file (fix the failing step)
3. Press Enter in the terminal
4. Engine re-translates the feature, detects the first changed step, resumes from there
5. If the fix works, execution continues to the end

**Note:** The browser state must be compatible with where you're resuming from. If you changed an earlier step, the page might not be in the right state.

## @include (Reusable Step Sequences)

Extract common step sequences into `.steps` files and include them in multiple features.

**Create a `.steps` file:**
```
# common_steps/login_flow.steps
Given I am on the login page
When I enter "user@example.com" for username
And I enter "password123" for password
And I click the Sign In button
```

**Use in a feature:**
```gherkin
Scenario: View dashboard after login
  And @include "login_flow"
  Then I should see the dashboard
```

**CLI:**
```bash
ai-qa-test run --feature-dir ./features/ --common-steps-dir ./common_steps/
```

The `@include` directive is expanded before translation — the AI sees the full steps, not the include reference.

## Secrets (Credentials & Sensitive Data)

Secrets are fetched at runtime — never hardcoded in `.feature` files.

**Lookup order:**
1. Environment variable (`.env` file or shell)
2. AWS Secrets Manager (automatic fallback if env var not found)

**Local development (env vars):**
```bash
# Set in .env or export in shell
TEST_EMAIL=fakeuser@example.com
TEST_PASSWORD=my_secret_pass

# Run
ai-qa-test run --feature-dir ./examples/05-excel-secrets/secrets.feature \
  --tag-url-map-file ./examples/05-excel-secrets/tag-url-mapping.json
```

**AWS (Secrets Manager) — for AgentCore or CI/CD:**
```bash
# Create the secret
aws secretsmanager create-secret \
  --name TEST_EMAIL \
  --secret-string "real-user@company.com" \
  --region us-east-1

# Or as a JSON bundle (multiple values in one secret)
aws secretsmanager create-secret \
  --name my-app/credentials \
  --secret-string '{"TEST_EMAIL":"user@co.com","TEST_PASSWORD":"s3cret"}' \
  --region us-east-1
```

The engine auto-detects: if the env var isn't set, it tries AWS Secrets Manager with the same name.

**In Gherkin:**
```gherkin
# Fetch and store
When I call 'get_secret' with secret_name "TEST_EMAIL" and store as "email"

# Use in a step
And I enter "${email}" for username
```

**Secure typing** (Playwright, not Nova Act — bypasses guardrails on auth pages):
```gherkin
And I enter "user@example.com" for username    # Uses Playwright keyboard.type()
And I enter "password123" for password         # Uses Playwright keyboard.type()
```

## AgentCore Deployment — Quick Reference

For full deployment guide, see the [AgentCore Deployment section](#agentcore-deployment-parallel-execution-at-scale) above.

**Results location:**
```
my-project/results/run-20260526-123456/
├── summary.json           ← pass/fail counts, durations
├── combined-report.html   ← dashboard with all scenarios
└── scenarios/
    └── <scenario_id>/
        ├── result.json    ← step-level details + extracted variables
        └── report.html    ← individual scenario report
```

**Teardown:**
```bash
./scripts/destroy.sh       # Removes all AWS resources
```

