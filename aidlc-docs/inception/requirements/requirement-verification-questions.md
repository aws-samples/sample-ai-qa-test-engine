# Requirements Verification Questions

Please answer the following questions to help clarify the requirements for ai-qa-test-engine.
Fill in the letter choice (or custom response) after each [Answer]: tag.

---

## Question 1
What is the primary execution mode for the first iteration? (We'll develop one feature at a time)

A) Local execution only (run tests locally with local browser, no AgentCore)
B) AgentCore deployment only (remote execution with AgentCore browser)
C) Both local and AgentCore from the start (configurable via flag/env)
D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 2
For the "custom functions utility" — how should custom functions be organized?

A) Single Python file (like current `custom_functions_sample.py`)
B) A directory of Python files auto-discovered (e.g., `functions/*.py`)
C) A registry/decorator pattern where functions self-register (e.g., `@custom_function`)
D) All of the above — single file, directory, or decorated functions all supported
E) Other (please describe after [Answer]: tag below)

[Answer]: E - a set of bundled utility function in a directory (dont need auto-discovery), but then user can supply some functions that will be outside this project that need get included somehow especially later when we need in agentcore runtime

---

## Question 3
For "read Excel for data" — what's the expected usage pattern?

A) Excel file specified per feature file (e.g., via a tag or annotation in the .feature file)
B) Excel file specified globally in config (one data source for all tests)
C) Excel file referenced inline in Gherkin steps (e.g., `Given data from "TestData.xlsx" sheet "Login"`)
D) All of the above — flexible referencing from tags, config, or inline steps
E) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## Question 4
For secrets management — what's the scope?

A) Only AWS Secrets Manager (fetch secrets at runtime, inject into variables)
B) AWS Secrets Manager + local .env file fallback for development
C) AWS Secrets Manager + support for other providers (Azure Key Vault, HashiCorp Vault)
D) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 5
For "extracting data via screenshot + Claude" — when should this be used vs Nova Act extraction?

A) Always use screenshot+Claude for extraction (replace Nova Act extraction entirely)
B) User explicitly chooses per step (e.g., annotation like `@screenshot-extract`)
C) Auto-fallback: try Nova Act extraction first, if it fails use screenshot+Claude
D) Configurable default with per-step override capability
E) Other (please describe after [Answer]: tag below)

[Answer]: E - Make it a custom function and user can specify in the step

---

## Question 6
For "common steps referenced from elsewhere" — what's the preferred syntax?

A) Custom `@import` annotation at feature level (e.g., `@import("common/login_steps.feature")`)
B) Custom `@include` step keyword (e.g., `And @include "login_flow"`)
C) Separate `.steps` files that define reusable step groups, referenced by name
D) Background-like blocks in a shared file, referenced by a custom tag
E) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 7
For "trajectory replay caching" — how should cacheable steps be indicated?

A) Explicit annotation in Gherkin (e.g., `@cacheable` on a step or scenario)
B) Auto-detect: system records trajectories and replays them automatically on subsequent runs
C) Configuration file mapping step patterns to cached trajectories
D) Hybrid: auto-detect + explicit `@no-cache` to force Nova Act for specific steps
E) Other (please describe after [Answer]: tag below)

[Answer]: D

---

## Question 8
For "stop at failure and re-execute from that point" — what's the expected developer workflow?

A) CLI-based: test stops, prints step number, user edits .feature, runs with `--from-step N`
B) Interactive: test stops, opens browser, waits for user to edit and press Enter to continue
C) File-watcher: test stops, watches .feature file for changes, auto-resumes on save
D) All of the above as options (CLI flag determines behavior)
E) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 9
For the report generation — what level of detail is needed?

A) Simple pass/fail summary with step details (like current test_translator)
B) Rich HTML dashboard with screenshots, timing, drill-down per step (like deploy_test_translator)
C) Full artifact download from Nova Act workflow + layered report on top
D) B + C combined (rich dashboard that also links to/embeds Nova Act artifacts)
E) Other (please describe after [Answer]: tag below)

[Answer]: D

---

## Question 10
For Gauge testing support (.md + .cpt files) — what's the priority?

A) Core feature — must be in first iteration alongside Gherkin
B) Second priority — implement after Gherkin is fully working
C) Nice-to-have — implement only if time permits
D) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 11
For CSV file support — what format is expected?

A) CSV with columns: Step Keyword, Step Text (simple step list)
B) CSV with columns: Step Keyword, Step Text, Expected Result, Step Type
C) Free-form CSV where columns map to Gherkin constructs (configurable mapping)
D) Other (please describe after [Answer]: tag below)

[Answer]: D - skip this for now. will need more thought

---

## Question 12
For mobile testing with AWS Device Farm — what's the priority and scope?

A) Core feature — must be in first iteration
B) Second priority — implement after browser testing is solid
C) Future feature — design for extensibility now, implement later
D) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 13
For the incremental development approach — what's the first feature to build and test?

A) Core Gherkin execution engine (port test_translator with improvements, local browser only)
B) AgentCore deployment (get basic execution working on AgentCore first)
C) Excel data reading + variable injection
D) Custom functions utility
E) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 14
What Python version and package manager should be used?

A) Python 3.11 + pip + requirements.txt
B) Python 3.11 + uv + pyproject.toml
C) Python 3.12 + uv + pyproject.toml
D) Python 3.13 + uv + pyproject.toml
E) Other (please describe after [Answer]: tag below)

[Answer]: D

---

## Question 15
For the project structure — should it be a monorepo or separate packages?

A) Single package (all code in one `src/ai_qa_test_engine/` directory)
B) Monorepo with separate packages (core, cli, agentcore-runner, etc.)
C) Single package with clear module boundaries (like test_translator but bigger)
D) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 16: Security Extensions
Should security extension rules be enforced for this project?

A) Yes — enforce all SECURITY rules as blocking constraints (recommended for production-grade applications)
B) No — skip all SECURITY rules (suitable for PoCs, prototypes, and experimental projects)
C) Other (please describe after [Answer]: tag below)

[Answer]: B

---
