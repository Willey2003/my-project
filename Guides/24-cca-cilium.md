---
tags: [devops-prep, guide]
---
# Phase 24 - CCA: Cilium Certified Associate

**Plan weeks:** Golden track G4, 2 weeks at 28 h, exam target Sun 30 May 2027 · **Hours:** 56 · **Exam:** CCA, 90 min online-proctored multiple choice, USD 250, one free retake · **Lab:** `./lab.sh kind up cilium`, `lab/golden/cilium/`

CCA is a multiple-choice exam, not a terminal exam, but the questions are written by people who run Cilium. You pass it by understanding *why* Cilium does something (identity, not IP; eBPF maps, not iptables chains), and the fastest way to get there is to break and fix it in the lab. You already met Cilium as the CNI in CKA week 28 and in the CKS lab - this phase goes deep. It comes before KCA (G5): network policy at the kernel level first, then admission policy.

| Week | Focus | Deliverable |
|---|---|---|
| 1 | eBPF basics, architecture (agent, operator, Hubble, identity), install + `cilium` CLI, IPAM modes, kube-proxy replacement, CiliumNetworkPolicy L3/L4/L7, DNS/FQDN policy, CCNP | `lab/golden/cilium/up.sh` running; all 3 policies in `lab/golden/cilium/policies/` applied and verified; `cilium config view` notes |
| 2 | Hubble observability, cluster mesh, service mesh + Gateway API, BGP + LB-IPAM, WireGuard/IPsec, review, self-check, sit exam | `hubble-exercises.md` done, one-page cluster mesh + BGP diagram in your notes, CCA |

## Domains (verify the current curriculum on training.linuxfoundation.org and github.com/cncf/curriculum)
| Domain | Weight | Your lab |
|---|---|---|
| Architecture | 20% | `cilium status --verbose`, `kubectl -n kube-system get ds,deploy`, identity drills below |
| Network Policy | 18% | `lab/golden/cilium/policies/` (L3/L4, L7, FQDN), CCNP example below |
| Service Mesh | 16% | Gateway API + Ingress on Cilium, mutual auth concepts, Envoy per node |
| Installation and Configuration | 10% | `cilium install`, Helm values, `cilium config view`, IPAM modes |
| Network Observability | 10% | `lab/golden/cilium/hubble-exercises.md` |
| Cluster Mesh | 10% | Read-only: concepts + `cilium clustermesh` commands (optional: two kind clusters) |
| eBPF | 10% | `bpftool` / `cilium bpf` inside the agent pod |
| BGP and External Networking | 6% | `CiliumBGPClusterConfig`, `CiliumLoadBalancerIPPool` concepts, L2 announcements |

