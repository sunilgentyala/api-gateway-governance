# Evaluation Results

This file summarizes the twelve-month production evaluation of the framework at two organizations. Full methodology is in `methodology.md`. The published paper contains the complete statistical analysis.

---

## Study Design

Pre-post quasi-experimental design. Three months of baseline measurement came first, before any framework component touched production. Deployment then unfolded over nine months in three phases: non-critical APIs, internal production traffic, external-facing endpoints. Four metrics were recorded weekly from start to finish.

---

## Organization Profiles

**Organization A**
Financial services firm. Running AWS API Gateway (3 instances), Kong (5 instances), and Envoy (3 instances). 2,400 endpoints across 7 Kubernetes clusters. 340 static credentials active at the start of the engagement.

**Organization B**
Healthcare technology provider. Running Azure APIM (2 instances), Kong (2 instances), and Envoy (2 instances). 900 endpoints across 3 Kubernetes clusters. 124 static credentials active at baseline.

---

## Results Table

| Metric | Org A Baseline | Org A Final | Org B Baseline | Org B Final |
|---|---|---|---|---|
| Policy Consistency | 61.2% | 97.8% | 73.5% | 96.1% |
| Lead Time (median) | 14.2 days | 87 min | 9.6 days | 52 min |
| Drift Incidents / Quarter | 31 | 8 | 18 | 5 |
| Escape Defects / Quarter | 7 | 1 | 4 | 1 |
| Static Credentials | 340 | 0 | 124 | 0 |

---

## Metric Definitions

**Policy Consistency**
Percentage of gateway configurations that matched the declared policy state at the time of weekly measurement. Measured by diffing live gateway configs against the compiled outputs in Git.

**Lead Time**
Time from policy change committed to Git until the change was active on all gateways. Measured as median across all policy changes during the measurement period.

**Drift Incidents**
Count of configurations that diverged from declared state within a given quarter. A configuration was considered drifted if the live gateway differed from the compiled output by any security-relevant parameter.

**Escape Defects**
Policy changes that reached production with an error that should have been caught earlier in the pipeline. Measured by post-incident review.

**Static Credentials**
Count of long-lived API keys, passwords, or tokens in the gateway estate at the time of measurement.

---

## Root Cause Analysis for Remaining Drift

Not everything was clean. Of the drift incidents that still occurred across both sites combined:

- **5 incidents** traced to legacy APIs running on gateway versions the adapters did not yet cover
- **8 incidents** traced to network partitions that delayed Argo CD reconciliation past the 60-second window; all 8 resolved automatically within 5 minutes once connectivity restored

---

## Lead Time Breakdown

The 87-minute lead time came mainly from removing three bottlenecks that had never been formally tracked before the engagement:

| Removed Step | Old Time | New Time |
|---|---|---|
| Security-team review of gateway configs | ~3 days | Seconds (automated contract testing) |
| CAB approval for routine updates | ~5 days | Minutes (pipeline gates) |
| Manual credential distribution | ~6 days | Instantaneous (SPIFFE issuance) |

---

## Limitations

The study has constraints worth naming for anyone trying to replicate or extend this work.

Both evaluation sites ran mature Kubernetes infrastructure. The framework depends on that: SPIFFE/SPIRE requires container orchestration. Organizations on bare-metal or VM-based gateways would need a different identity approach, not just a configuration change.

Adapter development took more engineering than expected. Kong required two weeks. AWS API Gateway required six. Any new gateway product joining the estate would require that investment from scratch.

Twelve months is not long enough to know how maintenance load will evolve as vendors change their APIs.

No formal usability studies were run with the engineers who operated the system day to day. Cognitive load and workflow friction data is missing.

The adapter library only covers REST. GraphQL, gRPC, and event-driven paradigms are outside scope.

Both sites are US-based. How the governance model transfers to other regulatory environments is an open question.

---

## Citation

If you use this data in your research, please cite:

> Sunil Gentyala, "Governing Heterogeneous API Gateway Estates Through Policy-as-Code: An Engineering Management Perspective," IEEE TEMSCON Global 2026.

See `../docs/PAPER-CITATION.md` for the full citation.
