#!/usr/bin/env bash
# KCA lab (Golden track G5): Kyverno policies 01-08 + a guided demo in namespace kyverno-lab.
# Prereq (from lab/): ./lab.sh kind up   (any profile). Installs Kyverno with ./lab.sh addon kyverno if missing.
# Usage:
#   ./up.sh          install Kyverno if needed, apply policies, create kyverno-lab, run the demo
#   ./up.sh test     run 'kyverno test' on test/ (needs the kyverno CLI)
#   ./up.sh down     delete kyverno-lab and every lab policy
# Also reachable as ./lab.sh golden kyverno [args].
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:$PATH"
NS=kyverno-lab

step() { printf '\n\033[1;32m## %s\033[0m\n' "$*"; }
need() { command -v "$1" >/dev/null 2>&1 || { echo "missing '$1' - run ./lab.sh tools"; exit 1; }; }

cli_test() {
  if command -v kyverno >/dev/null 2>&1; then
    kyverno test test/
  else
    echo "kyverno CLI not installed - skipping. Install: https://kyverno.io/docs/kyverno-cli/install/ (or: kubectl krew install kyverno)"
  fi
}

install_kyverno() {
  if kubectl get crd clusterpolicies.kyverno.io >/dev/null 2>&1; then
    echo "Kyverno already installed: $(kubectl -n kyverno get deploy -o name | tr '\n' ' ')"
  else
    ../../k8s/addons/install.sh kyverno
  fi
  kubectl -n kyverno rollout status deploy --timeout=300s
}

apply_policies() {
  for f in policies/*.yaml; do
    if grep -q 'REPLACE_WITH_YOUR_COSIGN_PUBLIC_KEY' "$f"; then
      echo "skip $f (paste your cosign.pub first - see the comment at the top of the file)"; continue
    fi
    kubectl apply -f "$f"
  done
  kubectl wait --for=condition=Ready clusterpolicy --all --timeout=120s
  kubectl get clusterpolicy,clustercleanuppolicy
}

demo() {
  step "namespace $NS (trigger for policy 04)"
  kubectl apply -f namespace.yaml
  for _ in $(seq 1 20); do kubectl -n "$NS" get netpol default-deny-ingress >/dev/null 2>&1 && break; sleep 3; done
  kubectl -n "$NS" get netpol --show-labels || echo "no NetworkPolicy yet - check: kubectl get updaterequests -n kyverno"

  step "bad pods through the real admission chain (server-side dry run, nothing is created)"
  kubectl apply --dry-run=server -f test/resources-bad.yaml 2>&1 | sed 's/^/  /' || true

  step "good pod: admitted and mutated by policy 03"
  kubectl apply -f test/resources-good.yaml
  kubectl -n "$NS" wait --for=condition=Ready pod/good-pod --timeout=120s || true
  kubectl -n "$NS" get pod good-pod -o jsonpath='{"pod:       "}{.spec.securityContext}{"\ncontainer: "}{.spec.containers[0].securityContext}{"\n"}'

  step "Audit violation: pod without labels is admitted, then reported (and cleaned up by policy 08)"
  kubectl -n "$NS" run audit-demo --image=docker.io/nginxinc/nginx-unprivileged:1.27-alpine \
    --overrides='{"spec":{"containers":[{"name":"audit-demo","image":"docker.io/nginxinc/nginx-unprivileged:1.27-alpine","resources":{"requests":{"cpu":"10m","memory":"32Mi"},"limits":{"memory":"64Mi"}}}]}}' \
    --labels=lab.devops/cleanup=enabled 2>&1 || true
  sleep 10
  kubectl -n "$NS" get policyreports -o wide || true

  step "kyverno CLI"
  cli_test
  cat <<EOT

Next: kubectl -n $NS get polr -o yaml | less      # per-resource results
      kubectl get events -n $NS --field-selector reason=PolicyViolation
      ../README.md exercises (PolicyException, mutate test, Pod Security library)
EOT
}

need kubectl
case "${1:-up}" in
  up)   install_kyverno; step "policies"; apply_policies; demo ;;
  test) cli_test ;;
  down) kubectl delete ns "$NS" --ignore-not-found
        kubectl delete -f policies/ --ignore-not-found ;;
  *)    sed -n '2,8p' "$0"; exit 1 ;;
esac
