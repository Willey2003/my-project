---
tags: [devops-prep, guide]
---
# Phase 28 - CNPA + CNPE: Cloud Native Platform Engineering

**Golden track step:** G8-G9 · 27 Jun-14 Jul 2027 (see schedule) · **Hours:** 68 (CNPA 28 + CNPE 40) · **Lab:** `lab/golden/platform/idp/`, plus `flux/` (phase 26) and `backstage/` (phase 27)

| Exam | Level | Hours | Format (verify) |
|---|---|---|---|
| CNPA - Cloud Native Platform Engineering Associate | Associate | 28 | Online, proctored, multiple choice (~120 min), USD 250 |
| CNPE - Certified Cloud Native Platform Engineer | Professional | 40 | Online, proctored, performance-based (hands-on tasks in live clusters) |

> **Check before you plan these weeks.** Go to https://www.cncf.io/training/ (and the exam pages on training.linuxfoundation.org)
> and confirm for **each** exam: (1) that it is currently available to book (CNPE is new and was in beta/early access at launch),
> (2) whether it is currently **required for, counts toward, or is excluded from** the Golden Kubestronaut title - the list of
> required certifications has changed more than once, and (3) the current domains and weights. Do not rely on this guide for any of these three.

Order: sit CNPA first (vocabulary + concepts), then build the hands-on skills for CNPE. Everything here reuses earlier phases:
GitOps (26), Backstage (27), policy (CKS/KCSA phase 14-15), observability (CKA/CKAD), multi-tenancy (CKA RBAC/quotas).

| Week | Focus | Deliverable |
|---|---|---|
| Study week 1 | Platform-as-product, IDP anatomy, CNCF platforms white paper + maturity model, Team Topologies | One-page "platform product brief" for your lab platform |
| Study week 2 | Golden paths, self-service APIs (CRDs/operators, Crossplane), GitOps delivery, policy as code | `idp/` namespace-as-a-service applied via Kustomize, policy rejecting a bad Deployment |
| Study week 3 | Observability for platforms, DORA + SPACE metrics, multi-tenancy models, mock exams, sit CNPA | CNPA |
| Study week 4 | CNPE hands-on: Crossplane v2 install, XRD + Composition + function pipeline | `crossplane/` concept exercise running for real |
| Study week 5 | Flux/Argo CD multi-tenant delivery, promotion, policy (Kyverno/Gatekeeper/VAP), secrets | Tenant onboarding = one PR |
| Study week 6 | Platform observability (Prometheus, OpenTelemetry, SLOs), troubleshooting controllers and reconcilers | Platform SLO dashboard + 3 alerts |
| Study week 7 | Timed drills (2 h), fix weak spots, sit CNPE | CNPE |

## CNPA domains (verify the current curriculum on github.com/cncf/curriculum)
| Domain | Weight | Where in this guide |
|---|---|---|
| Platform Engineering Core Fundamentals | 36% | Platform as product, IDP, golden paths, declarative APIs |
| Platform Observability, Security, and Conformance | 20% | Observability, policy as code, supply chain |
| Continuous Delivery & Platform Engineering | 16% | GitOps delivery (phase 26), CI/CD integration |
| Platform APIs and Provisioning Infrastructure | 12% | CRDs/operators, Crossplane, Cluster API |
| IDPs and Developer Experience | 8% | Portals (Backstage), self-service, DevEx |
| Measuring your Platform | 8% | DORA, SPACE, adoption metrics |

## CNPE domains (study map only - the exam is new; take the official list and weights from the curriculum repo)
| Area | Typical hands-on task | Your lab |
|---|---|---|
| GitOps and continuous delivery | Onboard a tenant/app through Flux or Argo CD, promote between envs, fix a failing reconcile | `flux/`, `lab/gitops/` |
| Platform APIs and self-service | Write/repair an XRD + Composition or a CRD-backed API, provision via a claim/XR | `idp/crossplane/` |
| Security, policy and multi-tenancy | Quotas, LimitRanges, NetworkPolicy, RBAC, admission policies per tenant | `idp/namespace-service/`, `idp/policy/` |
| Observability and operations | Find why a platform component is unhealthy from metrics/logs/events; add an SLO | Prometheus from `./lab.sh addon` |
| Platform architecture and developer experience | Golden path template, portal catalog wiring | `backstage/` |

