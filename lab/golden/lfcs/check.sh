#!/usr/bin/env bash
# Read-only grader for the [auto] tasks in tasks.md. It never changes system state.
#   sudo /lfcs/check.sh            # grades the tasks for this host (lfcs1 or lfcs2)
#   sudo /lfcs/check.sh all        # grades every [auto] task regardless of host
#   sudo /lfcs/check.sh 9 21       # grades only the listed task numbers
# Exit code: 0 if every graded task passed, 1 otherwise.
set -uo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "run as root (sudo) - ufw, sshd -T and crontab -l -u need it" >&2
  exit 2
fi

pass=0 fail=0
green=$'\e[32m' red=$'\e[31m' dim=$'\e[2m' off=$'\e[0m'
[[ -t 1 ]] || { green='' red='' dim='' off=''; }

# result <task> <description> <command...>: runs a read-only test, prints PASS/FAIL
result() {
  local n=$1 desc=$2; shift 2
  if "$@" >/dev/null 2>&1; then
    printf '%sPASS%s  %2s  %s\n' "$green" "$off" "$n" "$desc"; pass=$((pass + 1))
  else
    printf '%sFAIL%s  %2s  %s\n' "$red" "$off" "$n" "$desc"; fail=$((fail + 1))
  fi
}
have() { command -v "$1" >/dev/null 2>&1; }

# ---- individual checks (each returns 0 on pass) -----------------------------
t1()  { local f=/etc/netplan/60-lfcs.yaml
        [[ -f $f ]] && [[ $(stat -c %a "$f") == 600 ]] && grep -q '192.168.60.21/24' "$f" \
          && ip -br addr show enp0s8 | grep -q '192.168.60.21/'; }
t4()  { have ufw || return 1
        local s; s=$(ufw status verbose)
        grep -q '^Status: active' <<<"$s" && grep -q 'deny (incoming)' <<<"$s" \
          && grep -Eq '^(OpenSSH|22/tcp)[[:space:]]+ALLOW IN[[:space:]]+Anywhere' <<<"$s" \
          && grep -Eq '^80/tcp[[:space:]]+ALLOW IN[[:space:]]+192\.168\.60\.0/24' <<<"$s"; }
t7()  { dpkg-query -W -f='${Status}' nginx 2>/dev/null | grep -q 'install ok installed' \
          && apt-mark showhold | grep -qx nginx; }
t9()  { lvs vg_lfcs/lv_data >/dev/null 2>&1 \
          && [[ $(findmnt -n -o FSTYPE /data) == ext4 ]] \
          && awk '$2 == "/data" && $1 !~ /^#/' /etc/fstab | grep -q .; }
t11() { grep -q '^md0 : active raid1' /proc/mdstat \
          && grep -Eq '^ARRAY /dev/md(/)?0' /etc/mdadm/mdadm.conf \
          && findmnt -n /raid >/dev/null && awk '$2 == "/raid" && $1 !~ /^#/' /etc/fstab | grep -q .; }
t13() { swapon --show=NAME --noheadings | grep -qx /swapfile \
          && [[ $(stat -c %a /swapfile) == 600 ]] \
          && awk '$1 == "/swapfile" && $3 == "swap"' /etc/fstab | grep -q .; }
t16() { getent group ops >/dev/null \
          && id -nG alice | grep -qw ops && id -nG alice | grep -qw sudo \
          && id -nG bob | grep -qw ops \
          && [[ $(getent passwd alice | cut -d: -f7) == */bash ]] && [[ -d $(getent passwd bob | cut -d: -f6) ]]; }
t19() { crontab -l -u alice 2>/dev/null \
          | grep -Eq '^[[:space:]]*30[[:space:]]+2[[:space:]]+\*[[:space:]]+\*[[:space:]]+(1-5|mon-fri)[[:space:]]+/usr/local/bin/backup\.sh'; }
t20() { [[ $(systemctl is-enabled cleanup.timer 2>/dev/null) == enabled ]] \
          && systemctl is-active --quiet cleanup.timer \
          && systemctl cat cleanup.timer 2>/dev/null | grep -Eq '^Persistent=(true|yes)' \
          && systemctl cat cleanup.service 2>/dev/null | grep -q '^Type=oneshot'; }
