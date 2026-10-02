#!/usr/bin/env bash
# Phase 28 (CNPA/CNPE) golden-path platform exercise. Needs a cluster with an enforcing CNI for the
# NetworkPolicy part (./lab.sh kind up cilium) and Kubernetes >= 1.30 for ValidatingAdmissionPolicy.
#   ./up.sh                  namespace-as-a-service base (ns platform-lab) + admission policy + smoke test
#   ./up.sh tenant team-a    apply the tenants/team-a overlay (ns platform-lab-team-a)
#   ./up.sh crossplane       CONCEPT EXERCISE for real: install Crossplane v2 (Helm) + XRD/Composition/XR
#   ./up.sh down             delete everything this lab created (namespaces by label, policy, crossplane objects)
set -euo pipefail
cd "$(dirname "$0")"
need() { command -v "$1" >/dev/null || { echo "missing $1 - ./lab.sh tools all"; exit 1; }; }
need kubectl

base() {
  kubectl apply -k namespace-service/base
  kubectl apply -f policy/require-team-label.yaml
  sleep 2   # let the API server pick up the new policy
  echo ">> guardrail test: bad-deploy must be DENIED"
  if kubectl apply -f policy/bad-deploy.yaml 2>&1; then
    echo "!! bad-deploy was admitted - is your cluster >= 1.30?"; exit 1
  fi
  echo ">> guardrail test: good-deploy must be ADMITTED"
  kubectl apply -f policy/good-deploy.yaml
  kubectl -n platform-lab rollout status deploy/good-app --timeout=180s
  kubectl -n platform-lab get pod -l app=good-app \
    -o jsonpath='{range .items[*]}{.metadata.name}{"  "}{.spec.containers[0].resources}{"\n"}{end}'
  kubectl -n platform-lab describe resourcequota tenant-quota
  kubectl auth can-i create deploy -n platform-lab --as=jdoe --as-group=team-platform || true
  kubectl auth can-i create namespaces --as=jdoe --as-group=team-platform || true
}

install_crossplane() {
  need helm
  helm repo add crossplane-stable https://charts.crossplane.io/stable >/dev/null 2>&1 || true
  helm repo update crossplane-stable >/dev/null
  helm upgrade --install crossplane crossplane-stable/crossplane -n crossplane-system --create-namespace --wait
  kubectl apply -f crossplane/functions.yaml
  kubectl wait function.pkg.crossplane.io/function-patch-and-transform --for=condition=Healthy --timeout=300s
  kubectl apply -f crossplane/xrd.yaml
  kubectl wait xrd/xteamnamespaces.platform.lab.devops --for=condition=Established --timeout=120s
  kubectl apply -f crossplane/composition.yaml
  kubectl apply -f crossplane/example-xr.yaml
  sleep 10
  kubectl get xteamnamespace team-b
  kubectl -n platform-lab-team-b get resourcequota tenant-quota -o yaml | sed -n '/^spec:/,$p'
}

case "${1:-up}" in
  up) base ;;
  tenant)
    t="${2:?usage: $0 tenant <team>}"
    [ -d "namespace-service/tenants/$t" ] || { echo "no overlay namespace-service/tenants/$t - copy team-a"; exit 1; }
    kubectl apply -k "namespace-service/tenants/$t"
    kubectl get ns -l lab.devops/component=cnpe ;;
  crossplane) install_crossplane ;;
  down)
    kubectl delete -f crossplane/example-xr.yaml --ignore-not-found 2>/dev/null || true
    kubectl delete -f crossplane/composition.yaml -f crossplane/xrd.yaml --ignore-not-found 2>/dev/null || true
    kubectl delete -f policy/require-team-label.yaml --ignore-not-found
    kubectl delete ns -l lab.devops/component=cnpe --ignore-not-found ;;
  *) echo "usage: $0 [up|tenant <team>|crossplane|down]"; exit 1 ;;
esac
