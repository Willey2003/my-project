#!/usr/bin/env bash
# Installs cluster add-ons into the current kube context (normally kind-lab).
#   ./install.sh <addon> [<addon> ...]
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
need() { command -v "$1" >/dev/null || { echo "missing $1 - ./lab.sh tools all"; exit 1; }; }
need kubectl
repo() { need helm; helm repo add "$1" "$2" >/dev/null 2>&1 || true; helm repo update "$1" >/dev/null; }
wait_deploy() { kubectl -n "$1" rollout status deploy --timeout=300s; }

install_one() {
case "$1" in
  ingress)
    # ingress-nginx was retired upstream in March 2026 (no more fixes), but the Ingress API itself is
    # still exam material and this is the quickest kind-compatible controller. Prefer 'gateway' for new work.
    kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
    kubectl -n ingress-nginx wait --for=condition=ready pod -l app.kubernetes.io/component=controller --timeout=300s ;;
  gateway)
    # Gateway API CRDs + Envoy Gateway as the implementation (CKA now covers Gateway API).
    need helm
    helm upgrade --install eg oci://docker.io/envoyproxy/gateway-helm -n envoy-gateway-system --create-namespace --wait ;;
  metrics)
    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
    kubectl -n kube-system patch deploy metrics-server --type=json \
      -p '[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
    wait_deploy kube-system ;;
  cilium)
    if command -v cilium >/dev/null; then
      cilium install --wait
    else
      repo cilium https://helm.cilium.io
      helm upgrade --install cilium cilium/cilium -n kube-system --set ipam.mode=kubernetes \
        --set hubble.relay.enabled=true --set hubble.ui.enabled=true --wait
    fi
    kubectl wait --for=condition=Ready nodes --all --timeout=300s ;;
  tetragon)
    repo cilium https://helm.cilium.io
    helm upgrade --install tetragon cilium/tetragon -n kube-system --wait ;;
  falco)
    repo falcosecurity https://falcosecurity.github.io/charts
    helm upgrade --install falco falcosecurity/falco -n falco --create-namespace \
      --set driver.kind=modern_ebpf --set tty=true \
      --set-file "customRules.lab-rules\.yaml=$(dirname "$0")/../../security/falco-rules.yaml" --wait ;;
  argocd)
    kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
    kubectl apply -n argocd --server-side -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
    wait_deploy argocd
    echo "admin password: $(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d)"
    echo "UI: kubectl -n argocd port-forward svc/argocd-server 8443:443  -> https://localhost:8443" ;;
  rollouts)
    kubectl create namespace argo-rollouts --dry-run=client -o yaml | kubectl apply -f -
    kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml
    wait_deploy argo-rollouts ;;
  workflows)
    kubectl create namespace argo --dry-run=client -o yaml | kubectl apply -f -
    kubectl apply -n argo -f https://github.com/argoproj/argo-workflows/releases/latest/download/quick-start-minimal.yaml
    wait_deploy argo ;;
  events)
    kubectl create namespace argo-events --dry-run=client -o yaml | kubectl apply -f -
    kubectl apply -f https://raw.githubusercontent.com/argoproj/argo-events/stable/manifests/install.yaml
    wait_deploy argo-events ;;
  istio)
    need istioctl
    PROFILE=${ISTIO_PROFILE:-demo}   # ISTIO_PROFILE=ambient for ambient mode
    istioctl install --set profile="$PROFILE" -y
    # sidecar injection is enabled per lab namespace (mesh-bookinfo), not on 'default'
    istioctl verify-install || true ;;
  gatekeeper)
    repo gatekeeper https://open-policy-agent.github.io/gatekeeper/charts
    helm upgrade --install gatekeeper gatekeeper/gatekeeper -n gatekeeper-system --create-namespace --wait ;;
  policy-controller)
    repo sigstore https://sigstore.github.io/helm-charts
    helm upgrade --install policy-controller sigstore/policy-controller -n cosign-system --create-namespace --wait ;;
  kyverno)
    repo kyverno https://kyverno.github.io/kyverno/
    helm upgrade --install kyverno kyverno/kyverno -n kyverno --create-namespace --wait ;;
  monitoring)
    repo prometheus-community https://prometheus-community.github.io/helm-charts
    helm upgrade --install kps prometheus-community/kube-prometheus-stack -n monitoring --create-namespace \
      --set grafana.adminPassword=admin --wait
    echo "Grafana: kubectl -n monitoring port-forward svc/kps-grafana 3000:80 (admin/admin)" ;;
  *) echo "unknown addon '$1'"; exit 1 ;;
esac
}

[ $# -gt 0 ] || { grep -E '^  [a-z-]+\)' "$0" | tr -d ' )'; exit 0; }
for a in "$@"; do echo "==> $a"; install_one "$a"; done