t21() { [[ $(sysctl -n net.ipv4.ip_forward) == 1 ]] && [[ $(sysctl -n vm.swappiness) == 10 ]] \
          && grep -Rhsq '^[[:space:]]*net\.ipv4\.ip_forward[[:space:]]*=[[:space:]]*1' /etc/sysctl.d/ \
          && grep -Rhsq '^[[:space:]]*vm\.swappiness[[:space:]]*=[[:space:]]*10' /etc/sysctl.d/; }
t22() { [[ -f /etc/ssh/sshd_config.d/00-hardening.conf ]] || return 1
        local s; s=$(sshd -T 2>/dev/null) || return 1
        grep -qx 'permitrootlogin no' <<<"$s" && grep -qx 'passwordauthentication no' <<<"$s" \
          && grep -qx 'maxauthtries 3' <<<"$s"; }
t25() { have nft || return 1
        systemctl is-enabled --quiet nftables \
          && grep -Eq 'dport 9090 .*dnat (ip )?to 192\.168\.60\.12:8080' /etc/nftables.conf \
          && grep -q masquerade /etc/nftables.conf \
          && nft list ruleset 2>/dev/null | grep -Eq 'dport 9090 .*dnat (ip )?to 192\.168\.60\.12:8080'; }
t28() { have docker || return 1
        [[ $(docker inspect -f '{{.HostConfig.RestartPolicy.Name}} {{.State.Status}}' web 2>/dev/null) == "always running" ]] \
          && docker port web 80/tcp 2>/dev/null | grep -q ':8080$'; }
t30() { [[ -d /opt/configs/.git ]] \
          && git -c safe.directory=/opt/configs -C /opt/configs ls-files --error-unmatch nginx.conf \
          && git -c safe.directory=/opt/configs -C /opt/configs rev-parse -q --verify refs/tags/v1; }

declare -A DESC=(
  [1]="netplan 60-lfcs.yaml (mode 600) adds 192.168.60.21/24"
  [4]="ufw active, deny incoming, OpenSSH + 80/tcp from 192.168.60.0/24"
  [7]="nginx installed and held"
  [9]="vg_lfcs/lv_data ext4 on /data via fstab"
  [11]="md0 RAID1 active, in mdadm.conf, mounted on /raid via fstab"
  [13]="/swapfile active, mode 600, in fstab"
  [16]="group ops; alice (ops,sudo, bash) and bob (ops, home)"
  [19]="alice crontab: 30 2 * * 1-5 /usr/local/bin/backup.sh"
  [20]="cleanup.timer enabled+active, Persistent, oneshot service"
  [21]="ip_forward=1 and swappiness=10, persisted in sysctl.d"
  [22]="sshd: no root login, no password auth, MaxAuthTries 3"
  [25]="nftables DNAT 9090 -> 192.168.60.12:8080 + masquerade, persisted"
  [28]="docker 'web' running, restart=always, port 8080"
  [30]="/opt/configs git repo with nginx.conf and tag v1"
)
HOST1=(1 4 7 9 13 16 19 20 21 25 28 30)
HOST2=(11 22 28)

if [[ $# -eq 0 ]]; then
  case $(hostname -s) in
    lfcs1) tasks=("${HOST1[@]}") ;;
    lfcs2) tasks=("${HOST2[@]}") ;;
    *) echo "unknown host $(hostname -s); pass 'all' or task numbers" >&2; exit 2 ;;
  esac
elif [[ $1 == all ]]; then
  tasks=(1 4 7 9 11 13 16 19 20 21 22 25 28 30)
else
  tasks=("$@")
fi

echo "${dim}LFCS lab check on $(hostname -s) - read-only${off}"
for n in "${tasks[@]}"; do
  if [[ -z ${DESC[$n]:-} ]]; then
    printf 'SKIP  %2s  not auto-graded - use the Check line in tasks.md\n' "$n"; continue
  fi
  result "$n" "${DESC[$n]}" "t$n"
done
echo "${dim}---${off}"
echo "passed $pass / $((pass + fail))"
[[ $fail -eq 0 ]]
