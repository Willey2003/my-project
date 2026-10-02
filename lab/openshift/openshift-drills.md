# OpenShift drills (EX188 / EX280 / EX380 / EX430)

## EX188 (Podman, weeks 36-37) - on any RHEL/Fedora VM
- Build a rootless image from a Containerfile with a non-root USER, tag, push to a local registry (`podman run -d -p 5000:5000 registry`).
- Multi-container app with `podman-compose` or a pod: `podman pod create -p 8080:80 web` + two containers.
- Persist data: named volume vs bind mount with `:Z` (SELinux relabel). Why does `:Z` matter?
- Troubleshoot: `podman logs`, `podman inspect`, `podman exec`, `podman healthcheck run`.
- Generate a systemd Quadlet for the container and enable it as a user service.

## EX280 (weeks 38-41)
- `oc new-app` from image and from Git; expose route; edge vs passthrough vs re-encrypt TLS routes.
- Helm chart + Kustomize overlays (dev/prod) deploying the same app.
- HTPasswd IdP + groups + RBAC (`htpasswd-rbac.sh`), remove self-provisioner.
- NetworkPolicy: only the router namespace (`policy-group.network.openshift.io/ingress: ""`) may reach the app.
- Quotas/LimitRanges (`quotas-scc.yaml`), project template with a default quota (`oc adm create-bootstrap-project-template`).
- Install an Operator from OperatorHub via a Subscription YAML, approve a manual InstallPlan.
- CronJob that runs as a dedicated SA; SCC for a legacy UID app.
- Cluster update: read `oc adm upgrade`, channels, and what `oc get clusterversion` tells you.

## EX380 (weeks 42-44)
- LDAP IdP + group sync (`oc adm groups sync` with a sync config + CronJob).
- OADP: install operator, back up a namespace with PVs to an S3 bucket (MinIO in-cluster works), restore into a new namespace.
- MachineConfigPool: label a node `node-role.kubernetes.io/infra`, create an `infra` MCP, taint it, move router pods there.
- OpenShift GitOps operator: an Argo CD Application that manages a namespace's quotas.
- User-workload monitoring: ServiceMonitor for the lab app, PrometheusRule alert, find it in the console.
- Logging: install the logging operator + LokiStack (small size) and query app logs.

## EX430 (weeks 51-52) - RHACS
- Install RHACS operator, Central + SecuredCluster (use `../security/` images as test subjects).
- Vulnerability management: find the highest-CVSS image; create a policy that fails builds on fixable CRITICALs.
- Deploy-time policy enforcement: block `latest` tags and privileged containers - prove it blocks.
- Runtime policy: alert on shell spawned in container (`kubectl exec` into a pod and see the violation).
- Network graph: generate and apply a baseline NetworkPolicy from observed traffic.
- Compliance Operator: run the CIS profile scan, read ComplianceCheckResults, remediate one.
- `roxctl image check` in a CI job.
