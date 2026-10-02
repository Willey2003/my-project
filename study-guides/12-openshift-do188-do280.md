# Phase 12 - OpenShift Administration I & II (DO188 + DO280 -> EX188, EX280)

**Plan weeks:** 36-41 · **Hours:** 70 · **Exams:** EX188 (2.5 h) and EX280 (3 h), both hands-on, ~USD 550 each · **Lab:** Podman on node1, `lab/openshift/crc.sh`, `openshift-drills.md`

| Week | Focus | Deliverable |
|---|---|---|
| 36 | Podman deep dive: builds, Containerfiles, rootless, Compose | Hardened Containerfile + Podman Compose repo |
| 37 | Persisting data, troubleshooting, OpenShift overview, sit EX188 | EX188 |
| 38 | `oc` CLI, Kustomize, Templates, Helm | Helm + Kustomize multi-env repo |
| 39 | AuthN/AuthZ (HTPasswd, RBAC), TLS routes, NetworkPolicies, LoadBalancer/Multus | RBAC + NetworkPolicy lab |
| 40 | Quotas/LimitRanges, Operators via OLM, SCCs, CronJobs | Multi-tenant quota policy + operator install |
| 41 | Cluster updates, review, mocks, sit EX280 | EX280 |

Known gap from your sheet: DO280 assumes DO180 background; your KCNA/CKA/CKAD work covers most of it. Skim the DO180 outline and fill gaps (routes, `oc new-app`, image streams).

## OpenShift vs vanilla Kubernetes
| Kubernetes | OpenShift adds |
|---|---|
| Namespace | Project (namespace + annotations, self-provisioning, templates) |
| Ingress | Route (edge / passthrough / re-encrypt TLS) + Ingress Operator (HAProxy router) |
| Pod Security Admission | SecurityContextConstraints (default `restricted-v2`: random UID, no root) |
| kubectl | `oc` (superset: `oc new-app`, `oc adm`, `oc login`, `oc debug node/`) |
| install-it-yourself add-ons | Operators everywhere, managed by OLM; cluster itself is operator-managed (ClusterVersion, MachineConfig) |
| basic auth plumbing | OAuth server with identity providers (HTPasswd, LDAP, OIDC) |
| no registry | Integrated image registry + ImageStreams |

## EX188 (Podman) essentials
```bash
podman build -t localhost/app:1 -f Containerfile . ; podman images ; podman image tree localhost/app:1
podman run -d --name db -e POSTGRESQL_USER=app ... -v dbdata:/var/lib/pgsql/data:Z registry.redhat.io/rhel9/postgresql-16
podman pod create --name web -p 8080:8080 ; podman run -d --pod web ...
podman logs -f db ; podman exec -it db bash ; podman inspect db --format '{{.State.Health.Status}}'
podman network create appnet ; podman run --network appnet ...   # name resolution between containers
podman-compose up -d  (or: podman compose)
podman save/load ; podman push --tls-verify=false localhost:5000/app:1
```
Rootless containers map your UID to root inside via `/etc/subuid`; ports < 1024 need `net.ipv4.ip_unprivileged_port_start` or a higher port. `:Z` relabels volumes for SELinux (private), `:z` shared.

## EX280 essentials
```bash
oc login -u kubeadmin https://api.crc.testing:6443 ; oc whoami --show-console
oc new-project demo ; oc new-app --name web --image registry.access.redhat.com/ubi9/httpd-24
oc expose svc/web ; oc create route edge web-tls --service web --hostname web.apps-crc.testing
oc set resources deploy/web --requests cpu=100m,memory=128Mi --limits cpu=500m,memory=256Mi
oc set probe deploy/web --readiness --get-url http://:8080/
oc scale deploy/web --replicas 3 ; oc autoscale deploy/web --min 2 --max 5 --cpu-percent 70
oc adm policy add-role-to-user edit developer -n demo ; oc adm policy who-can delete pods -n demo
oc get clusteroperators ; oc get clusterversion ; oc adm upgrade
oc debug node/<node> -- chroot /host journalctl -u kubelet
oc adm must-gather     # support data collection
```
- Identity: `lab/openshift/htpasswd-rbac.sh` (HTPasswd IdP, groups, remove `self-provisioner`).
- Quotas/limits/SCCs: `lab/openshift/quotas-scc.yaml`. Project template with default quota: `oc adm create-bootstrap-project-template -o yaml > tpl.yaml`, edit, `oc create -f tpl.yaml -n openshift-config`, set `projectRequestTemplate` in `project.config.openshift.io/cluster`.
- Operators: Subscription (channel, `installPlanApproval: Manual`) + OperatorGroup; approve with `oc patch installplan ... --type merge -p '{"spec":{"approved":true}}'`.
- Network security: routes with TLS, NetworkPolicies that allow only the ingress router namespace, LoadBalancer services and Multus secondary networks for non-HTTP apps.
- Kustomize (`oc apply -k`) and Helm (`helm install` against OpenShift) for packaged apps.

## Practice rhythm
Weeks 36-37: every day one Podman task from `openshift-drills.md` against a timer. Weeks 38-41: one full EX280 section per day, then the EX280V4.18K practice set as two timed mocks in week 41. Rebuild CRC (`crc delete && crc start`) before each mock.

## Self-check
1. Pod fails with "unable to validate against any security context constraint". Fix without granting `privileged`.
2. Which route type lets the pod terminate TLS itself?
3. How do you stop regular users from creating projects?
4. Where do you look first when `oc login` with a new HTPasswd user fails?
5. Why does a rootless Podman container with `-v ./data:/data` get "permission denied" on RHEL?

<details><summary>Answers</summary>

1. Dedicated service account + least-privileged SCC that fits (e.g. `anyuid`), or fix the image to run as arbitrary UID.
2. Passthrough.
3. Remove the `self-provisioner` cluster role from `system:authenticated:oauth`.
4. `oc get pods -n openshift-authentication` (rollout finished?), the secret name/key in the OAuth CR, the htpasswd file hash format.
5. SELinux label on the host directory; add `:Z`.
</details>

## Resources
DO188 (v4.18), DO280 (v4.18), EX280V4.18K practice set, https://docs.redhat.com/en/documentation/openshift_container_platform, OpenShift Local, Developer Sandbox
