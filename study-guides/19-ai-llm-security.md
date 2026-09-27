# Phase 19 - AI / LLM & Agentic Security

**Plan weeks:** 59-66 · **Hours:** 88 · **Cert:** none (portfolio) · **Lab:** `lab/ai-security/` (isolated sandbox, local model only)

| Week | Focus | Deliverable |
|---|---|---|
| 59 | LLM threat modelling, OWASP LLM Top 10 | LLM threat model doc |
| 60 | Automated red-teaming of your own local endpoint (PyRIT) | PyRIT scan report |
| 61 | LLM vulnerability scanning (Garak) | Garak report + remediation notes |
| 62 | Agent / MCP threat surface with mock tools | Injection PoC + mitigation checklist |
| 63 | Model supply chain scanning (ModelScan) | ModelScan CI job |
| 64 | Policy-as-code for model deployment gating (Gatekeeper) | OPA policy pack |
| 65 | Governance: NIST AI RMF, ISO 42001, EU AI Act, India DPDP/SEBI/RBI | Governance-to-control crosswalk |
| 66 | Detection content, portfolio indexing | Sigma rule pack + portfolio index |

Ground rule: evaluate only models and endpoints you own, inside the sandbox. The goal is measuring and reducing risk, and every report ends with mitigations.

## Frameworks to know
- **OWASP Top 10 for LLM Applications (2025):** prompt injection, sensitive information disclosure, supply chain, data and model poisoning, improper output handling, excessive agency, system prompt leakage, vector/embedding weaknesses, misinformation, unbounded consumption.
- **MITRE ATLAS:** adversary tactics/techniques for ML systems - use it to label threats in the model.
- **NIST AI RMF:** Govern, Map, Measure, Manage. **ISO/IEC 42001:** AI management system (think ISO 27001 for AI). **EU AI Act:** risk tiers (prohibited, high-risk, limited, minimal) and GPAI obligations. **India:** DPDP Act + Rules 2025 (consent, data fiduciary duties), SEBI CSCRF, RBI directions for regulated entities.

## Week-by-week notes
- **59 Threat model:** use `lab/capstone/templates/stride-threat-model.md`; draw the copilot data flow (user -> app -> retriever -> vector DB -> LLM -> tools). Mark trust boundaries: every piece of retrieved or tool-returned content is untrusted input.
- **60-61 Evaluation:** run the scanners against the local Ollama model per `lab/ai-security/README.md`; record which probe categories succeed, then re-run with a hardened system prompt and output filtering and compare rates. The report shows before/after numbers, not just findings.
- **62 Agents:** `mock_agent.py` measures how often untrusted document text causes an unrequested tool call, with and without mitigations (content delimiting, stripping instruction-like content, and most important, a policy check outside the model that only permits tools the user asked for). Checklist themes: least-privilege tools, human confirmation for side effects, allow-listed destinations, no secrets in context, logging of every tool call.
- **63 Model supply chain:** pickle-based model files can execute code on load; prefer safetensors, scan with ModelScan in CI, pin model hashes, use trusted registries.
- **64 Deployment gating:** a Gatekeeper constraint that only admits model-serving pods with a `model-scan: passed` label and an approved image registry (pattern in `lab/security/gatekeeper-policies.yaml`).
- **65 Governance crosswalk:** spreadsheet rows = controls you actually built (scanning, signing, access control, logging, evaluation); columns = NIST AI RMF function, ISO 42001 clause, EU AI Act article, DPDP obligation. This is the artefact leaders read.
- **66 Detection:** Sigma rules for suspicious events from your stack (e.g. Falco shell-in-container, unusual tool call volume from the copilot), converted to your SIEM; README index of all portfolio repos.

## Self-check
1. Why is indirect prompt injection harder to stop than direct?
2. Most reliable mitigation for excessive agency?
3. Why are pickle model files risky and what replaces them?
4. Which EU AI Act tier would a credit-scoring model fall into?

<details><summary>Answers</summary>

1. The malicious text arrives via data the user never sees (web pages, documents, tool outputs), so input filtering on the user prompt misses it.
2. Deterministic authorisation outside the model: least-privilege tools plus human approval for consequential actions.
3. Unpickling can run arbitrary code; use safetensors and scan/pin artefacts.
4. High-risk.
</details>

## Resources
https://genai.owasp.org · https://atlas.mitre.org · https://www.nist.gov/itl/ai-risk-management-framework · https://artificialintelligenceact.eu · PyRIT, Garak, ModelScan docs
