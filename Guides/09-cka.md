---
tags: [devops-prep, guide]
---
# Phase 9 - CKA: Certified Kubernetes Administrator

**Plan weeks:** 26-29 · **Hours:** 46 · **Exam:** 2 h, performance-based, USD 445 (look for LF coupons), 2 killer.sh sessions included · **Lab:** `./lab.sh kind up`, `./lab.sh break ...`

| Week | Focus | Deliverable |
|---|---|---|
| 26 | Cluster architecture & install: kubeadm, TLS bootstrapping, RBAC | cka-week1-cluster-setup-lab repo |
| 27 | Workloads & scheduling: requests/limits, taints/tolerations, DaemonSets/StatefulSets | Scheduling lab write-up |
| 28 | Services/Ingress/Gateway API/CNI (Cilium), PV/PVC/StorageClass | Cilium + Ingress lab |
| 29 | Troubleshooting, killer.sh mocks, sit exam | CKA |

## Domains (from your sheet; verify current curriculum - the Feb 2025 revision added Gateway API, Helm, Kustomize, CRDs/operators)
| Domain | Weight | Your lab |
|---|---|---|
| Troubleshooting | 30% | `./lab.sh break random` daily |
| Cluster Architecture, Installation & Configuration | 25% | kubeadm on 2 VMs, RBAC, etcd backup |
| Services & Networking | 20% | `kind up cilium`, NetworkPolicy, Ingress, Gateway |
| Workloads & Scheduling | 15% | `k8s/manifests/*` |
| Storage | 10% | `k8s/manifests/storage.yaml` |

## Exam technique (worth 10-15 points by itself)
```bash
alias k=kubectl ; export do="--dry-run=client -o yaml" ; export now="--force --grace-period 0"
source <(kubectl completion bash) ; complete -o default -F __start_kubectl k
k config use-context <ctx>          # EVERY question starts by switching context - read the header
k explain pod.spec.containers.securityContext --recursive | less
```
Generate YAML imperatively, then edit: `k run`, `k create deploy|job|cronjob|cm|secret|sa|role|rolebinding|ingress|svc`, `k expose`. Skip and flag hard questions; come back. Verify each answer (get/describe/curl) before moving on.

## Week 26 - cluster install and maintenance (practise on node1/node2 VMs, not kind)
kubeadm flow (know the order):
1. On all nodes: swap off, load `overlay` + `br_netfilter`, sysctl `net.ipv4.ip_forward=1`, install containerd (`SystemdCgroup = true`), kubeadm/kubelet/kubectl from pkgs.k8s.io, hold versions.
2. `kubeadm init --pod-network-cidr=10.244.0.0/16 --apiserver-advertise-address=<ip>`; copy admin.conf to `~/.kube/config`.
3. Install CNI (Cilium or Calico). 4. `kubeadm token create --print-join-command` on control plane; run it on workers.
- **Upgrade** (exam classic): control plane first - `apt/dnf` upgrade kubeadm -> `kubeadm upgrade plan` -> `kubeadm upgrade apply v1.x.y` -> drain -> upgrade kubelet/kubectl -> restart kubelet -> uncordon; workers: `kubeadm upgrade node`.
- **etcd backup/restore:**
  ```bash
  ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 --cacert=/etc/kubernetes/pki/etcd/ca.crt \
    --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key snapshot save /opt/snap.db
  etcdutl snapshot restore /opt/snap.db --data-dir /var/lib/etcd-restore   # then point the etcd static pod hostPath there
  ```
- Certificates: `kubeadm certs check-expiration`, `kubeadm certs renew all`. TLS bootstrapping: kubelet uses a bootstrap token to request a client cert via CSR (`k get csr`, `k certificate approve`).
- RBAC: Role/ClusterRole + RoleBinding/ClusterRoleBinding; `k auth can-i --list --as system:serviceaccount:ns:sa`. Users are certs: create key, CSR object, approve, build kubeconfig.
- Helm & Kustomize basics: `helm install/upgrade --set`, `helm template`; `kubectl apply -k overlays/dev`.
- CRDs/operators: `k get crd`, `k explain <crd-kind>`, install an operator and create its custom resource.

