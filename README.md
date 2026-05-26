# AI QA Test Engine

AI-powered QA test execution engine using Nova Act browser automation. Translates Gherkin feature files into executable tests using AI, then runs them with natural language browser automation.

## Quick Start

```bash
# Install (from workspace root)
uv sync

# Run sample tests
cd sample-tests/feature-01-core-execution/
ai-qa-test run --feature-dir ./features/

# Translate only (no execution)
ai-qa-test translate --feature-dir ./features/
```

### Windows

The CLI (`ai-qa-test run`, `translate`, `validate`) works natively on Windows with Python 3.11+ and uv. No WSL needed for running tests.

For the bash scripts (`scripts/test-cli.sh`, `scripts/deploy.sh`), use one of:
- **Windows 11**: WSL2 with WSLg (GUI browser support built-in) — `wsl --install`
- **Windows 10**: WSL2 + headless mode (`--browser-mode headless`)
- **Git Bash**: Works for deploy.sh, limited for test-cli.sh (no mkfifo)

```powershell
# Windows native setup
uv sync
cd sample-tests\feature-01-core-execution\
ai-qa-test run --feature-dir .\features\ --browser-mode headed
```

## Features

| Feature | Description | Example |
|---------|-------------|---------|
| **Gherkin Execution** | Parse and execute .feature files with Nova Act | `Given I am on the home page` → browser navigates |
| **Background Steps** | Shared steps prepended to every scenario | `Background:` block runs before each scenario |
| **Scenario Outline** | Data-driven tests with Examples table | `Scenario Outline:` + `Examples:` expands to N scenarios |
| **Data Tables** | Tabular data in steps | `\| field \| value \|` passed as step parameters |
| **Variable Extraction** | Extract values from page, use in later steps | `store it as "order_id"` → `${order_id}` in next steps |
| **Variable Substitution** | Reference extracted values with `${name}` | `Then I should see "${order_id}"` |
| **Input Variables** | Pre-load variables from JSON file | `--variables-file vars.json` → `${name}` available in all steps |
| **Output Variables** | Save extracted variables to JSON after scenario | Auto-saved to `extracted_variables/<scenario>.json` |
| **Custom Functions** | Call Python functions from Gherkin steps | `I call 'calculate_tax' with amount 100 and store as 'tax'` |
| **Multi-value Return (dict)** | Functions returning dict auto-unpack to `${key.field}` | `store as 'row'` → `${row.name}`, `${row.price}` |
| **Multi-value Return (tuple)** | Comma-separated storage keys unpack tuple/list | `store as 'username, password'` → `${username}`, `${password}` |
| **Reserved Params** | Functions can access browser and context | `nova_act` param = browser, `context` param = variables |
| **Translation Caching** | Cache Gherkin→JSON translation (content-hash) | Second run skips translation, uses cached JSON |
| **Tag-to-URL Mapping** | Map `@tags` to starting URLs | `@MyApp` → `https://myapp.com` via env or JSON file |
| **Excel Data** | Load test data from .xlsx files | `I call 'load_excel_field' with file "data.xlsx" and sheet "Login"` |
| **Secrets (env)** | Fetch secrets from .env for local dev | `I call 'get_secret' with secret_name "PASSWORD" and store as 'pw'` |
| **Secrets (AWS SM)** | Fetch secrets from AWS Secrets Manager | Same as above — tries AWS SM first, falls back to .env |
| **Secure Typing** | Type credentials via Playwright (not Nova Act) | `And I enter "user@example.com" for username` |
| **Screenshot+Claude** | Extract data from screenshots using Claude | `I call 'extract_from_screenshot' with prompt "What is the order ID?"` |
| **@include Steps** | Reuse common step sequences from .steps files | `And @include "login_flow"` expands steps inline |
| **Stop on Failure** | Pause on failure, edit .feature, retry | `--stop-on-failure` keeps browser open, re-translates on Enter |
| **Browser Modes** | Headed, headless, or AgentCore (remote) | `--browser-mode headed` / `headless` |
| **HTML Reports** | Rich dashboard with step details + screenshots | Auto-generated at `reports/report.html` |
| **CLI** | Command-line interface for all operations | `ai-qa-test run --feature-dir ./features/` |
| **Validate Command** | Check variables + functions without running browser | `ai-qa-test validate --feature-dir ./features/` |
| **Video Recording** | Record browser session video | `--video` flag or `ENABLE_VIDEO_RECORDING=true` |
| **Force Re-translate** | Bypass cache and re-translate all features | `--force-translate` |
| **Trajectory Replay** | Cache browser trajectories, replay without AI model calls | Second run auto-replays; `--no-cache` to bypass |
| **@no-cache Annotation** | Skip trajectory cache for specific steps | `When I click submit @no-cache` always uses Nova Act |
| **@id Tag** | Assign explicit scenario IDs for stable naming | `@id:TC-001` → used in workflow names, S3 paths, reports |
| **Trajectory Strict** | Validate URL/screenshot/DOM during replay | `--trajectory-strict` fails on page state mismatch |
| **AgentCore Deploy** | Parallel execution at scale with S3 I/O | `./scripts/deploy.sh` — Orchestrator + N Test Runners |
| **Screenshot on Fail** | Auto-captures screenshot when a step fails | Embedded in HTML report |

### Planned (not yet implemented)

| Feature | Description | Status |
|---------|-------------|--------|
| **Gauge Support** | .md + .cpt test format | Feature 6 |
| **Mobile Testing** | AWS Device Farm integration | Feature 7 |

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

### Deploy

```bash
# Deploy infrastructure (CFN + Docker + S3)
./scripts/deploy.sh --create-ecr

# Upload tests to S3
aws s3 sync ./my-tests/ s3://<bucket>/my-project/tests/

# Invoke orchestrator
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn <orchestrator-arn> \
  --payload '{"input_bucket":"<bucket>","input_prefix":"my-project/tests/","output_bucket":"<bucket>","output_prefix":"my-project/results","test_runner_arn":"<test-runner-arn>","max_concurrency":10}'
```

## Project Structure

```
ai-qa-test-engine/
├── packages/
│   ├── core/          # Execution engine, translation, caching, reporting
│   └── cli/           # Command-line interface
├── sample-tests/      # Sample test suites per feature
└── pyproject.toml     # uv workspace
```

## CLI Commands

```bash
# Execute tests
ai-qa-test run --feature-dir ./features/ [options]

# Options:
#   --browser-mode [headed|headless]  Browser mode (default: headed)
#   --stop-on-failure                 Stop and keep browser open on failure
#   --from-step N                     Resume from step N
#   --force-translate                 Bypass translation cache
#   --no-cache                        Disable trajectory replay (always use Nova Act)
#   --trajectory-strict               Strict trajectory validation (fail on mismatch)
#   --video                           Enable video recording
#   --tag key=url                     Tag-to-URL mapping
#   --functions-file path.py          Custom functions file
#   --tag-url-map-file map.json       Tag-URL mapping JSON file
#   --env-file .env                   Environment file
#   --variables-file vars.json        Pre-load variables from JSON

# Translate only
ai-qa-test translate --feature-dir ./features/ [options]
```

## Configuration

Configuration is loaded from (in order of precedence):
1. CLI flags
2. Environment variables
3. `.env` file in working directory
4. Defaults

See `sample-tests/feature-01-core-execution/.env` for a complete example.

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
