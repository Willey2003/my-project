#!/usr/bin/env bash
# Deploys the PCA (Prometheus) and OTCA (OpenTelemetry) labs into the kind cluster.
#   ./up.sh [pca|otel|all]        default: all
#   ./up.sh down                  delete ns prom-lab and otel-lab
# Assumes: ./lab.sh kind up (cluster "lab", local registry localhost:5001) and ./lab.sh addon monitoring
# (kube-prometheus-stack, release "kps", ns monitoring - provides the ServiceMonitor/PrometheusRule CRDs).
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:$PATH"
CLUSTER=${CLUSTER:-lab}
REGISTRY=${REGISTRY:-localhost:5001}
IMAGE="$REGISTRY/otel-demo:0.1"

need() { command -v "$1" >/dev/null || { echo "missing $1 - ./lab.sh tools all"; exit 1; }; }
need kubectl

preflight() {
  local ctx; ctx=$(kubectl config current-context 2>/dev/null || true)
  [ "$ctx" = "kind-$CLUSTER" ] || echo "!! current context is '$ctx', expected 'kind-$CLUSTER' - continuing anyway"
  kubectl get crd servicemonitors.monitoring.coreos.com prometheusrules.monitoring.coreos.com >/dev/null 2>&1 || {
    echo "Prometheus Operator CRDs not found - run: ./lab.sh addon monitoring"; exit 1; }
}

pca() {
  echo "==> pca (ns prom-lab)"
  # Let the kps Alertmanager pick up AlertmanagerConfig CRs from every namespace. A merge patch with {}
  # only fills the selectors when they are unset (nil = own namespace only); existing selectors are kept.
  local am
  am=$(kubectl -n monitoring get alertmanager -o name 2>/dev/null | head -1 || true)
  if [ -n "$am" ]; then
    kubectl -n monitoring patch "$am" --type merge \
      -p '{"spec":{"alertmanagerConfigSelector":{},"alertmanagerConfigNamespaceSelector":{}}}' >/dev/null
  else
    echo "!! no Alertmanager CR in ns monitoring - AlertmanagerConfig will not be used"
  fi
  kubectl apply -k pca
  kubectl -n prom-lab rollout status deploy/shop-api --timeout=300s
  kubectl -n prom-lab rollout status deploy/alert-sink --timeout=300s
}

build_image() {
  need docker
  docker build -t "$IMAGE" otel/app
  if docker push "$IMAGE" >/dev/null 2>&1; then
    echo "pushed $IMAGE"
  else
    need kind
    echo "registry $REGISTRY not reachable - loading the image into kind cluster '$CLUSTER' instead"
    kind load docker-image "$IMAGE" --name "$CLUSTER"
  fi
}

otel() {
  echo "==> otel (ns otel-lab)"
  build_image
  kubectl apply -k otel
  for d in jaeger otel-collector otel-demo otel-loadgen; do
    kubectl -n otel-lab rollout status "deploy/$d" --timeout=300s
  done
}

hints() {
  local prom am
  prom=$(kubectl -n monitoring get svc -l app=kube-prometheus-stack-prometheus -o name 2>/dev/null | head -1 || true)
  am=$(kubectl -n monitoring get svc -l app=kube-prometheus-stack-alertmanager -o name 2>/dev/null | head -1 || true)
  cat <<TXT

Port-forwards:
  kubectl -n monitoring port-forward ${prom:-svc/kps-kube-prometheus-stack-prometheus} 9090     # Prometheus
  kubectl -n monitoring port-forward ${am:-svc/kps-kube-prometheus-stack-alertmanager} 9093     # Alertmanager
  kubectl -n monitoring port-forward svc/kps-grafana 3000:80                                     # Grafana admin/admin
  kubectl -n otel-lab   port-forward svc/jaeger 16686                                            # Jaeger UI
  kubectl -n otel-lab   port-forward svc/otel-collector 8889 8888 55679                          # app metrics, self-metrics, zpages
Exercises: pca/promql-exercises.md, otel/otel-exercises.md
TXT
}

case "${1:-all}" in
  pca)  preflight; pca;  hints ;;
  otel) preflight; otel; hints ;;
  all)  preflight; pca; otel; hints ;;
  down) kubectl delete ns prom-lab otel-lab --ignore-not-found ;;
  *) echo "usage: $0 [pca|otel|all|down]"; exit 1 ;;
esac
