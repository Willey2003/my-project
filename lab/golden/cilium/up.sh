#!/usr/bin/env bash
# CCA lab (Golden track G4): Star Wars demo app + CiliumNetworkPolicy walkthrough in namespace cilium-lab.
# Prereq (from lab/):  ./lab.sh kind up cilium        (kind cluster with Cilium as the CNI)
# Usage:
#   ./up.sh                    deploy the demo app, enable Hubble relay/UI if missing, run the test matrix
#   ./up.sh policy l3l4|l7|fqdn|none   apply one policy (none = delete all CNPs in cilium-lab), then test
#   ./up.sh test               run the curl test matrix against whatever policy is active
#   ./up.sh down               delete namespace cilium-lab
# Also reachable as ./lab.sh golden cilium [args].
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:$PATH"
NS=cilium-lab
SVC=deathstar.$NS.svc.cluster.local

step() { printf '\n\033[1;32m## %s\033[0m\n' "$*"; }
need() { command -v "$1" >/dev/null 2>&1 || { echo "missing '$1' - run ./lab.sh tools"; exit 1; }; }

prereq() {
  need kubectl
  if ! kubectl -n kube-system get ds cilium >/dev/null 2>&1; then
    echo "Cilium is not installed in context '$(kubectl config current-context 2>/dev/null || echo none)'."
    echo "Run first:  cd lab && ./lab.sh kind up cilium"
    exit 1
  fi
}

enable_hubble() {
  if kubectl -n kube-system get deploy hubble-relay >/dev/null 2>&1; then
    echo "hubble-relay already installed"
  elif command -v cilium >/dev/null 2>&1; then
    cilium hubble enable --ui
    cilium status --wait
  else
    echo "hubble-relay missing and no cilium CLI - install it (./lab.sh tools cilium) and run: cilium hubble enable --ui"
  fi
}

# probe <pod> <method> <url> <expected>
probe() {
  local out
  out=$(kubectl -n "$NS" exec "$1" -- curl -s -m 5 -X "$2" "$3" 2>/dev/null | head -c 60 | tr -d '\n') || true
  [ -n "$out" ] || out="(no response / timeout)"
  printf '  %-10s %-5s %-45s -> %-28s expect: %s\n' "$1" "$2" "${3#http://}" "$out" "$4"
}

test_matrix() {
  step "test matrix (expectations: none | l3l4 | l7)"
  probe tiefighter POST "http://$SVC/v1/request-landing" "landed | landed | landed"
  probe xwing      POST "http://$SVC/v1/request-landing" "landed | timeout | timeout"
  probe tiefighter PUT  "http://$SVC/v1/exhaust-port"    "panic | panic | Access denied"
  step "FQDN egress from mediabot (expectations: none | fqdn)"
  probe mediabot   GET  "https://api.github.com"          "json | json"
  probe mediabot   GET  "https://www.google.com"          "html | timeout"
  echo; echo "Watch it live: cilium hubble port-forward & hubble observe -n $NS -f   (see hubble-exercises.md)"
}

deploy() {
  step "deploy demo app into $NS"
  kubectl apply -f demo-app.yaml
  kubectl -n "$NS" rollout status deploy/deathstar --timeout=180s
  kubectl -n "$NS" wait --for=condition=Ready pod/tiefighter pod/xwing pod/mediabot --timeout=180s
  kubectl -n "$NS" get pods -o wide --show-labels
  step "Cilium view of the endpoints (identity per label set)"
  kubectl -n "$NS" get ciliumendpoints
}

policy() {
  case "${1:-}" in
    l3l4) kubectl -n "$NS" delete cnp mediabot-fqdn --ignore-not-found; kubectl apply -f policies/01-l3-l4.yaml ;;
    l7)   kubectl -n "$NS" delete cnp mediabot-fqdn --ignore-not-found; kubectl apply -f policies/02-l7-http.yaml ;;
    fqdn) kubectl apply -f policies/03-dns-fqdn-egress.yaml ;;
    none) kubectl -n "$NS" delete cnp --all ;;
    *)    echo "usage: $0 policy l3l4|l7|fqdn|none"; exit 1 ;;
  esac
  kubectl -n "$NS" get cnp
  sleep 3   # let the agents regenerate endpoint policy
}

prereq
case "${1:-up}" in
  up)     enable_hubble; deploy; test_matrix ;;
  policy) policy "${2:-}"; test_matrix ;;
  test)   test_matrix ;;
  down)   kubectl delete ns "$NS" --ignore-not-found ;;
  *)      sed -n '2,10p' "$0"; exit 1 ;;
esac
