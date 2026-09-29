---
tags: [devops-prep, guide]
---
# Phase 20 - Capstone & Portfolio

**Plan weeks:** 67-70 · **Hours:** 56 · **Lab:** `lab/capstone/`

| Week | Focus | Deliverable |
|---|---|---|
| 67 | Scope + STRIDE threat model for the full platform | Threat model doc |
| 68 | Build: RAG investigation copilot over the K8s + Istio + Argo + security stack | Working prototype repo |
| 69 | FAIR Monte Carlo risk quantification + board narrative | Model + narrative deck |
| 70 | Portfolio consolidation, ADRs, mock Staff/Principal system-design interviews | Public portfolio + "why hire me" one-pager |

## The platform you present
Kind (or EKS) cluster built by Ansible -> deployed by Argo CD from Git -> Istio STRICT mTLS + AuthorizationPolicies -> CKS-level hardening (PSA restricted, signed images only, Falco/Tetragon, audit log) -> CI in GitHub Actions with Trivy gate and OIDC to AWS -> optional OpenShift redeploy with RHACS. One repo, one README with an architecture diagram, and a 5-minute demo video.

## Week 68 copilot build plan
1. `cd lab/capstone/copilot && docker compose up -d --build` (Ollama on the host with `nomic-embed-text` and a small chat model).
2. Ingest: runbooks from this kit, Falco alerts (JSON), `kubectl get events -A -o json`, Argo CD sync history.
3. Ask: "Why did the canary roll back at 14:05?" - the answer must cite sources.
4. Evaluate: 20 questions with expected sources; track hit rate; keep the eval in CI.
5. Secure: reuse week 62 mitigations (logs are untrusted input), rate limits, no write tools.

## Week 69 FAIR model
`python3 lab/capstone/risk/fair_montecarlo.py` gives mean/P50/P90/P99 annualised loss per scenario and ROI of controls. Replace the ranges with estimates you can defend (cite incident data or expert estimates), then write a one-page board narrative: top three risks in money, what the controls cost, what residual risk you recommend accepting.

## Week 70 portfolio and interviews
- ADRs (`templates/adr-template.md`): one per big choice (kind vs EKS, Cilium vs Calico, Argo CD vs Flux, sidecar vs ambient, Gatekeeper vs Kyverno).
- Principal narrative checklist from your sheet: a system-design story with trade-offs from a real NTT DATA/VMware incident, 2-3 mentoring stories with outcomes, the Prometheus/Grafana alert-response improvement reframed as org-level impact, a polished writing sample, at least one standalone public tool repo, and 3-5 mock system-design interviews.
- System design practice prompts: multi-region internal developer platform; secure CI/CD for 500 engineers; observability for 2,000 microservices; secrets management migration; zero-downtime cluster upgrades at scale.

## Definition of done
- Public repo(s) with READMEs a reviewer can understand in 5 minutes.
- Every cert on LinkedIn + Credly; portfolio link in your CV header.
- Job search plan starting months 14-18 per the Career sheet.


---
[[Home]] · [[Schedule]]