## Platform as a product
- **Platform engineering:** building and running an internal platform that reduces developers' cognitive load by offering
  curated, self-service capabilities (infrastructure, delivery, observability, security) behind consistent interfaces.
- **Platform as a product:** developers are the customers. The platform team does user research, has a product owner and a public roadmap,
  measures adoption and satisfaction, and markets features. Adoption is earned - a platform people route around has failed.
- **Thinnest Viable Platform (TVP):** start with the smallest thing that helps (a wiki page + a template may be enough), grow on demand.
- **Team Topologies:** stream-aligned teams (deliver features), platform team (provides X-as-a-Service), enabling team (coaches),
  complicated-subsystem team. Interaction modes: collaboration, X-as-a-Service, facilitating. Platform team goal: X-as-a-Service.
- **CNCF Platforms white paper** (TAG App Delivery, now the Platforms working group): a platform provides capabilities (provisioning, delivery,
  observability, security, artifact storage, data/messaging, identity) through interfaces (portal, API, CLI, templates, docs).
- **CNCF Platform Engineering Maturity Model:** levels Provisional -> Operational -> Scalable -> Optimizing across aspects
  Investment, Adoption, Interfaces, Operations, Measurement. Know which behaviours sit at which level (e.g. "ad-hoc scripts" = Provisional,
  "self-service with integrated measurement" = Optimizing).
- Anti-patterns: ticket-ops (developers file tickets for everything), "build it and they will come", mandatory platform with no feedback loop,
  platform team as a renamed ops team, portal-only platforms with no automation behind the buttons.

## Internal Developer Platform (IDP)
The **platform** is the capability layer (APIs, automation, guardrails); the **portal** (Backstage, Port, etc.) is one interface to it.
An IDP typically has: a developer portal + service catalog, templates/golden paths, a platform API (Kubernetes API with CRDs is common),
infrastructure orchestration (Crossplane, Terraform/OpenTofu controllers, Cluster API), GitOps delivery, secrets management, policy engine,
observability stack, and identity/RBAC wiring. Reference architecture words to recognise: developer control plane, integration and delivery plane,
resource plane, monitoring and logging plane, security plane.

## Golden paths
A **golden path** (paved road) is the opinionated, supported, documented way to do a common task end to end - "new service to production
in a day". It is **optional but attractive**: teams may leave it, but then they own what they build. Implemented as templates (Backstage
scaffolder, `lab/golden/platform/backstage/templates/new-service`), pre-wired CI, default manifests, and self-service APIs such as
"namespace as a service" (`idp/namespace-service/`). A golden path encodes the guardrails (quotas, policies, observability) so developers get them for free.

## Self-service with Kubernetes APIs
- **Kubernetes as the platform control plane:** declarative API + reconciliation loops + RBAC + admission = everything a platform API needs.
- **CRDs + operators:** a CustomResourceDefinition adds a new kind (`kind: Database`); an operator (controller) watches it and reconciles
  real resources. Build with Kubebuilder or Operator SDK (Go), or kopf (Python). Operator maturity: install, upgrades, lifecycle, insights, autopilot.
- **Crossplane** (CNCF graduated) turns the cluster into a universal control plane:
  | Object | Role |
  |---|---|
  | Provider | Package that installs CRDs + controller for an external API (AWS, GCP, Azure, Helm, Kubernetes) |
  | Managed Resource (MR) | One external resource (an S3 bucket, an RDS instance) |
  | CompositeResourceDefinition (XRD) | Defines the platform API schema you offer developers (like a CRD) |
  | Composition | How one composite resource (XR) is built - a pipeline of **Functions** (patch-and-transform, go-templating, KCL, Python) |
  | Composite Resource (XR) | An instance of your API; in Crossplane v2 XRs can be namespaced and compose any Kubernetes resource |
  | Claim | v1 namespaced handle for a cluster-scoped XR - legacy in v2, where you create namespaced XRs directly |
  Commands: `helm install crossplane crossplane-stable/crossplane -n crossplane-system --create-namespace`, `kubectl get xrd`,
  `kubectl get composition`, `crossplane beta trace <kind> <name>`, `crossplane render xr.yaml composition.yaml functions.yaml` (offline preview).
