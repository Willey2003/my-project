---
tags: [devops-prep, guide]
---
# Phase 26 - CGOA: Certified GitOps Associate

**Golden track step:** G6 · 10-16 Jun 2027 (see schedule) · **Hours:** 28 · **Exam:** CGOA, 90 min online multiple choice, USD 250 (verify price and format on training.linuxfoundation.org) · **Lab:** `lab/golden/platform/flux/`, `lab/gitops/` (Argo CD, from phase 17)

You already ran Argo CD in phase 17 (CAPA). CGOA is tool-neutral: it tests the OpenGitOps principles and
vocabulary first and tools second. Learn the words exactly as OpenGitOps defines them - many questions hinge on one term.

| Week | Focus | Deliverable |
|---|---|---|
| Study week 1 | OpenGitOps principles + glossary, desired vs actual state, reconciliation, drift | One-page glossary in your own words (commit it to your notes) |
| Study week 2 | Patterns: push vs pull, app of apps, environment promotion, secrets, progressive delivery; Flux bootstrap | `flux-lab` running podinfo from Git + Helm |
| Study week 3 | Flux image automation, Flux vs Argo CD, related practices (IaC, CI/CD, DevSecOps), mock exams, sit CGOA | CGOA |

## Domains (verify the current curriculum on github.com/cncf/curriculum before you book)
| Domain | Weight | Your lab |
|---|---|---|
| GitOps Principles | 30% | Principles section below; break each principle on purpose in `flux-lab` |
| GitOps Terminology | 20% | Glossary drill (week 1) |
| GitOps Patterns | 20% | App of apps (`lab/gitops/root-app.yaml`), promotion folders, drift drill |
| GitOps Related Practices | 16% | IaC, config as code, policy as code, CI vs CD split, DevSecOps |
| Tooling | 14% | Flux (`lab/golden/platform/flux/`), Argo CD (`lab/gitops/`), Helm, Kustomize |

## The four OpenGitOps principles (v1.0.0 - memorise them word for word)
1. **Declarative** - "A system managed by GitOps must have its desired state expressed declaratively."
   You describe *what* (a Deployment with 3 replicas), not *how* (`kubectl scale`, a bash script of steps).
2. **Versioned and Immutable** - "Desired state is stored in a way that enforces immutability, versioning and retains a complete version history."
   Git is the usual store, but the principle says *a state store*, not Git. OCI artifacts and S3 buckets qualify if they are versioned and immutable.
3. **Pulled Automatically** - "Software agents automatically pull the desired state declarations from the source."
   An agent inside (or next to) the target system fetches the state; CI does not push credentials into the cluster.
4. **Continuously Reconciled** - "Software agents continuously observe actual system state and attempt to apply the desired state."
   A loop, not a one-shot deploy: observe -> diff -> act, forever, which is what corrects drift.

Exam traps:
- "GitOps requires Git" - false by the principles; Git is the common implementation of principle 2.
- "GitOps requires Kubernetes" - false; Kubernetes is the most common target because its API is declarative already.
- A pipeline that runs `kubectl apply` on merge satisfies 1 and 2 but fails 3 and 4 (push, one-shot, no drift correction).
- Webhooks that *notify* an agent to pull sooner are still pull-based; the agent still fetches the state itself.

## Terminology (OpenGitOps glossary + what the exam expects)
| Term | Meaning |
|---|---|
| Desired state | The aggregate of all configuration data that is sufficient to recreate the system, with its history |
| Actual (live) state | What is really running right now, as observed by the agent |
| State store | System that stores immutable versions of desired state (Git repo, OCI registry, bucket) |
| Reconciliation | Process of making actual state match desired state |
| Software agent | The automation that pulls desired state and reconciles (Flux controllers, Argo CD application-controller) |
| Feedback loop | Open GitOps loop: observe, diff, act, repeat; reports status back (conditions, UI, notifications) |
| Drift | Actual state diverges from desired state (manual `kubectl edit`, a hotfix, a failing controller) |
| Rollback | Revert to an earlier version in the state store (`git revert`) and let the agent reconcile |
| Continuous | Reconciliation keeps happening, not only on commit (interval-based and/or event-triggered) |
| Declarative description | Configuration that states the desired outcome without the steps |
| Source of truth | The single authoritative place for desired state; for GitOps, the state store |

