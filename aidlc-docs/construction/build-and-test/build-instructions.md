# Build Instructions — Feature 1

## Prerequisites

- **Python**: 3.13+
- **uv**: Latest version ([install guide](https://docs.astral.sh/uv/getting-started/installation/))
- **AWS Credentials**: Configured for Bedrock (translation) and Nova Act (execution)
- **OS**: macOS or Linux

## Build Steps

### 1. Navigate to project root

```bash
cd /Users/dedhiaj/projects/ai-qa-test-engine
```

### 2. Create virtual environment and install dependencies

```bash
uv venv
```

```bash
source .venv/bin/activate
```

### 3. Install workspace packages in development mode

```bash
uv pip install -e packages/core
```

```bash
uv pip install -e packages/cli
```

### 4. Verify installation

```bash
ai-qa-test --version
```

Expected output:
```
ai-qa-test, version 0.1.0
```

### 5. Verify imports work

```bash
python -c "from ai_qa_test_engine import Feature, AppConfig; print('Core imports OK')"
```

```bash
python -c "from ai_qa_test_engine_cli.main import cli; print('CLI imports OK')"
```

## Troubleshooting

| Error | Fix |
|-------|-----|
| `No module named 'nova_act'` | `uv pip install nova-act` |
| `No module named 'strands'` | `uv pip install strands-agents` |
| `No module named 'gherkin'` | `uv pip install gherkin-official` |
| `No module named 'click'` | `uv pip install click` |
| `uv: command not found` | Install uv: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
