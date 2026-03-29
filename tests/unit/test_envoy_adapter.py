"""
Unit Tests - Envoy Adapter
============================
Tests that the Envoy adapter correctly compiles policy definitions
into valid Envoy filter chain configuration.

Run with:
    pytest tests/unit/test_envoy_adapter.py -v
"""

import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from framework.adapters.envoy.compile import (
    compile,
    compile_rate_limit,
    compile_auth,
    compile_workload_identity,
    parse_window_to_seconds,
)


class TestWindowParsing:
    """Tests for the window string parser."""

    def test_seconds_parsing(self):
        assert parse_window_to_seconds("60s") == 60

    def test_minutes_parsing(self):
        assert parse_window_to_seconds("2m") == 120

    def test_hours_parsing(self):
        assert parse_window_to_seconds("1h") == 3600

    def test_default_fallback(self):
        assert parse_window_to_seconds("unknown") == 60


class TestRateLimitCompilation:
    """Tests for rate-limit policy compilation to Envoy format."""

    def test_compiles_to_local_ratelimit_filter(self):
        """A rate-limit policy should produce an Envoy local_ratelimit filter."""
        policy = {
            "name": "test-rate-limit",
            "type": "rate-limit",
            "limit": 100,
            "window": "60s",
        }
        result = compile_rate_limit(policy)

        assert result["name"] == "envoy.filters.http.local_ratelimit"

    def test_token_bucket_max_tokens(self):
        """max_tokens should equal the policy limit."""
        policy = {"name": "p", "type": "rate-limit", "limit": 100, "window": "60s"}
        result = compile_rate_limit(policy)

        bucket = result["typed_config"]["token_bucket"]
        assert bucket["max_tokens"] == 100

    def test_token_bucket_fill_interval(self):
        """fill_interval should match the policy window."""
        policy = {"name": "p", "type": "rate-limit", "limit": 100, "window": "60s"}
        result = compile_rate_limit(policy)

        bucket = result["typed_config"]["token_bucket"]
        assert bucket["fill_interval"] == "60s"

    def test_filter_enabled_100_percent(self):
        """Filter should be enabled for 100% of requests."""
        policy = {"name": "p", "type": "rate-limit", "limit": 100, "window": "60s"}
        result = compile_rate_limit(policy)

        enabled = result["typed_config"]["filter_enabled"]["default_value"]
        assert enabled["numerator"] == 100
        assert enabled["denominator"] == "HUNDRED"

    def test_correct_type_url(self):
        """typed_config must have the correct @type URL for Envoy."""
        policy = {"name": "p", "type": "rate-limit", "limit": 100, "window": "60s"}
        result = compile_rate_limit(policy)

        assert "local_ratelimit" in result["typed_config"]["@type"]

    def test_has_source_metadata(self):
        """Compiled output must carry source metadata."""
        policy = {"name": "my-policy", "type": "rate-limit", "limit": 50, "window": "60s"}
        result = compile_rate_limit(policy)

        assert result["_source_policy"] == "my-policy"
        assert "_compiled_by" in result
        assert "_do_not_edit" in result


class TestAuthCompilation:
    """Tests for authentication policy compilation to Envoy format."""

    def test_compiles_to_jwt_authn_filter(self):
        """A JWT auth policy should produce an Envoy jwt_authn filter."""
        policy = {
            "name": "test-auth",
            "type": "authentication",
            "issuer": "https://auth.example.com",
            "audience": "api.example.com",
        }
        result = compile_auth(policy)

        assert result["name"] == "envoy.filters.http.jwt_authn"

    def test_issuer_in_provider_config(self):
        """Issuer from policy should appear in the JWT provider config."""
        policy = {
            "name": "p",
            "type": "authentication",
            "issuer": "https://auth.mycompany.com",
            "audience": "api.mycompany.com",
        }
        result = compile_auth(policy)

        providers = result["typed_config"]["providers"]
        assert providers["jwt_provider"]["issuer"] == "https://auth.mycompany.com"

    def test_forward_jwt_is_true(self):
        """JWT should be forwarded upstream after validation."""
        policy = {
            "name": "p",
            "type": "authentication",
            "issuer": "https://x.com",
            "audience": "y",
        }
        result = compile_auth(policy)

        assert result["typed_config"]["providers"]["jwt_provider"]["forward"] is True

    def test_rules_cover_all_paths(self):
        """JWT rules should apply to all paths (prefix /)."""
        policy = {
            "name": "p",
            "type": "authentication",
            "issuer": "https://x.com",
            "audience": "y",
        }
        result = compile_auth(policy)

        rules = result["typed_config"]["rules"]
        assert any(r["match"].get("prefix") == "/" for r in rules)


class TestWorkloadIdentityCompilation:
    """Tests for workload identity policy compilation to Envoy format."""

    def test_compiles_to_tls_filter(self):
        """A workload identity policy should produce an Envoy TLS transport socket."""
        policy = {
            "name": "test-wi",
            "type": "workload-identity",
            "certificate_lifetime": {"production": "30m", "pipeline": "10m"},
        }
        result = compile_workload_identity(policy)

        assert result["name"] == "envoy.transport_sockets.tls"

    def test_requires_client_certificate(self):
        """mTLS should require client certificates."""
        policy = {"name": "p", "type": "workload-identity"}
        result = compile_workload_identity(policy)

        assert result["typed_config"]["require_client_certificate"] is True

    def test_spiffe_uri_san_matching(self):
        """SAN matching should be configured for SPIFFE URIs."""
        policy = {"name": "p", "type": "workload-identity"}
        result = compile_workload_identity(policy)

        ctx = result["typed_config"]["common_tls_context"]
        val_ctx = ctx["combined_validation_context"]["default_validation_context"]
        san_matchers = val_ctx["match_typed_subject_alt_names"]

        assert any(
            m.get("san_type") == "URI" and "spiffe" in m.get("matcher", {}).get("prefix", "")
            for m in san_matchers
        )

    def test_certificate_lifetimes_stored(self):
        """Certificate lifetimes should be stored in the compiled output."""
        policy = {
            "name": "p",
            "type": "workload-identity",
            "certificate_lifetime": {"production": "30m", "pipeline": "10m"},
        }
        result = compile_workload_identity(policy)

        assert result["_certificate_lifetime"]["production"] == "30m"
        assert result["_certificate_lifetime"]["pipeline"] == "10m"
