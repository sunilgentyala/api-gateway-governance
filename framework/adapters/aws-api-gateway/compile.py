#!/usr/bin/env python3
"""
AWS API Gateway Adapter - Policy Compiler
==========================================
Reads a product-agnostic policy definition and outputs
the equivalent AWS API Gateway configuration JSON.

Usage:
    python compile.py --policy path/to/policy.yaml --output path/to/output.json

What it does:
    AWS API Gateway uses Usage Plans and API Keys (or authorizers for JWT).
    This adapter translates the simple policy format into the exact
    JSON that the AWS SDK or Terraform expects.
    You never write AWS-specific config by hand.
"""

import argparse
import json
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


def parse_window_to_period(window: str) -> tuple:
    """
    Convert our window format to AWS throttle period.
    AWS uses requests per second (burst) and requests per day/month.
    Returns (throttle_rate_limit, throttle_burst_limit, quota_limit, quota_period).
    """
    if window.endswith("s"):
        seconds = int(window[:-1])
    elif window.endswith("m"):
        seconds = int(window[:-1]) * 60
    elif window.endswith("h"):
        seconds = int(window[:-1]) * 3600
    else:
        seconds = 60  # default

    return seconds


def compile_rate_limit(policy: dict) -> dict:
    """
    Compile a rate-limit policy to AWS API Gateway Usage Plan format.

    AWS Usage Plans define throttle (requests per second) and
    quota (requests per day/month). We map our simpler format
    to the closest AWS equivalent.
    """
    limit = policy.get("limit", 100)
    window_seconds = parse_window_to_period(policy.get("window", "60s"))

    # AWS throttle is requests per second
    rate_per_second = limit / window_seconds

    # AWS quota is per DAY or per MONTH - we use per-day
    requests_per_day = int((limit / window_seconds) * 86400)

    return {
        "usagePlan": {
            "name": policy.get("name", "default-plan"),
            "description": policy.get("description", ""),
            "throttle": {
                "rateLimit": round(rate_per_second, 2),
                "burstLimit": limit,
            },
            "quota": {
                "limit": requests_per_day,
                "period": "DAY",
            },
        },
        "_source_policy": policy.get("name", "unknown"),
        "_compiled_by": "api-gateway-governance/adapters/aws-api-gateway",
        "_do_not_edit": "This file is generated. Edit the source policy instead.",
    }


def compile_auth(policy: dict) -> dict:
    """Compile a JWT authentication policy to AWS Cognito/JWT authorizer format."""
    return {
        "authorizer": {
            "name": policy.get("name", "jwt-authorizer"),
            "type": "JWT",
            "identitySource": "$request.header.Authorization",
            "jwtConfiguration": {
                "issuer": policy.get("issuer", ""),
                "audience": [policy.get("audience", "")],
            },
        },
        "_source_policy": policy.get("name", "unknown"),
        "_compiled_by": "api-gateway-governance/adapters/aws-api-gateway",
        "_do_not_edit": "This file is generated. Edit the source policy instead.",
    }


def compile_workload_identity(policy: dict) -> dict:
    """
    Compile workload identity policy to AWS API Gateway mTLS config.
    AWS API Gateway v2 supports mTLS with a truststore in S3.
    """
    lifetime_prod = policy.get("certificate_lifetime", {}).get("production", "30m")
    return {
        "mutualTlsAuthentication": {
            "truststoreUri": "s3://${SPIFFE_TRUSTSTORE_BUCKET}/truststore.pem",
            "truststoreVersion": "latest",
        },
        "certificate_config": {
            "production_lifetime": lifetime_prod,
            "pipeline_lifetime": policy.get("certificate_lifetime", {}).get("pipeline", "10m"),
            "attestation_required": True,
        },
        "_source_policy": policy.get("name", "unknown"),
        "_compiled_by": "api-gateway-governance/adapters/aws-api-gateway",
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
        description="Compile a policy definition to AWS API Gateway JSON."
    )
    parser.add_argument(
        "--policy",
        required=True,
        help="Path to the policy YAML file",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Where to write the compiled AWS config",
    )
    args = parser.parse_args()

    policy = load_policy(args.policy)
    compiled = compile(policy)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(compiled, f, indent=2)

    print(f"Compiled '{policy.get('name')}' to AWS API Gateway format.")
    print(f"Output written to: {args.output}")


if __name__ == "__main__":
    main()
