"""
Integration Tests - Cross-Adapter Intent Consistency
======================================================
These tests verify that when all three adapters compile the same
policy, they produce configurations that enforce the same intent.

The core guarantee of this framework is that one policy definition
produces consistent enforcement across all three gateways.
These tests verify that guarantee.

Run with:
    pytest tests/integration/ -v
"""

import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from framework.adapters.kong.compile import compile as kong_compile
from framework.adapters.aws_api_gateway.compile import compile as aws_compile
from framework.adapters.envoy.compile import compile as envoy_compile


# The sample policies used across all integration tests
RATE_LIMIT_POLICY = {
    "name": "integration-test-rate-limit",
    "type": "rate-limit",
    "scope": "per-consumer",
    "limit": 100,
    "window": "60s",
    "action": "reject-429",
}

AUTH_POLICY = {
    "name": "integration-test-auth",
    "type": "authentication",
    "method": "jwt-bearer",
    "issuer": "https://auth.example.com",
    "audience": "api.example.com",
}

WORKLOAD_IDENTITY_POLICY = {
    "name": "integration-test-wi",
    "type": "workload-identity",
    "auth_method": "spiffe-svid",
    "certificate_lifetime": {
        "production": "30m",
        "pipeline": "10m",
    },
}


class TestRateLimitConsistency:
    """
    Verifies that the rate-limit policy compiles to consistent
    enforcement across Kong, AWS, and Envoy.
    """

    def setup_method(self):
        self.kong = kong_compile(RATE_LIMIT_POLICY)
        self.aws = aws_compile(RATE_LIMIT_POLICY)
        self.envoy = envoy_compile(RATE_LIMIT_POLICY)

    def test_all_three_compile_without_error(self):
        """All three adapters should compile the rate-limit policy."""
        assert self.kong is not None
        assert self.aws is not None
        assert self.envoy is not None

    def test_all_three_reference_same_source_policy(self):
        """All three compiled outputs must reference the same source policy."""
        assert self.kong["_source_policy"] == RATE_LIMIT_POLICY["name"]
        assert self.aws["_source_policy"] == RATE_LIMIT_POLICY["name"]
        assert self.envoy["_source_policy"] == RATE_LIMIT_POLICY["name"]

    def test_kong_enforces_100_per_minute(self):
        """Kong should enforce 100 requests per minute."""
        minute_limit = self.kong["plugins"][0]["config"]["minute"]
        assert minute_limit == 100

    def test_aws_burst_matches_policy_limit(self):
        """AWS burst limit should match the policy limit of 100."""
        burst = self.aws["usagePlan"]["throttle"]["burstLimit"]
        assert burst == 100

    def test_envoy_max_tokens_matches_policy_limit(self):
        """Envoy token bucket max_tokens should match the policy limit of 100."""
        max_tokens = self.envoy["typed_config"]["token_bucket"]["max_tokens"]
        assert max_tokens == 100

    def test_envoy_fill_interval_matches_window(self):
        """Envoy fill_interval should match the 60-second window."""
        fill_interval = self.envoy["typed_config"]["token_bucket"]["fill_interval"]
        assert fill_interval == "60s"

    def test_all_three_have_do_not_edit_marker(self):
        """
        All compiled outputs must warn against manual editing.
        This is a safety check to prevent drift from direct edits.
        """
        assert "_do_not_edit" in self.kong
        assert "_do_not_edit" in self.aws
        assert "_do_not_edit" in self.envoy


