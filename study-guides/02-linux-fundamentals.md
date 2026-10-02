# Phase 2 - Linux Fundamentals

**Plan weeks:** 2-5 · **Hours:** 42 · **Cert:** none (foundation for RHCSA) · **Lab:** `./lab.sh vms up` (node1/node2), `lab/linux/`

| Week | Focus | Deliverable |
|---|---|---|
| 2 | Filesystem hierarchy, users/groups, permissions & ACLs, packages | Bash cheatsheet + permissions lab repo |
| 3 | systemd units/timers, journald, cron, processes | Custom systemd service + timer |
| 4 | Partitioning, LVM, ext4/xfs, mounting, fstab, quotas | LVM resize lab write-up |
| 5 | Shell scripting: functions, arrays, traps, sed/awk/regex | Server health-check script (GitHub) |

## Week 2 - Filesystem, users, permissions, packages
**FHS:** `/etc` config, `/var` variable data (logs, spool, lib), `/usr` read-only programs, `/opt` add-on software, `/srv` served data, `/run` runtime (tmpfs), `/proc` & `/sys` kernel interfaces, `/home`, `/root`, `/tmp` (sticky).

**Users/groups:** `/etc/passwd` (name:x:UID:GID:GECOS:home:shell), `/etc/shadow` (hashes, aging), `/etc/group`. UID 0 = root, 1-999 system, 1000+ humans. Primary group vs supplementary groups.
```bash
useradd -m -G wheel -s /bin/bash alice ; passwd alice ; usermod -aG devs alice   # -a or you REPLACE groups
chage -M 90 -W 7 alice ; chage -l alice ; id alice ; groups alice
visudo -f /etc/sudoers.d/alice      # alice ALL=(root) /usr/bin/systemctl restart httpd
```
**Permissions:** `rwx` for user/group/other; on directories `x` = enter, `r` = list, `w` = create/delete entries. Octal: r=4 w=2 x=1. `umask 022` -> files 644, dirs 755.
Special bits: **setuid** (4xxx, run as file owner, e.g. `passwd`), **setgid** on dir (2xxx, new files inherit group - shared team dirs), **sticky** (1xxx, only owner deletes - `/tmp`).
**ACLs:** `setfacl -m u:bob:rw file`, `setfacl -d -m g:auditors:rx dir` (default ACL for new files), `getfacl`. A `+` after the mode in `ls -l` means an ACL exists. The ACL *mask* caps group/named entries.
**Packages:** RHEL: `dnf install/remove/search/provides/history/module`, repos in `/etc/yum.repos.d/*.repo`; `rpm -qa`, `rpm -qf /path`, `rpm -ql pkg`. Ubuntu: `apt`, `dpkg -S`.

## Week 3 - Processes, systemd, logging, scheduling
- Processes: PID, PPID, states (R, S, D uninterruptible IO, Z zombie, T stopped). `ps aux`, `ps -ef --forest`, `top`/`htop`, `pgrep -a`, `kill -15` (polite) vs `-9` (cannot be caught), `nice`/`renice`.
- **systemd:** units (`.service`, `.socket`, `.timer`, `.target`, `.mount`). Files: vendor `/usr/lib/systemd/system`, admin overrides `/etc/systemd/system` (wins), drop-ins via `systemctl edit unit`.
  ```bash
  systemctl status|start|stop|restart|reload|enable --now|disable|mask sshd
  systemctl list-units --failed ; systemctl list-timers ; systemctl cat sshd ; systemd-analyze blame
  systemctl get-default ; systemctl set-default multi-user.target ; systemctl isolate rescue.target
  ```
  Service types: `simple` (default), `exec`, `forking`, `oneshot` (scripts), `notify`. `Restart=on-failure`, `RestartSec=5`.
- **journald:** `journalctl -u sshd -f`, `-b -1` (previous boot), `-p err`, `--since "1 hour ago"`, `-o json-pretty`. Persist logs: `Storage=persistent` in `/etc/systemd/journald.conf` (or create `/var/log/journal`).
- **Timers vs cron:** timers log to the journal, support `Persistent=true` (catch up missed runs) and randomised delays. Cron: `crontab -e`, `/etc/cron.d/`, syntax `m h dom mon dow cmd`. `at` for one-offs.
- Lab: `lab/linux/health-check.{sh,service,timer}` - install, enable, then read `systemd-analyze security health-check`.

