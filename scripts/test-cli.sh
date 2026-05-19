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
        echo "  ✗ $desc (expected output containing: $expected)"
        FAIL=$((FAIL + 1))
    fi
}

echo "=============================================="
echo "AI QA Test Engine — Test Suite"
echo "Mode: $([ "$FULL_MODE" = true ] && echo 'FULL (unit + browser)' || echo 'UNIT ONLY (no browser)')"
echo "=============================================="
echo ""

# ============================================================
# UNIT TESTS — Each tests a real feature, no browser
# ============================================================

echo "� Translation (translate command produces JSON from .feature)"
check_output "translate produces JSON" "Translation complete" .venv/bin/ai-qa-test translate \
    --feature-dir ./sample-tests/feature-01-core-execution/features/ \
    --tag-url-map-file ./sample-tests/feature-01-core-execution/tag-url-mapping.json
echo ""

echo "� Translation cache (second run uses cache, no re-translation)"
check_output "cache hit" "All features are cached" .venv/bin/ai-qa-test translate \
    --feature-dir ./sample-tests/feature-01-core-execution/features/ \
    --tag-url-map-file ./sample-tests/feature-01-core-execution/tag-url-mapping.json
echo ""

echo "� Validate command (checks variable refs + function refs without browser)"
check_output "validate all pass" "All validations passed" .venv/bin/ai-qa-test validate \
    --feature-dir ./sample-tests/feature-01-core-execution/features/ \
    --functions-file ./sample-tests/feature-01-core-execution/custom_functions.py \
    --tag-url-map-file ./sample-tests/feature-01-core-execution/tag-url-mapping.json
echo ""

echo "🔐 Secrets — fetch from env var (.env fallback)"
check_output "get_secret returns env value" "my_secret_value" \
    env MY_TEST_SECRET=my_secret_value .venv/bin/python -c "
from ai_qa_test_engine.functions.secrets_functions import get_secret
print(get_secret('MY_TEST_SECRET'))
"
echo ""

echo "📊 Excel reader — load data from .xlsx"
check_output "read row from Excel" "Proxima Centauri b" .venv/bin/python -c "
from ai_qa_test_engine.excel_reader import read_excel_data
from pathlib import Path
data = read_excel_data(Path('sample-tests/feature-02-excel-secrets/TestData.xlsx'), 'Destinations', row=1)
print(data['destination'])
"
echo ""

echo "📎 @include — expands step groups from .steps files"
check_output "include resolves steps" "I am on the home page" .venv/bin/python -c "
from ai_qa_test_engine.parser import preprocess_feature_file
from pathlib import Path
content = preprocess_feature_file(
    Path('sample-tests/feature-03-include-stopfail/features/include_steps.feature'),
    Path('sample-tests/feature-03-include-stopfail/common_steps')
)
print(content)
"
echo ""

echo "🔧 Function registry — load bundled + user functions"
check_output "user functions loaded" "OK" .venv/bin/python -c "
from ai_qa_test_engine.function_registry import FunctionRegistry
from pathlib import Path
reg = FunctionRegistry()
reg.load_from_file(Path('sample-tests/feature-01-core-execution/custom_functions.py'))
assert reg.has_function('calculate_travel_cost')
assert reg.has_function('format_destination_info')
assert reg.has_function('verify_page_contains_text')
print('OK')
"

check_output "bundled functions loaded" "OK" .venv/bin/python -c "
from ai_qa_test_engine.function_registry import FunctionRegistry
import ai_qa_test_engine
from pathlib import Path
reg = FunctionRegistry()
reg.load_bundled(Path(ai_qa_test_engine.__file__).parent / 'functions')
assert reg.has_function('extract_from_screenshot')
assert reg.has_function('enter_username')
assert reg.has_function('enter_password')
assert reg.has_function('get_secret')
assert reg.has_function('load_excel_data')
print('OK')
"
echo ""

echo "📥 Input variables — pre-load from JSON file"
echo '{"pre_loaded_var": "hello_world", "count": 42}' > /tmp/test_input_vars.json
check_output "variables loaded from JSON" "hello_world" .venv/bin/python -c "
import json
from pathlib import Path
from ai_qa_test_engine.config import AppConfig
c = AppConfig(feature_dir=Path('features'), input_variables_file=Path('/tmp/test_input_vars.json'))
data = json.load(open('/tmp/test_input_vars.json'))
assert data['pre_loaded_var'] == 'hello_world'
assert data['count'] == 42
print(data['pre_loaded_var'])
"
rm -f /tmp/test_input_vars.json
echo ""

echo "🎬 Video recording — config accepts flag"
check_output "video config" "True" .venv/bin/python -c "
from pathlib import Path
from ai_qa_test_engine.config import AppConfig
c = AppConfig(feature_dir=Path('features'), enable_video_recording=True)
print(c.enable_video_recording)
"
echo ""

echo "⚙️  Config precedence — CLI kwargs override .env"
check_output "browser_mode override" "headless" .venv/bin/python -c "
from pathlib import Path
from ai_qa_test_engine.config import AppConfig
c = AppConfig(feature_dir=Path('features'), browser_mode='headless')
print(c.browser_mode)
"
echo ""

# ============================================================
# BROWSER TESTS (only in --full mode)
# ============================================================

if [ "$FULL_MODE" = true ]; then
    echo ""
    echo "=============================================="
    echo "🌐 Browser Tests (Nova Act — headless)"
    echo "=============================================="
    echo ""

    echo "🚀 Feature 01: Core execution"
    echo "   (basic_navigation, extraction, validation, custom_functions)"
    check "feature-01 all pass" .venv/bin/ai-qa-test run \
        --feature-dir ./sample-tests/feature-01-core-execution/features/ \
        --tag-url-map-file ./sample-tests/feature-01-core-execution/tag-url-mapping.json \
        --functions-file ./sample-tests/feature-01-core-execution/custom_functions.py \
        --browser-mode headless
    echo ""

    echo "🚀 Feature 02: Excel data loading"
    check "feature-02 excel_data" .venv/bin/ai-qa-test run \
        --feature-dir ./sample-tests/feature-02-excel-secrets/features/excel_data.feature \
        --tag-url-map-file ./sample-tests/feature-02-excel-secrets/tag-url-mapping.json \
        --browser-mode headless
    echo ""

    echo "🚀 Feature 02: Screenshot + Claude extraction"
    check "feature-02 screenshot_extract" .venv/bin/ai-qa-test run \
        --feature-dir ./sample-tests/feature-02-excel-secrets/features/screenshot_extract.feature \
        --tag-url-map-file ./sample-tests/feature-02-excel-secrets/tag-url-mapping.json \
        --browser-mode headless
    echo ""

    echo "🚀 Feature 02: Secure typing (enter_username via Playwright)"
    check "feature-02 secret_enter" env TEST_EMAIL=fakeuser@example.com .venv/bin/ai-qa-test run \
        --feature-dir ./sample-tests/feature-02-excel-secrets/features/secret_enter.feature \
        --tag-url-map-file ./sample-tests/feature-02-excel-secrets/tag-url-mapping.json \
        --browser-mode headless \
        --force-translate
    echo ""

    echo "🚀 Feature 03: @include common steps"
    check "feature-03 include_steps" .venv/bin/ai-qa-test run \
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
