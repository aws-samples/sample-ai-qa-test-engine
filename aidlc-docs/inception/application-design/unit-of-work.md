# Units of Work

## Decomposition Strategy

Given the "port first, modify minimally" approach and incremental feature development, we decompose into **2 units for Feature 1**:

1. **Unit: core** — The execution engine (ported from test_translator + new modules)
2. **Unit: cli** — The command-line interface (new, replaces pytest runner)

The AgentCore packages (units 3 & 4) are deferred to Feature 5.

---

## Unit 1: core

**Package**: `packages/core/`
**Type**: Python library package
**Priority**: Must be built first (cli depends on it)

**Description**: Contains all business logic for parsing, translating, executing, caching, and reporting. Mostly ported from test_translator with minimal modifications.

**Modules**:
| Module | Source | Status |
|--------|--------|--------|
| `models.py` | test_translator/translator/models.py | Port as-is + add StepResult, RunSummary |
| `config.py` | test_translator/config/app_config.py | Port + extend (CLI args, cache_dir, browser_mode) |
| `exceptions.py` | test_translator/config/exceptions.py | Port as-is |
| `translator.py` | test_translator/translator/agent.py | Port as-is |
| `executor.py` | test_translator/utils/execution.py | Port + extract browser creation, add from_step, add StepResult collection |
| `functions.py` | test_translator/utils/function_helpers.py | Port + add FunctionRegistry class |
| `parser.py` | NEW (extract from translator/agent.py) | Gherkin parsing + @include resolution |
| `browser.py` | NEW (extract from executor) | Browser session abstraction |
| `cache.py` | NEW | Local file cache with content-hash |
| `reporter.py` | Port from deploy_test_translator/reporting.py | Adapt for local use |
| `services.py` | NEW | Thin orchestration wrappers |
| `prompts/system_prompt.md` | test_translator/translator/system_prompt.md | Port as-is |

**Dependencies**: 
- nova-act
- strands-agents
- gherkin-official
- pydantic, pydantic-settings
- python-dotenv
- boto3 (optional, for S3 cache mode)

---

## Unit 2: cli

**Package**: `packages/cli/`
**Type**: Python CLI application (installable as `ai-qa-test` command)
**Priority**: Built after core

**Description**: Thin CLI wrapper that configures and invokes core services. Replaces the pytest-based test runner from test_translator.

**Modules**:
| Module | Source | Status |
|--------|--------|--------|
| `main.py` | NEW | Click/Typer CLI with run/translate commands |

**Dependencies**:
- ai-qa-test-engine (core package)
- click or typer

**CLI Commands**:
- `ai-qa-test run` — Execute tests
- `ai-qa-test translate` — Translate only

---

## Unit 3: agentcore-runner (DEFERRED — Feature 5)

**Package**: `packages/agentcore-runner/`
**Type**: AgentCore agent (Container build)
**Priority**: Feature 5

---

## Unit 4: agentcore-orchestrator (DEFERRED — Feature 5)

**Package**: `packages/agentcore-orchestrator/`
**Type**: AgentCore agent (CodeZip build)
**Priority**: Feature 5

---

## Build Order

```
Unit 1 (core) → Unit 2 (cli) → [test with sample-tests] → Feature 1 complete
```

Unit 2 depends on Unit 1. They are built sequentially within this AI-DLC run.
