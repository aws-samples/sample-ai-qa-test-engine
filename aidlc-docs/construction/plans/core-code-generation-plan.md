# Code Generation Plan — Feature 1: Core + CLI

## Overview
Port test_translator into monorepo structure, add new modules (cache, browser, reporter, services, CLI).
Build order: workspace setup → core package → CLI package → sample tests.

---

## Step 1: Workspace Setup
- [x] Create `pyproject.toml` (uv workspace root)
- [x] Create `.gitignore`
- [x] Create `.python-version` (3.13)
- [x] Create `README.md` (project overview)

## Step 2: Core Package — Project Files
- [x] Create `packages/core/pyproject.toml`
- [x] Create `packages/core/src/ai_qa_test_engine/__init__.py`

## Step 3: Core — Models (port translator/models.py)
- [x] Create `packages/core/src/ai_qa_test_engine/models.py`

## Step 4: Core — Exceptions (port config/exceptions.py)
- [x] Create `packages/core/src/ai_qa_test_engine/exceptions.py`

## Step 5: Core — Config (port config/app_config.py + decorators.py)
- [x] Create `packages/core/src/ai_qa_test_engine/config.py`

## Step 6: Core — System Prompt (port translator/system_prompt.md)
- [x] Create `packages/core/src/ai_qa_test_engine/prompts/system_prompt.md`

## Step 7: Core — Parser (extract from translator/agent.py)
- [x] Create `packages/core/src/ai_qa_test_engine/parser.py`

## Step 8: Core — Translator (port translator/agent.py)
- [x] Create `packages/core/src/ai_qa_test_engine/translator.py`

## Step 9: Core — Functions (port utils/function_helpers.py + extend)
- [x] Create `packages/core/src/ai_qa_test_engine/functions.py`

## Step 10: Core — Browser Backend (new, extracted from executor)
- [x] Create `packages/core/src/ai_qa_test_engine/browser.py`

## Step 11: Core — Executor (port utils/execution.py)
- [x] Create `packages/core/src/ai_qa_test_engine/executor.py`

## Step 12: Core — Cache Manager (new)
- [x] Create `packages/core/src/ai_qa_test_engine/cache.py`

## Step 13: Core — Reporter (port from deploy_test_translator + adapt)
- [x] Create `packages/core/src/ai_qa_test_engine/reporter.py`

## Step 14: Core — Services (new orchestration layer)
- [x] Create `packages/core/src/ai_qa_test_engine/services.py`

## Step 15: CLI Package — Project Files
- [x] Create `packages/cli/pyproject.toml`
- [x] Create `packages/cli/src/ai_qa_test_engine_cli/__init__.py`

## Step 16: CLI — Main (new)
- [x] Create `packages/cli/src/ai_qa_test_engine_cli/main.py`

## Step 17: Sample Tests
- [x] Create `sample-tests/feature-01-core-execution/features/basic_navigation.feature`
- [x] Create `sample-tests/feature-01-core-execution/features/extraction.feature`
- [x] Create `sample-tests/feature-01-core-execution/features/validation.feature`
- [x] Create `sample-tests/feature-01-core-execution/features/custom_functions.feature`
- [x] Create `sample-tests/feature-01-core-execution/custom_functions.py`
- [x] Create `sample-tests/feature-01-core-execution/tag-url-mapping.json`
- [x] Create `sample-tests/feature-01-core-execution/.env`

## Step 18: Verification
- [ ] Verify all 61 porting checklist items are covered
- [ ] Verify project structure matches design
- [ ] Document run commands for testing

---

## Total Steps: 18
## Estimated Files: ~25 files
