# Study Methodology

This document describes how the twelve-month evaluation was designed and conducted. It is intended for researchers who want to understand the validity of the results or replicate the study.

---

## Study Design

The evaluation used a pre-post quasi-experimental design. There was no control group running the old process in parallel; both sites transitioned fully. Baseline data was collected for three months before any framework component was introduced. The framework was then deployed in three phases over nine months.

**Why quasi-experimental and not a randomized controlled trial?**
Randomizing gateway governance across production API traffic in live financial and healthcare environments is not feasible. The pre-post design with three months of baseline is a reasonable alternative for operational research of this type.

---

## Deployment Phases

### Phase 1: Non-critical APIs (Months 1-3 of deployment)
Low-traffic, internal APIs with no direct customer impact. This phase was deliberately conservative: adapters were deployed but Argo CD reconciliation ran in dry-run mode, logging what it would change without applying anything. Engineers reviewed every proposed change before it went live.

### Phase 2: Internal production traffic (Months 4-6)
Internal service-to-service APIs with production traffic but no direct customer exposure. Argo CD reconciliation moved from dry-run to live. The SPIFFE/SPIRE migration for internal services happened in this phase.

### Phase 3: External-facing APIs (Months 7-9)
Customer-facing API endpoints. Full automated reconciliation. All remaining static credentials replaced with SPIFFE/SPIRE certificates. Red-team exercises ran during this phase.

---

## Metrics Collection

All four metrics were collected weekly by automated scripts that diffed live gateway configurations against the compiled outputs stored in Git.

**Policy Consistency** was measured by pulling the live configuration from each gateway via its management API and comparing it against the corresponding compiled output in the policy Git repository. Any security-relevant field difference counted as inconsistent.

**Lead Time** was measured from the timestamp of the Git commit that changed a policy file to the timestamp when Argo CD reported the change as synced across all gateways. Only policy changes were counted; infrastructure changes were excluded.

**Drift Incidents** were counted when a weekly consistency check found a gateway configuration that had diverged from declared state. Each affected gateway counted as one incident.

**Escape Defects** were counted when a post-incident review determined that a defect reaching production should have been caught by the pipeline. Each incident was reviewed by two engineers independently.

---

## Red-Team Exercises

Quarterly red-team exercises ran at both sites during Phase 3. The red team was given the task of injecting policy tampering into the pipeline, specifically trying to modify compiled outputs between the Sign and Reconcile stages. 100% of injected tampering attempts were detected and blocked by signature verification in the Reconcile stage.

Four attempts were made per quarter per site. All 16 attempts across the two sites were caught.

---

## Statistical Notes

No formal statistical significance testing was applied. The study was observational and operational, not a clinical trial. Confidence in the results comes from:

- Consistent direction of results across both sites
- Twelve months of data, not a one-time measurement
- Quantitative metrics collected by automated scripts, not self-reported

A larger multi-site study with formal statistical analysis is listed as future work in the paper.
