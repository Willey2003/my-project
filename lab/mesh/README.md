# Istio lab (weeks 56-58)

```bash
./lab.sh kind up mesh                       # installs Istio 'demo' profile
kubectl apply -f mesh/traffic.yaml        # creates namespace mesh-bookinfo (sidecar injection on) + routing
kubectl apply -n mesh-bookinfo -f https://raw.githubusercontent.com/istio/istio/master/samples/bookinfo/platform/kube/bookinfo.yaml
kubectl apply -n mesh-bookinfo -f https://raw.githubusercontent.com/istio/istio/master/samples/bookinfo/networking/bookinfo-gateway.yaml
kubectl apply -f mesh/security.yaml
kubectl -n istio-system port-forward svc/istio-ingressgateway 8080:80   # http://localhost:8080/productpage
```
Ambient mode: `ISTIO_PROFILE=ambient ./lab.sh addon istio` on a fresh cluster, then
`kubectl label ns mesh-bookinfo istio.io/dataplane-mode=ambient istio-injection-`.

Troubleshooting drills (ICA 20%): `istioctl analyze`, `istioctl proxy-status`, `istioctl proxy-config routes deploy/productpage-v1`,
`istioctl x describe pod <pod>`, and break things on purpose: wrong subset name, missing DestinationRule, STRICT mTLS with a non-mesh client.
