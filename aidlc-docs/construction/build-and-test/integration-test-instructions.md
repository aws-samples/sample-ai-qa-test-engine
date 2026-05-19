# Integration Test Instructions — Feature 1

## Overview

Integration tests verify that all components work together end-to-end:
Parser → Translator → Cache → Executor → Browser → Reporter

Since Feature 1 is local-only, integration testing IS the sample test execution.
The "unit tests" in `unit-test-instructions.md` are effectively integration tests.

## Full Integration Test

Run all sample tests end-to-end:

```bash
cd /Users/dedhiaj/projects/ai-qa-test-engine/sample-tests/feature-01-core-execution
```

```bash
ai-qa-test run --feature-dir ./features/
```

## Component Integration Verification

### 1. Parser + Translator Integration
Verify Gherkin parsing feeds correctly into translation:
```bash
ai-qa-test translate --feature-dir ./features/
```
Then inspect `translated/*.json` — verify:
- Each .feature produced a .json
- JSON contains correct scenarios with classified steps
- Variable references are validated
- Tags are preserved

### 2. Cache Integration
```bash
# First run — translates
ai-qa-test translate --feature-dir ./features/

# Verify cache files exist
ls translated/
ls translated/.*.hash

# Second run — uses cache (should be instant)
ai-qa-test translate --feature-dir ./features/

# Modify a feature file, re-run — should re-translate only that file
echo "# comment" >> ./features/basic_navigation.feature
ai-qa-test translate --feature-dir ./features/

# Clean up
git checkout ./features/basic_navigation.feature
```

### 3. Executor + Browser Integration
```bash
ai-qa-test run --feature-dir ./features/basic_navigation.feature
```
Verify:
- Browser opens (headed mode)
- Navigation occurs
- Steps execute sequentially
- Browser closes after completion

### 4. Functions + Executor Integration
```bash
ai-qa-test run --feature-dir ./features/custom_functions.feature
```
Verify:
- Custom functions loaded from `custom_functions.py`
- Parameters resolved (including ${variable} substitution)
- Results stored in variable context
- Subsequent steps can reference stored results

### 5. Reporter Integration
After any run, verify:
```bash
cat reports/summary.json | python -m json.tool
open reports/report.html
```
Verify:
- JSON summary has correct counts
- HTML report renders correctly
- Step details are present
- Timing information is accurate

## Regression Test Command

After building any subsequent feature (2, 3, 4, 5), run this to verify Feature 1 still works:

```bash
cd /Users/dedhiaj/projects/ai-qa-test-engine/sample-tests/feature-01-core-execution
ai-qa-test run --feature-dir ./features/
```

Exit code 0 = regression passes.