Also know: **idempotent** (applying the same state twice changes nothing), **convergence** (system moves toward desired
state over time), **immutable artifact** (image by digest, chart by version, commit SHA), **environment** (a target,
often a namespace/cluster + a folder/branch of config), **pull request as change control** (review, audit trail, approvals).

## Patterns
**Push vs pull deployment**
| | Push (CI deploys) | Pull (GitOps agent) |
|---|---|---|
| Who applies | CI runner with cluster credentials | Agent running in/near the cluster |
| Credentials | Cluster admin creds live in CI (big attack surface) | Cluster only needs read access to Git/registry |
| Drift | Not detected until next pipeline run | Detected and corrected every interval |
| Firewall | CI must reach the API server | Cluster reaches out; API can stay private |
| Audit | Pipeline logs | Git history is the audit log |

**CI/CD split in GitOps:** CI builds, tests, scans and pushes an immutable image, then *writes the new tag/digest to the
config repo* (PR or commit). CD is the agent pulling that config. Image automation (Flux) or Argo CD Image Updater can do the write-back.

**Repo structures:** monorepo (apps + infra in one repo, simple) vs polyrepo (repo per team/app, separate config repo),
app repo vs config (environment) repo - keep them separate so a config change does not trigger an app build.
Folder per environment (`clusters/dev`, `clusters/prod`) is preferred over branch per environment (branches drift, merges get painful).

**App of apps / bootstrapping:** one root object points at a folder of more app objects, so a whole cluster is
recreated from one entry point. Argo CD: root `Application` -> `apps/*.yaml` (`lab/gitops/root-app.yaml`) or
`ApplicationSet` generators. Flux: `flux bootstrap` creates `flux-system` Kustomization -> it applies `clusters/<name>/`,
which holds more Kustomizations (`infrastructure`, `apps`) chained with `dependsOn`.

**Environment promotion:** same artifact, different config per environment.
- Folder per env with Kustomize overlays (`base/`, `overlays/dev`, `overlays/prod`); promote = PR that copies the tag from dev to prod.
- Helm values per env (`values-dev.yaml`, `values-prod.yaml`).
- Automated promotion: CI opens the prod PR after dev passes tests; tools like Kargo or Flagger automate stage gates.
- Never rebuild for prod - promote the same digest that was tested.

**Drift:** detection = agent compares live vs desired (`flux diff kustomization`, Argo CD OutOfSync). Correction =
self-heal (Argo CD `selfHeal: true`, Flux reconciles every `interval`; Flux reverts changes to fields it manages).
Intentional exceptions: `ignoreDifferences` (Argo CD) for fields an HPA or a mutating webhook owns; Flux
`kustomize.toolkit.fluxcd.io/reconcile: disabled` annotation, or `flux suspend` during an incident (then fix Git and resume).

**Other patterns you will be asked about:** progressive delivery (canary/blue-green driven by Git: Argo Rollouts, Flagger),
secrets (Sealed Secrets, SOPS + age/KMS - Flux decrypts natively via `spec.decryption`, External Secrets Operator),
multi-cluster (hub-and-spoke: one Argo CD manages many clusters; or agent per cluster: Flux in each cluster reading its own path),
pruning / garbage collection (delete from Git -> deleted from cluster; `prune: true`), dependency ordering (Flux `dependsOn`,
Argo CD sync waves), rollback by `git revert` rather than `kubectl rollout undo`.

## Related practices (16%)
- **Infrastructure as Code** - Terraform/OpenTofu, Crossplane; GitOps applies the same loop to infra (Crossplane, tofu-controller).
- **Configuration as Code** and **Policy as Code** - OPA Gatekeeper, Kyverno, ValidatingAdmissionPolicy; policies live in Git too.
- **DevOps / DevSecOps** - shift-left scanning in CI, signed images (cosign), admission verifies signatures; Git gives audit trails.
- **CI/CD** - CI = build/test/package; CD = release to environments. GitOps is a way of doing CD.
- **Continuous delivery vs continuous deployment** - delivery keeps a manual gate (PR approval to prod); deployment goes straight to prod.

