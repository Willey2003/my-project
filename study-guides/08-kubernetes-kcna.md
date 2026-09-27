# Phase 8 - Kubernetes Fundamentals + KCNA

**Plan weeks:** 23-25 · **Hours:** 30 · **Exam:** KCNA, 90 min, 60 multiple choice, USD 250, no prerequisite · **Lab:** `./lab.sh kind up`

| Week | Focus | Deliverable |
|---|---|---|
| 23 | Cloud native landscape, control plane / node architecture | Kind cluster provisioned via Ansible (bonus: write a playbook that runs `lab.sh kind up`) |
| 24 | Pods, Deployments, Services, ConfigMaps, Namespaces | Sample app manifests repo (`k8s/manifests/app.yaml`) |
| 25 | Observability, service mesh, GitOps (concepts), sit KCNA | KCNA |

Note: the plan's Certification Reference sheet lists "Active CKA required" as the KCNA prerequisite - that is a typo; KCNA has none.

## Exam domains (weights from your sheet)
| Domain | Weight |
|---|---|
| Kubernetes Fundamentals | 46% |
| Container Orchestration | 22% |
| Cloud Native Architecture | 16% |
| Cloud Native Observability | 8% |
| Cloud Native Application Delivery | 8% |
(CNCF revises weights occasionally - confirm on the curriculum repo before booking.)

## Architecture
**Control plane:** `kube-apiserver` (the only thing that talks to etcd; authn -> authz (RBAC) -> admission -> persist), `etcd` (consistent key-value store, Raft), `kube-scheduler` (filter + score nodes for unscheduled pods), `kube-controller-manager` (reconcile loops: Deployment, ReplicaSet, Node, Job...), `cloud-controller-manager` (cloud LBs, routes).
**Node:** `kubelet` (runs pods via CRI, reports status, probes), container runtime (containerd/CRI-O), `kube-proxy` (Service VIPs via iptables/IPVS/nftables; replaceable by Cilium eBPF), CNI plugin (pod networking).
**Declarative + reconciliation:** you declare desired state; controllers loop "observe -> diff -> act" forever. This idea explains 80% of KCNA questions.

## Core objects
| Object | Purpose |
|---|---|
| Pod | 1+ containers sharing network namespace + volumes; ephemeral |
| ReplicaSet | keeps N pods; rarely used directly |
| Deployment | rolling updates/rollbacks of ReplicaSets (stateless apps) |
| StatefulSet | stable names/storage per replica (databases) |
| DaemonSet | one pod per node (agents: logging, CNI, Falco) |
| Job / CronJob | run to completion / on schedule |
| Service | stable virtual IP + DNS name for a set of pods (ClusterIP, NodePort, LoadBalancer, headless) |
| Ingress / Gateway API | L7 HTTP routing into the cluster (Gateway API is the successor) |
| ConfigMap / Secret | config and sensitive config (Secrets are base64, not encrypted, unless etcd encryption is on) |
| Namespace | scope for names, RBAC, quotas, network policy |
| PV / PVC / StorageClass | storage abstraction and dynamic provisioning |
| HPA | scale replicas on metrics |

## kubectl you need even for KCNA
```bash
kubectl get pods -A -o wide ; kubectl describe pod x ; kubectl logs x -c container --previous
kubectl create deploy web --image=nginx --replicas=3 --dry-run=client -o yaml > web.yaml
kubectl expose deploy web --port 80 ; kubectl scale deploy web --replicas=5
kubectl rollout status|history|undo deploy/web ; kubectl explain deploy.spec.strategy
kubectl get events --sort-by=.lastTimestamp ; kubectl api-resources
```

## Cloud native concepts (the other 54%)
- **Orchestration:** scheduling (requests, affinity, taints), self-healing (restart, reschedule), autoscaling (HPA pods, VPA sizes, Cluster Autoscaler/Karpenter nodes), rolling updates.
- **Architecture:** microservices vs monolith, 12-factor apps, serverless (Knative, FaaS), service mesh (Istio/Linkerd: mTLS, traffic shifting, observability via sidecars or ambient), autoscaling, multi-tenancy. CNCF project maturity: sandbox -> incubating -> graduated. Roles: SRE, platform engineering. Open standards: OCI (image/runtime), CRI, CNI, CSI, SMI.
- **Observability:** metrics (Prometheus pull model, PromQL), logs (Fluent Bit, Loki), traces (OpenTelemetry, Jaeger), SLI/SLO/error budgets.
- **Delivery:** CI vs CD, GitOps principles (declarative, versioned, pulled automatically, continuously reconciled - OpenGitOps), Argo CD, Flux, Helm, Kustomize.

## Labs
1. `./lab.sh kind up` then `kubectl get nodes -o wide`; `docker exec -it lab-control-plane crictl ps` - find the control-plane static pods; `ls /etc/kubernetes/manifests`.
2. Build and push the lab image: `docker build -t localhost:5001/lab-api:v1 --target runtime lab/docker/app && docker push localhost:5001/lab-api:v1`; `kubectl apply -f lab/k8s/manifests/app.yaml`; `curl http://api.localtest.me`.
3. Kill a pod, watch the ReplicaSet replace it. Delete a node's pods with `kubectl drain lab-worker --ignore-daemonsets`, uncordon.
4. Change `APP_VERSION` in the ConfigMap - why don't running pods see it? (`kubectl rollout restart`).
5. `./lab.sh addon metrics` + `kubectl autoscale deploy api -n shop --min 3 --max 6 --cpu-percent 50`.

## Self-check
1. Which component decides the node for a pod, and which starts it?
2. Where is cluster state stored and who can talk to it directly?
3. Service types and when each is used?
4. What makes a practice "GitOps" rather than CI pushing to a cluster?
5. Pull vs push metrics collection - which does Prometheus use?

<details><summary>Answers</summary>

1. kube-scheduler decides; kubelet on that node starts it via the runtime.
2. etcd; only the API server.
3. ClusterIP internal, NodePort on every node's port, LoadBalancer cloud LB, headless (no VIP) for StatefulSet DNS.
4. Desired state in Git, an in-cluster agent pulls and continuously reconciles.
5. Pull (scrapes /metrics); Pushgateway exists for short-lived jobs.
</details>

## Resources
https://kubernetes.io/docs/concepts/ · https://github.com/cncf/curriculum · https://landscape.cncf.io · https://opengitops.dev · KodeKloud/Killercoda free KCNA playgrounds
