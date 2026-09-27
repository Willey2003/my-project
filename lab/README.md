# DevOps lab kit

Everything you need to practise the 70-week plan on your own laptop/desktop. One entry point: `./lab.sh`.

## Host requirements
| Phase | RAM | Notes |
|---|---|---|
| Git, Linux, networking, RHCSA, RHCE (weeks 1-16) | 8 GiB free | 3 Vagrant VMs (Alma/RHEL-compatible) |
| Docker, CI/CD, Kubernetes, CKA/CKAD/KCSA/CKS, Argo, Istio (17-58) | 8-12 GiB | Docker + kind, no VMs needed |
| OpenShift Local / RHACS (36-44, 51-52) | 16-20 GiB | CRC; or use the free Developer Sandbox |
| AWS (33-35) | any | real AWS account, costs money while applied |
| AI security (59-66) | 8 GiB | small local model via Ollama |

Linux (Fedora/Ubuntu) or macOS works; on Windows use WSL2 + Docker Desktop, and VirtualBox on the Windows side for the VMs.

## First run
```bash
cd lab
chmod +x lab.sh */*.sh */*/*.sh
./lab.sh doctor            # what you have / what is missing
./lab.sh tools             # kubectl kind helm k9s yq jq terraform trivy ansible aws -> ~/.local/bin
# install yourself (needs admin): Docker, VirtualBox (or libvirt), Vagrant
```

## Map: week -> lab
| Weeks | Topic | Start here |
|---|---|---|
| 1 | Git/GitHub | this repo (`my-project`) is your home base: branch, commit, PR every lab here |
| 2-5 | Linux | `./lab.sh vms up`; `linux/permissions-lab.sh`, `linux/lvm-lab.sh`, `linux/health-check.sh` + `.service/.timer` |
| 6-8 | Networking | `networking/subnetting-drills.py`, `networking/netns-lab.sh`, `networking/haproxy-lab.yml` |
| 9-12 | RHCSA | `linux/rhcsa-practice.md` on node1/node2 (2.5 h timer, reboot at the end) |
| 13-16 | RHCE | `vagrant ssh control` -> `sudo -iu student` -> `cd /lab/ansible` -> `ansible-playbook playbooks/01-baseline.yml` |
| 17-20 | Docker | `./lab.sh compose up`, `docker/docker-exercises.md`, `./lab.sh compose scan` |
| 21-22 | GitHub Actions | `cicd/README.md` |
| 23-25 | KCNA | `./lab.sh kind up`; `kubectl apply -f k8s/manifests/app.yaml` |
| 26-29 | CKA | `./lab.sh break list` / `./lab.sh break random` (11 fault drills), `k8s/manifests/storage.yaml`, `./lab.sh kind up cilium` |
| 30-32 | CKAD | `k8s/manifests/pod-patterns.yaml`, `k8s/manifests/rbac-netpol.yaml` |
| 33-35 | AWS | `aws/terraform/README.md` (`terraform destroy` after every session) |
| 36-44 | OpenShift EX188/EX280/EX380 | `openshift/crc.sh`, `openshift/openshift-drills.md` |
| 45-50 | KCSA/CKS | `./lab.sh kind up security`; `security/` (kube-bench, Falco, Tetragon, supply chain, PSA, Gatekeeper) |
| 51-52 | RHACS EX430 | `openshift/openshift-drills.md` (EX430 section) |
| 53-55 | Argo (CAPA) | `./lab.sh addon argocd rollouts workflows`; `gitops/` |
| 56-58 | Istio (ICA) | `./lab.sh kind up mesh`; `mesh/README.md` |
| 59-66 | AI/LLM security | `ai-security/README.md` |
| 67-70 | Capstone | `capstone/` (copilot, FAIR model, ADR + STRIDE templates) |

## Namespaces (one per component)
Every manifest creates and targets its own namespace, so components never collide and each can be removed with `kubectl delete ns <name>`.
`kubectl apply -f k8s/namespaces.yaml` pre-creates them all.

| Namespace | Component | Files |
|---|---|---|
| `shop` | sample app (KCNA/CKA/CKAD), RBAC + NetworkPolicy | `k8s/manifests/app.yaml`, `rbac-netpol.yaml` |
| `ckad-patterns` | init/sidecar/Job/CronJob patterns | `k8s/manifests/pod-patterns.yaml` |
| `cka-storage` | PVC + StatefulSet | `k8s/manifests/storage.yaml` |
| `trouble` | CKA break-fix drills | `k8s/scenarios/break.sh` |
| `cks-bench` | CIS benchmark job | `security/kube-bench-job.yaml` |
| `cks-runtime` | Tetragon enforcement test | `security/tetragon-policy.yaml` |
| `secure` | signed-images-only supply chain demo | `security/supply-chain.sh` |
| `psa-restricted`, `psa-baseline` | Pod Security Admission levels | `security/pod-security.yaml` |
| `rollouts-demo` | Argo Rollouts canary | `gitops/rollouts/canary.yaml` |
| `mesh-bookinfo` | Istio bookinfo, traffic + security policies | `mesh/` |
| `team-a` | OpenShift quotas/RBAC | `openshift/` |
| add-on namespaces | ingress-nginx, envoy-gateway-system, argocd, argo, argo-rollouts, argo-events, falco, gatekeeper-system, cosign-system, kyverno, monitoring, istio-system | `k8s/addons/install.sh` |

## Safety
- Security labs run only against your own disposable clusters. See `security/advanced-security-labs.md`.
- Never commit `aws/terraform/terraform.tfstate`, `*.tfvars`, `security/cosign.key` or `ansible/secrets.yml` (see `.gitignore`).
