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

- **Gherkin → Nova Act**: AI translates BDD test steps into browser automation prompts
- **Variable System**: Extract values from pages, use `${variable_name}` in later steps
- **Custom Functions**: Call Python functions from Gherkin steps
- **Translation Caching**: Cache translations locally (git-committable) to avoid repeated AI calls
- **Rich Reports**: HTML dashboard with step details, screenshots, timing
- **Browser Modes**: Headed (debug), headless (CI), AgentCore (scaled)
- **AgentCore Deployment**: Parallel test execution at scale (Feature 5)

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
#   --tag key=url                     Tag-to-URL mapping
#   --functions-file path.py          Custom functions file
#   --tag-url-map-file map.json       Tag-URL mapping JSON file
#   --env-file .env                   Environment file

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