## Week 27 - scheduling
requests (scheduling) vs limits (enforcement: CPU throttled, memory OOMKilled), QoS classes (Guaranteed/Burstable/BestEffort), LimitRange/ResourceQuota, `nodeSelector`, node affinity (`requiredDuringScheduling...`), pod (anti-)affinity with `topologyKey`, taints (`NoSchedule`, `PreferNoSchedule`, `NoExecute`) + tolerations, `topologySpreadConstraints`, PriorityClass/preemption, static pods (`/etc/kubernetes/manifests`, `staticPodPath` in kubelet config), manual scheduling via `nodeName`.

## Week 28 - networking and storage
- Pod-to-pod flat network (CNI), Service -> EndpointSlices -> kube-proxy rules; CoreDNS names `svc.ns.svc.cluster.local`, pods `1-2-3-4.ns.pod.cluster.local`.
- NetworkPolicy: once a pod is selected by any policy for a direction, everything not allowed is denied. Remember DNS egress (UDP+TCP 53). Needs an enforcing CNI (`./lab.sh kind up cilium`).
- Ingress (`ingressClassName`, pathType Prefix/Exact, TLS secret) and **Gateway API** (GatewayClass -> Gateway -> HTTPRoute) - `./lab.sh addon gateway`.
- Storage: PV (cluster) <-> PVC (namespace) binding by class/size/access mode (RWO, ROX, RWX, RWOP); reclaim policy Retain/Delete; `volumeBindingMode: WaitForFirstConsumer`; expanding PVCs (`allowVolumeExpansion`).

## Week 29 - troubleshooting playbook
| Symptom | First commands |
|---|---|
| Pending | `describe pod` events: insufficient CPU/mem, taints, PVC unbound, no scheduler |
| ImagePullBackOff | image name/tag, registry auth (`imagePullSecrets`) |
| CrashLoopBackOff | `logs --previous`, command/args, missing config, probes killing it |
| Service no response | `get endpointslices`, selector vs labels, targetPort, NetworkPolicy |
| Node NotReady | `ssh node; systemctl status kubelet; journalctl -u kubelet`; containerd running? certs expired? |
| Control plane down | `crictl ps -a` on control plane; static pod manifest typo in `/etc/kubernetes/manifests`; `crictl logs` |
| DNS failures | coredns pods/replicas, `k run t --image=busybox:1.36 -it --rm -- nslookup kubernetes` |
Do all 11 drills in `lab/k8s/scenarios/break.sh` until each takes < 5 minutes. Then killer.sh session 1 (score honestly), fix weak spots, session 2 two days before the exam.

## Self-check
1. Order of upgrade steps on the control plane?
2. Pod is Pending with no events at all. Why?
3. Allow pods labelled `role=frontend` in ns `web` to reach `app=api` in ns `shop` on 8000 - write the NetworkPolicy `from` block.
4. How do you find which PVC a pod uses and why it is unbound?
5. Create a user `dev` who can only list pods in ns `shop` - list the objects involved.

<details><summary>Answers</summary>

1. upgrade kubeadm pkg -> `kubeadm upgrade plan/apply` -> drain -> upgrade kubelet+kubectl -> `systemctl daemon-reload && restart kubelet` -> uncordon.
2. No scheduler (static pod missing/broken) - scheduler would record FailedScheduling.
3. `- from: [{namespaceSelector: {matchLabels: {kubernetes.io/metadata.name: web}}, podSelector: {matchLabels: {role: frontend}}}]` in ONE list item (AND), ports 8000.
4. `k get pod -o yaml | grep claimName`, `k describe pvc` (no matching class/PV, WaitForFirstConsumer).
5. Key + CSR + CertificateSigningRequest approved -> kubeconfig; Role (pods: list) + RoleBinding to user `dev`.
</details>

## Resources
kubernetes-scenario-notes.pdf (60+ incidents - read 3 per day in weeks 27-29), https://kubernetes.io/docs (allowed in exam - learn where things are), https://killercoda.com/killer-shell-cka, killer.sh


---
[[Home]] · [[Schedule]]
