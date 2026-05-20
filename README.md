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
| **Trajectory Strict** | Validate URL/screenshot/DOM during replay | `--trajectory-strict` fails on page state mismatch |
| **Screenshot on Fail** | Auto-captures screenshot when a step fails | Embedded in HTML report |

### Planned (not yet implemented)

| Feature | Description | Status |
|---------|-------------|--------|
| **AgentCore Deploy** | Parallel execution at scale with S3 I/O | Feature 5 |
| **Gauge Support** | .md + .cpt test format | Feature 6 |
| **Mobile Testing** | AWS Device Farm integration | Feature 7 |

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
