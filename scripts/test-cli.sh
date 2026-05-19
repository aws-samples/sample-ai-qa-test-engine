#!/bin/bash
# test-cli.sh — Full test suite for AI QA Test Engine
#
# Runs ALL tests: unit tests + browser tests (Nova Act).
# Run from project root: ./scripts/test-cli.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

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

check_fail() {
    # Expects the command to FAIL (non-zero exit)
    local desc="$1"
    shift
    if "$@" > /dev/null 2>&1; then
        echo "  ✗ $desc (expected failure but got success)"
        FAIL=$((FAIL + 1))
    else
        echo "  ✓ $desc"
        PASS=$((PASS + 1))
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
        echo "  ✗ $desc (expected output: $expected)"
        FAIL=$((FAIL + 1))
    fi
}

check_not_output() {
    # Verifies the expected string is NOT in output
    local desc="$1"
    local unexpected="$2"
    shift 2
    if "$@" 2>&1 | grep -q "$unexpected"; then
        echo "  ✗ $desc (unexpected output found: $unexpected)"
        FAIL=$((FAIL + 1))
    else
        echo "  ✓ $desc"
        PASS=$((PASS + 1))
    fi
}

check_file_exists() {
    local desc="$1"
    local path="$2"
    if [ -f "$path" ]; then
        echo "  ✓ $desc"
        PASS=$((PASS + 1))
    else
        echo "  ✗ $desc (file not found: $path)"
        FAIL=$((FAIL + 1))
    fi
}

echo "=============================================="
echo "AI QA Test Engine — Full Test Suite"
echo "=============================================="
echo ""

# ============================================================
# 1. TRANSLATION
# ============================================================
echo "📝 Translation"
check_output "translate produces JSON" "Translation complete" .venv/bin/ai-qa-test translate \
    --feature-dir ./sample-tests/feature-01-core-execution/features/ \
    --tag-url-map-file ./sample-tests/feature-01-core-execution/tag-url-mapping.json

# Verify JSON files actually exist
check_file_exists "basic_navigation.json created" "translated/basic_navigation.json"
check_file_exists "extraction.json created" "translated/extraction.json"
check_file_exists "custom_functions.json created" "translated/custom_functions.json"

# Verify JSON is valid and has scenarios
check_output "JSON has scenarios" "scenarios" .venv/bin/python -c "
import json
data = json.load(open('translated/basic_navigation.json'))
assert 'scenarios' in data
assert len(data['scenarios']) > 0
print('scenarios')
"
echo ""

# ============================================================
# 2. TRANSLATION CACHE
# ============================================================
echo "💾 Translation cache"
# Cache hit — no re-translation
check_output "cache hit (no re-translate)" "All features are cached" .venv/bin/ai-qa-test translate \
    --feature-dir ./sample-tests/feature-01-core-execution/features/ \
    --tag-url-map-file ./sample-tests/feature-01-core-execution/tag-url-mapping.json

# Verify "Translating" does NOT appear (proves no Bedrock call)
check_not_output "no Bedrock call on cache hit" "Translating basic_navigation" .venv/bin/ai-qa-test translate \
    --feature-dir ./sample-tests/feature-01-core-execution/features/ \
    --tag-url-map-file ./sample-tests/feature-01-core-execution/tag-url-mapping.json

# Cache invalidation — modify file, verify re-translation triggered
cp sample-tests/feature-01-core-execution/features/basic_navigation.feature /tmp/basic_nav_backup.feature
echo "# cache invalidation test" >> sample-tests/feature-01-core-execution/features/basic_navigation.feature
check_output "cache invalidation triggers re-translate" "Translating" .venv/bin/ai-qa-test translate \
    --feature-dir ./sample-tests/feature-01-core-execution/features/basic_navigation.feature \
    --tag-url-map-file ./sample-tests/feature-01-core-execution/tag-url-mapping.json
# Restore original
cp /tmp/basic_nav_backup.feature sample-tests/feature-01-core-execution/features/basic_navigation.feature
rm /tmp/basic_nav_backup.feature
# Re-cache the original
.venv/bin/ai-qa-test translate \
    --feature-dir ./sample-tests/feature-01-core-execution/features/basic_navigation.feature \
    --tag-url-map-file ./sample-tests/feature-01-core-execution/tag-url-mapping.json > /dev/null 2>&1
echo ""

# ============================================================
# 3. VALIDATE COMMAND
# ============================================================
echo "🔍 Validate command"
check_output "validate passes with valid features" "All validations passed" .venv/bin/ai-qa-test validate \
    --feature-dir ./sample-tests/feature-01-core-execution/features/ \
    --functions-file ./sample-tests/feature-01-core-execution/custom_functions.py \
    --tag-url-map-file ./sample-tests/feature-01-core-execution/tag-url-mapping.json
