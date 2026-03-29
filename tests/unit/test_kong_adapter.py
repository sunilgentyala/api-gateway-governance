"""
Unit Tests - Kong Adapter
==========================
Tests that the Kong adapter correctly compiles policy definitions
into valid Kong plugin configuration.

Run with:
    pytest tests/unit/test_kong_adapter.py -v
"""

import sys
import pytest
from pathlib import Path

# Add the repo root to the path so we can import the adapter
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from framework.adapters.kong.compile import (
    compile,
    compile_rate_limit,
    compile_auth,
    compile_workload_identity,
)


class TestRateLimitCompilation:
    """Tests for rate-limit policy compilation to Kong format."""

    def test_basic_rate_limit_compiles(self):
        """A simple rate-limit policy should produce a Kong rate-limiting plugin."""
        policy = {
            "name": "test-rate-limit",
            "type": "rate-limit",
            "scope": "per-consumer",
            "limit": 100,
            "window": "60s",
            "action": "reject-429",
        }
        result = compile_rate_limit(policy)

        assert "plugins" in result
        assert len(result["plugins"]) == 1
        assert result["plugins"][0]["name"] == "rate-limiting"

    def test_rate_limit_minute_calculation(self):
        """100 requests per 60 seconds should map to 100 requests per minute in Kong."""
        policy = {
            "name": "test-rate-limit",
            "type": "rate-limit",
            "limit": 100,
            "window": "60s",
        }
        result = compile_rate_limit(policy)

        config = result["plugins"][0]["config"]
        assert config["minute"] == 100

    def test_rate_limit_higher_window(self):
        """200 requests per 120 seconds should map to 100 per minute."""
        policy = {
            "name": "test-rate-limit",
            "type": "rate-limit",
            "limit": 200,
            "window": "120s",
        }
        result = compile_rate_limit(policy)

        config = result["plugins"][0]["config"]
        assert config["minute"] == 100

    def test_rate_limit_has_fault_tolerant(self):
        """Kong config should have fault_tolerant set to True."""
        policy = {"name": "p", "type": "rate-limit", "limit": 50, "window": "60s"}
        result = compile_rate_limit(policy)

        assert result["plugins"][0]["config"]["fault_tolerant"] is True

    def test_rate_limit_has_source_metadata(self):
        """Compiled output must carry source policy metadata."""
        policy = {"name": "my-policy", "type": "rate-limit", "limit": 10, "window": "60s"}
        result = compile_rate_limit(policy)

        assert result["_source_policy"] == "my-policy"
        assert "_compiled_by" in result
        assert "_do_not_edit" in result

    def test_rate_limit_scope_per_consumer(self):
        """Scope per-consumer should set limit_by to consumer."""
        policy = {
            "name": "p",
            "type": "rate-limit",
            "scope": "per-consumer",
            "limit": 100,
            "window": "60s",
        }
        result = compile_rate_limit(policy)
        assert result["plugins"][0]["config"]["limit_by"] == "consumer"


class TestAuthCompilation:
    """Tests for authentication policy compilation to Kong format."""

    def test_auth_compiles_to_jwt_plugin(self):
        """A JWT auth policy should produce a Kong jwt plugin."""
        policy = {
            "name": "test-auth",
            "type": "authentication",
            "method": "jwt-bearer",
            "issuer": "https://auth.example.com",
        }
        result = compile_auth(policy)

        assert "plugins" in result
        assert result["plugins"][0]["name"] == "jwt"

    def test_auth_has_exp_claim_verification(self):
        """JWT config should verify the exp claim."""
        policy = {"name": "p", "type": "authentication", "method": "jwt-bearer"}
        result = compile_auth(policy)

        claims = result["plugins"][0]["config"]["claims_to_verify"]
        assert "exp" in claims

    def test_auth_has_source_metadata(self):
        """Compiled output must carry source policy metadata."""
        policy = {"name": "my-auth", "type": "authentication", "method": "jwt-bearer"}
        result = compile_auth(policy)

        assert result["_source_policy"] == "my-auth"


class TestWorkloadIdentityCompilation:
    """Tests for workload identity policy compilation to Kong format."""

    def test_workload_identity_compiles_to_mtls(self):
        """A workload identity policy should produce a Kong mtls-auth plugin."""
        policy = {
            "name": "test-wi",
            "type": "workload-identity",
            "auth_method": "spiffe-svid",
        }
        result = compile_workload_identity(policy)

        assert "plugins" in result
        assert result["plugins"][0]["name"] == "mtls-auth"

    def test_workload_identity_has_ca_certificates(self):
        """mTLS config must reference the SPIFFE CA cert."""
        policy = {"name": "p", "type": "workload-identity"}
        result = compile_workload_identity(policy)

        ca_certs = result["plugins"][0]["config"]["ca_certificates"]
        assert len(ca_certs) > 0


class TestCompileRouter:
    """Tests for the main compile() routing function."""

    def test_routes_rate_limit(self):
        """compile() should route rate-limit policies correctly."""
        policy = {"name": "p", "type": "rate-limit", "limit": 10, "window": "60s"}
        result = compile(policy)
        assert result["plugins"][0]["name"] == "rate-limiting"

    def test_routes_authentication(self):
        """compile() should route authentication policies correctly."""
        policy = {"name": "p", "type": "authentication", "method": "jwt-bearer"}
        result = compile(policy)
        assert result["plugins"][0]["name"] == "jwt"

    def test_routes_workload_identity(self):
        """compile() should route workload-identity policies correctly."""
        policy = {"name": "p", "type": "workload-identity"}
        result = compile(policy)
        assert result["plugins"][0]["name"] == "mtls-auth"

    def test_unknown_type_raises_system_exit(self):
        """An unknown policy type should call sys.exit."""
        policy = {"name": "p", "type": "unsupported-type"}
        with pytest.raises(SystemExit):
            compile(policy)