## Flux vs Argo CD
| | Flux | Argo CD |
|---|---|---|
| Shape | Set of controllers (GitOps Toolkit): source, kustomize, helm, notification, image-reflector, image-automation | One app with API server, repo-server, application-controller, UI, Dex/SSO |
| UI | None built in (Weave GitOps / Headlamp / Flux Operator UI are separate) | Rich web UI + CLI |
| Core objects | GitRepository/OCIRepository/HelmRepository/Bucket + Kustomization + HelmRelease | Application, AppProject, ApplicationSet |
| Helm | Native `helm install/upgrade` via helm-controller (real Helm releases, hooks run) | Renders with `helm template`, applies manifests (no Helm release secret) |
| Multi-tenancy | Kubernetes RBAC + `serviceAccountName` impersonation per Kustomization | AppProjects + Argo CD RBAC/SSO |
| Image updates | Built-in image automation controllers (write back to Git) | Argo CD Image Updater (separate project) |
| Bootstrap | `flux bootstrap` commits its own manifests to Git (Flux manages itself) | Install manifests/Helm, then app of apps |
| CNCF status | Graduated | Graduated |
Both follow all four principles. Pick Flux for lightweight, API-first, Helm-heavy platforms; Argo CD when teams want a UI and SSO-driven self-service.

## Flux hands-on (study weeks 2-3)
Setup: `./lab.sh kind up`, then install the CLI: `curl -s https://fluxcd.io/install.sh | bash` (or `brew install fluxcd/tap/flux`).
```bash
flux check --pre                                     # cluster version + prerequisites
# Option A - full GitOps: Flux commits itself to a repo it creates (needs a GitHub PAT with repo scope)
export GITHUB_TOKEN=<pat> GITHUB_USER=<you>
flux bootstrap github --owner=$GITHUB_USER --repository=fleet-infra --branch=main \
  --path=./clusters/lab --personal \
  --components-extra=image-reflector-controller,image-automation-controller --read-write-key
# Option B - offline practice: controllers only, no Git write-back
flux install --components-extra=image-reflector-controller,image-automation-controller
kubectl -n flux-system get pods                      # source, kustomize, helm, notification (+ image controllers)
```
After bootstrap, look at what Flux committed: `clusters/lab/flux-system/{gotk-components.yaml,gotk-sync.yaml,kustomization.yaml}`.
`gotk-sync.yaml` is a GitRepository + Kustomization pointing at your own repo - Flux reconciles itself (upgrade = re-run bootstrap).

**GitRepository** (source-controller fetches, packs an artifact, exposes it inside the cluster):
```bash
flux create source git podinfo --url=https://github.com/stefanprodan/podinfo --branch=master \
  --interval=1m --namespace=flux-lab --export > podinfo-source.yaml
```
Fields to know: `spec.url`, `spec.ref` (branch/tag/semver/commit), `spec.interval`, `spec.secretRef` (SSH key or token),
`spec.ignore`, `spec.verify` (signed commits). Status: `status.artifact.revision` = `master@sha1:<commit>`.

**Kustomization** (kustomize-controller builds and applies a path from a source):
```bash
flux create kustomization podinfo --source=GitRepository/podinfo --path="./kustomize" --prune=true \
  --interval=10m --target-namespace=flux-lab --namespace=flux-lab --wait --export > podinfo-ks.yaml
```
Key fields: `sourceRef`, `path`, `prune`, `interval` / `retryInterval`, `targetNamespace`, `dependsOn`, `healthChecks` / `wait`,
`postBuild.substitute` (variable substitution), `patches`, `decryption` (SOPS), `serviceAccountName` (tenant impersonation).

