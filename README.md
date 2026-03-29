# Policy-as-Code Framework for Heterogeneous API Gateway Governance

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Paper](https://img.shields.io/badge/IEEE-TEMSCON%202026-blue)](docs/)
[![ORCID](https://img.shields.io/badge/ORCID-0009--0005--2642--3479-green)](https://orcid.org/0009-0005-2642-3479)

---

## What This Is

Most large enterprises run four or more API gateway products at the same time. AWS API Gateway handles external traffic. Kong runs internal services. Envoy manages service mesh. Each one has its own configuration format, its own policy syntax, and its own idea of what a rate limit looks like.

When a security team writes a policy, someone has to translate it into three different formats by hand. All three translations drift. Incidents happen. No one is sure which gateway is actually enforcing what.

This repository contains a working policy-as-code framework that solves that problem. You write a policy once, in a plain format that describes what you want. The adapters in this repo translate it automatically into Kong plugin YAML, an AWS usage plan, and an Envoy filter chain. Argo CD pushes the compiled configs to your gateways. Nobody edits gateway configs by hand.

This was deployed at two production organizations over twelve months. A financial services firm with 2,400 endpoints cut drift incidents by 74% and reduced policy deployment time from 14 days to 87 minutes. A healthcare technology provider with 900 endpoints saw comparable results. 464 static API keys were eliminated across both sites and replaced with SPIFFE/SPIRE workload identity certificates.

---

## The Problem This Solves

### Before this framework

```
Security writes policy
       |
       v
Engineer A translates to Kong YAML     (takes 3 days, may be wrong)
Engineer B translates to AWS plan      (takes 3 days, slightly different)
Engineer C translates to Envoy filter  (takes 3 days, also different)
       |
       v
All three drift within weeks
Configuration review takes 14 days average
464 API keys floating around with no rotation
```

### After this framework

```
Security writes one policy file
       |
       v
Adapters compile Kong YAML + AWS plan + Envoy filter automatically
       |
       v
Pipeline signs artifacts with SLSA provenance
       |
       v
Argo CD deploys all three in 87 minutes
No static credentials. No manual translation. No drift.
```

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                 CONTROL PLANE (Git)                 │
│  API Catalog  │  Policy Registry  │  Contract Store │
└─────────────────────────┬───────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│              ADAPTER COMPILATION LAYER              │
│  Policy Compilers  │  Contract Validators           │
└──────┬─────────────────────────────┬────────────────┘
       │                             │
       ▼                             ▼
┌─────────────┐              ┌──────────────┐
│  DATA PLANE │              │  DATA PLANE  │
│    (Kong)   │              │    (AWS)     │
└─────────────┘              └──────────────┘
       │                             │
       └──────────────┬──────────────┘
                      ▼
          ┌───────────────────────┐
          │     OBSERVABILITY     │
          │  Metrics │ Logs │ SLO │
          └───────────────────────┘
```

---

## Results From Production Deployment

| Metric | Org A Before | Org A After | Org B Before | Org B After |
|---|---|---|---|---|
| Policy Consistency | 61.2% | 97.8% | 73.5% | 96.1% |
| Lead Time (median) | 14.2 days | 87 minutes | 9.6 days | 52 minutes |
| Drift Incidents/Quarter | 31 | 8 | 18 | 5 |
| Escape Defects/Quarter | 7 | 1 | 4 | 1 |
| Static Credentials | 340 | 0 | 124 | 0 |

---

## Who This Is For

If you are a security engineer tired of writing the same policy three times in three different syntaxes, this is for you.

If you are an engineering manager trying to get policy deployment time under control, the results section above shows what twelve months of production use looked like.

If you are a researcher studying policy-as-code or zero-trust API governance, the evaluation data and methodology are in the `evaluation/` folder and in the published paper.

---

## What Is In This Repo

```
api-gateway-governance/
├── README.md                          ← You are reading this
├── LICENSE                            ← MIT
├── CITATION.cff                       ← Cite this work in your papers
│
├── framework/
│   ├── control-plane/
│   │   ├── policies/                  ← Sample policy definitions (human-readable YAML)
│   │   └── contracts/                 ← Sample OpenAPI contract tests
│   ├── adapters/
│   │   ├── kong/                      ← Compiles policies to Kong plugin YAML
│   │   ├── aws-api-gateway/           ← Compiles policies to AWS usage plans
│   │   └── envoy/                     ← Compiles policies to Envoy filter chains
│   └── pipeline/
│       └── slsa-workflow.yml          ← GitHub Actions CI/CD with SLSA attestation
│
├── evaluation/
│   ├── results-summary.md             ← Full results from both evaluation sites
│   └── methodology.md                 ← How the study was designed and measured
│
├── tests/
│   ├── unit/                          ← Unit tests for each adapter
│   └── integration/                   ← End-to-end compilation tests
│
├── scripts/
│   └── validate-policy.sh             ← Quick validation script for new policies
│
└── docs/
    └── PAPER-CITATION.md              ← IEEE TEMSCON 2026 paper reference
```

---

## Quick Start

You do not need Kubernetes or a live gateway to try this. The adapter scripts run locally and show you what they would produce.

### Step 1: Clone the repo

```bash
git clone https://github.com/sunilgentyala/api-gateway-governance.git
cd api-gateway-governance
```

### Step 2: Install dependencies

```bash
pip install pyyaml jsonschema
```

### Step 3: Write a policy

Open `framework/control-plane/policies/sample-rate-limit.yaml` and look at the format. It is plain English translated into YAML.

### Step 4: Compile it

```bash
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

### Step 5: Run the tests

```bash
python -m pytest tests/ -v
```

You should see all tests pass, confirming that the three outputs enforce the same intent.

---

## The Policy Format

A policy file looks like this:

```yaml
# framework/control-plane/policies/sample-rate-limit.yaml
policy:
  name: api-rate-limit-standard
  type: rate-limit
  scope: per-consumer
  limit: 100
  window: 60s
  action: reject-429
  description: Standard rate limit for consumer-facing APIs
```

That one file compiles to all three gateway formats. The adapters handle the translation. You never touch Kong YAML, AWS usage plans, or Envoy filter chains directly.

---

## Workload Identity

This framework uses SPIFFE/SPIRE for workload identity. No API keys. No static secrets. Certificates rotate automatically every 30 minutes in production and every 10 minutes in pipeline stages.

If you are new to SPIFFE, the short version is: instead of giving a service an API key (which someone might copy, share, or forget to rotate), SPIFFE gives it a short-lived certificate tied to its actual identity on the cluster. The certificate expires before anyone can do much damage with it.

See `framework/control-plane/policies/sample-workload-identity.yaml` for a working example.

---

## Related Paper

This framework was published and evaluated in:

> Sunil Gentyala, "Governing Heterogeneous API Gateway Estates Through Policy-as-Code: An Engineering Management Perspective," IEEE TEMSCON Global 2026.

Full citation and DOI in `docs/PAPER-CITATION.md` once the paper is published in IEEE Xplore.

---

## Contributing

Pull requests are welcome. If you write an adapter for a gateway product not covered here (Azure APIM, Apigee, Nginx), please open a PR. The adapter interface is documented in `framework/adapters/README.md`.

---

## Author

**Sunil Gentyala** (Senior Member, IEEE)
Lead Cybersecurity and AI Security Consultant, HCLTech
ORCID: [0009-0005-2642-3479](https://orcid.org/0009-0005-2642-3479)
GitHub: [github.com/sunilgentyala](https://github.com/sunilgentyala)
LinkedIn: [linkedin.com/in/sunil-gentyala](https://linkedin.com/in/sunil-gentyala/)

---

## License

MIT. See [LICENSE](LICENSE) for details.