## Exam technique
- 90 minutes for roughly 60 questions: about 90 seconds each. Answer everything on the first pass (no penalty for guessing), flag the doubtful ones, return at the end.
- Many wrong answers are "Kubernetes-true but Cilium-false": e.g. "policies are enforced on pod IPs" (Cilium enforces on **identities**), "kube-proxy is required" (not with kube-proxy replacement), "Hubble needs a sidecar" (it reads events from the agent's eBPF datapath).
- Know which component owns what: agent (per node, datapath + policy), operator (cluster-wide chores: IPAM for some modes, CRD GC, identity GC), Hubble relay (aggregates per-node Hubble servers), Envoy (L7, per node).
- Know the CRD names cold: `CiliumNetworkPolicy`, `CiliumClusterwideNetworkPolicy`, `CiliumEndpoint`, `CiliumIdentity`, `CiliumNode`, `CiliumLoadBalancerIPPool`, `CiliumBGPClusterConfig`, `CiliumBGPPeerConfig`, `CiliumBGPAdvertisement`, `CiliumL2AnnouncementPolicy`, `CiliumEnvoyConfig`.
- Useful lab aliases while you study:
```bash
alias k=kubectl
alias cexec='kubectl -n kube-system exec ds/cilium -c cilium-agent --'
cilium status --wait ; cilium config view | grep -Ei 'ipam|kube-proxy|routing|encrypt|hubble'
```

## Week 1 - eBPF basics
- **eBPF** = sandboxed programs loaded into the Linux kernel at runtime, run on hooks, no kernel module and no reboot. Written in restricted C, compiled to eBPF bytecode, checked by the **verifier** (no unbounded loops, no invalid memory access, bounded complexity), then **JIT**-compiled to native code.
- **Hooks Cilium uses:** XDP (earliest point in the NIC driver - used for fast drop/LB), **tc** ingress/egress on veth and physical devices (main datapath), socket hooks (`cgroup/connect4`, `sendmsg`, `recvmsg` - socket-level load balancing so ClusterIP translation happens at `connect()`), kprobes/tracepoints (Tetragon, not core Cilium).
- **Maps** = kernel key/value stores shared between eBPF programs and user space: hash, LRU hash, array, LPM trie, per-CPU variants, ring buffer. Cilium keeps policy, connection tracking (CT), NAT, service/backends, IP cache (IP -> identity) and endpoint info in maps.
- **Why it matters:** hash-map lookups are O(1) regardless of how many services/policies exist; iptables is a linear list of rules evaluated per packet and rewritten wholesale on change.
- Look at it yourself:
```bash
cexec cilium-dbg bpf lb list | head          # service VIP -> backends (kube-proxy replacement map)
cexec cilium-dbg bpf ct list global | head   # connection tracking table
cexec cilium-dbg bpf ipcache list | head     # IP/CIDR -> security identity
cexec cilium-dbg bpf policy get --all | head # per-endpoint policy maps
cexec cilium-dbg map list                    # every map, entry counts, errors
```
(Older releases call the in-pod binary `cilium`; since 1.15 it is `cilium-dbg` to avoid confusion with the CLI on your laptop.)

## Week 1 - architecture
| Component | Runs as | Job |
|---|---|---|
| **cilium-agent** | DaemonSet, one per node | Watches the K8s API, compiles and loads eBPF programs, writes maps, allocates endpoint identities, enforces policy, embeds the Hubble server |
| **cilium-operator** | Deployment (usually 2 replicas) | Cluster-wide tasks: IPAM in `cluster-pool` / cloud modes, garbage-collecting identities and CiliumEndpoints, CRD registration, LB-IPAM, BGP bits, Gateway API reconciliation |
| **cilium-envoy** | DaemonSet (default since 1.16) or embedded in the agent | L7 proxy: HTTP/gRPC/Kafka policy, Ingress, Gateway API, L7 visibility. One Envoy per node, **not** a sidecar per pod |
| **Hubble server** | inside each agent | Reads flow events from the datapath (perf/ring buffer), exposes a gRPC API on the node |
| **Hubble relay** | Deployment | Connects to every node's Hubble server and gives one cluster-wide API (port 4245) |
| **Hubble UI** | Deployment | Service map + flow table in the browser |
| **cilium CLI** | on your laptop | Install, status, connectivity test, hubble/clustermesh enablement |
| **CNI plugin** | binary on each node | kubelet calls it at pod creation; it hands the work to the agent |

**Identity** is the core idea. Cilium derives a numeric **security identity** from a pod's *security-relevant labels* (pod labels + namespace + service account, filtered by the identity label config). All pods with the same label set share one identity, cluster-wide. Policy is compiled against identities, so a pod restarting with a new IP needs no policy change.
- Identities are stored as `CiliumIdentity` CRDs (default, `identity-allocation-mode: crd`) or in a kvstore (etcd).
- Reserved identities: `1 host`, `2 world`, `3 unmanaged`, `4 health`, `5 init`, `6 remote-node`, `7 kube-apiserver`, `8 ingress`; `world` is further split into `world-ipv4`/`world-ipv6` on dual-stack.
- The **ipcache** map lets the datapath turn a source IP into an identity; across nodes the identity can also be carried in the tunnel header (VXLAN/Geneve VNI) so the receiver does not need to look it up.
- Each pod is a `CiliumEndpoint`: `kubectl get cep -A` shows endpoint ID, identity, policy enforcement state.
```bash
kubectl get ciliumidentities | head ; kubectl -n cilium-lab get cep -o wide
cexec cilium-dbg endpoint list      # policy enforcement ingress/egress per endpoint
cexec cilium-dbg identity get <id>  # which labels produced this identity
```

## Week 1 - installation and the cilium CLI
Two install paths, same result (the CLI drives the Helm chart under the hood):
```bash
cilium install --version 1.18.x --set kubeProxyReplacement=true --set k8sServiceHost=lab-control-plane --set k8sServicePort=6443
helm upgrade --install cilium cilium/cilium -n kube-system -f values.yaml     # GitOps-friendly
cilium status --wait                  # agents, operator, envoy, hubble, cluster health
cilium config view                    # the live cilium-config ConfigMap
cilium config set debug true          # change a setting (restarts agents)
cilium connectivity test              # ~100 end-to-end checks in namespace cilium-test (slow, thorough)
cilium sysdump                        # support bundle - know it exists
cilium upgrade --version 1.18.y       # run the pre-flight check first on real clusters
```
- Prerequisites to know: Linux kernel >= 5.4 (5.10+ recommended for full features), mounted BPF filesystem (`/sys/fs/bpf`), cgroup v2 for socket LB.
- On kind the default CNI must be disabled (`networking.disableDefaultCNI: true` in `lab/k8s/kind/cilium.yaml`) or two CNIs fight.
- **Routing modes:** *encapsulation* (default, VXLAN or Geneve overlay between nodes - works anywhere) vs *native routing* (`routingMode: native`, `ipv4NativeRoutingCIDR` - the underlying network or BGP must route pod CIDRs; less overhead, pod IPs visible on the wire).
- **Masquerading:** `bpf.masquerade=true` does SNAT to the node IP in eBPF instead of iptables.

## Week 1 - IPAM modes
| Mode | Who allocates pod CIDRs | When |
|---|---|---|
| `cluster-pool` (default) | cilium-operator carves per-node CIDRs from `clusterPoolIPv4PodCIDRList`, stored in `CiliumNode` | Most self-managed clusters |
| `kubernetes` | kube-controller-manager (`--allocate-node-cidrs`), Cilium reads `node.spec.podCIDR` | kubeadm/kind clusters that already assign podCIDRs (this lab's Helm fallback uses it) |
| `multi-pool` | operator, from several `CiliumPodIPPool`s selected by annotation | Different pools per namespace/workload |
| `eni` / `azure` / `alibabacloud` | operator talks to the cloud API, pods get VPC-routable IPs | EKS/AKS without an overlay |
| `delegated-plugin` | another CNI IPAM plugin | Special cases |
Changing IPAM mode on a live cluster is **not supported** - it is a reinstall decision. Check with `kubectl get ciliumnodes -o yaml | grep -A3 ipam`.

## Week 1 - kube-proxy replacement (KPR)
- `kubeProxyReplacement=true` (older releases: `strict`) makes Cilium implement ClusterIP, NodePort, LoadBalancer, externalIPs and hostPort in eBPF; kube-proxy can then be deleted (or never installed: `kubeadm init --skip-phases=addon/kube-proxy`). Cilium must then be told the API server address (`k8sServiceHost`/`k8sServicePort`) because it can no longer rely on the `kubernetes` ClusterIP.
- **Socket-level LB:** for traffic from pods, the ClusterIP is translated to a backend at `connect()` time, so there is no per-packet DNAT and no conntrack entry for the VIP.
- **Maglev** consistent hashing (`loadBalancer.algorithm=maglev`) keeps backend selection stable across nodes; **DSR** (`loadBalancer.mode=dsr`) lets the backend answer the client directly for NodePort/LB traffic; **XDP acceleration** (`loadBalancer.acceleration=native`) does NodePort LB in the NIC driver.
- Verify: `cilium status | grep KubeProxyReplacement`, `cexec cilium-dbg service list`, `kubectl -n kube-system get ds kube-proxy` (should be absent).
- The lab keeps kube-proxy (see the comment in `lab/k8s/kind/cilium.yaml`) - for a KPR run, add `kubeProxyMode: none` under `networking` in a copy of that file and reinstall with `kubeProxyReplacement=true`.

## Week 1 - CiliumNetworkPolicy (CNP)
Cilium enforces standard `NetworkPolicy` **and** its own CRDs. Same default-deny rule as K8s: as soon as any policy selects an endpoint in a direction, everything not explicitly allowed in that direction is dropped. Rules are allow-lists; `ingressDeny`/`egressDeny` exist and **deny wins** over allow.
| Layer | Selectors | Example |
|---|---|---|
| L3 identity | `fromEndpoints` / `toEndpoints` (label selectors, add `k8s:io.kubernetes.pod.namespace` for other namespaces) | only `org=empire` may reach the deathstar |
| L3 entities | `fromEntities` / `toEntities`: `world`, `cluster`, `host`, `remote-node`, `kube-apiserver`, `all` | allow egress to `kube-apiserver` only |
| L3 CIDR | `fromCIDR`, `toCIDR`, `toCIDRSet` with `except` | allow 10.0.0.0/8 except 10.96.0.0/12 |
| L3 services | `toServices` (K8s service name/selector) | egress to a headless DB service |
| L4 | `toPorts: [{ports: [{port: "80", protocol: TCP}]}]` | TCP 80 only |
| L7 | `toPorts[].rules.http` (method, path regex, headers), `rules.dns`, `rules.kafka` | only `POST /v1/request-landing` |
| FQDN | `toFQDNs: [{matchName: api.github.com}]`, `matchPattern: "*.github.com"` | egress to named SaaS only |
- L7 rules send traffic through the node's Envoy; a denied HTTP request gets **403 Access denied** (not a timeout), while an L3/L4 deny is a silent drop (timeout).
- FQDN policy needs a DNS rule too: the agent's **DNS proxy** watches the answers and programs the returned IPs into the policy. Without `rules.dns` on port 53 the pod cannot resolve and no IPs are learned.
- Ordering does not exist: policies are additive (union of allows) minus denies. Two CNPs on the same endpoint, one allowing all of port 80 and one allowing only `POST /x`, = all of port 80 allowed. That is why the lab's L7 policy **replaces** the L3/L4 one (same name).
- `policyEnforcementMode` (agent setting): `default` (enforce once selected), `always` (default-deny everything, even unselected endpoints), `never`.
- Lab (`lab/golden/cilium/`):
```bash
./up.sh                                   # deathstar, tiefighter, xwing, mediabot in ns cilium-lab
kubectl -n cilium-lab exec xwing -- curl -s -m3 -XPOST deathstar/v1/request-landing   # works (no policy yet)
./up.sh policy l3l4 ; kubectl -n cilium-lab exec xwing -- curl -s -m3 -XPOST deathstar/v1/request-landing   # times out
./up.sh policy l7   ; kubectl -n cilium-lab exec tiefighter -- curl -s -m3 -XPUT deathstar/v1/exhaust-port  # Access denied
./up.sh policy fqdn ; kubectl -n cilium-lab exec mediabot -- curl -sI -m5 https://api.github.com | head -1     # 200
kubectl -n cilium-lab get cnp ; kubectl -n cilium-lab describe cnp rule1
```

## Week 1 - CiliumClusterwideNetworkPolicy (CCNP)
Same spec as CNP but cluster-scoped (no namespace), so the selectors must say which namespace they mean. Typical uses: cluster-wide baseline (allow DNS for everyone), protecting nodes with **host policies** (`nodeSelector` instead of `endpointSelector`, needs `hostFirewall.enabled=true`), blocking the cloud metadata endpoint.
```yaml
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata: { name: deny-metadata-endpoint }
spec:
  endpointSelector: {}                         # every pod in every namespace
  egressDeny:
    - toCIDR: ["169.254.169.254/32"]
```
Careful: a CCNP with an *allow* rule and `endpointSelector: {}` puts **every** pod (including kube-system) into default-deny for that direction. Deny-only policies do not trigger default-deny.

## Week 2 - Hubble observability
- Hubble shows every flow the datapath sees, with identities, verdicts (FORWARDED, DROPPED, AUDIT, REDIRECTED, TRANSLATED), drop reasons and, for L7-visible traffic, HTTP method/path/status and DNS queries.
- Pieces: Hubble server (in agent) -> Hubble relay (cluster-wide gRPC, port 4245) -> `hubble` CLI or Hubble UI. Metrics: `hubble.metrics.enabled` exposes Prometheus metrics (dns, drop, tcp, flow, http...) on each agent.
```bash
cilium hubble enable --ui ; cilium hubble port-forward &     # relay on localhost:4245
hubble status ; hubble observe -n cilium-lab --last 20
hubble observe -n cilium-lab --verdict DROPPED -f            # watch denials live
hubble observe --pod cilium-lab/xwing --to-pod cilium-lab/deathstar -o jsonpb
hubble observe -n cilium-lab --protocol http ; hubble observe -n cilium-lab --protocol dns
cilium hubble ui                                             # opens the service map
```
- L7 visibility requires the traffic to pass through Envoy: either an L7 policy selects it, or you enable visibility (policy with an L7 rule that allows everything, e.g. `http: [{}]`).
- Full drill list: `lab/golden/cilium/hubble-exercises.md`.

## Week 2 - cluster mesh
- Connects multiple Cilium clusters into one network: pod-to-pod across clusters, **global services** (`service.cilium.io/global: "true"` annotation on a Service with the same name/namespace in each cluster; backends from all clusters), and **cross-cluster policy** (`io.cilium.k8s.policy.cluster: <name>` label in selectors).
- Requirements: unique `cluster.name` and `cluster.id` (1-255) per cluster, **non-overlapping PodCIDRs**, node-to-node reachability, same routing mode, compatible Cilium versions.
- Each cluster runs a **clustermesh-apiserver** (with its own etcd) exposing its identities/services/endpoints; agents in the other clusters connect to it (read-only).
- Service affinity annotation `service.cilium.io/affinity: local|remote|none` prefers local or remote backends.
```bash
cilium clustermesh enable --context kind-c1 --service-type NodePort
cilium clustermesh connect --context kind-c1 --destination-context kind-c2
cilium clustermesh status --wait
```

## Week 2 - service mesh and Gateway API
- **Sidecar-less**: one Envoy per node handles L7 for all pods on that node; L3/L4 stays in eBPF. Fewer proxies, less memory, but a shared proxy per node.
- **Ingress**: `ingressController.enabled=true`, `ingressClassName: cilium`; `loadbalancerMode: shared|dedicated`.
- **Gateway API**: `gatewayAPI.enabled=true` (install the Gateway API CRDs first), `GatewayClass` named `cilium`, then `Gateway` + `HTTPRoute` / `GRPCRoute` / `TLSRoute`. Traffic splitting, header matching and redirects live in the route.
- **Mutual authentication** (beta): SPIFFE identities via SPIRE, enabled per policy with `authentication: {mode: required}`; the handshake is out-of-band and the data path is then encrypted with WireGuard/IPsec.
- `CiliumEnvoyConfig` / `CiliumClusterwideEnvoyConfig`: raw Envoy config for advanced L7 (e.g. retries, custom LB). Know it exists.
- Compared with Istio (Phase 18): Istio = sidecar or ambient ztunnel + waypoint, rich L7 features; Cilium = eBPF-first, fewer moving parts. Expect "which component handles X" questions.

## Week 2 - BGP, LB-IPAM and L2 announcements
- **LB-IPAM**: Cilium assigns IPs to `type: LoadBalancer` Services from a `CiliumLoadBalancerIPPool` (`spec.blocks: [{cidr: 172.18.250.0/28}]`, optional `serviceSelector`). Assigning an IP does not make it reachable - something must announce it.
- **L2 announcements**: `l2announcements.enabled=true` + `CiliumL2AnnouncementPolicy` - a node answers ARP for the service IP (MetalLB L2-style, good for kind/bare metal on one L2 segment).
- **BGP control plane** (`bgpControlPlane.enabled=true`): Cilium peers with routers (GoBGP inside the agent). Current API: `CiliumBGPClusterConfig` (which nodes, local ASN, peers) -> `CiliumBGPPeerConfig` (timers, families, graceful restart) -> `CiliumBGPAdvertisement` (advertise PodCIDR, Service LoadBalancer/ClusterIP/external IPs). `CiliumBGPNodeConfigOverride` for per-node tweaks. The older `CiliumBGPPeeringPolicy` (v2alpha1) is deprecated.
- Check: `cilium bgp peers`, `cilium bgp routes advertised ipv4 unicast`.
- **Egress gateway**: `CiliumEgressGatewayPolicy` sends selected pods' egress out of specific nodes with a fixed source IP (firewall allow-lists).

## Week 2 - transparent encryption
| | WireGuard | IPsec |
|---|---|---|
| Enable | `encryption.enabled=true`, `encryption.type=wireguard` | `encryption.type=ipsec` + a `cilium-ipsec-keys` Secret |
| Keys | Generated per node automatically, public keys shared via `CiliumNode` | You create and rotate the pre-shared key (bump the SPI) |
| Interface | `cilium_wg0` | kernel XFRM states/policies |
| Notes | Simple, fast; optional node-to-node encryption (`encryption.nodeEncryption`) | FIPS-friendly; rotation is a manual, exam-relevant procedure |
```bash
cilium status | grep -i encryption ; cexec cilium-dbg encrypt status
```
Both encrypt pod-to-pod traffic *between nodes*; traffic between pods on the same node never leaves the host.

## Week 2 - final review checklist
- Draw the architecture from memory: agent, operator, envoy, Hubble server/relay/UI, clustermesh-apiserver, CRDs.
- Explain in one sentence each: identity, ipcache, DNS proxy, socket LB, Maglev, DSR, LB-IPAM, L2 announcements.
- Re-run all three policies and all Hubble exercises from a clean cluster (`./lab.sh kind down && ./lab.sh kind up cilium`).

## Self-check
1. What checks an eBPF program before it may run, and what does it reject?
2. Which eBPF hook runs earliest on the receive path, and what does Cilium use it for?
3. Two pods with identical labels in the same namespace run on different nodes. How many security identities do they have?
4. What are reserved identities 1, 2 and 6?
5. Which component allocates per-node pod CIDRs in `cluster-pool` IPAM mode, and where are they stored?
6. You want to switch a running cluster from `kubernetes` IPAM to `cluster-pool`. What is the supported approach?
7. With `kubeProxyReplacement=true`, why must you set `k8sServiceHost`?
8. What is socket-level load balancing and what does it avoid?
9. A pod is selected by one CNP allowing all TCP/80 and another allowing only `GET /health` on 80. What is allowed?
10. L3/L4 deny vs L7 deny: what does the client see in each case?
11. An FQDN egress policy for `api.github.com` exists but curl fails to resolve the name. What is missing?
12. Which selector lets a CNP allow egress to the Kubernetes API server regardless of its IP?
13. How does a CCNP differ from a CNP, and what is a host policy?
14. What does `ingressDeny` do when an `ingress` rule allows the same traffic?
15. Name the Hubble pieces from datapath to your terminal, with the relay port.
16. Why does `hubble observe --protocol http` show nothing for traffic that no policy touches?
17. List three requirements for connecting two clusters with cluster mesh.
18. How do you make a Service load-balance across backends in both clusters?
19. A `type: LoadBalancer` Service got an IP from a `CiliumLoadBalancerIPPool`, but nothing outside the cluster can reach it. What else is needed?
20. WireGuard vs IPsec in Cilium: who manages keys, and which interface do you look for?

<details><summary>Answers</summary>

1. The in-kernel **verifier**: rejects unbounded loops, out-of-bounds/uninitialised memory access, invalid helper calls and programs that are too complex; accepted programs are then JIT-compiled.
2. **XDP**, in the NIC driver before an skb is allocated - used for fast drops (e.g. prefilter) and NodePort load-balancing acceleration.
3. **One**: identity is derived from the security-relevant label set (incl. namespace), not from the pod or node.
4. 1 = `host`, 2 = `world` (anything outside the cluster), 6 = `remote-node` (other cluster nodes).
5. The **cilium-operator**, from `clusterPoolIPv4PodCIDRList`; stored in each node's `CiliumNode` resource (`spec.ipam.podCIDRs`).
6. There is none in place - changing IPAM mode means rebuilding/reinstalling (or migrating workloads to a new cluster).
7. Without kube-proxy nothing programs the `kubernetes` ClusterIP until Cilium is running, so the agent needs the real API server address to bootstrap.
8. ClusterIP -> backend translation at `connect()`/`sendmsg()` in the socket layer: no per-packet DNAT, no conntrack entry for the VIP, less overhead.
9. **All TCP/80**: policies are additive (union of allows). To restrict to L7, the L4-only allow must go.
10. L3/L4 deny = packet dropped silently (client times out). L7 deny = Envoy answers **403 Access denied**.
11. A DNS rule: egress to kube-dns on port 53 with `rules.dns` (e.g. `matchPattern: "*"`), so the DNS proxy sees answers and learns the IPs.
12. `toEntities: [kube-apiserver]`.
13. CCNP is cluster-scoped (no namespace; selectors need namespace labels). A host policy uses `nodeSelector` to protect the node itself and needs `hostFirewall.enabled=true`.
14. The deny wins - deny rules take precedence over allows.
15. eBPF datapath events -> Hubble server in each cilium-agent -> Hubble relay (gRPC, **4245**) -> `hubble` CLI / Hubble UI.
16. L7 fields are only produced when traffic is redirected through Envoy (an L7 policy/visibility rule); otherwise Hubble only sees L3/L4 flows.
17. Any three of: unique cluster name and ID, non-overlapping PodCIDRs, node-to-node IP reachability, same routing mode/compatible versions, clustermesh-apiserver reachable.
18. Deploy the Service with the same name/namespace in each cluster and annotate it `service.cilium.io/global: "true"` (optionally `service.cilium.io/affinity`).
19. Announcement: BGP control plane with a `CiliumBGPAdvertisement` for LoadBalancer IPs, or L2 announcements with a `CiliumL2AnnouncementPolicy`.
20. WireGuard: Cilium generates per-node keys automatically, interface `cilium_wg0`. IPsec: you create/rotate the PSK in the `cilium-ipsec-keys` Secret; state lives in kernel XFRM.
</details>

## Resources
https://docs.cilium.io (the main source - read Concepts + Network Policy + Hubble end to end), https://github.com/cncf/curriculum (CCA PDF), https://isovalent.com/labs (free hands-on labs: Getting Started, Cluster Mesh, BGP, Gateway API, Mutual Auth), https://ebpf.io/what-is-ebpf, "Learning eBPF" (Liz Rice, O'Reilly), `lab/golden/cilium/README.md`


---
[[Home]] · [[Schedule]]
