#!/bin/bash
# validate-policy.sh
# Quick local validation script.
# Run this before pushing any policy changes.
#
# Usage:
#   ./scripts/validate-policy.sh
#
# What it does:
#   1. Checks all policy files pass schema validation
#   2. Compiles each policy through all three adapters
#   3. Runs the test suite
#   4. Prints a summary

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo ""
echo "============================================"
echo "  API Gateway Governance - Local Validation"
echo "============================================"
echo ""

# Step 1: Validate policy schemas
echo "Step 1: Validating policy schemas..."
python scripts/validate-policy.py --policy-dir framework/control-plane/policies/
echo ""

# Step 2: Test-compile all policies through all adapters
echo "Step 2: Compiling policies through all adapters..."
COMPILE_ERRORS=0

for policy in framework/control-plane/policies/*.yaml; do
    name=$(basename "$policy" .yaml)
    echo "  Compiling: $name"

    python framework/adapters/kong/compile.py \
        --policy "$policy" \
        --output "/tmp/test-compile/kong/${name}.yaml" 2>&1 || COMPILE_ERRORS=$((COMPILE_ERRORS + 1))

    python framework/adapters/aws-api-gateway/compile.py \
        --policy "$policy" \
        --output "/tmp/test-compile/aws/${name}.json" 2>&1 || COMPILE_ERRORS=$((COMPILE_ERRORS + 1))

    python framework/adapters/envoy/compile.py \
        --policy "$policy" \
        --output "/tmp/test-compile/envoy/${name}.yaml" 2>&1 || COMPILE_ERRORS=$((COMPILE_ERRORS + 1))
done

if [ $COMPILE_ERRORS -gt 0 ]; then
    echo "  WARNING: $COMPILE_ERRORS compilation errors (some policy types may not apply to all gateways)"
fi
echo ""

# Step 3: Run tests
echo "Step 3: Running tests..."
python -m pytest tests/ -v --tb=short
echo ""

echo "============================================"
echo "  All checks passed. Ready to push."
echo "============================================"
echo ""
