# Business Rules — Core Package

## Rules Ported from test_translator (unchanged)

### BR-01: Step Type XOR Constraint
Each TestStep must have EXACTLY ONE of: instruction, extraction, validation, function_call.
- Enforced by Pydantic model_validator in TestStep
- Zero set → ValidationError
- Multiple set → ValidationError

### BR-02: Variable Reference Validation
All `${variable_name}` references must point to variables defined by extraction or function_call steps EARLIER in the scenario.
- Enforced by model_validator in TestScenario
- A step cannot reference its own extraction key
- Variables are registered AFTER the step's references are validated

### BR-03: Function Validation Before Execution
All function_call steps must reference functions that exist in the loaded modules.
- Validated before any step executes
- Checks function name exists (supports dot-notation)
- Does NOT validate parameter signatures (runtime error if wrong)

### BR-04: Reserved Parameter Injection
Functions with parameters named `nova_act` or `context` get those injected automatically:
- `nova_act` → the active NovaActQa browser instance
- `context` → dict with `{'variables': extracted_values}`

### BR-05: Comparison Mapping
Validation comparisons map to NovaActQa methods:
- "equal", "contain", "match", "greater_than", "less_than", "greater_or_equal", "less_or_equal" → `to_{comparison}`
- "true", "false" → `to_be_{comparison}`

### BR-06: Scenario Outline Expansion
Scenario Outlines are expanded into concrete scenarios (one per Examples row) during translation.
- Name format: "{original_name} - Example {row_number}"
- Placeholder substitution from Examples table

### BR-07: Background Steps
Background steps are prepended to every scenario in the feature during translation.
- Maintain original keywords
- Execute before scenario-specific steps

### BR-08: Tag-to-URL Resolution
Feature tags map to starting URLs:
- Check each tag against tag_url_map
- First match wins
- Fallback to "default" key if no match
- Error if no mapping found

---

## New Rules (Feature 1)

### BR-09: Cache Invalidation by Content Hash
Translation cache is invalidated when source file content changes:
- SHA-256 hash of .feature file content
- Hash stored alongside cached JSON
- Stale = stored hash ≠ current hash
- Force-translate bypasses cache entirely

### BR-10: Step Result Collection
Every step produces a StepResult regardless of pass/fail:
- PASSED: step completed successfully
- FAILED: assertion/validation failed (test failure)
- ERROR: unexpected exception (infrastructure/code error)
- Screenshot captured on FAILED or ERROR

### BR-11: From-Step Resume
When `from_step` is specified:
- Steps 1..N-1 are marked as SKIPPED (not executed)
- Execution begins at step N
- Variable context is empty (no prior extractions available)
- Browser must already be at the correct state (user responsibility)

### BR-12: Browser Mode Selection
- "headed": Local Chrome, visible window, tty=False
- "headless": Local Chrome, no window, headless=True
- "agentcore": Remote browser via CDP (Feature 5)
- Default: "headed" (developer-friendly)

### BR-13: Report Generation
- Always generate per-scenario HTML with step details
- Always generate combined HTML dashboard
- Always generate JSON summary
- Screenshots embedded as base64 (no external files)
- Report written to config.report_dir

---

## Validation Rules (from Pydantic models — unchanged)

| Model | Field | Rule |
|-------|-------|------|
| TestStep | instruction/extraction/validation/function_call | Exactly one must be set (XOR) |
| TestScenario | steps | Variable references must be defined earlier |
| Extraction | extraction_type | Must be "string", "number", or "boolean" |
| Validation | comparison | Must be one of the defined comparison types |
| FunctionCall | function_name | Non-empty string |
| Feature | base_url | Resolved from tags (non-empty after resolution) |