echo ""

# ============================================================
# 4. SECRETS
# ============================================================
echo "🔐 Secrets"
# Success case — env var found
check_output "get_secret returns env value" "my_secret_value" \
    env MY_TEST_SECRET=my_secret_value .venv/bin/python -c "
from ai_qa_test_engine.functions.secrets_functions import get_secret
print(get_secret('MY_TEST_SECRET'))
"

# Failure case — missing secret raises KeyError
check_output "missing secret raises error" "KeyError" .venv/bin/python -c "
from ai_qa_test_engine.functions.secrets_functions import get_secret
try:
    get_secret('NONEXISTENT_SECRET_XYZ')
except KeyError as e:
    print(f'KeyError: {e}')
"
echo ""

# ============================================================
# 5. EXCEL READER
# ============================================================
echo "📊 Excel reader"
check_output "read row 1" "Proxima Centauri b" .venv/bin/python -c "
from ai_qa_test_engine.excel_reader import read_excel_data
from pathlib import Path
data = read_excel_data(Path('sample-tests/feature-02-excel-secrets/TestData.xlsx'), 'Destinations', row=1)
print(data['destination'])
"

check_output "read row 2" "Ross 128 b" .venv/bin/python -c "
from ai_qa_test_engine.excel_reader import read_excel_data
from pathlib import Path
data = read_excel_data(Path('sample-tests/feature-02-excel-secrets/TestData.xlsx'), 'Destinations', row=2)
print(data['destination'])
"

# Error case — missing file
check_output "missing file raises error" "FileNotFoundError" .venv/bin/python -c "
from ai_qa_test_engine.excel_reader import read_excel_data
from pathlib import Path
try:
    read_excel_data(Path('nonexistent.xlsx'), 'Sheet1', row=1)
except FileNotFoundError as e:
    print(f'FileNotFoundError: {e}')
"

# Error case — wrong sheet
check_output "wrong sheet raises error" "not found" .venv/bin/python -c "
from ai_qa_test_engine.excel_reader import read_excel_data
from pathlib import Path
try:
    read_excel_data(Path('sample-tests/feature-02-excel-secrets/TestData.xlsx'), 'BadSheet', row=1)
except ValueError as e:
    print(e)
"
echo ""

# ============================================================
# 6. @INCLUDE RESOLUTION
# ============================================================
echo "📎 @include"
check_output "expands steps from .steps file" "I am on the home page" .venv/bin/python -c "
from ai_qa_test_engine.parser import preprocess_feature_file
from pathlib import Path
content = preprocess_feature_file(
    Path('sample-tests/feature-03-include-stopfail/features/include_steps.feature'),
    Path('sample-tests/feature-03-include-stopfail/common_steps')
)
print(content)
"

# Verify @include directive is gone (replaced with actual steps)
check_not_output "@include removed after expansion" "@include" .venv/bin/python -c "
from ai_qa_test_engine.parser import preprocess_feature_file
from pathlib import Path
content = preprocess_feature_file(
    Path('sample-tests/feature-03-include-stopfail/features/include_steps.feature'),
    Path('sample-tests/feature-03-include-stopfail/common_steps')
)
print(content)
"

# Error case — missing .steps file
check_output "missing .steps file raises error" "not found" .venv/bin/python -c "
from ai_qa_test_engine.parser import resolve_includes
try:
    from pathlib import Path
    resolve_includes('And @include \"nonexistent_flow\"', Path('sample-tests/feature-03-include-stopfail/common_steps'))
except FileNotFoundError as e:
    print(e)
"
echo ""

# ============================================================
# 7. FUNCTION REGISTRY
# ============================================================
echo "🔧 Function registry"
check_output "load user functions + call" "4200.0" .venv/bin/python -c "
from ai_qa_test_engine.function_registry import FunctionRegistry
from pathlib import Path
reg = FunctionRegistry()
reg.load_from_file(Path('sample-tests/feature-01-core-execution/custom_functions.py'))
result = reg.call('calculate_travel_cost', {'base_price': 1000, 'distance_multiplier': 4.2})
print(result)
"

check_output "bundled functions available" "OK" .venv/bin/python -c "
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

# Error case — missing function
check_output "missing function raises error" "AttributeError" .venv/bin/python -c "
from ai_qa_test_engine.function_registry import FunctionRegistry
reg = FunctionRegistry()
try:
    reg.get_function('nonexistent_function')
except AttributeError as e:
    print(f'AttributeError: {e}')
"
echo ""

# ============================================================
# 8. INPUT VARIABLES
# ============================================================
echo "📥 Input variables"
echo '{"pre_loaded": "hello_world", "count": 42}' > /tmp/test_input_vars.json
check_output "substitution with pre-loaded var" "hello_world" .venv/bin/python -c "
from ai_qa_test_engine.executor import substitute_variables
import json
vars = json.load(open('/tmp/test_input_vars.json'))
result = substitute_variables('value is \${pre_loaded}', vars)
print(result)
"

