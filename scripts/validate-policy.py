#!/usr/bin/env python3
"""
Policy Validator
=================
Validates all policy YAML files in the policies directory
against the required schema before compilation begins.

Usage:
    python scripts/validate-policy.py --policy-dir framework/control-plane/policies/

    # Or validate a single file:
    python scripts/validate-policy.py --policy framework/control-plane/policies/sample-rate-limit.yaml

This runs as Stage 1 of the CI pipeline. If any policy file
fails validation, the pipeline stops before any compilation happens.
"""

import argparse
import sys
import yaml
from pathlib import Path

# Required fields for every policy type
BASE_REQUIRED_FIELDS = ["name", "version", "type", "description", "owner"]

# Additional required fields per policy type
TYPE_REQUIRED_FIELDS = {
    "rate-limit": ["limit", "window", "action"],
    "authentication": ["method", "issuer", "audience"],
    "workload-identity": ["auth_method", "certificate_lifetime"],
}

VALID_TYPES = list(TYPE_REQUIRED_FIELDS.keys())


def validate_policy(policy_path: Path) -> list:
    """
    Validate a single policy file.
    Returns a list of error strings. Empty list means the policy is valid.
    """
    errors = []

    # Load the file
    try:
        with open(policy_path) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [f"YAML parse error: {e}"]

    # Must have a top-level 'policy' key
    if not isinstance(data, dict) or "policy" not in data:
        return ["Missing top-level 'policy' key."]

    policy = data["policy"]

    # Check base required fields
    for field in BASE_REQUIRED_FIELDS:
        if field not in policy:
            errors.append(f"Missing required field: '{field}'")

    # Check policy type is valid
    policy_type = policy.get("type", "")
    if policy_type not in VALID_TYPES:
        errors.append(
            f"Unknown policy type: '{policy_type}'. "
            f"Valid types are: {VALID_TYPES}"
        )
        return errors  # No point checking type-specific fields

    # Check type-specific required fields
    for field in TYPE_REQUIRED_FIELDS.get(policy_type, []):
        if field not in policy:
            errors.append(f"Missing required field for type '{policy_type}': '{field}'")

    # Validate specific field formats
    if policy_type == "rate-limit":
        window = policy.get("window", "")
        if not (window.endswith("s") or window.endswith("m") or window.endswith("h")):
            errors.append(
                f"Invalid window format: '{window}'. "
                "Use seconds (60s), minutes (5m), or hours (1h)."
            )
        limit = policy.get("limit", 0)
        if not isinstance(limit, (int, float)) or limit <= 0:
            errors.append(f"limit must be a positive number, got: {limit}")

    if policy_type == "workload-identity":
        lifetime = policy.get("certificate_lifetime", {})
        if not isinstance(lifetime, dict):
            errors.append("certificate_lifetime must be a dict with 'production' and 'pipeline' keys.")
        else:
            for env in ["production", "pipeline"]:
                if env not in lifetime:
                    errors.append(f"certificate_lifetime missing '{env}' key.")

    return errors


def validate_directory(policy_dir: Path) -> dict:
    """
    Validate all YAML files in a directory.
    Returns a dict mapping filename to list of errors.
    """
    results = {}
    yaml_files = list(policy_dir.glob("*.yaml")) + list(policy_dir.glob("*.yml"))

    if not yaml_files:
        print(f"No policy files found in {policy_dir}")
        return results

    for policy_file in sorted(yaml_files):
        errors = validate_policy(policy_file)
        results[policy_file.name] = errors

    return results


def main():
    parser = argparse.ArgumentParser(description="Validate policy YAML files.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--policy-dir", help="Directory containing policy YAML files")
    group.add_argument("--policy", help="Single policy file to validate")
    args = parser.parse_args()

    if args.policy:
        # Single file validation
        policy_path = Path(args.policy)
        errors = validate_policy(policy_path)
        if errors:
            print(f"FAIL: {policy_path.name}")
            for e in errors:
                print(f"  - {e}")
            sys.exit(1)
        else:
            print(f"PASS: {policy_path.name}")
            sys.exit(0)

    # Directory validation
    policy_dir = Path(args.policy_dir)
    if not policy_dir.exists():
        print(f"Error: Directory not found: {policy_dir}")
        sys.exit(1)

    results = validate_directory(policy_dir)
    failed = 0
    passed = 0

    print(f"\nValidating policies in: {policy_dir}\n")
    print(f"{'File':<50} {'Status'}")
    print("-" * 60)

    for filename, errors in results.items():
        if errors:
            print(f"{filename:<50} FAIL")
            for e in errors:
                print(f"  {'':50} - {e}")
            failed += 1
        else:
            print(f"{filename:<50} PASS")
            passed += 1

    print("-" * 60)
    print(f"\n{passed} passed, {failed} failed out of {passed + failed} policies.\n")

    if failed > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
