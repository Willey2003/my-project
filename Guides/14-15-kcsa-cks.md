---
tags: [devops-prep, guide]
---
# Phases 14-15 - KCSA and CKS (Kubernetes security)

**KCSA:** weeks 45-46, 20 h, 90 min multiple choice, USD 250. **CKS:** weeks 47-50, 50 h, 2 h hands-on, USD 445, requires an active CKA.
**Lab:** `./lab.sh kind up security` (Cilium + Tetragon + Falco + API audit log), `lab/security/`

| Week | Focus | Deliverable |
|---|---|---|
| 45 | 4C's model, cluster component security | API server / etcd hardening notes |
| 46 | Threat model, RBAC, Pod Security Admission, supply chain, compliance; sit KCSA | KCSA |
| 47 | CIS benchmark (kube-bench), anonymous auth off, RBAC least privilege | kube-bench report |
| 48 | Supply chain: Trivy, cosign signing, admission enforcement | Signed-image-only policy demo |
| 49 | Runtime: Falco rules, seccomp/AppArmor, Tetragon | Tetragon policy pack |
| 50 | NetworkPolicies, mTLS, mocks, sit CKS | CKS |

## KCSA domain map (sheet weights)
| Domain | Weight | Key ideas |
|---|---|---|
| Kubernetes Cluster Component Security | 22% | API server authn/authz/admission, kubelet auth (`anonymous: false`, `authorization: Webhook`), etcd TLS + encryption at rest, scheduler/controller bind addresses |
| Kubernetes Security Fundamentals | 22% | RBAC, service accounts, NetworkPolicy, Pod Security Standards (privileged/baseline/restricted), admission control, Secrets handling |
| Overview of Cloud Native Security | 14% | 4C's: Cloud, Cluster, Container, Code - each layer trusts the one below |
| Kubernetes Threat Model | 16% | trust boundaries, privilege escalation paths, persistence, denial of service, data access |
| Platform Security | 16% | image scanning, SBOMs, signing, registries, observability, service mesh, PKI |
| Compliance and Security Frameworks | 10% | CIS benchmarks, NIST, threat-modelling frameworks, automation of compliance |

## CKS: defensive hardening by domain
**Cluster setup (10%)**
- Run `kubectl apply -f lab/security/kube-bench-job.yaml`, read the FAIL items, fix a few (file permissions on manifests, kubelet flags), re-run and compare. Save before/after as the deliverable.
- Restrict API server exposure; disable anonymous auth; verify platform binaries against published checksums (`sha512sum`).
- Ingress with TLS; restrict access to the cloud metadata endpoint with a NetworkPolicy egress deny for 169.254.169.254/32.

**Cluster hardening (15%)**
- Least-privilege RBAC: no wildcards, no `cluster-admin` bindings for apps; audit with `kubectl auth can-i --list --as ...`.
- Service accounts: `automountServiceAccountToken: false` by default, dedicated SA per app, short-lived projected tokens.
- Keep Kubernetes patched (upgrade drill from CKA).

**System hardening (15%)**
- Reduce host attack surface: minimal OS, close unneeded ports, limit node SSH.
- seccomp `RuntimeDefault` everywhere; custom profiles in `/var/lib/kubelet/seccomp/`.
- AppArmor profiles (`appArmorProfile` field) on Ubuntu nodes; SELinux on RHEL.
- See `lab/security/pod-security.yaml` for a pod that passes the `restricted` level.

**Minimize microservice vulnerabilities (20%)**
- Pod Security Admission labels per namespace (`enforce`, `warn`, `audit`).
- Policy engines: OPA Gatekeeper (`lab/security/gatekeeper-policies.yaml`) or Kyverno.
- Secrets: encryption at rest (`EncryptionConfiguration` with aescbc/kms provider), external secret stores.
- Isolation: RuntimeClass (gVisor/Kata) for untrusted workloads; mTLS between services (Istio or Cilium) - covered deeper in phase 18.

**Supply chain security (20%)**
- Minimal base images, pinned digests, SBOM (`trivy image --format cyclonedx`), scan in CI (phase 7 gate).
- Signing and verification: `lab/security/supply-chain.sh` walks through build, scan, sign with cosign and enforce in namespace `secure` with the Sigstore policy-controller; only signed images are admitted.
- Static analysis of manifests: `trivy config`, `kubesec`.

**Monitoring, logging and runtime security (20%)**
- API audit logging: the security profile enables it with `k8s/kind/audit-policy.yaml`; query `exec` events with `jq`.
- Falco: behavioural detection rules in `lab/security/falco-rules.yaml` (shell in container, service-account token reads, package managers at runtime). Trigger them yourself with a benign `kubectl exec` and read the alerts.
- Tetragon: `lab/security/tetragon-policy.yaml` enforces a namespace-scoped policy; test on a throwaway pod first.
- Immutable containers: `readOnlyRootFilesystem: true`, no package managers in runtime images.

## Study method
- KCSA: read the Kubernetes security docs section end-to-end, then one domain per day with flashcards; 2 practice exams.
- CKS: each lab day ends with a 20-minute "harden this" task on a fresh kind cluster. killer.sh CKS twice (week 50).
- Keep a "control -> threat it mitigates -> how to verify" table; it becomes interview material.

## Self-check
1. Name three kubelet settings that reduce risk.
2. What does the `restricted` Pod Security Standard require beyond `baseline`?
3. How do you encrypt Secrets at rest and prove it?
4. Where do you look to see who ran `kubectl exec` into a pod yesterday?
5. Why sign by digest rather than tag?

<details><summary>Answers</summary>

1. `anonymous.enabled: false`, `authorization.mode: Webhook`, `readOnlyPort: 0` (plus rotating certs, `protectKernelDefaults`).
2. Non-root, no privilege escalation, drop ALL capabilities, seccomp RuntimeDefault/Localhost, restricted volume types.
3. EncryptionConfiguration referenced by `--encryption-provider-config`, rewrite existing secrets (`kubectl get secrets -A -o json | kubectl replace -f -`), then read the raw value from etcd with `etcdctl` and confirm it is ciphertext.
4. The API server audit log (`pods/exec` subresource events).
5. Tags are mutable; a digest identifies exactly one image.
</details>

## Resources
https://kubernetes.io/docs/concepts/security/ · CIS Kubernetes Benchmark · https://falco.org/docs · https://tetragon.io/docs · https://docs.sigstore.dev · killer.sh CKS · Killercoda CKS scenarios


---
[[Home]] · [[Schedule]]