check_output "numeric var substitution" "42" .venv/bin/python -c "
from ai_qa_test_engine.executor import substitute_variables
import json
vars = json.load(open('/tmp/test_input_vars.json'))
result = substitute_variables('count is \${count}', vars)
print(result)
"

# Error case — undefined variable
check_output "undefined var raises error" "not found" .venv/bin/python -c "
from ai_qa_test_engine.executor import substitute_variables
try:
    substitute_variables('value is \${undefined_var}', {})
except KeyError as e:
    print(e)
"
rm -f /tmp/test_input_vars.json
echo ""

# ============================================================
# 9. CONFIG
# ============================================================
echo "⚙️  Config"
check_output "CLI kwargs override defaults" "headless" .venv/bin/python -c "
from pathlib import Path
from ai_qa_test_engine.config import AppConfig
c = AppConfig(feature_dir=Path('features'), browser_mode='headless')
print(c.browser_mode)
"

check_output "video recording flag" "True" .venv/bin/python -c "
from pathlib import Path
from ai_qa_test_engine.config import AppConfig
c = AppConfig(feature_dir=Path('features'), enable_video_recording=True)
print(c.enable_video_recording)
"

check_output "tag-url-map from JSON file" "https://nova" .venv/bin/python -c "
from pathlib import Path
from ai_qa_test_engine.config import AppConfig
c = AppConfig(feature_dir=Path('features'), tag_url_map_file=Path('sample-tests/feature-01-core-execution/tag-url-mapping.json'))
mapping = c.get_tag_url_mapping()
print(mapping.get('nextdotgym', ''))
"
echo ""

# ============================================================
# 10. BROWSER TESTS
# ============================================================
echo ""
echo "=============================================="
echo "🌐 Browser Tests (Nova Act — headless)"
echo "=============================================="
echo ""

echo "🚀 Feature 01: Core execution (navigation, extraction, validation, functions, input_variables)"
check "feature-01 core pass" .venv/bin/ai-qa-test run \
    --feature-dir ./sample-tests/feature-01-core-execution/features/ \
    --tag-url-map-file ./sample-tests/feature-01-core-execution/tag-url-mapping.json \
    --functions-file ./sample-tests/feature-01-core-execution/custom_functions.py \
    --variables-file ./sample-tests/feature-01-core-execution/input_vars.json \
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

echo "🚀 Feature 03: Stop-on-failure (automated — fix file + Enter)"
TEST_TMP="/tmp/test-stop-fail-$$"
mkdir -p "$TEST_TMP/features"
cp sample-tests/feature-03-include-stopfail/features/will_fail.feature "$TEST_TMP/features/"
cp sample-tests/feature-03-include-stopfail/tag-url-mapping.json "$TEST_TMP/"

FIFO="$TEST_TMP/stdin_pipe"
mkfifo "$FIFO"
OUTPUT="$TEST_TMP/output.log"

# Run with --stop-on-failure in background, stdin from FIFO
.venv/bin/ai-qa-test run \
    --feature-dir "$TEST_TMP/features/" \
    --tag-url-map-file "$TEST_TMP/tag-url-mapping.json" \
    --browser-mode headless \
    --stop-on-failure \
    --force-translate < "$FIFO" > "$OUTPUT" 2>&1 &
TEST_PID=$!

# Wait for "Press Enter" message (up to 180s)
WAITED=0
while [ $WAITED -lt 180 ]; do
    if grep -q "Press Enter" "$OUTPUT" 2>/dev/null; then
        break
    fi
    sleep 2
    WAITED=$((WAITED + 2))
done

if grep -q "Press Enter" "$OUTPUT" 2>/dev/null; then
    # Fix the feature file
    sed -i '' 's/"Mars"/"Proxima Centauri b"/' "$TEST_TMP/features/will_fail.feature"
    # Send Enter
    echo "" > "$FIFO"
    # Wait for process (up to 180s)
    if wait $TEST_PID 2>/dev/null; then
        echo "  ✓ stop-on-failure: fix + retry succeeded"
        PASS=$((PASS + 1))
    else
        echo "  ✗ stop-on-failure: retry failed (exit $?)"
        FAIL=$((FAIL + 1))
    fi
else
    echo "  ✗ stop-on-failure: never reached prompt (timeout)"
    kill $TEST_PID 2>/dev/null
    echo "" > "$FIFO" 2>/dev/null
    FAIL=$((FAIL + 1))
fi
rm -rf "$TEST_TMP"
echo ""

# Verify report was generated
check_file_exists "HTML report generated" "reports/report.html"
echo ""

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
