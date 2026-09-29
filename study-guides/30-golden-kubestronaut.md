# Golden Kubestronaut roadmap

**Track:** G1-G9, after the core path · **Dates:** Tue 13 Apr 2027 to Wed 14 Jul 2027 · **Hours:** 368 · **Lab:** `lab/golden/`

Golden Kubestronaut is the CNCF title for holding every CNCF certification plus LFCS. CNCF adds certifications over time, so **check the current list on cncf.io (Kubestronaut program page) before booking**. The table below is the list this kit plans for.

| Cert | Where it is in this kit | Guide | Lab / namespace | Target |
|---|---|---|---|---|
| KCNA | core path, phase 8 | [08-kubernetes-kcna](08-kubernetes-kcna.md) | `lab/k8s` / shop | 2 Dec 2026 |
| CKA | core path, phase 9 | [09-cka](09-cka.md) | `lab/k8s` / cka-storage, trouble | 13 Dec 2026 |
| CKAD | core path, phase 10 | [10-ckad](10-ckad.md) | `lab/golden/ckad` / ckad-lab | 21 Dec 2026 |
| KCSA | core path, phase 14 | [14-15-kcsa-cks](14-15-kcsa-cks.md) | `lab/security` / secure | 31 Jan 2027 |
| CKS | core path, phase 15 | [14-15-kcsa-cks](14-15-kcsa-cks.md) | `lab/security` / cks-bench, cks-runtime | 12 Feb 2027 |
| CAPA | core path, phase 17 | [17-argo-capa](17-argo-capa.md) | `lab/gitops` / rollouts-demo | 26 Feb 2027 |
| ICA | core path, phase 18 | [18-istio-ica](18-istio-ica.md) | `lab/mesh` / mesh-bookinfo | 6 Mar 2027 |
| LFCS | G1 | [29-lfcs](29-lfcs.md) | `lab/golden/lfcs` (Ubuntu VMs) | 22 Apr 2027 |
| PCA | G2 | [22-pca-prometheus](22-pca-prometheus.md) | `lab/golden/observability/pca` / prom-lab | 6 May 2027 |
| OTCA | G3 | [23-otca-opentelemetry](23-otca-opentelemetry.md) | `lab/golden/observability/otel` / otel-lab | 16 May 2027 |
| CCA | G4 | [24-cca-cilium](24-cca-cilium.md) | `lab/golden/cilium` / cilium-lab | 30 May 2027 |
| KCA | G5 | [25-kca-kyverno](25-kca-kyverno.md) | `lab/golden/kyverno` / kyverno-lab | 9 Jun 2027 |
| CGOA | G6 | [26-cgoa-gitops](26-cgoa-gitops.md) | `lab/golden/platform/flux` / flux-lab | 16 Jun 2027 |
| CBA | G7 | [27-cba-backstage](27-cba-backstage.md) | `lab/golden/platform/backstage` / backstage-lab | 26 Jun 2027 |
| CNPA | G8 | [28-cnpa-cnpe-platform](28-cnpa-cnpe-platform.md) | `lab/golden/platform/idp` / platform-lab | 3 Jul 2027 |
| CNPE | G9 | [28-cnpa-cnpe-platform](28-cnpa-cnpe-platform.md) | `lab/golden/platform/idp` / platform-lab | 14 Jul 2027 |

## Why this order
1. **LFCS first.** It reuses RHCSA muscle memory while it is fresh; only the Ubuntu tooling is new.
2. **PCA then OTCA.** Metrics first, then traces and the Collector, which exports to the Prometheus you just learned.
3. **CCA then KCA.** Network policy at the kernel level, then admission policy. Both build directly on CKS.
4. **CGOA, CBA, CNPA, CNPE last.** They are about the platform as a whole, so they come once every piece exists. CNPE's final lab ties all the Golden labs into one demo.

## Money and booking
- Watch for Linux Foundation bundle and sale pricing (Cyber Monday, KubeCon). The associate exams (PCA, OTCA, CCA, KCA, CGOA, CBA, CNPA) are multiple choice and cheaper; CNPE and LFCS are performance-based.
- Most certs are valid 2-3 years and Golden status needs them all active, so sit the associate exams close together.
- Book about two weeks ahead, and only after a full timed mock finishes with time to spare.

## One cluster for the whole track
```bash
./lab.sh kind up cilium          # CCA needs Cilium; everything else runs fine on it
./lab.sh addon monitoring        # PCA / OTCA
./lab.sh addon kyverno           # KCA
kubectl apply -f k8s/namespaces.yaml
kubectl get ns -l lab.devops/component --show-labels
```
Clean up one component with `kubectl delete ns <name>`.