- Alternatives worth naming: Terraform/OpenTofu via controllers, kro (Kube Resource Orchestrator, ResourceGraphDefinition), Cluster API (clusters as resources),
  KubeVela/OAM (application model), Helm charts as a lightweight "API".
- Self-service interfaces: PR to a GitOps repo (auditable), portal form (Backstage template that writes the PR), `kubectl apply` of an XR, CLI.

## Policy as code
Guardrails, not gates: policies should give fast, explainable feedback and run in several places.
| Tool | Language | Notes |
|---|---|---|
| ValidatingAdmissionPolicy | CEL, built in (GA 1.30) | No extra install; `ValidatingAdmissionPolicy` + `ValidatingAdmissionPolicyBinding`; `validationActions: [Deny\|Warn\|Audit]` |
| MutatingAdmissionPolicy | CEL | Built-in mutation (newer; check your cluster version) |
| OPA Gatekeeper | Rego | ConstraintTemplate + Constraint; audit of existing objects (`lab/security/gatekeeper-policies.yaml`) |
| Kyverno | YAML/CEL | Validate, mutate, generate (e.g. generate a default NetworkPolicy per new namespace), verify images |
| Conftest / kyverno CLI / gator | Rego/YAML | Same policies in CI against manifests before they reach Git main |
Where policies run: IDE/pre-commit -> CI -> admission -> runtime audit. Start in audit/warn mode, measure, then enforce.
Supply chain policy: signed images (cosign/Sigstore), SBOM + vulnerability gates, allowed registries.

## Observability for platforms
- Observe the **platform itself** as a product: API/controller availability, reconcile latency and errors (`controller_runtime_reconcile_errors_total`,
  `workqueue_depth`), GitOps sync failures (`gotk_reconcile_condition`, Argo CD `argocd_app_info`), provisioning time (request -> namespace ready),
  template success rate, admission denials.
- Offer observability **to tenants** as a capability: OpenTelemetry (collector + SDKs, OTLP), Prometheus/Thanos/Mimir for metrics, Loki/Elasticsearch for logs,
  Tempo/Jaeger for traces, Grafana dashboards per team; defaults injected by the golden path (ServiceMonitor, OTel env vars).
- SLOs for platform services: SLI (e.g. fraction of namespace requests ready < 5 min) + SLO target (99%) + error budget; alert on burn rate.
- Cost visibility (FinOps): OpenCost/Kubecost by namespace/label - one reason for consistent `team` labels.

## Measuring the platform: DORA and SPACE
**DORA** (delivery performance, from the State of DevOps research):
| Metric | Measures |
|---|---|
| Deployment frequency | How often you deploy to production (throughput) |
| Lead time for changes | Commit -> running in production (throughput) |
| Change failure rate | % of deployments causing a failure needing remediation (stability) |
| Failed deployment recovery time (was MTTR / time to restore) | How fast you recover from a failed change (stability) |
Newer reports add **rework rate** and discuss reliability as a fifth dimension. Use them at team level, trend over time, never to rank individuals.

**SPACE** (developer productivity is multi-dimensional): **S**atisfaction and well-being, **P**erformance (outcomes), **A**ctivity (counts),
**C**ommunication and collaboration, **E**fficiency and flow. Pick metrics from at least three dimensions and mix surveys with system data.
Platform-specific: adoption (% of services on the golden path), time to first deploy for a new service/new hire, onboarding time,
ticket volume to the platform team, developer NPS/CSAT, DevEx survey scores (feedback loops, cognitive load, flow state).

