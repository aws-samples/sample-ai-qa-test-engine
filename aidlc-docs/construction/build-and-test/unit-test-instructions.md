# Unit Test Instructions — Feature 1

## Overview

For Feature 1, "unit tests" are the sample Gherkin test files that exercise the engine end-to-end against Nova Act's Next Dot Gym. These are integration tests by nature (they require a browser and Nova Act), but they serve as our verification that the ported code works correctly.

## Quick Smoke Test (Single Scenario)

Run just the basic navigation test to verify the engine works:

```bash
cd /Users/dedhiaj/projects/ai-qa-test-engine/sample-tests/feature-01-core-execution
```

```bash
ai-qa-test run --feature-dir ./features/basic_navigation.feature
```

Expected: Scenario passes, HTML report generated in `reports/`.

## Run All Feature 1 Sample Tests

```bash
cd /Users/dedhiaj/projects/ai-qa-test-engine/sample-tests/feature-01-core-execution
```

```bash
ai-qa-test run --feature-dir ./features/
```

Expected:
- All 4 feature files translated (or loaded from cache)
- All scenarios execute against Next Dot Gym
- HTML report generated at `reports/report.html`
- Exit code 0 (all pass)

## Test Translation Only (No Execution)

Verify translation works without needing Nova Act browser:

```bash
cd /Users/dedhiaj/projects/ai-qa-test-engine/sample-tests/feature-01-core-execution
```

```bash
ai-qa-test translate --feature-dir ./features/
```

Expected:
- JSON files created in `translated/` directory
- Hash files created (`.basic_navigation.hash`, etc.)
- No browser launched

## Test Cache Behavior

### First run (translates):
```bash
ai-qa-test translate --feature-dir ./features/
```

### Second run (uses cache):
```bash
ai-qa-test translate --feature-dir ./features/
```
Expected: "All features are cached, no translation needed"

### Force re-translate:
```bash
ai-qa-test translate --feature-dir ./features/ --force
```
Expected: Re-translates all features regardless of cache

## Test Custom Functions

The `custom_functions.feature` exercises:
- Function call syntax parsing
- Parameter passing with variable substitution
- Result storage in variables
- Reserved parameter injection (nova_act, context)

```bash
ai-qa-test run --feature-dir ./features/custom_functions.feature
```

## Test Headless Mode

```bash
ai-qa-test run --feature-dir ./features/basic_navigation.feature --browser-mode headless
```

Expected: Same results, no visible browser window.

## Verify Reports

After any run, check:
```bash
open reports/report.html
```

Report should contain:
- Dashboard with pass/fail counts
- Collapsible scenario sections
- Step details with timing
- Screenshots on failure (if any)

## Expected Test Results

| Feature File | Scenarios | Expected |
|-------------|-----------|----------|
| basic_navigation.feature | 1 | PASS |
| extraction.feature | 2 | PASS |
| validation.feature | 1 | PASS |
| custom_functions.feature | 1 | PASS |
| **Total** | **5** | **ALL PASS** |