## Week 4 - Storage
- Disks -> partitions (GPT via `gdisk`/`parted`, MBR via `fdisk`) -> filesystems, or disks -> **LVM**: PV (`pvcreate`) -> VG (`vgcreate -s 16M`) -> LV (`lvcreate -L 1G` or `-l 50` extents or `-l 100%FREE`).
- Filesystems: **xfs** (RHEL default, grows online, cannot shrink), **ext4** (grows and shrinks - shrink offline). `mkfs.xfs`, `mkfs.ext4`, `xfs_growfs`, `resize2fs`; easiest: `lvextend -r -L +300M /dev/vg/lv` (resizes the fs too).
- Mounting: `mount`, `findmnt`, `lsblk -f`, `blkid`. `/etc/fstab`: `UUID=... /data xfs defaults 0 0`. Always test with `mount -a` and `findmnt --verify` **before** rebooting; a bad fstab line drops you into emergency mode (`nofail` protects non-critical mounts).
- Swap: `mkswap`, `swapon`, fstab `swap defaults 0 0`.
- Quotas: xfs mount option `uquota`/`gquota`; `xfs_quota -x -c 'limit bsoft=100m bhard=120m alice' /data`.
- Lab: `sudo lab/linux/lvm-lab.sh setup` (loop devices) and its 8 exercises; write the LVM resize write-up as the deliverable.

## Week 5 - Shell scripting
Script skeleton that you should be able to write from memory:
```bash
#!/usr/bin/env bash
set -Eeuo pipefail            # exit on error, unset vars, pipeline failures
trap 'echo "failed at line $LINENO" >&2' ERR
trap 'rm -f "$tmp"' EXIT
tmp=$(mktemp)
usage() { echo "usage: $0 -f file" >&2; exit 64; }
while getopts "f:h" o; do case $o in f) file=$OPTARG ;; *) usage ;; esac; done
: "${file:?-f required}"
declare -a hosts=(web1 web2) ; declare -A port=([web]=80 [db]=5432)
for h in "${hosts[@]}"; do printf '%s\n' "$h"; done
[[ $file =~ \.log$ ]] && echo "log file"
```
- Quoting: always `"$var"`; `$(...)` not backticks; `[[ ]]` for tests in bash.
- Text tools: `grep -E`, `sed -E 's/old/new/g'`, `sed -n '10,20p'`, `awk -F: '$3>=1000 {print $1}' /etc/passwd`, `cut`, `sort | uniq -c | sort -rn`, `xargs -P4`, `find / -user alice -exec cp -a {} /root/found \;`.
- Exit codes: 0 ok, non-zero error; `$?`; `cmd || handle`; `set -e` pitfalls (functions in `if`, pipelines).
- Deliverable: extend `lab/linux/health-check.sh` (JSON output, thresholds from a config file, cert expiry check with `openssl x509 -enddate`), push to GitHub with a README.

## Self-check
1. Why can user bob delete a file he cannot read?
2. What happens with `usermod -G devs alice` (no `-a`)?
3. A service starts manually but not at boot. Two things to check?
4. xfs LV is full: exact commands to add 2 GiB?
5. What does `set -o pipefail` change for `grep foo file | wc -l`?

<details><summary>Answers</summary>

1. Deletion is a write on the *directory*, not the file (unless the sticky bit is set).
2. Alice is removed from every other supplementary group.
3. `systemctl is-enabled` and the unit's `WantedBy=`/target; also dependency ordering/`After=network-online.target`.
4. `vgs` (check free extents; `vgextend` with a new PV if needed) then `lvextend -r -L +2G /dev/vg/lv`.
5. The pipeline's status becomes grep's failure (1) if no match, instead of wc's 0.
</details>

## Resources
- linux-for-devops.pdf (primer), https://linuxjourney.com, https://killercoda.com (free browser Linux)
- `man 5 systemd.service`, `man 5 fstab`, `man 7 lvm`, `man bash` (section "Parameter Expansion")