## Multi-tenancy
| Model | Isolation | Cost | Tools |
|---|---|---|---|
| Namespace per tenant (soft) | RBAC, ResourceQuota, LimitRange, NetworkPolicy, Pod Security Admission, policies | Lowest | Native, Capsule, Kyverno generate |
| Virtual cluster per tenant | Own API server/control plane, shared nodes | Medium | vcluster, Kamaji (hosted control planes) |
| Node pool per tenant | Taints/tolerations + node affinity, separate kernels from other tenants | Medium | Native scheduling |
| Cluster per tenant (hard) | Full isolation, separate blast radius | Highest | Cluster API, managed K8s, Crossplane |
Namespace-as-a-service checklist (what `idp/namespace-service/base` creates): Namespace with labels (team, PSA level), ResourceQuota,
LimitRange (defaults so pods without requests are admitted and counted), default-deny NetworkPolicy + allow DNS/same-namespace,
RoleBinding of the team group to `edit` (namespaced power, no cluster access). Noisy neighbours are handled by quotas + requests/limits + PriorityClass.

## Labs (`lab/golden/platform/idp/`)
```bash
./lab.sh kind up cilium                                  # NetworkPolicy needs an enforcing CNI
cd lab/golden/platform/idp
kubectl kustomize namespace-service/base | less          # read what the golden path stamps out
./up.sh                                                  # applies base (ns platform-lab) + admission policy + smoke test
kubectl -n platform-lab describe quota,limitrange
kubectl -n platform-lab get netpol
kubectl auth can-i create deploy -n platform-lab --as=jdoe --as-group=team-platform   # yes
kubectl auth can-i create ns --as=jdoe --as-group=team-platform                        # no
```
1. **Namespace as a service:** `./up.sh tenant team-a` renders the `tenants/team-a` overlay (ns `platform-lab-team-a`, smaller quota, team-a group).
   Write `tenants/team-b` yourself - onboarding a tenant must be a copy + 3 edits. Then make Flux apply `namespace-service/tenants/` so onboarding is a PR.
2. **LimitRange defaults:** `kubectl -n platform-lab run t --image=nginx:1.27` and `kubectl -n platform-lab get pod t -o jsonpath='{.spec.containers[0].resources}'` - requests were injected.
   Delete the LimitRange and retry: the quota now rejects the pod (quota on requests needs every pod to set them).
3. **Default deny:** `kubectl -n platform-lab run c --image=busybox:1.36 --rm -it -- wget -qO- -T 3 http://example.com` fails; DNS still resolves; same-namespace traffic works.
4. **Policy as code:** `kubectl apply -f policy/bad-deploy.yaml` is denied by the ValidatingAdmissionPolicy (no `team` label); `policy/good-deploy.yaml` passes.
   Switch the binding to `validationActions: [Warn, Audit]` and compare the client output.
5. **Crossplane concept exercise (CNPE, study week 4):** read `crossplane/*.yaml` first - it is marked as a concept exercise. Then for real:
   `./up.sh crossplane` installs Crossplane v2 + the patch-and-transform function and applies the XRD, Composition and one XR;
   `kubectl get xteamnamespace`, `crossplane beta trace xteamnamespace team-b`. Change `size: small` to `large` and watch the quota change.
6. **Golden path end to end:** Backstage template (`../backstage/templates/new-service`) -> repo with `catalog-info.yaml` -> Flux/Argo CD deploys it
   into a namespace created by step 1 -> it shows up in the catalog with docs. Draw it; this is your CNPA mental model.
7. **Measure it:** for one week log deploys of your lab apps (Git log is enough) and compute deployment frequency and lead time; write one SPACE survey question per dimension.

CNPE drill list (2 h timer, kind cluster, docs open): onboard a tenant (ns + quota + limits + netpol + RBAC) from scratch; fix a Flux Kustomization stuck
on a bad path; fix an XR stuck not Ready (read `crossplane beta trace` + events); write a VAP that blocks `:latest` images; expose a platform metric
and write a PromQL alert for reconcile errors; promote an app from dev to prod overlay by PR only.

