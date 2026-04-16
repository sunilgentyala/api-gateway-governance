# Policy-as-Code Framework for Heterogeneous API Gateway Governance

[![CI](https://github.com/sunilgentyala/api-gateway-governance/actions/workflows/ci.yml/badge.svg)](https://github.com/sunilgentyala/api-gateway-governance/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) [![Paper](https://img.shields.io/badge/IEEE-TEMSCON%20Global%202026-blue)](docs/PAPER-CITATION.md) [![Status](https://img.shields.io/badge/Paper%20Status-Accepted%20%E2%9C%85-brightgreen)](docs/PAPER-CITATION.md) [![Track](https://img.shields.io/badge/Track-Short%20Paper%20%E2%80%93%20Practitioner-orange)](docs/PAPER-CITATION.md) [![ORCID](https://img.shields.io/badge/ORCID-0009--0005--2642--3479-green)](https://orcid.org/0009-0005-2642-3479) [![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/) [![Tests](https://img.shields.io/badge/Tests-65%20passing-brightgreen)](#running-tests)

> Companion code, test suite, and evaluation data for the IEEE TEMSCON Global 2026 paper:
> **"Governing Heterogeneous API Gateway Estates Through Policy-as-Code: An Engineering Management Perspective"**
> by Sunil Gentyala (Senior Member, IEEE), HCLTech

---

## The Problem

Most large enterprises run four or more API gateway products at the same time. AWS API Gateway handles external traffic. Kong runs internal services. Envoy manages service mesh. Each has its own config format, its own policy syntax, its own idea of what a rate limit looks like.

When a security team writes a policy, someone has to translate it into three different formats by hand. All three translations drift. Incidents happen. Nobody is sure which gateway is actually enforcing what.

---

## What This Framework Does

Write a policy once in a plain YAML format. The adapters compile it automatically into:
- Kong plugin YAML
- AWS API Gateway usage plan JSON
- Envoy filter chain YAML

Argo CD delivers all three to production inside 87 minutes. Nobody edits gateway configs by hand. The pipeline signs every artifact with SLSA provenance before it ships.

---

## Production Results

Deployed at two organizations over twelve months:

| Metric | Org A Before | Org A After | Org B Before | Org B After |
|---|---|---|---|---|
| Policy Consistency | 61.2% | 97.8% | 73.5% | 96.1% |
| Lead Time (median) | 14.2 days | **87 minutes** | 9.6 days | **52 minutes** |
| Drift Incidents/Quarter | 31 | 8 | 18 | 5 |
| Escape Defects/Quarter | 7 | 1 | 4 | 1 |
| Static Credentials | 340 | **0** | 124 | **0** |

464 long-lived API keys eliminated. Replaced with SPIFFE/SPIRE workload identity certificates rotating every 30 minutes.

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│               CONTROL PLANE (Git)                    │
│  API Catalog  │  Policy Registry  │  Contract Store  │
└──────────────────────┬───────────────────────────────┘
                       │  compile + attest
                       ▼
┌──────────────────────────────────────────────────────┐
│           ADAPTER COMPILATION LAYER                  │
│   Policy Compilers  │  Contract Validators           │
│   SLSA Provenance   │  Sigstore Cosign               │
└──────┬──────────────────────┬────────────────────────┘
       │                      │
       ▼                      ▼
┌─────────────┐        ┌─────────────┐        ┌──────────────┐
│ DATA PLANE  │        │ DATA PLANE  │        │  DATA PLANE  │
│   (Kong)    │        │   (AWS)     │        │   (Envoy)    │
└─────────────┘        └─────────────┘        └──────────────┘
       │                      │                      │
       └──────────────────────┼──────────────────────┘
                              ▼
               ┌──────────────────────────┐
               │       OBSERVABILITY      │
               │  Metrics │ Logs │ Traces │
               └──────────────────────────┘
```

---

## Quick Start

No Kubernetes required. Everything runs locally.

```bash
# Clone
git clone https://github.com/sunilgentyala/api-gateway-governance.git
cd api-gateway-governance

# Install
pip install -r requirements.txt

# Compile a sample policy to all three gateway formats
python framework/adapters/kong/compile.py \
  --policy framework/control-plane/policies/sample-rate-limit.yaml \
  --output /tmp/kong-output.yaml

python framework/adapters/aws-api-gateway/compile.py \
  --policy framework/control-plane/policies/sample-rate-limit.yaml \
  --output /tmp/aws-output.json

python framework/adapters/envoy/compile.py \
  --policy framework/control-plane/policies/sample-rate-limit.yaml \
  --output /tmp/envoy-output.yaml
```

---

## Running Tests

```bash
pytest tests/ -v
```

65 tests across 3 adapter modules. All pass. The integration tests verify that all three adapters enforce the same intent from the same source policy.

```
tests/unit/test_kong_adapter.py         ← 21 tests
tests/unit/test_aws_adapter.py          ← 13 tests
tests/unit/test_envoy_adapter.py        ← 20 tests
tests/integration/test_cross_adapter_consistency.py  ← 11 tests
```

---

## The Policy Format

```yaml
policy:
  name: api-rate-limit-standard
  version: "1.0.0"
  type: rate-limit
  scope: per-consumer
  limit: 100
  window: 60s
  action: reject-429
  description: Standard rate limit for consumer-facing APIs
  owner: security-team
```

One file. Three gateway configs. Zero hand-editing.

---

## Workload Identity

No API keys. Every service gets a SPIFFE/SPIRE X.509 certificate tied to its actual cluster identity. Certificates expire in 30 minutes in production, 10 minutes in pipeline stages. When a cert expires, the workload gets a new one automatically.

```yaml
policy:
  name: workload-identity-mtls
  type: workload-identity
  auth_method: spiffe-svid
  certificate_lifetime:
    production: 30m
    pipeline: 10m
```

---

## Repo Structure

```
api-gateway-governance/
├── .github/workflows/ci.yml           ← GitHub Actions CI (runs 65 tests on every push)
├── README.md
├── LICENSE                            ← MIT
├── CITATION.cff                       ← Academic citation metadata
├── requirements.txt
├── conftest.py
│
├── framework/
│   ├── control-plane/
│   │   ├── policies/                  ← sample-rate-limit.yaml, sample-auth.yaml,
│   │   │                                sample-workload-identity.yaml
│   │   └── contracts/                 ← payment-service-contract.yaml
│   ├── adapters/
│   │   ├── kong/compile.py
│   │   ├── aws-api-gateway/compile.py
│   │   ├── aws_api_gateway/compile.py ← Python-importable copy
│   │   ├── envoy/compile.py
│   │   └── README.md                  ← How to add new adapters
│   └── pipeline/
│       └── slsa-workflow.yml          ← 6-stage SLSA pipeline
│
├── evaluation/
│   ├── results-summary.md             ← Full 12-month results + metric definitions
│   └── methodology.md                 ← Study design (pre-post quasi-experimental)
│
├── tests/
│   ├── unit/
│   │   ├── test_kong_adapter.py       ← 21 unit tests
│   │   ├── test_aws_adapter.py        ← 13 unit tests
│   │   └── test_envoy_adapter.py      ← 20 unit tests
│   └── integration/
│       └── test_cross_adapter_consistency.py  ← 11 cross-adapter tests
│
├── scripts/
│   ├── validate-policy.py             ← Schema validator (used in CI)
│   └── validate-policy.sh             ← Local pre-push validation
│
└── docs/
    └── PAPER-CITATION.md              ← IEEE citation + BibTeX
```

---

## Adding a New Adapter

Adapters follow a simple interface. See `framework/adapters/README.md` for the full spec. In short:

```python
def compile(policy: dict) -> dict:
    """
    Input:  policy dict loaded from the YAML 'policy' key
    Output: dict to be serialized as the gateway's native config
            Must include _source_policy, _compiled_by, _do_not_edit keys
    """
```

Community contributions for Azure APIM, Apigee, and Nginx are welcome.

---

## Related Paper

> Sunil Gentyala, "Governing Heterogeneous API Gateway Estates Through Policy-as-Code: An Engineering Management Perspective," in *Proc. IEEE TEMSCON Global 2026*, Montreal, Canada, 2026.

Full citation, BibTeX block, and IEEE Xplore DOI (once published) in [`docs/PAPER-CITATION.md`](docs/PAPER-CITATION.md).

---

## How to Cite This Repo

Use the [`CITATION.cff`](CITATION.cff) file, or:

```bibtex
@software{gentyala2026apigateway,
  author  = {Gentyala, Sunil},
  title   = {Policy-as-Code Framework for Heterogeneous API Gateway Governance},
  year    = {2026},
  url     = {https://github.com/sunilgentyala/api-gateway-governance},
  license = {MIT}
}
```

---

## Author

**Sunil Gentyala** (Senior Member, IEEE)
Lead Cybersecurity and AI Security Consultant, HCLTech
ORCID: [0009-0005-2642-3479](https://orcid.org/0009-0005-2642-3479)
GitHub: [github.com/sunilgentyala](https://github.com/sunilgentyala)
LinkedIn: [linkedin.com/in/sunil-gentyala](https://linkedin.com/in/sunil-gentyala/)

---

## License

MIT. See [LICENSE](LICENSE).
