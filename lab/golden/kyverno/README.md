# KCA lab - Kyverno (Golden track G5)

Guide: [`study-guides/25-kca-kyverno.md`](../../../study-guides/25-kca-kyverno.md) · Namespace: `kyverno-lab` (label `lab.devops/component: kca`)

All policies are scoped to `kyverno-lab` (or to namespaces labelled `lab.devops/component=kca`), so they never touch kube-system or other labs. They use the per-rule `failureAction` syntax, which needs **Kyverno 1.13 or newer** (the `./lab.sh addon kyverno` chart installs the latest).

| File | Type | Mode | What |
|---|---|---|---|
| `policies/01-require-labels.yaml` | validate | Audit | `app.kubernetes.io/name` + `lab.devops/component` labels on pods (admitted, reported, kubectl warning) |
| `policies/02-disallow-latest-tag.yaml` | validate | Enforce | two rules: a tag is required, and it is not `latest` |
| `policies/03-add-default-securitycontext.yaml` | mutate | - | adds `runAsNonRoot`, `seccompProfile: RuntimeDefault`, `allowPrivilegeEscalation: false`, drop ALL caps if absent |
| `policies/04-generate-default-networkpolicy.yaml` | generate | - | `default-deny-ingress` NetworkPolicy in every `lab.devops/component=kca` namespace (+ RBAC for the background controller) |
| `policies/05-require-requests-limits.yaml` | validate | Enforce | cpu/memory requests and a memory limit |
| `policies/06-restrict-image-registries.yaml` | validate | Enforce | docker.io, ghcr.io, registry.k8s.io, localhost:5001 (lab registry), ttl.sh - fully qualified names only |
| `policies/07-verify-images.yaml` | verifyImages | Audit | cosign signature check for `ttl.sh/*` and `ghcr.io/REPLACE-ME/*`; **placeholder key**, skipped by `up.sh` until you paste yours |
| `policies/08-cleanup-bare-pods.yaml` | ClusterCleanupPolicy | every 10 min | deletes bare pods labelled `lab.devops/cleanup=enabled` (+ RBAC for the cleanup controller) |
| `namespace.yaml` | - | - | `kyverno-lab`, applied after the policies so 04 fires |
| `test/kyverno-test.yaml` | CLI test | - | 17 expected results for 01, 02, 05, 06 against `resources-good.yaml` / `resources-bad.yaml` |

## Run it
```bash
cd lab
./lab.sh kind up                     # any profile; 'cilium' if you are doing CCA too
./lab.sh golden kyverno              # = golden/kyverno/up.sh: installs Kyverno if missing, policies, demo
cd golden/kyverno
./up.sh test                         # kyverno test test/  (same as: kyverno test lab/golden/kyverno/test from the repo root)
./up.sh down                         # delete kyverno-lab and the lab policies
```
Kyverno CLI (not installed by `./lab.sh tools`):
```bash
V=$(curl -fsSL https://api.github.com/repos/kyverno/kyverno/releases/latest | grep -m1 tag_name | cut -d'"' -f4)
curl -fsSL "https://github.com/kyverno/kyverno/releases/download/$V/kyverno-cli_${V}_linux_x86_64.tar.gz" | tar -xz -C ~/.local/bin kyverno
kyverno version
```

## What the demo shows
1. `kyverno-lab` is created and immediately gets `NetworkPolicy/default-deny-ingress` (generate, `synchronize: true` - delete it and watch it come back).
2. Every pod in `test/resources-bad.yaml` goes through the real webhooks with `--dry-run=server`: the Enforce policies print their `message`; `bad-no-labels` is admitted with a warning (Audit).
3. `good-pod` is admitted and its `securityContext` shows the fields policy 03 added.
4. `audit-demo` (no labels) is admitted, appears as `fail` in `kubectl -n kyverno-lab get polr`, and is deleted by policy 08 within 10 minutes.

## Exercises (do them without looking at the answers in the guide)
1. **Audit -> Enforce:** switch 01 to `Enforce`, re-apply, and retry the `audit-demo` pod. Then create a Deployment without labels - which rule name rejects it? (`autogen-check-required-labels`)
2. **PolicyException:** allow pods named `legacy-*` in `kyverno-lab` to use `:latest`. Check whether exceptions are enabled in your install (`kubectl -n kyverno get deploy kyverno-admission-controller -o yaml | grep -i exception`); if not: `helm upgrade kyverno kyverno/kyverno -n kyverno --reuse-values --set features.policyExceptions.enabled=true --set features.policyExceptions.namespace=kyverno`. The YAML is in the guide (Week 2 - PolicyExceptions).
3. **Mutate test:** add policy 03 to `test/kyverno-test.yaml` with a `patchedResources` file holding the expected mutated `good-pod`, and make `kyverno test` pass.
4. **preconditions:** make 05 skip pods labelled `lab.devops/skip=true`, and prove it with a `skip` result in the test file.
5. **verifyImages:** run `lab/security/supply-chain.sh` (CKS lab) to get `cosign.pub` and a signed/unsigned image on ttl.sh, paste the key into 07, apply it, and run both images in `kyverno-lab`. Compare the PolicyReport entries, then switch to `Enforce` and `mutateDigest: true`.
6. **TTL cleanup:** `kubectl -n kyverno-lab run ttl --image=docker.io/nginxinc/nginx-unprivileged:1.27-alpine --labels=app.kubernetes.io/name=ttl,lab.devops/component=kca,cleanup.kyverno.io/ttl=2m` (it fails 05 - fix that first) and watch it disappear.
7. **Pod Security library:** `helm upgrade --install kyverno-policies kyverno/kyverno-policies -n kyverno --set podSecurityStandard=restricted --set validationFailureAction=Audit`, then `kubectl get polr -A` - which workloads in other lab namespaces fail `restricted`? Uninstall when done.
8. **CLI against the cluster:** `kyverno apply policies/02-disallow-latest-tag.yaml --cluster` - which existing pods in the whole cluster would fail if the policy were not scoped to `kyverno-lab`? (Remove the `namespaces` line in a copy to find out.)
