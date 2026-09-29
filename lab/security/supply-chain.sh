#!/usr/bin/env bash
# Week 48 / CKS supply chain: scan -> sign -> enforce "signed images only" in namespace 'secure'.
# Prereqs: ./lab.sh kind up ; ./lab.sh addon policy-controller ; cosign + trivy installed.
# Images go to ttl.sh (anonymous, auto-expiring public registry) because the admission controller runs
# inside the cluster and cannot reach the host's localhost:5001 registry. Images are public for 2 h -
# they contain only the lab app and a BENIGN marker file, never real malware.
set -euo pipefail
cd "$(dirname "$0")"
ID=${ID:-lab-$(whoami)-$RANDOM}
GOOD=ttl.sh/${ID}-signed:2h
BAD=ttl.sh/${ID}-tainted:2h
export COSIGN_PASSWORD=${COSIGN_PASSWORD:-lab}

step() { printf '\n\033[1;32m## %s\033[0m\n' "$*"; }

step "1. build a good image and a 'tainted' one (benign marker file)"
docker build -q -t "$GOOD" --target runtime ../docker/app
printf 'FROM %s\nRUN echo "LAB-TAINT-MARKER: pretend backdoor" > /tmp/marker\n' "$GOOD" | docker build -q -t "$BAD" -
docker push -q "$GOOD"; docker push -q "$BAD"

step "2. scan"
trivy image --severity HIGH,CRITICAL --ignore-unfixed "$GOOD" || true

step "3. sign ONLY the good image by digest (key pair in ./cosign.key / cosign.pub)"
[ -f cosign.key ] || cosign generate-key-pair
DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' "$GOOD")
cosign sign --yes --key cosign.key "$DIGEST"
cosign verify --key cosign.pub "$DIGEST" >/dev/null && echo "verified $DIGEST"

step "4. enforce: namespace 'secure' only admits images signed by cosign.pub"
kubectl create ns secure --dry-run=client -o yaml | kubectl apply -f -
kubectl label ns secure policy.sigstore.dev/include=true --overwrite
kubectl apply -f - <<YAML
apiVersion: policy.sigstore.dev/v1beta1
kind: ClusterImagePolicy
metadata:
  name: lab-signed-only
spec:
  images:
    - glob: "ttl.sh/**"
  authorities:
    - key:
        data: |
$(sed 's/^/          /' cosign.pub)
YAML

step "5. prove it"
kubectl -n secure run good --image="$DIGEST" && echo "signed image admitted"
if kubectl -n secure run bad --image="$BAD"; then
  echo "!! unsigned image admitted - policy not working"
else
  echo "unsigned image BLOCKED - write this up as your before/after demo"
fi
