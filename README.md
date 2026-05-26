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
| **Screenshot+Claude** | Extract data from screenshots using Claude | [`05-excel-secrets/screenshot_extract.feature`](examples/05-excel-secrets/screenshot_extract.feature) |
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
| **Trajectory Strict** | Validate URL/screenshot/DOM during replay | `--trajectory-strict` fails on page state mismatch |
| **AgentCore Deploy** | Parallel execution at scale with S3 I/O | `./scripts/deploy-infra.sh` + `./scripts/update-agent.sh` |
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
```

No CloudFormation, no admin involvement. Just rebuilds the container and tells AgentCore to pick up the new image.

### Step 5: Invoke

```bash
# Upload tests to S3
aws s3 sync ./my-tests/ s3://<bucket>/my-project/tests/

# Invoke orchestrator
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn <orchestrator-arn> \
  --payload '{"input_bucket":"<bucket>","input_prefix":"my-project/tests/","output_bucket":"<bucket>","output_prefix":"my-project/results","test_runner_arn":"<test-runner-arn>","max_concurrency":10}'
```

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
