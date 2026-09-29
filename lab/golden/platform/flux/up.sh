#!/usr/bin/env bash
# Phase 26 (CGOA) Flux lab. Needs a cluster (./lab.sh kind up) and the flux CLI
# (curl -s https://fluxcd.io/install.sh | bash, or brew install fluxcd/tap/flux).
#   ./up.sh          install Flux controllers if missing, apply podinfo.yaml, wait for Ready
#   ./up.sh status   flux get all -n flux-lab
#   ./up.sh drift    change the image by hand, force a reconcile, show Flux reverting it
#   ./up.sh down     delete namespace flux-lab (controllers stay; 'flux uninstall' removes them)
set -euo pipefail
cd "$(dirname "$0")"
need() { command -v "$1" >/dev/null || { echo "missing $1 - see header"; exit 1; }; }
need kubectl; need flux
case "${1:-up}" in
  up)
    flux check --pre
    if ! kubectl get ns flux-system >/dev/null 2>&1; then
      flux install --components-extra=image-reflector-controller,image-automation-controller
    fi
    kubectl apply -f podinfo.yaml
    flux reconcile source git podinfo -n flux-lab --timeout=2m || true
    kubectl -n flux-lab wait kustomization/podinfo --for=condition=Ready --timeout=5m
    kubectl -n flux-lab wait helmrelease/podinfo-helm --for=condition=Ready --timeout=5m
    flux get all -n flux-lab
    kubectl -n flux-lab get deploy,svc,hpa ;;
  status)
    flux get all -n flux-lab ;;
  drift)
    kubectl -n flux-lab set image deploy/podinfo podinfod=ghcr.io/stefanprodan/podinfo:6.0.0
    kubectl -n flux-lab get deploy podinfo -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
    flux reconcile kustomization podinfo -n flux-lab --with-source
    echo "after reconcile:"
    kubectl -n flux-lab get deploy podinfo -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}' ;;
  down)
    kubectl delete -f podinfo.yaml --ignore-not-found ;;
  *) echo "usage: $0 [up|status|drift|down]"; exit 1 ;;
esac