## Self-check
1. Define platform engineering in one sentence.
2. What makes a platform "a product"? Name three practices.
3. What is the Thinnest Viable Platform?
4. Which Team Topologies interaction mode should a mature platform team mostly use?
5. What is the difference between an IDP and a developer portal?
6. What is a golden path and why must it be optional?
7. How does an operator implement a platform API on Kubernetes?
8. In Crossplane, what are an XRD, a Composition and an XR?
9. What changed about claims in Crossplane v2?
10. Name the four stages of the CNCF Platform Engineering Maturity Model.
11. List the four DORA metrics and whether each measures throughput or stability.
12. What does SPACE stand for?
13. Give two platform-specific adoption metrics.
14. Why should DORA metrics not be used to rank individual engineers?
15. Name three built-in Kubernetes controls for soft multi-tenancy.
16. When would you give a tenant its own cluster or virtual cluster?
17. Why does a namespace with a CPU-requests ResourceQuota usually also need a LimitRange?
18. Compare ValidatingAdmissionPolicy, Gatekeeper and Kyverno in one line each.
19. Name three things you would monitor about the platform itself (not tenant apps).
20. What must you check on cncf.io/training before booking CNPA or CNPE?

<details><summary>Answers</summary>

1. Designing and running internal self-service platforms that reduce developer cognitive load by offering curated capabilities behind consistent interfaces.
2. Developers treated as customers: user research/feedback, a product owner and public roadmap, adoption and satisfaction metrics (also docs, marketing, SLAs).
3. The smallest set of capabilities (even docs + templates) that accelerates teams; grown only as demand is proven.
4. X-as-a-Service (collaboration while discovering a new capability, facilitating for coaching).
5. The IDP is the whole capability layer (APIs, automation, guardrails); a portal such as Backstage is one user interface on top of it.
6. The supported, opinionated, documented path for a common task; optional so teams with real needs can diverge (owning the consequences), and adoption stays a signal of value.
7. A CRD defines the API; a controller watches custom resources and continuously reconciles real resources to match their spec, reporting status.
8. XRD = schema of the API you offer; Composition = how an XR is turned into resources (function pipeline); XR = an instance of that API.
9. v2 supports namespaced XRs created directly by users, so claims are legacy (kept for v1-style cluster-scoped XRs); XRs can compose any Kubernetes resource.
10. Provisional, Operational, Scalable, Optimizing.
11. Deployment frequency (throughput), lead time for changes (throughput), change failure rate (stability), failed deployment recovery time (stability).
12. Satisfaction and well-being, Performance, Activity, Communication and collaboration, Efficiency and flow.
13. % of services on the golden path/templates; time to first deploy for a new service or new hire (also self-service vs ticket ratio, developer NPS).
14. They describe team/system delivery performance; used on individuals they get gamed (Goodhart's law) and damage trust.
15. RBAC (Role/RoleBinding), ResourceQuota + LimitRange, NetworkPolicy, Pod Security Admission (also taints/affinity, PriorityClass).
16. When tenants need cluster-scoped resources (CRDs, their own operators), different Kubernetes versions, strict compliance/blast-radius isolation, or are untrusted.
17. A quota on requests rejects pods that do not declare requests; the LimitRange injects default requests/limits so such pods are admitted and counted.
18. VAP: built-in CEL validation, no extra components; Gatekeeper: OPA/Rego with constraint templates and audit; Kyverno: YAML/CEL policies that can validate, mutate, generate and verify images.
19. Reconcile errors/latency of controllers (Flux, Crossplane, operators), time to provision (namespace/database ready), GitOps sync failures, admission denials, template success rate, API server/controller availability SLOs.
20. That each exam is currently available, whether it counts toward (or is required for) Golden Kubestronaut right now, and the current domains/weights and format.
</details>

## Resources
https://www.cncf.io/training (availability + Golden Kubestronaut requirements) · https://github.com/cncf/curriculum (CNPA/CNPE PDFs) ·
https://tag-app-delivery.cncf.io/whitepapers/platforms and .../platform-eng-maturity-model · https://docs.crossplane.io ·
https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy · https://dora.dev · "The SPACE of Developer Productivity" (ACM Queue, 2021) ·
*Team Topologies* (Skelton & Pais) · Linux Foundation LFS144 "Introduction to Platform Engineering"


---
[[Home]] · [[Schedule]]
