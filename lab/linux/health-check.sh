#!/usr/bin/env bash
# Week 5 deliverable starter: server health check with functions, arrays, traps and thresholds.
# Usage: ./health-check.sh [-j] [-w disk_warn%] ; exit code 0=ok 1=warn 2=crit
set -Eeuo pipefail

DISK_WARN=80; DISK_CRIT=90; LOAD_FACTOR=1.5; JSON=0
SERVICES=(sshd chronyd firewalld)
declare -a PROBLEMS=()
STATUS=0

trap 'echo "error on line $LINENO" >&2; exit 3' ERR
trap 'rm -f "${TMPF:-}"' EXIT
TMPF=$(mktemp)

while getopts "jw:" opt; do
  case $opt in j) JSON=1 ;; w) DISK_WARN=$OPTARG ;; *) echo "usage: $0 [-j] [-w pct]"; exit 64 ;; esac
done

raise() { # level message
  PROBLEMS+=("$1: $2")
  [ "$1" = CRIT ] && STATUS=2
  [ "$1" = WARN ] && [ $STATUS -lt 1 ] && STATUS=1
  return 0
}

check_disk() {
  df -P -x tmpfs -x devtmpfs | awk 'NR>1 {gsub("%","",$5); print $6, $5}' > "$TMPF"
  while read -r mnt pct; do
    if   [ "$pct" -ge "$DISK_CRIT" ]; then raise CRIT "disk $mnt at ${pct}%"
    elif [ "$pct" -ge "$DISK_WARN" ]; then raise WARN "disk $mnt at ${pct}%"; fi
  done < "$TMPF"
}

check_load() {
  local cores load1 limit
  cores=$(nproc); load1=$(cut -d' ' -f1 /proc/loadavg)
  limit=$(awk -v c="$cores" -v f="$LOAD_FACTOR" 'BEGIN{print c*f}')
  awk -v l="$load1" -v m="$limit" 'BEGIN{exit !(l>m)}' && raise WARN "load $load1 > $limit"
  return 0
}

check_mem() {
  local avail_pct
  avail_pct=$(awk '/MemTotal/{t=$2}/MemAvailable/{a=$2}END{printf "%d", a*100/t}' /proc/meminfo)
  [ "$avail_pct" -lt 10 ] && raise CRIT "memory available ${avail_pct}%"
  return 0
}

check_services() {
  local s
  [ -d /run/systemd/system ] || { raise WARN "systemd not running - service checks skipped"; return 0; }
  for s in "${SERVICES[@]}"; do
    systemctl is-active --quiet "$s" 2>/dev/null || raise CRIT "service $s not active"
  done
}

check_failed_units() {
  [ -d /run/systemd/system ] || return 0
  local n; n=$( { systemctl --failed --no-legend 2>/dev/null || true; } | wc -l)
  [ "$n" -gt 0 ] && raise WARN "$n failed systemd unit(s)"
  return 0
}

check_disk; check_load; check_mem; check_services; check_failed_units

if [ $JSON -eq 1 ]; then
  printf '{"host":"%s","status":%d,"problems":[' "$(hostname)" "$STATUS"
  for i in "${!PROBLEMS[@]}"; do printf '%s"%s"' "$([ "$i" -gt 0 ] && echo ,)" "${PROBLEMS[$i]}"; done
  echo ']}'
else
  echo "$(date -Is) $(hostname) status=$STATUS"
  for p in "${PROBLEMS[@]}"; do echo "  - $p"; done
fi
exit $STATUS
