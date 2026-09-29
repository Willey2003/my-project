---
tags: [devops-prep]
---
# Tool gaps by role (beyond your current kit)

Checked against `prep/lab/` and `prep/content/`. Already covered well: Linux/RHEL, Ansible, Vagrant, Docker, Trivy, Cosign, GitHub Actions, kind, Helm, Kustomize, Cilium, Falco, Tetragon, kube-bench, Gatekeeper, Kyverno (light), Argo CD/Rollouts/Workflows, Istio, Terraform on AWS, OpenShift/CRC, RHACS, Ollama, garak, PyRIT.
"Light" below means it is mentioned in a guide but has no hands-on lab yet.

## Senior DevOps engineer (hands-on depth)
| Area | Gap | Why it matters |
|---|---|---|
| Observability | **Prometheus + Grafana + Loki + Tempo, OpenTelemetry Collector** (light today) | Every senior interview asks "how do you know it's broken?" Alertmanager rules, PromQL, traces |
| Secrets | **HashiCorp Vault + External Secrets Operator** (Vault only in Ansible) | Standard pattern for K8s secrets; pairs with your AWS OIDC work |
| Certs/ingress | cert-manager, ingress-nginx or Gateway API | Real clusters need TLS automation |
| Autoscaling | KEDA, Karpenter (light), VPA | EKS cost/scale questions |
| Backup/DR | Velero (light) | DR drills are expected at senior level |
| CI security | Gitleaks, Semgrep, Checkov/tfsec, Syft (SBOM), Renovate | Shift-left pipeline; you have Trivy+Cosign, not SAST/secret/IaC scanning |
| Load testing | k6 (light) | Proves SLOs before release |
| Image build | Packer, Buildah/Podman | Golden AMIs; Red Hat shops use Podman |

## DevOps lead (team and delivery)
| Area | Gap | Why it matters |
|---|---|---|
| Delivery metrics | DORA metrics (Four Keys, Apache DevLake), SLOs with Sloth or Pyrra | Leads are measured on lead time, MTTR, change failure rate |
| Incident mgmt | PagerDuty or Grafana OnCall/Incident, blameless postmortems, runbooks | On-call ownership |
| Terraform at team scale | Terragrunt, Atlantis or Spacelift, Infracost | PR-based plans, cost review, drift |
| Dependency hygiene | Renovate/Dependabot policies, CODEOWNERS, branch protection | Governance without slowing people down |
| Chaos | LitmusChaos or Chaos Mesh | Game days |

## DevOps architect (platform and multi-cloud)
| Area | Gap | Why it matters |
|---|---|---|
| Platform engineering | **Backstage** (developer portal), **Crossplane** (infra via K8s APIs) | Internal developer platform is the 2026 architect conversation |
| Multi-cloud | Azure (AKS, Bicep) or GCP (GKE); Pulumi as alternative IaC | Your plan is AWS + OpenShift only |
| Fleet management | Cluster API, ACM (Red Hat Advanced Cluster Mgmt), Fleet/Flux | Many clusters, one control plane |
| FinOps | OpenCost/Kubecost, AWS Cost Explorer, Cloud Custodian | Architects own cost |
| Policy as code | OPA/Conftest for Terraform, Kyverno deeper | Guardrails across IaC and clusters |
| Design artefacts | C4 model with Structurizr, diagrams-as-code, ADRs (you have template), AWS Well-Architected Tool | How architects communicate |
| Service mesh alt | Linkerd, Cilium service mesh / Hubble | Trade-off discussions vs Istio |

## AI security architect
| Area | Gap | Why it matters |
|---|---|---|
| LLM red teaming | **promptfoo** (red-team + evals in CI) | Complements garak/PyRIT; easy to wire into GitHub Actions |
| Guardrails | **LLM Guard, NeMo Guardrails, Llama Guard**, Presidio (PII) | Input/output filtering is the core control |
| AI gateway | LiteLLM proxy (rate limits, keys, logging) | Central choke point for model access |
| LLM observability | Langfuse or OpenLLMetry | Tracing prompts, tool calls, cost, abuse |
| Model supply chain | ModelScan / picklescan, model signing (Sigstore model-transparency), CycloneDX ML-BOM | Poisoned or malicious model files |
| Agent/MCP security | MCP server allow-listing and scanning (e.g. mcp-scan), sandboxed tool execution (gVisor, Firecracker) | Agentic AI is the fastest-growing attack surface |
| MLOps platform | MLflow, KServe or vLLM on K8s | You need to secure what ML teams actually run |
| Frameworks | OWASP LLM Top 10 and Agentic Top 10, MITRE ATLAS, NIST AI RMF, ISO/IEC 42001, EU AI Act | Architect-level governance language |
| Cloud security posture | Prowler, Wiz/Prisma-style CSPM concepts, DefectDojo for findings | Consolidating findings across the stack |

## Add to the lab first (in this order)
1. **Observability stack** (kube-prometheus-stack + Loki + Tempo + OTel Collector) as a `./lab.sh addon observability`. Everything later (SLOs, chaos, AI tracing) depends on it.
2. **Vault + External Secrets Operator** on kind, feeding the sample app. Fits weeks 45-50.
3. **CI security gates** in `cicd/`: Gitleaks, Semgrep, Checkov, Syft SBOM next to the existing Trivy + Cosign steps. Small effort, big portfolio value.
4. **AI guardrail layer** in `ai-security/`: LiteLLM proxy -> LLM Guard -> Ollama, with promptfoo red-team tests in CI and Langfuse tracing. This turns the sandbox into an architecture you can demo.
5. **Backstage + Crossplane** as a capstone platform demo (architect story).

Later or read-only: Terragrunt/Atlantis, OpenCost, Chaos Mesh, Azure/GCP, Cluster API.


---
[[Home]]
