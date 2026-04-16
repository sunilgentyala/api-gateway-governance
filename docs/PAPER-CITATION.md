
# Paper Citation

This repository is the companion code, test suite, and evaluation data for the following peer-reviewed paper.

---

## Paper Details

| Field | Value |
|---|---|
| **Title** | Governing Heterogeneous API Gateway Estates Through Policy-as-Code: An Engineering Management Perspective |
| **Author** | Sunil Gentyala (Senior Member, IEEE), HCLTech, Dallas TX USA |
| **Conference** | IEEE Technology and Engineering Management Society Conference – Global (TEMSCON Global 2026) |
| **Location** | Montreal, Canada, 2026 |
| **Track** | Short Paper – Practitioner Track |
| **Status** | ✅ Accepted |
| **EDAS ID** | #145 (1571270844) |
| **IEEE Xplore DOI** | Pending publication of proceedings |
| **Keywords** | API governance; policy-as-code; zero-trust security; workload identity; GitOps; SPIFFE; SLSA; multi-cloud; engineering management |

---

## Abstract

Four API gateway products running at once means four different configuration syntaxes, four separate translation jobs, and four separate chances for a security policy to drift before anyone notices. This recurring pattern of configuration drift across heterogeneous gateway environments motivated the development of a policy-as-code framework to address the problem systematically. Write a policy once; the adapters handle Kong, AWS API Gateway, and Envoy from the same source file; Argo CD delivers all three inside 87 minutes. The framework was evaluated in two production environments over twelve months. A financial services firm with 2,400 endpoints reduced drift incidents from 31 to 8 per quarter. A healthcare provider with 900 endpoints saw similar results. Across both, 464 static API keys were replaced by SPIFFE/SPIRE certificates rotating every 30 minutes. The pipeline signs every artifact using SLSA provenance. Red-team exercises each quarter attempted to tamper with compiled outputs; none succeeded. The organizational preparation — team structure, rollout sequencing, and making drift visible to managers — proved as consequential as the technical design.

---

## How to Cite

### IEEE Format

S. Gentyala, "Governing Heterogeneous API Gateway Estates Through Policy-as-Code: An Engineering Management Perspective," in *Proc. IEEE TEMSCON Global 2026*, Montreal, Canada, 2026.

### BibTeX

```bibtex
@inproceedings{gentyala2026apigateway,
  author    = {Gentyala, Sunil},
  title     = {Governing Heterogeneous {API} Gateway Estates Through Policy-as-Code:
               An Engineering Management Perspective},
  booktitle = {Proceedings of IEEE TEMSCON Global 2026},
  year      = {2026},
  address   = {Montreal, Canada},
  publisher = {IEEE},
  track     = {Short Paper -- Practitioner Track},
  note      = {EDAS submission \#145 (ID: 1571270844).
               Companion code: https://github.com/sunilgentyala/api-gateway-governance}
}
```

### APA Format

Gentyala, S. (2026). Governing heterogeneous API gateway estates through policy-as-code: An engineering management perspective. *Proceedings of IEEE TEMSCON Global 2026*. Montreal, Canada: IEEE.

### For Citing the Code Repository

Use the `CITATION.cff` file at the root of this repository, or cite as:

> S. Gentyala, "Policy-as-Code Framework for Heterogeneous API Gateway Governance," GitHub, 2026. [Online]. Available: https://github.com/sunilgentyala/api-gateway-governance

---

## Reviewer Scores (EDAS)

| Reviewer | Expertise | Presentation | Relevance | Technical Quality | Originality | Overall |
|---|---|---|---|---|---|---|
| 1 | Familiar | Above Average | Good | Excellent | Excellent | **Accept** |
| 2 | Familiar | Average | Average | Average | Average | Accept if Room |
| 3 | Outside area | Average | Good | Above Average | Above Average | Accept if Room |

---

## DOI

The IEEE Xplore DOI will be added to this file once the paper is published in the proceedings (format: `10.1109/TEMSCON...`).

A Zenodo DOI for the repository itself will be added once the `v1.0.0` release is archived. See [GitHub Docs: Citable code](https://docs.github.com/en/repositories/archiving-a-github-repository/referencing-and-citing-content) for instructions.
