---
tags: [devops-prep, guide]
---
# Phase 18 - Istio Service Mesh (ICA)

**Plan weeks:** 56-58 · **Hours:** 32 · **Exam:** ICA, 2 h performance-based, USD 250 · **Lab:** `./lab.sh kind up mesh`, `lab/mesh/`

| Week | Focus | Deliverable |
|---|---|---|
| 56 | Install (sidecar vs ambient), VirtualService/DestinationRule, gateways | Traffic-splitting demo |
| 57 | mTLS (PeerAuthentication), AuthorizationPolicy, JWT | Zero-trust mesh policy pack |
| 58 | Control/data plane troubleshooting, sit ICA | ICA |

## Domains (sheet weights)
| Domain | Weight |
|---|---|
| Traffic Management | 35% |
| Securing Workloads | 25% |
| Installation, Upgrade & Configuration | 20% |
| Troubleshooting | 20% |

## Architecture
- **istiod:** control plane (config distribution via xDS, certificate authority issuing SPIFFE identities, sidecar injection webhook).
- **Sidecar mode:** Envoy proxy injected into each pod (`istio-injection=enabled` label). **Ambient mode:** per-node ztunnel for L4 mTLS + optional waypoint proxies for L7 - no sidecars.
- Install: `istioctl install --set profile=demo|default|minimal|ambient`, or Helm (base, istiod, gateway charts). Upgrades: canary control plane via revisions (`--revision 1-2x`) and revision tags.

## Traffic management
- **Gateway** (edge listener) + **VirtualService** (routing rules: match on URI/headers, weights, retries, timeouts, fault injection, mirroring) + **DestinationRule** (subsets by labels, load balancing, connection pools, outlier detection = circuit breaking) + **ServiceEntry** (external services) + **Sidecar** resource (limit config scope). Kubernetes Gateway API is also supported and increasingly the default.
- Lab file `lab/mesh/traffic.yaml`: 80/20 split, header-based routing for user `jason`, a 3 s delay fault on 50% of ratings calls, circuit breaker settings.

## Security
- PeerAuthentication: `PERMISSIVE` (accept both) -> `STRICT` (mTLS only). Apply mesh-wide in `istio-system`, override per namespace/workload.
- AuthorizationPolicy: ALLOW/DENY/CUSTOM, match on source principals (service accounts), namespaces, methods, paths, JWT claims. An empty policy in a namespace = deny all.
- RequestAuthentication validates JWTs; pair with AuthorizationPolicy `requestPrincipals` to require them.
- Lab file `lab/mesh/security.yaml` builds least-privilege access for bookinfo.

## Troubleshooting toolkit
```bash
istioctl analyze -A
istioctl proxy-status                         # is every proxy SYNCED?
istioctl proxy-config routes|clusters|listeners|endpoints deploy/productpage-v1
istioctl x describe pod <pod>
kubectl logs deploy/productpage-v1 -c istio-proxy
istioctl dashboard kiali|grafana|jaeger       # demo profile addons
```
Common faults: VirtualService refers to a subset not defined in a DestinationRule (503 NR), STRICT mTLS with a client outside the mesh (connection reset), missing injection label (no proxy), port naming/appProtocol wrong (treated as TCP).

## Self-check
1. Where do you define subsets and where do you route to them?
2. Effect of an AuthorizationPolicy with `spec: {}` in namespace `default`?
3. How to do a canary upgrade of Istio itself?
4. A request gets 503 with flag `NR`. Meaning?

<details><summary>Answers</summary>

1. Subsets in DestinationRule; routes in VirtualService.
2. Deny all requests to workloads in that namespace.
3. Install a new revision, relabel namespaces (`istio.io/rev`), restart workloads, remove the old revision.
4. No route configured (often a missing subset/DestinationRule).
</details>

## Resources
https://istio.io/latest/docs · https://istio.io/latest/docs/setup/getting-started · LF ICA curriculum


---
[[Home]] · [[Schedule]]
