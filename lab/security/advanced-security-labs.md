# Advanced security labs (from the "Advanced Security Labs" sheet)

Ground rules for every lab here:
- Only on your own isolated kind cluster / VM. Snapshot first, destroy after.
- Detection and defence are the deliverable. Attack tooling only reproduces a technique so you can detect it.
- No real malware, no self-replicating code, never point load tools at anything you do not own.

| Lab | Setup | Reproduce with | Detect / defend with | Deliverable |
|---|---|---|---|---|
| Container escape | `kind up security`; a pod with `privileged: true` + `hostPath: /` in a throwaway ns | Peirates (inside that pod) | Falco rules (`falco-rules.yaml`), Tetragon, PSA restricted | Detection rule pack + writeup |
| Worm-style lateral movement | multi-node kind, stolen SA token scenario | Stratus Red Team k8s techniques | audit log (`k8s/kind/audit-policy.yaml`), Falco SA-token rule, Sigma | Attack graph + Sigma rules |
| L7 flood | ingress-nginx on kind | k6 against `api.localtest.me` only | ingress rate limit annotations, Prometheus/Grafana | k6 report + rate-limit config |
| Volumetric (concept) | `networking/netns-lab.sh` | `tc qdisc ... netem` between namespaces | Hubble flow metrics | design doc only |
| Supply chain poisoning | local registry | `supply-chain.sh` benign marker image | cosign + policy-controller, Gatekeeper | signed-only before/after demo |
| eBPF enforcement | `kind up security` | benign `sh` exec | `tetragon-policy.yaml` | TracingPolicy pack |
| OpenShift SCC abuse | CRC, custom permissive SCC bound to a test SA | kube-hunter (passive mode) | RHACS policies, Compliance Operator | SCC review checklist |

Useful commands:
```bash
kubectl -n falco logs -l app.kubernetes.io/name=falco -f | grep LAB
docker exec lab-control-plane tail -f /var/log/kubernetes/audit.log | jq 'select(.objectRef.subresource=="exec")'
kubectl -n kube-system exec ds/tetragon -c tetragon -- tetra getevents -o compact
```
