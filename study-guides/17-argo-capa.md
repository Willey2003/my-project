# Phase 17 - Argo / GitOps (CAPA)

**Plan weeks:** 53-55 · **Hours:** 32 · **Exam:** CAPA, 90 min multiple choice, USD 250 · **Lab:** `./lab.sh addon argocd rollouts workflows events`, `lab/gitops/`

| Week | Focus | Deliverable |
|---|---|---|
| 53 | GitOps principles, Application/AppProject, sync policies, Helm/Kustomize | App-of-apps repo deploying the kind stack |
| 54 | Argo Rollouts: canary, blue-green, analysis | Canary rollout demo |
| 55 | Argo Workflows DAGs, Argo Events, sit CAPA | CAPA |

## Domains (sheet weights)
| Domain | Weight |
|---|---|
| Argo Workflows | 36% |
| Argo CD | 34% |
| Argo Rollouts | 18% |
| Argo Events | 12% |

## Argo CD
- **Application:** source (repo, revision, path, Helm/Kustomize/plain), destination (cluster, namespace), sync policy (`automated`, `prune`, `selfHeal`), sync options (`CreateNamespace=true`, `ServerSideApply=true`).
- **AppProject:** allowed source repos, destinations, cluster-scoped kinds, roles - multi-tenancy guard rails (`lab/gitops/apps/lab-project.yaml`).
- Sync status (Synced/OutOfSync) vs health (Healthy/Progressing/Degraded/Missing). Sync waves (`argocd.argoproj.io/sync-wave`) and hooks (PreSync/Sync/PostSync/SyncFail) order resources.
- Patterns: app-of-apps (`root-app.yaml`), ApplicationSet generators (list, cluster, git directory, matrix) for many envs/clusters.
- CLI: `argocd login`, `argocd app list|get|sync|diff|history|rollback`, `argocd repo add`, `argocd cluster add`.
- Secrets in GitOps: Sealed Secrets, External Secrets Operator, SOPS - never plain Secrets in Git.

## Argo Rollouts
Rollout CRD replaces Deployment. Canary steps (`setWeight`, `pause`, `analysis`), blue-green (`activeService`, `previewService`, `autoPromotionEnabled`). AnalysisTemplate providers: Prometheus, Job, Web, Datadog... Abort on failed analysis rolls back automatically. Traffic routers (Istio, NGINX, Gateway API plugin) give precise weights instead of replica ratios. Lab: `lab/gitops/rollouts/canary.yaml` and `kubectl argo rollouts` commands in its header.

## Argo Workflows
Workflow = templates (container, script, resource, dag, steps, suspend). DAG tasks with `dependencies`, parameters and artifacts (S3/MinIO), `retryStrategy`, `withItems`/`withParam` fan-out, WorkflowTemplate/ClusterWorkflowTemplate for reuse, CronWorkflow, exit handlers. Lab: `lab/gitops/workflows/dag.yaml`.

## Argo Events
EventSource (webhook, GitHub, S3, calendar, Kafka...) -> EventBus (NATS/JetStream) -> Sensor (dependencies + triggers: create a Workflow, Rollout, HTTP call). Lab: webhook EventSource + Sensor that submits the DAG workflow.

## Deliverable walkthrough
1. Push `lab/` to your `devops-lab` repo; set the repo URL in `root-app.yaml` and `apps/*.yaml`.
2. `kubectl apply -n argocd -f lab/gitops/root-app.yaml` - root creates the project and child apps.
3. Change the replica count in Git, watch Argo CD sync; change it with kubectl, watch self-heal revert it.
4. CI hand-off: make the release pipeline commit the new image tag to Git instead of deploying directly.

## Self-check
1. Difference between sync status and health status?
2. What does `selfHeal` do and when would you turn it off?
3. Canary vs blue-green: one advantage of each.
4. How do you pass a file from one workflow step to another?

<details><summary>Answers</summary>

1. Sync = does live match Git; health = is the running app working.
2. Reverts manual changes to match Git; turn off temporarily during incident debugging.
3. Canary limits blast radius gradually; blue-green gives instant full switch and rollback.
4. Output artifact in one template, input artifact in the next (artifact repository required).
</details>

## Resources
https://argo-cd.readthedocs.io · https://argoproj.github.io/argo-rollouts · https://argo-workflows.readthedocs.io · https://argoproj.github.io/argo-events · Killercoda argoproj scenarios
