#!/usr/bin/env python3
"""
Envoy Adapter - Policy Compiler
=================================
Reads a product-agnostic policy definition and outputs
the equivalent Envoy filter chain YAML.

Usage:
    python compile.py --policy path/to/policy.yaml --output path/to/output.yaml

What it does:
    Envoy uses HTTP filters in a filter chain for rate limiting,
    JWT auth, and mTLS. The syntax is verbose and easy to get wrong.
    This adapter produces the correct Envoy config from the simple
    policy format so nobody has to learn Envoy's filter chain syntax.
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


def parse_window_to_seconds(window: str) -> int:
    """Convert window string to seconds for Envoy token bucket config."""
    if window.endswith("s"):
        return int(window[:-1])
    elif window.endswith("m"):
        return int(window[:-1]) * 60
    elif window.endswith("h"):
        return int(window[:-1]) * 3600
    return 60


def compile_rate_limit(policy: dict) -> dict:
    """
    Compile a rate-limit policy to Envoy local rate limit filter.

    Envoy's local_ratelimit filter uses a token bucket algorithm.
    We set max_tokens (the burst capacity) and tokens_per_fill
    (the refill rate) to match our limit/window spec.
    """
    limit = policy.get("limit", 100)
    window_seconds = parse_window_to_seconds(policy.get("window", "60s"))

    return {
        "name": "envoy.filters.http.local_ratelimit",
        "typed_config": {
            "@type": "type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit",
            "stat_prefix": "http_local_rate_limiter",
            "token_bucket": {
                "max_tokens": limit,
                "tokens_per_fill": limit,
                "fill_interval": f"{window_seconds}s",
            },
            "filter_enabled": {
                "runtime_key": "local_rate_limit_enabled",
                "default_value": {"numerator": 100, "denominator": "HUNDRED"},
            },
            "filter_enforced": {
                "runtime_key": "local_rate_limit_enforced",
                "default_value": {"numerator": 100, "denominator": "HUNDRED"},
            },
            "response_headers_to_add": [
                {
                    "append": False,
                    "header": {"key": "x-local-rate-limit", "value": "true"},
                }
            ],
        },
        "_source_policy": policy.get("name", "unknown"),
        "_compiled_by": "api-gateway-governance/adapters/envoy",
        "_do_not_edit": "This file is generated. Edit the source policy instead.",
    }


def compile_auth(policy: dict) -> dict:
    """Compile a JWT authentication policy to Envoy JWT authn filter."""
    return {
        "name": "envoy.filters.http.jwt_authn",
        "typed_config": {
            "@type": "type.googleapis.com/envoy.extensions.filters.http.jwt_authn.v3.JwtAuthentication",
            "providers": {
                "jwt_provider": {
                    "issuer": policy.get("issuer", ""),
                    "audiences": [policy.get("audience", "")],
                    "remote_jwks": {
                        "http_uri": {
                            "uri": f"{policy.get('issuer', '')}/.well-known/jwks.json",
                            "cluster": "jwt_provider_cluster",
                            "timeout": "5s",
                        },
                        "cache_duration": "300s",
                    },
                    "forward": True,
                    "clock_skew_seconds": 30,
                }
            },
            "rules": [
                {
                    "match": {"prefix": "/"},
                    "requires": {"provider_name": "jwt_provider"},
                }
            ],
        },
        "_source_policy": policy.get("name", "unknown"),
        "_compiled_by": "api-gateway-governance/adapters/envoy",
        "_do_not_edit": "This file is generated. Edit the source policy instead.",
    }


def compile_workload_identity(policy: dict) -> dict:
    """Compile workload identity policy to Envoy mTLS downstream TLS context."""
    lifetime = policy.get("certificate_lifetime", {})
    return {
        "name": "envoy.transport_sockets.tls",
        "typed_config": {
            "@type": "type.googleapis.com/envoy.extensions.transport_sockets.tls.v3.DownstreamTlsContext",
            "require_client_certificate": True,
            "common_tls_context": {
                "tls_certificate_sds_secret_configs": [
                    {"name": "spiffe://cluster.local/server-cert"}
                ],
                "combined_validation_context": {
                    "default_validation_context": {
                        "match_typed_subject_alt_names": [
                            {
                                "san_type": "URI",
                                "matcher": {"prefix": "spiffe://cluster.local/"},
                            }
                        ]
                    },
                    "validation_context_sds_secret_config": {
                        "name": "spiffe://cluster.local/ca"
                    },
                },
            },
        },
        "_certificate_lifetime": {
            "production": lifetime.get("production", "30m"),
            "pipeline": lifetime.get("pipeline", "10m"),
        },
        "_source_policy": policy.get("name", "unknown"),
        "_compiled_by": "api-gateway-governance/adapters/envoy",
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
        description="Compile a policy definition to Envoy filter chain YAML."
    )
    parser.add_argument(
        "--policy",
        required=True,
        help="Path to the policy YAML file",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Where to write the compiled Envoy config",
    )
    args = parser.parse_args()

    policy = load_policy(args.policy)
    compiled = compile(policy)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        yaml.dump(compiled, f, default_flow_style=False, sort_keys=False)

    print(f"Compiled '{policy.get('name')}' to Envoy format.")
    print(f"Output written to: {args.output}")


if __name__ == "__main__":
    main()
