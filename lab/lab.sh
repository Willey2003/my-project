#!/usr/bin/env bash
# One entry point for every lab in the plan. Run ./lab.sh with no args for help.
set -euo pipefail
cd "$(dirname "$0")"
LAB_DIR=$(pwd)
export PATH="$HOME/.local/bin:$PATH"

usage() {
cat <<'EOF'
usage: ./lab.sh <command> [args]

 setup
   doctor                 check host resources + which tools are present
   tools [all|<name>..]   install CLI tools into ~/.local/bin (host/install-tools.sh)

 VMs (Linux / RHCSA / RHCE / networking, weeks 2-16)
   vms up|halt|destroy|ssh <vm>   Vagrant: control, node1, node2 (Alma/RHEL-compatible)
   ansible-ping                   ping node1/node2 from the control VM

 Containers & CI (weeks 17-22)
   compose up|down|scan           3-tier app (nginx + api + postgres), Trivy scan

 Kubernetes (weeks 23+)
   kind up [profile]      profiles: basic (default) | cilium | security | mesh
   kind down              delete the kind cluster
   addon <name>           ingress | metrics | cilium | argocd | rollouts | istio |
                          falco | tetragon | gatekeeper | policy-controller | monitoring
   break <scenario>       inject a CKA troubleshooting fault (k8s/scenarios/)
   break list             list scenarios; 'break reset' removes them

 Later phases
   aws plan|apply|destroy Terraform VPC+ECS stack (costs money when applied!)
   crc                    OpenShift Local helper (openshift/crc.sh)
   ai up|down             isolated Ollama + scanner sandbox (ai-security/)
   capstone up|down       FastAPI + Qdrant copilot skeleton
EOF
}

need() { command -v "$1" >/dev/null 2>&1 || { echo "missing '$1' - run ./lab.sh tools or ./lab.sh doctor"; exit 1; }; }
CLUSTER=${CLUSTER:-lab}

doctor() {
  echo "== host"
  uname -srm
  if [ -r /proc/meminfo ]; then awk '/MemTotal/ {printf "RAM: %.1f GiB\n", $2/1048576}' /proc/meminfo
  elif command -v sysctl >/dev/null; then sysctl -n hw.memsize | awk '{printf "RAM: %.1f GiB\n", $1/1073741824}'; fi
  command -v nproc >/dev/null && echo "CPUs: $(nproc)"
  df -h "$HOME" | awk 'NR==2 {print "Free disk in $HOME: " $4}'
  echo "   recommended: 16 GiB RAM (32 for OpenShift Local), 8 vCPU, 100 GiB free"
  echo "== tools"
  for t in git docker vagrant VBoxManage virsh kubectl kind helm k9s yq jq terraform aws ansible trivy cosign argocd istioctl cilium crc python3; do
    if command -v "$t" >/dev/null 2>&1; then printf '  [ok]      %s\n' "$t"; else printf '  [missing] %s\n' "$t"; fi
  done
  if command -v docker >/dev/null && ! docker info >/dev/null 2>&1; then
    echo "  !! docker CLI found but daemon not reachable (start Docker / add user to docker group)"
  fi
  if [ -r /proc/sys/fs/inotify/max_user_instances ] && [ "$(cat /proc/sys/fs/inotify/max_user_instances)" -lt 512 ]; then
    echo "  !! raise inotify limits for multi-node kind:"
    echo "     sudo sysctl fs.inotify.max_user_instances=512 fs.inotify.max_user_watches=524288"
  fi
}

kind_up() {
  need kind; need kubectl
  local profile=${1:-basic}
  local cfg="k8s/kind/${profile}.yaml"
  [ -f "$cfg" ] || { echo "unknown profile $profile"; ls k8s/kind; exit 1; }
  k8s/kind/local-registry.sh start
  kind create cluster --name "$CLUSTER" --config "$cfg"
  k8s/kind/local-registry.sh connect "$CLUSTER"
  case "$profile" in
    cilium|security) k8s/addons/install.sh cilium ;;
  esac
  case "$profile" in
    security) k8s/addons/install.sh tetragon; k8s/addons/install.sh falco ;;
    mesh)     k8s/addons/install.sh istio ;;
  esac
  k8s/addons/install.sh ingress
  kubectl get nodes -o wide
}

cmd=${1:-help}; shift || true
case "$cmd" in
  doctor)  doctor ;;
  tools)   host/install-tools.sh "$@" ;;
  vms)
    need vagrant; cd vagrant
    case "${1:-up}" in
      up)      VAGRANT_EXPERIMENTAL=disks vagrant up ;;
      ssh)     vagrant ssh "${2:-control}" ;;
      *)       vagrant "$1" ;;
    esac ;;
  ansible-ping) cd vagrant && vagrant ssh control -c "sudo -iu student bash -c 'cd /lab/ansible && ansible all -m ping'" ;;
  compose)
    need docker; cd docker
    case "${1:-up}" in
      up)   docker compose up -d --build && docker compose ps ;;
      down) docker compose down -v ;;
      scan) ./scan.sh ;;
    esac ;;
  kind)
    case "${1:-up}" in
      up)   kind_up "${2:-basic}" ;;
      down) kind delete cluster --name "$CLUSTER" ;;
    esac ;;
  addon)   k8s/addons/install.sh "$@" ;;
  break)   k8s/scenarios/break.sh "$@" ;;
  aws)
    need terraform; cd aws/terraform
    terraform init -input=false >/dev/null
    case "${1:-plan}" in
      plan)    terraform plan ;;
      apply)   terraform apply ;;
      destroy) terraform destroy ;;
    esac ;;
  crc)     openshift/crc.sh "$@" ;;
  ai)      cd ai-security; [ "${1:-up}" = up ] && docker compose up -d || docker compose down -v ;;
  capstone) cd capstone/copilot; [ "${1:-up}" = up ] && docker compose up -d --build || docker compose down -v ;;
  help|-h|--help|*) usage ;;
esac
