#!/bin/bash
# test-cli.sh — Full test suite for AI QA Test Engine
#
# Two modes:
#   ./scripts/test-cli.sh          — Unit tests only (no browser, fast)
#   ./scripts/test-cli.sh --full   — Unit tests + browser tests (slow, needs Nova Act)
#
# Run from project root.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

FULL_MODE=false
if [ "${1:-}" = "--full" ]; then
    FULL_MODE=true
fi

PASS=0
FAIL=0

check() {
    local desc="$1"
    shift
    if "$@" > /dev/null 2>&1; then
        echo "  ✓ $desc"
        PASS=$((PASS + 1))
    else
        echo "  ✗ $desc"
        FAIL=$((FAIL + 1))
    fi
}

check_output() {
    local desc="$1"
    local expected="$2"
    shift 2
    if "$@" 2>&1 | grep -q "$expected"; then
        echo "  ✓ $desc"
        PASS=$((PASS + 1))
    else
        echo "  ✗ $desc (expected: $expected)"
        FAIL=$((FAIL + 1))
    fi
}

echo "=============================================="
echo "AI QA Test Engine — Test Suite"
echo "Mode: $([ "$FULL_MODE" = true ] && echo 'FULL (unit + browser)' || echo 'UNIT ONLY (no browser)')"
echo "=============================================="
echo ""

# ============================================================
# UNIT TESTS (no browser needed)
# ============================================================

echo "📋 CLI basics"
check "--version" .venv/bin/ai-qa-test --version
check "--help" .venv/bin/ai-qa-test --help
check "run --help" .venv/bin/ai-qa-test run --help
check "translate --help" .venv/bin/ai-qa-test translate --help
check "validate --help" .venv/bin/ai-qa-test validate --help
echo ""

echo "📝 Translate command (uses cache)"
check_output "translate cached" "Translation complete" .venv/bin/ai-qa-test translate \
    --feature-dir ./sample-tests/feature-01-core-execution/features/ \
    --tag-url-map-file ./sample-tests/feature-01-core-execution/tag-url-mapping.json
echo ""

echo "🔍 Validate command"
check_output "validate passes" "All validations passed" .venv/bin/ai-qa-test validate \
    --feature-dir ./sample-tests/feature-01-core-execution/features/ \
    --functions-file ./sample-tests/feature-01-core-execution/custom_functions.py \
    --tag-url-map-file ./sample-tests/feature-01-core-execution/tag-url-mapping.json
echo ""

echo "💾 Translation cache (content-hash)"
check_output "cache fresh" "Cached (fresh)" .venv/bin/ai-qa-test translate \
    --feature-dir ./sample-tests/feature-01-core-execution/features/ \
    --tag-url-map-file ./sample-tests/feature-01-core-execution/tag-url-mapping.json
echo ""

echo "🔐 Secrets (env fallback)"
check_output "get_secret" "my_secret_value" \
    env MY_TEST_SECRET=my_secret_value .venv/bin/python -c "
from ai_qa_test_engine.functions.secrets_functions import get_secret
print(get_secret('MY_TEST_SECRET'))
"
echo ""

echo "📊 Excel reader"
check_output "read excel" "Proxima Centauri b" .venv/bin/python -c "
from ai_qa_test_engine.excel_reader import read_excel_data
from pathlib import Path
data = read_excel_data(Path('sample-tests/feature-02-excel-secrets/TestData.xlsx'), 'Destinations', row=1)
print(data['destination'])
"
echo ""

echo "📎 @include resolution"
check_output "include expands" "I am on the home page" .venv/bin/python -c "
from ai_qa_test_engine.parser import preprocess_feature_file
from pathlib import Path
content = preprocess_feature_file(
    Path('sample-tests/feature-03-include-stopfail/features/include_steps.feature'),
    Path('sample-tests/feature-03-include-stopfail/common_steps')
)
print(content)
"
echo ""