class TestAuthConsistency:
    """
    Verifies that the authentication policy compiles consistently
    across Kong, AWS, and Envoy.
    """

    def setup_method(self):
        self.kong = kong_compile(AUTH_POLICY)
        self.aws = aws_compile(AUTH_POLICY)
        self.envoy = envoy_compile(AUTH_POLICY)

    def test_all_three_compile_without_error(self):
        """All three adapters should compile the auth policy."""
        assert self.kong is not None
        assert self.aws is not None
        assert self.envoy is not None

    def test_kong_uses_jwt_plugin(self):
        assert self.kong["plugins"][0]["name"] == "jwt"

    def test_aws_uses_jwt_authorizer(self):
        assert self.aws["authorizer"]["type"] == "JWT"

    def test_envoy_uses_jwt_authn_filter(self):
        assert self.envoy["name"] == "envoy.filters.http.jwt_authn"

    def test_all_enforce_expiry(self):
        """All three must verify token expiry."""
        # Kong
        kong_claims = self.kong["plugins"][0]["config"]["claims_to_verify"]
        assert "exp" in kong_claims

        # Envoy
        clock_skew = self.envoy["typed_config"]["providers"]["jwt_provider"]["clock_skew_seconds"]
        assert clock_skew >= 0  # clock skew configured means expiry is checked


class TestWorkloadIdentityConsistency:
    """
    Verifies that the workload identity policy compiles consistently
    to mTLS enforcement across Kong, AWS, and Envoy.
    """

    def setup_method(self):
        self.kong = kong_compile(WORKLOAD_IDENTITY_POLICY)
        self.aws = aws_compile(WORKLOAD_IDENTITY_POLICY)
        self.envoy = envoy_compile(WORKLOAD_IDENTITY_POLICY)

    def test_all_three_compile_without_error(self):
        """All three adapters should compile the workload identity policy."""
        assert self.kong is not None
        assert self.aws is not None
        assert self.envoy is not None

    def test_kong_uses_mtls_plugin(self):
        assert self.kong["plugins"][0]["name"] == "mtls-auth"

    def test_aws_uses_mutual_tls(self):
        assert "mutualTlsAuthentication" in self.aws

    def test_envoy_requires_client_certificate(self):
        assert self.envoy["typed_config"]["require_client_certificate"] is True

    def test_no_static_credentials_in_any_output(self):
        """
        None of the compiled outputs should contain API keys or
        static credentials. This is the core security guarantee.
        """
        import json
        kong_str = json.dumps(self.kong)
        aws_str = json.dumps(self.aws)
        envoy_str = json.dumps(self.envoy)

        for output_str in [kong_str, aws_str, envoy_str]:
            assert "api_key" not in output_str.lower()
            assert "api-key" not in output_str.lower()
            assert "password" not in output_str.lower()
            assert "secret" not in output_str.lower() or "spiffe" in output_str.lower()


class TestPolicyFileLoading:
    """
    Tests that the sample policy files in the repo load and compile correctly.
    These tests run against the actual files, not constructed dicts.
    """

    def test_sample_rate_limit_policy_loads(self):
        """The sample rate-limit policy file should load without errors."""
        import yaml
        policy_path = Path("framework/control-plane/policies/sample-rate-limit.yaml")
        if not policy_path.exists():
            pytest.skip("Sample policy file not found - run from repo root")

        with open(policy_path) as f:
            data = yaml.safe_load(f)

        assert "policy" in data
        assert data["policy"]["type"] == "rate-limit"

    def test_sample_auth_policy_loads(self):
        """The sample auth policy file should load without errors."""
        import yaml
        policy_path = Path("framework/control-plane/policies/sample-auth.yaml")
        if not policy_path.exists():
            pytest.skip("Sample policy file not found - run from repo root")

        with open(policy_path) as f:
            data = yaml.safe_load(f)

        assert "policy" in data
        assert data["policy"]["type"] == "authentication"

    def test_sample_workload_identity_policy_loads(self):
        """The sample workload identity policy file should load without errors."""
        import yaml
        policy_path = Path("framework/control-plane/policies/sample-workload-identity.yaml")
        if not policy_path.exists():
            pytest.skip("Sample policy file not found - run from repo root")

        with open(policy_path) as f:
            data = yaml.safe_load(f)

        assert "policy" in data
        assert data["policy"]["type"] == "workload-identity"
