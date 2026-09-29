#!/usr/bin/env bash
# Local OCI registry for kind (localhost:5001 on the host, kind-registry:5000 inside nodes).
# Used by the supply-chain labs (push, sign with cosign, enforce signatures).
set -euo pipefail
NAME=kind-registry; PORT=5001
case "${1:-}" in
start)
  if [ "$(docker inspect -f '{{.State.Running}}' $NAME 2>/dev/null || true)" != true ]; then
    docker run -d --restart=always -p "127.0.0.1:${PORT}:5000" --network bridge --name $NAME registry:2 >/dev/null
    echo "registry started on localhost:$PORT"
  fi ;;
connect)
  cluster=${2:-lab}
  for node in $(kind get nodes --name "$cluster"); do
    docker exec "$node" mkdir -p "/etc/containerd/certs.d/localhost:${PORT}"
    printf '[host."http://%s:5000"]\n' "$NAME" | docker exec -i "$node" cp /dev/stdin "/etc/containerd/certs.d/localhost:${PORT}/hosts.toml"
  done
  docker network connect kind $NAME 2>/dev/null || true
  kubectl apply -f - <<YAML
apiVersion: v1
kind: ConfigMap
metadata:
  name: local-registry-hosting
  namespace: kube-public
data:
  localRegistryHosting.v1: |
    host: "localhost:${PORT}"
    help: "https://kind.sigs.k8s.io/docs/user/local-registry/"
YAML
  ;;
stop) docker rm -f $NAME ;;
*) echo "usage: $0 start|connect [cluster]|stop" ;;
esac
