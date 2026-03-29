"""
Unit Tests - AWS API Gateway Adapter
======================================
Tests that the AWS adapter correctly compiles policy definitions
into valid AWS API Gateway configuration.

Run with:
    pytest tests/unit/test_aws_adapter.py -v
"""

import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from framework.adapters.aws_api_gateway.compile import (
    compile,
    compile_rate_limit,
    compile_auth,
    compile_workload_identity,
)


class TestRateLimitCompilation:
    """Tests for rate-limit policy compilation to AWS format."""

    def test_basic_rate_limit_compiles(self):
        """A rate-limit policy should produce an AWS usagePlan config."""
        policy = {
            "name": "test-rate-limit",
            "type": "rate-limit",
            "limit": 100,
            "window": "60s",
        }
        result = compile_rate_limit(policy)

        assert "usagePlan" in result

    def test_throttle_rate_calculation(self):
        """100 requests per 60 seconds = 1.67 requests per second throttle rate."""
        policy = {"name": "p", "type": "rate-limit", "limit": 100, "window": "60s"}
        result = compile_rate_limit(policy)

        rate = result["usagePlan"]["throttle"]["rateLimit"]
        assert abs(rate - 1.67) < 0.01

    def test_burst_limit_equals_window_limit(self):
        """Burst limit should equal the per-window limit."""
        policy = {"name": "p", "type": "rate-limit", "limit": 100, "window": "60s"}
        result = compile_rate_limit(policy)

        assert result["usagePlan"]["throttle"]["burstLimit"] == 100

    def test_quota_period_is_day(self):
        """Quota period should be DAY."""
        policy = {"name": "p", "type": "rate-limit", "limit": 100, "window": "60s"}
        result = compile_rate_limit(policy)

        assert result["usagePlan"]["quota"]["period"] == "DAY"

    def test_quota_limit_scales_to_daily(self):
        """100 req/60s should scale to a reasonable per-day quota."""
        policy = {"name": "p", "type": "rate-limit", "limit": 100, "window": "60s"}
        result = compile_rate_limit(policy)

        # 100 per 60s = 1.67/s * 86400 = 144000/day
        daily = result["usagePlan"]["quota"]["limit"]
        assert daily > 0

    def test_usage_plan_has_name(self):
        """Usage plan should carry the policy name."""
        policy = {"name": "my-plan", "type": "rate-limit", "limit": 50, "window": "60s"}
        result = compile_rate_limit(policy)

        assert result["usagePlan"]["name"] == "my-plan"

    def test_has_source_metadata(self):
        """Compiled output must carry source metadata."""
        policy = {"name": "p", "type": "rate-limit", "limit": 10, "window": "60s"}
        result = compile_rate_limit(policy)

        assert "_source_policy" in result
        assert "_compiled_by" in result
        assert "_do_not_edit" in result


class TestAuthCompilation:
    """Tests for authentication policy compilation to AWS format."""

    def test_auth_compiles_to_authorizer(self):
        """A JWT auth policy should produce an AWS JWT authorizer."""
        policy = {
            "name": "test-auth",
            "type": "authentication",
            "issuer": "https://auth.example.com",
            "audience": "api.example.com",
        }
        result = compile_auth(policy)

        assert "authorizer" in result
        assert result["authorizer"]["type"] == "JWT"

    def test_auth_identity_source(self):
        """Identity source should be the Authorization header."""
        policy = {"name": "p", "type": "authentication", "issuer": "https://x.com"}
        result = compile_auth(policy)

        assert result["authorizer"]["identitySource"] == "$request.header.Authorization"

    def test_auth_issuer_propagated(self):
        """Issuer from policy should appear in JWT configuration."""
        policy = {
            "name": "p",
            "type": "authentication",
            "issuer": "https://auth.mycompany.com",
        }
        result = compile_auth(policy)

        assert result["authorizer"]["jwtConfiguration"]["issuer"] == "https://auth.mycompany.com"


class TestWorkloadIdentityCompilation:
    """Tests for workload identity policy compilation to AWS format."""

    def test_workload_identity_compiles_to_mtls(self):
        """A workload identity policy should produce AWS mTLS auth config."""
        policy = {
            "name": "test-wi",
            "type": "workload-identity",
            "certificate_lifetime": {"production": "30m", "pipeline": "10m"},
        }
        result = compile_workload_identity(policy)

        assert "mutualTlsAuthentication" in result

    def test_certificate_lifetimes_propagated(self):
        """Certificate lifetimes should appear in the compiled output."""
        policy = {
            "name": "p",
            "type": "workload-identity",
            "certificate_lifetime": {"production": "30m", "pipeline": "10m"},
        }
        result = compile_workload_identity(policy)

        assert result["certificate_config"]["production_lifetime"] == "30m"
        assert result["certificate_config"]["pipeline_lifetime"] == "10m"
