#!/usr/bin/env bash
# Installs the CLI toolchain used across the whole 70-week plan into ~/.local/bin
# (no root needed for the binaries). Works on Linux x86_64/arm64, macOS, and WSL2.
#
#   ./install-tools.sh            # core set (weeks 1-35)
#   ./install-tools.sh all        # core + security/gitops/mesh tools (weeks 45+)
#   ./install-tools.sh kubectl helm   # just the named tools
#
# Docker Engine/Desktop, VirtualBox/libvirt and Vagrant need admin rights and are
# NOT installed here; run ./lab.sh doctor to see what is missing.
set -euo pipefail

BIN="${BIN:-$HOME/.local/bin}"
mkdir -p "$BIN"
export PATH="$BIN:$PATH"

OS=$(uname -s | tr '[:upper:]' '[:lower:]')          # linux | darwin
ARCH=$(uname -m)
case "$ARCH" in x86_64|amd64) ARCH=amd64 ;; aarch64|arm64) ARCH=arm64 ;; *) echo "unsupported arch $ARCH"; exit 1 ;; esac
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }
gh_latest() { # owner/repo -> tag (e.g. v1.2.3)
  curl -fsSL "https://api.github.com/repos/$1/releases/latest" | grep -m1 '"tag_name"' | cut -d'"' -f4
}
fetch_bin() { # url name
  curl -fsSL "$1" -o "$BIN/$2" && chmod +x "$BIN/$2"
}

install_kubectl() {
  local v; v=$(curl -fsSL https://dl.k8s.io/release/stable.txt)
  fetch_bin "https://dl.k8s.io/release/$v/bin/$OS/$ARCH/kubectl" kubectl
}
install_kind()   { fetch_bin "https://github.com/kubernetes-sigs/kind/releases/latest/download/kind-$OS-$ARCH" kind; }
install_helm()   { curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | HELM_INSTALL_DIR="$BIN" USE_SUDO=false bash; }
install_k9s()    { curl -fsSL "https://github.com/derailed/k9s/releases/latest/download/k9s_$(uname -s)_${ARCH}.tar.gz" | tar -xz -C "$BIN" k9s; }
install_yq()     { fetch_bin "https://github.com/mikefarah/yq/releases/latest/download/yq_${OS}_${ARCH}" yq; }
install_jq()     { local a=$ARCH; [ "$OS" = darwin ] && os=macos || os=linux; fetch_bin "https://github.com/jqlang/jq/releases/latest/download/jq-${os}-${a}" jq; }
install_terraform() {
  local v; v=$(curl -fsSL https://checkpoint-api.hashicorp.com/v1/check/terraform 2>/dev/null | grep -o '"current_version": *"[^"]*"' | cut -d'"' -f4 || true)
  [ -n "$v" ] || v=$(curl -fsSL https://releases.hashicorp.com/terraform/ | grep -oE 'terraform_[0-9]+\.[0-9]+\.[0-9]+<' | head -1 | tr -dc '0-9.')
  curl -fsSL "https://releases.hashicorp.com/terraform/$v/terraform_${v}_${OS}_${ARCH}.zip" -o "$TMP/tf.zip"
  unzip -oq "$TMP/tf.zip" -d "$BIN" terraform
}
install_trivy()  { curl -fsSL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b "$BIN"; }
install_cosign() { fetch_bin "https://github.com/sigstore/cosign/releases/latest/download/cosign-$OS-$ARCH" cosign; }
install_argocd() { fetch_bin "https://github.com/argoproj/argo-cd/releases/latest/download/argocd-$OS-$ARCH" argocd; }
install_rollouts(){ fetch_bin "https://github.com/argoproj/argo-rollouts/releases/latest/download/kubectl-argo-rollouts-$OS-$ARCH" kubectl-argo-rollouts; }
install_istioctl() {
  local v; v=$(gh_latest istio/istio)
  local os=$OS; [ "$OS" = darwin ] && os=osx
  local suffix="$os-$ARCH"; [ "$os" = osx ] && [ "$ARCH" = amd64 ] && suffix=osx
  curl -fsSL "https://github.com/istio/istio/releases/download/$v/istioctl-$v-$suffix.tar.gz" | tar -xz -C "$BIN"
}
install_cilium() {
  local v; v=$(curl -fsSL https://raw.githubusercontent.com/cilium/cilium-cli/main/stable.txt)
  curl -fsSL "https://github.com/cilium/cilium-cli/releases/download/$v/cilium-$OS-$ARCH.tar.gz" | tar -xz -C "$BIN"
}
install_kubebench() {
  local v; v=$(gh_latest aquasecurity/kube-bench); v=${v#v}
  echo "kube-bench runs as a Job inside the cluster (security/kube-bench-job.yaml); CLI $v not needed on host."
}
install_ansible() {
  have python3 || { echo "python3 required for ansible"; return 1; }
  python3 -m pip install --user --upgrade ansible-core ansible-lint >/dev/null
  "$HOME/.local/bin/ansible-galaxy" collection install ansible.posix community.general >/dev/null || true
}
install_aws() {
  if [ "$OS" = linux ]; then
    local a=x86_64; [ "$ARCH" = arm64 ] && a=aarch64
    curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-$a.zip" -o "$TMP/aws.zip"
    unzip -q "$TMP/aws.zip" -d "$TMP" && "$TMP/aws/install" -i "$HOME/.local/aws-cli" -b "$BIN" --update
  else
    echo "macOS: install the AWS CLI pkg from https://awscli.amazonaws.com/AWSCLIV2.pkg"
  fi
}

CORE=(kubectl kind helm k9s yq jq terraform trivy ansible aws)
EXTRA=(cosign argocd rollouts istioctl cilium kubebench)

if [ $# -eq 0 ]; then TOOLS=("${CORE[@]}")
elif [ "$1" = all ]; then TOOLS=("${CORE[@]}" "${EXTRA[@]}")
else TOOLS=("$@"); fi

for t in "${TOOLS[@]}"; do
  log "installing $t"
  if ! "install_$t"; then echo "  !! $t failed, continuing"; fi
done

log "done. Make sure $BIN is on your PATH:"
echo "   echo 'export PATH=\$HOME/.local/bin:\$PATH' >> ~/.bashrc"