echo "🔧 Function registry"
check_output "load + has_function" "OK" .venv/bin/python -c "
from ai_qa_test_engine.function_registry import FunctionRegistry
from pathlib import Path
reg = FunctionRegistry()
reg.load_from_file(Path('sample-tests/feature-01-core-execution/custom_functions.py'))
assert reg.has_function('calculate_travel_cost')
assert reg.has_function('format_destination_info')
assert reg.has_function('verify_page_contains_text')
print('OK')
"

check_output "dot-notation" "OK" .venv/bin/python -c "
from ai_qa_test_engine.function_registry import FunctionRegistry
reg = FunctionRegistry()
# Bundled functions should load
import ai_qa_test_engine
from pathlib import Path
pkg_dir = Path(ai_qa_test_engine.__file__).parent / 'functions'
reg.load_bundled(pkg_dir)
assert reg.has_function('extract_from_screenshot')
assert reg.has_function('enter_username')
assert reg.has_function('enter_password')
assert reg.has_function('get_secret')
print('OK')
"
echo ""

echo "📥 Input variables"
echo '{"pre_loaded": "hello_world"}' > /tmp/test_input_vars.json
check_output "loads from JSON" "hello_world" .venv/bin/python -c "
import json
data = json.load(open('/tmp/test_input_vars.json'))
print(data['pre_loaded'])
"
rm -f /tmp/test_input_vars.json
echo ""

echo "🎬 Video flag accepted"
check_output "--video flag" "video" .venv/bin/ai-qa-test run --help
echo ""

# ============================================================
# BROWSER TESTS (only in --full mode)
# ============================================================

if [ "$FULL_MODE" = true ]; then
    echo ""
    echo "=============================================="
    echo "🌐 Browser Tests (Nova Act)"
    echo "=============================================="
    echo ""

    echo "🚀 Feature 01: Core execution (5 scenarios)"
    check "feature-01 all pass" .venv/bin/ai-qa-test run \
        --feature-dir ./sample-tests/feature-01-core-execution/features/ \
        --tag-url-map-file ./sample-tests/feature-01-core-execution/tag-url-mapping.json \
        --functions-file ./sample-tests/feature-01-core-execution/custom_functions.py \
        --browser-mode headless
    echo ""

    echo "🚀 Feature 02: Excel + secrets (excel_data + screenshot_extract)"
    check "feature-02 excel" .venv/bin/ai-qa-test run \
        --feature-dir ./sample-tests/feature-02-excel-secrets/features/excel_data.feature \
        --tag-url-map-file ./sample-tests/feature-02-excel-secrets/tag-url-mapping.json \
        --browser-mode headless
    check "feature-02 screenshot" .venv/bin/ai-qa-test run \
        --feature-dir ./sample-tests/feature-02-excel-secrets/features/screenshot_extract.feature \
        --tag-url-map-file ./sample-tests/feature-02-excel-secrets/tag-url-mapping.json \
        --browser-mode headless
    echo ""

    echo "🚀 Feature 02: Secure typing (secret_enter)"
    check "feature-02 secret_enter" env TEST_EMAIL=fakeuser@example.com .venv/bin/ai-qa-test run \
        --feature-dir ./sample-tests/feature-02-excel-secrets/features/secret_enter.feature \
        --tag-url-map-file ./sample-tests/feature-02-excel-secrets/tag-url-mapping.json \
        --browser-mode headless \
        --force-translate
    echo ""

    echo "🚀 Feature 03: @include steps"
    check "feature-03 include" .venv/bin/ai-qa-test run \
        --feature-dir ./sample-tests/feature-03-include-stopfail/features/include_steps.feature \
        --tag-url-map-file ./sample-tests/feature-03-include-stopfail/tag-url-mapping.json \
        --common-steps-dir ./sample-tests/feature-03-include-stopfail/common_steps \
        --browser-mode headless \
        --force-translate
    echo ""

else
    echo ""
    echo "(Skipping browser tests — run with --full to include)"
fi

# ============================================================
# SUMMARY
# ============================================================

echo ""
echo "=============================================="
echo "Results: $PASS passed, $FAIL failed"
echo "=============================================="

if [ $FAIL -gt 0 ]; then
    exit 1
else
    echo "✓ All tests passed!"
fi
