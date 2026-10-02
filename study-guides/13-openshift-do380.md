# Phase 13 - OpenShift Administration III: Scaling Deployments (DO380 -> EX380)

**Plan weeks:** 42-44 · **Hours:** 38 · **Exam:** EX380, hands-on, ~USD 550 (confirm duration at booking) · **Lab:** OpenShift Local with 16+ GiB, `openshift-drills.md` (EX380 section)

Version gap from your sheet: DO380 material is OpenShift 4.14, the exam targets 4.18+. Validate every lab on a current cluster and read the 4.15-4.18 release notes for changed operator names/fields.

| Week | Focus | Deliverable |
|---|---|---|
| 42 | Advanced identity (LDAP/OIDC, group sync, kubeconfigs), OADP backup/restore | OADP backup + restore runbook |
| 43 | Cluster partitioning (node pools, MachineConfig), advanced scheduling, PDBs | Node-pool isolation lab |
| 44 | OpenShift GitOps, monitoring, logging, review, sit EX380 | EX380 |

## Identity at scale
- LDAP identity provider: `bindDN`, `bindPassword` secret, `ca` configmap, `url` with search filter. Group sync: `oc adm groups sync --sync-config=ldap-sync.yaml --confirm`, then automate with a CronJob running under a service account with the right cluster role.
- OIDC providers (Keycloak/Red Hat build of Keycloak, Entra ID): claims mapping for username/groups.
- kubeconfig management: multiple contexts, service-account tokens for automation (`oc create token sa --duration`), `oc config` subcommands.

## Backup and DR with OADP
OADP = Velero + plugins, installed via operator. `DataProtectionApplication` points at object storage (S3, or MinIO in-cluster for the lab). `Backup` CRs select namespaces/labels; PV data via CSI snapshots or file-system backup (Kopia). `Restore` CR can map namespaces (restore into `app-restored`). `Schedule` CR for periodic backups. Your runbook should include: what is backed up, RPO/RTO, how to verify a backup, a restore test transcript.

## Partitioning and scheduling
- Label nodes with roles (`node-role.kubernetes.io/infra=`), create a MachineConfigPool selecting them, taint them (`infra=reserved:NoSchedule`), then move router/registry/monitoring with nodePlacement + tolerations in their operator configs.
- MachineConfig: declarative OS config (files, systemd units, kernel args) rolled out by the Machine Config Operator; watch `oc get mcp` UPDATED/UPDATING/DEGRADED. Pause a pool during maintenance.
- Advanced scheduling: node/pod affinity, anti-affinity for HA replicas, topology spread across zones, PDBs protecting availability during drains and upgrades.

## Day-2 platform services
- OpenShift GitOps operator (Argo CD): cluster-scoped instance for platform config, namespace-scoped instances for teams; RBAC via `argocd-rbac-cm` and AppProjects.
- Monitoring: platform Prometheus is operator-managed; enable user workload monitoring (`enableUserWorkload: true` in `cluster-monitoring-config`), add ServiceMonitor + PrometheusRule for your app, silence/route alerts in Alertmanager.
- Logging: Logging operator + Loki operator, `ClusterLogForwarder` pipelines (application/infrastructure/audit), retention settings.

## Self-check
1. Restore a namespace from backup into a new name - which CR field?
2. A node pool is stuck with DEGRADED=True. First command?
3. How do you make only infra nodes run the router?
4. Why use a PDB before cluster upgrades?
5. Where do user alerts for application metrics live?

<details><summary>Answers</summary>

1. `spec.namespaceMapping` in the Velero `Restore`.
2. `oc describe mcp <pool>` then `oc get mc` / MCD pod logs on the failing node.
3. `nodePlacement` (nodeSelector + tolerations) in the IngressController CR.
4. Drains respect PDBs, so replicas are not all evicted at once.
5. PrometheusRule objects in the app namespace with user workload monitoring enabled.
</details>

## Resources
DO380 (4.14 - validate on 4.18+), OADP docs, OpenShift GitOps docs, https://www.redhat.com/en/services/certification
