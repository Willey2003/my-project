#!/usr/bin/env bash
# OpenShift Local (CRC) helper for weeks 36-44 and 51-52.
# Needs: 4 vCPU, 10.5 GiB free RAM minimum (give it 16 GiB for OADP/RHACS labs), 35 GiB disk, KVM/Hyper-V/macOS HVF.
# 1) Download crc + your pull secret (free Red Hat Developer account):
#    https://console.redhat.com/openshift/create/local
# 2) ./crc.sh setup ; ./crc.sh start ; eval "$(crc oc-env)"
# Too heavy for your laptop? Use the free Developer Sandbox (https://developers.redhat.com/developer-sandbox)
# for DO188/DO280 app-level work; cluster-admin tasks (OAuth, MachineConfig, OADP) need CRC or a cloud cluster.
set -euo pipefail
command -v crc >/dev/null || { echo "install crc first (see header)"; exit 1; }
case "${1:-status}" in
  setup)
    crc config set cpus 6
    crc config set memory 16384
    crc config set disk-size 60
    crc config set enable-cluster-monitoring true   # needed for DO380 monitoring labs
    crc setup ;;
  start)
    crc start -p "${PULL_SECRET:-$HOME/pull-secret.txt}"
    crc console --credentials ;;
  stop)   crc stop ;;
  status) crc status ;;
  delete) crc delete -f ;;
esac