**HelmRelease** (helm-controller runs real Helm installs/upgrades from a HelmRepository, OCIRepository or GitRepository chart):
```bash
flux create source helm podinfo --url=https://stefanprodan.github.io/podinfo --namespace=flux-lab --export
flux create helmrelease podinfo-helm --source=HelmRepository/podinfo --chart=podinfo --chart-version=">=6.0.0 <7.0.0" \
  --target-namespace=flux-lab --namespace=flux-lab --export
helm -n flux-lab list                                # a real Helm release exists (Argo CD would not create one)
```
Know: `spec.chart.spec` vs `spec.chartRef` (OCIRepository), `values` + `valuesFrom` (ConfigMap/Secret), `install.remediation.retries`,
`upgrade.remediation` (rollback on failure), `driftDetection.mode: enabled` (Helm drift is off by default), `dependsOn`.

**Image automation** (three objects, needs the extra controllers and a writable Git source):
1. `ImageRepository` - scans a registry for tags (`image: ghcr.io/stefanprodan/podinfo`, `interval: 5m`).
2. `ImagePolicy` - picks the "latest" tag by rule (`semver: {range: ">=6.0.0"}`, `alphabetical`, `numerical`, `filterTags`).
3. `ImageUpdateAutomation` - clones the repo, rewrites fields marked with a setter comment, commits and pushes.
```yaml
image: ghcr.io/stefanprodan/podinfo:6.5.0 # {"$imagepolicy": "flux-lab:podinfo"}
```
```bash
flux get image repository -n flux-lab ; flux get image policy -n flux-lab   # LATESTIMAGE column
flux get image update -n flux-lab                                           # last commit pushed by Flux
```
The loop stays GitOps: the registry change becomes a Git commit, and the Kustomization applies that commit.

**Daily Flux CLI:**
```bash
flux get all -n flux-lab                            # every Flux object + Ready + revision
flux reconcile kustomization podinfo -n flux-lab --with-source   # force a pull now instead of waiting for interval
flux suspend kustomization podinfo -n flux-lab ; flux resume kustomization podinfo -n flux-lab
flux diff kustomization podinfo -n flux-lab --path ./local/path  # preview a change before you push it
flux tree kustomization podinfo -n flux-lab         # what objects it manages
flux trace deployment podinfo -n flux-lab           # which Flux object + source + revision owns this Deployment
flux events -n flux-lab ; flux logs --level=error --all-namespaces
flux uninstall --keep-namespace                     # removes controllers, leaves workloads
```

## Lab walkthrough (`lab/golden/platform/flux/`)
1. `./lab.sh kind up`, install the flux CLI, then `lab/golden/platform/flux/up.sh` (runs `flux install` if needed and applies `podinfo.yaml`).
2. `flux get all -n flux-lab` until both the Kustomization and the HelmRelease are Ready; `kubectl -n flux-lab get deploy`.
3. **Drift drill (principle 4):** `kubectl -n flux-lab set image deploy/podinfo podinfod=ghcr.io/stefanprodan/podinfo:6.0.0`, then
   `flux reconcile kustomization podinfo -n flux-lab` - Flux puts the Git image back. Now `kubectl -n flux-lab scale deploy podinfo --replicas=1`:
   Flux does NOT revert it, because the podinfo manifest omits `replicas` (the HPA owns it; `flux tree` shows the HPA). Flux only corrects fields it manages.
4. **Prune drill:** delete the `podinfo` Kustomization object (`kubectl delete kustomization podinfo -n flux-lab`) - with `prune: true` the Deployment goes too.
5. **Suspend drill:** suspend, change something by hand, resume - the change is reverted on the next reconcile.
6. **Principle 2 drill:** point `spec.ref` at a tag (`tag: 6.5.0`), then at a semver range - which is more immutable? (A commit SHA or digest.)
7. Repeat steps 3-4 with Argo CD from phase 17 (`selfHeal`, `prune`) and write down which object/field does the same job in each tool.
8. Optional: bootstrap to your own GitHub repo, commit `image-automation.yaml` and watch Flux push a commit.

