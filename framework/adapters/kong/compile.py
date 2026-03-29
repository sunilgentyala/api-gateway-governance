#!/usr/bin/env python3
"""
Kong Adapter - Policy Compiler
================================
Reads a product-agnostic policy definition and outputs
the equivalent Kong plugin configuration YAML.

Usage:
    python compile.py --policy path/to/policy.yaml --output path/to/output.yaml

What it does:
    Takes the simple policy format that security writes,
    and produces the exact Kong plugin YAML that Kong expects.
    Nobody has to know Kong's plugin syntax to write a policy.
"""

import argparse
import sys
import yaml
from pathlib import Path


def load_policy(policy_path: str) -> dict:
    """Load and validate the policy file."""
    path = Path(policy_path)
    if not path.exists():
        print(f"Error: Policy file not found: {policy_path}")
        sys.exit(1)

    with open(path) as f:
        data = yaml.safe_load(f)

    if "policy" not in data:
        print("Error: Policy file must have a top-level 'policy' key.")
        sys.exit(1)

    return data["policy"]


def compile_rate_limit(policy: dict) -> dict:
    """
    Compile a rate-limit policy to Kong plugin format.

    Kong's rate-limiting plugin counts requests per consumer
    per time window. We translate our simple limit/window
    format into Kong's minute/hour/day counters.
    """
    window = policy.get("window", "60s")

    # Parse the window string (e.g. "60s", "1m", "1h")
    if window.endswith("s"):
        seconds = int(window[:-1])
        minute_limit = int((policy["limit"] / seconds) * 60)
        kong_config = {
            "minute": minute_limit,
            "policy": "local",
            "fault_tolerant": True,
            "hide_client_headers": False,
            "limit_by": "consumer",
        }
    elif window.endswith("m"):
        minutes = int(window[:-1])
        minute_limit = int(policy["limit"] / minutes)
        kong_config = {
            "minute": minute_limit,
            "policy": "local",
            "fault_tolerant": True,
            "hide_client_headers": False,
            "limit_by": "consumer",
        }
    else:
        # Default: treat the raw limit as per-minute
        kong_config = {
            "minute": policy["limit"],
            "policy": "local",
            "fault_tolerant": True,
            "hide_client_headers": False,
            "limit_by": "consumer",
        }

    return {
        "plugins": [
            {
                "name": "rate-limiting",
                "config": kong_config,
            }
        ],
        "_source_policy": policy.get("name", "unknown"),
        "_compiled_by": "api-gateway-governance/adapters/kong",
        "_do_not_edit": "This file is generated. Edit the source policy instead.",
    }


def compile_auth(policy: dict) -> dict:
    """Compile a JWT authentication policy to Kong jwt plugin format."""
    return {
        "plugins": [
            {
                "name": "jwt",
                "config": {
                    "uri_param_names": ["jwt"],
                    "cookie_names": [],
                    "key_claim_name": "iss",
                    "claims_to_verify": ["exp", "iat"],
                    "maximum_expiration": 3600,
                },
            }
        ],
        "_source_policy": policy.get("name", "unknown"),
        "_compiled_by": "api-gateway-governance/adapters/kong",
        "_do_not_edit": "This file is generated. Edit the source policy instead.",
    }


def compile_workload_identity(policy: dict) -> dict:
    """Compile a workload identity policy to Kong mTLS plugin format."""
    return {
        "plugins": [
            {
                "name": "mtls-auth",
                "config": {
                    "ca_certificates": ["${SPIFFE_CA_CERT_ID}"],
                    "skip_consumer_lookup": False,
                    "authenticated_group_by": "dn",
                },
            }
        ],
        "_source_policy": policy.get("name", "unknown"),
        "_compiled_by": "api-gateway-governance/adapters/kong",
        "_do_not_edit": "This file is generated. Edit the source policy instead.",
    }


def compile(policy: dict) -> dict:
    """Route to the right compiler based on policy type."""
    policy_type = policy.get("type", "").lower()

    compilers = {
        "rate-limit": compile_rate_limit,
        "authentication": compile_auth,
        "workload-identity": compile_workload_identity,
    }

    if policy_type not in compilers:
        print(f"Error: Unknown policy type '{policy_type}'.")
        print(f"Supported types: {list(compilers.keys())}")
        sys.exit(1)

    return compilers[policy_type](policy)


def main():
    parser = argparse.ArgumentParser(
        description="Compile a policy definition to Kong plugin YAML."
    )
    parser.add_argument(
        "--policy",
        required=True,
        help="Path to the policy YAML file",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Where to write the compiled Kong config",
    )
    args = parser.parse_args()

    policy = load_policy(args.policy)
    compiled = compile(policy)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        yaml.dump(compiled, f, default_flow_style=False, sort_keys=False)

    print(f"Compiled '{policy.get('name')}' to Kong format.")
    print(f"Output written to: {args.output}")


if __name__ == "__main__":
    main()