## Self-check
1. Name the four OpenGitOps principles in order.
2. Does GitOps require Git? Justify with the principle text.
3. A CI job runs `kubectl apply -f k8s/` on every merge to main. Which principles does it violate?
4. Define "desired state" as OpenGitOps does.
5. What is drift and name two causes.
6. How does a GitOps system roll back a bad release?
7. Why is pull-based deployment considered more secure than push?
8. What does a webhook from GitHub to Flux or Argo CD change about the pull model?
9. Folder per environment or branch per environment - which is recommended and why?
10. What is the app-of-apps pattern and what is its Flux equivalent?
11. Which Flux controller fetches Git repositories and Helm charts?
12. What does `prune: true` do on a Flux Kustomization?
13. Name the three image automation objects and their jobs.
14. How do you make Flux reconcile right now instead of waiting for `interval`?
15. One difference in how Flux and Argo CD handle Helm charts.
16. How are secrets kept in a GitOps repo safely? Give two tools.
17. What is the difference between continuous delivery and continuous deployment?
18. Where should the image tag change happen in a GitOps CI/CD split?
19. How do you pause reconciliation during an incident in Flux, and what must you do afterwards?
20. Which Flux field lets a tenant's Kustomization run with restricted permissions?

<details><summary>Answers</summary>

1. Declarative; Versioned and Immutable; Pulled Automatically; Continuously Reconciled.
2. No. Principle 2 requires a versioned, immutable state store with full history - Git is the usual one; OCI registries or buckets also qualify.
3. Pulled Automatically (it is pushed) and Continuously Reconciled (one-shot, no drift correction). It is declarative and versioned.
4. The aggregate of all configuration data sufficient to recreate the system so that instances are indistinguishable, including its version history.
5. Actual state differs from desired state; manual `kubectl edit/scale`, a hotfix, another controller or webhook mutating fields.
6. Revert the commit (`git revert`) in the state store; the agent reconciles the cluster to the previous version.
7. The cluster pulls with read-only access; no CI system holds cluster-admin credentials, and the API server need not be reachable from outside.
8. Nothing fundamental - the webhook only triggers the agent sooner; the agent still pulls and reconciles.
9. Folder per environment (overlays): one branch, easy diff/promotion via PR, no long-lived branches drifting apart.
10. One root object manages a folder of other app objects so a cluster is recreated from one entry point; Flux: the bootstrap `flux-system` Kustomization applying `clusters/<name>/` with nested Kustomizations.
11. source-controller (GitRepository, OCIRepository, HelmRepository, HelmChart, Bucket).
12. Objects that were applied before but are no longer in the source are deleted from the cluster (garbage collection).
13. ImageRepository scans tags; ImagePolicy selects the newest allowed tag; ImageUpdateAutomation writes it to Git and pushes.
14. `flux reconcile kustomization <name> --with-source` (or `helmrelease`, `source git`).
15. Flux helm-controller performs real Helm releases (hooks, release history, `helm list`); Argo CD renders with `helm template` and applies manifests.
16. SOPS (Flux `spec.decryption`), Sealed Secrets, External Secrets Operator (secret stays in Vault/cloud manager; Git holds a reference).
17. Delivery keeps every change releasable with a manual approval to production; deployment releases every passing change automatically.
18. CI builds and pushes an immutable image, then commits the new tag/digest to the config repo (or image automation does it); the agent deploys it.
19. `flux suspend kustomization <name>`; afterwards fix the desired state in Git and `flux resume` it, or Flux will revert your manual fix.
20. `spec.serviceAccountName` - kustomize-controller impersonates that ServiceAccount, so Kubernetes RBAC limits what the tenant can apply.
</details>

## Resources
https://opengitops.dev (principles + glossary - read both twice) · https://fluxcd.io/flux/get-started · https://fluxcd.io/flux/guides/image-update ·
https://argo-cd.readthedocs.io · https://github.com/cncf/curriculum (CGOA PDF) · Linux Foundation LFS169 "Introduction to GitOps" (free)


---
[[Home]] · [[Schedule]]
