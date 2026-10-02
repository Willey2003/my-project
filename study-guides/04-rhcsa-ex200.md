# Phase 4 - RHCSA (EX200, RHEL 10)

**Plan weeks:** 9-12 · **Hours:** 42 · **Exam:** 2.5 h, 100% hands-on, ~USD 550 · **Lab:** node1/node2 VMs, `lab/linux/rhcsa-practice.md`

EX200 moved to RHEL 10 in May 2026. Use RH134 (RHEL 9) as the concept reference but practise on RHEL 10 / AlmaLinux 10. **Check the live objectives page before booking**: https://www.redhat.com/en/services/certification/rhcsa

| Week | Focus | Deliverable |
|---|---|---|
| 9 | Install, user/group admin, SELinux contexts & booleans | Practice lab #1 |
| 10 | Storage (LVM/partitions), boot/GRUB2, targets | Practice lab #2 |
| 11 | nmcli networking, Podman basics, firewalld zones | Practice lab #3 |
| 12 | Timed mocks, sit exam | RHCSA |

## The exam in one paragraph
You get a couple of VMs and a task list. No internet; `man`, `--help`, `/usr/share/doc` are allowed. The grader checks the *end state after reboot*. Anything not persistent (runtime-only firewall rule, `mount` without fstab, `setenforce` instead of config, `chcon` instead of `semanage fcontext`) scores zero. Budget ~6-8 min per task and reboot-test twice.

## Must-know areas and the commands
**Essential tools:** redirection (`> >> 2>&1 |`), `grep -E`, `find`, `tar -czf/-xJf`, `ln -s`, permissions, `man -k`.

**Boot & recovery**
```bash
# Root password reset: at GRUB press e, append  rd.break  (or init=/bin/bash) to the linux line, Ctrl-x
mount -o remount,rw /sysroot ; chroot /sysroot ; passwd root ; touch /.autorelabel ; exit ; exit
systemctl get-default ; systemctl set-default multi-user.target
grubby --update-kernel=ALL --args="console=ttyS0" ; grubby --default-kernel
```
**SELinux** (the #1 point-loser)
```bash
getenforce ; sestatus ; vi /etc/selinux/config          # persistent mode
ls -Z /var/www/html ; ps -eZ | grep httpd
semanage fcontext -a -t httpd_sys_content_t '/web(/.*)?' ; restorecon -Rv /web
semanage port -a -t http_port_t -p tcp 82 ; semanage port -l | grep http
getsebool -a | grep httpd ; setsebool -P httpd_enable_homedirs on
ausearch -m AVC -ts recent ; sealert -a /var/log/audit/audit.log
```
Mental model: process domain (e.g. `httpd_t`) may only access object types allowed by policy. Fix labels with `semanage fcontext` + `restorecon`, ports with `semanage port`, optional behaviours with booleans. Never "fix" by disabling SELinux.

**Storage:** partitions (`parted /dev/sdb mklabel gpt mkpart primary 1MiB 513MiB`), LVM with specific extent size, `lvextend -r`, swap on LV or partition, fstab with UUID. Autofs (NFS home dirs): `/etc/auto.master.d/home.autofs` -> `/rhome /etc/auto.rhome`, map `* -rw,sync nfsserver:/rhome/&`.

**Networking:** `nmcli` static IPv4/IPv6, hostname, `/etc/hosts`, firewalld permanent rules, `chronyc sources`.

**Software:** repo files, `dnf install/group install/module`, flatpak may appear on RHEL 10 objectives - check.

**Users & security:** users, groups, password aging (`/etc/login.defs` for defaults), sudo via `/etc/sudoers.d`, SSH key auth, `umask` for a user in `~/.bashrc`.

**Scheduling & tuning:** `crontab -e -u natasha`, systemd timers, `at`; `tuned-adm recommend/profile`, `nice/renice`, journald persistence.

**Containers (Podman):**
```bash
podman login registry.redhat.io ; podman search httpd ; podman pull registry.access.redhat.com/ubi9/httpd-24
podman run -d --name web -p 8080:8080 -v ~/web:/var/www/html:Z ubi9/httpd-24
# Start at boot as a normal user (Quadlet - replaces 'podman generate systemd'):
mkdir -p ~/.config/containers/systemd
cat > ~/.config/containers/systemd/web.container <<'EOF'
[Container]
Image=registry.access.redhat.com/ubi9/httpd-24
PublishPort=8080:8080
Volume=%h/web:/var/www/html:Z
[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload ; systemctl --user start web ; loginctl enable-linger $USER
```
Note: log in as the user via `ssh user@localhost`, not `su -`, or `systemctl --user` has no session bus.

## 4-week drill routine
- Days 1-4 of each week: learn + lab the week's objectives (see schedule).
- Every session: 15-min "speed round" from `lab/linux/rhcsa-practice.md` (random 3 tasks, stopwatch).
- Week 12: two full 2.5 h mocks (Mock 1 and Mock 2), destroy/recreate VMs between them (`vagrant destroy -f node1 node2 && vagrant up node1 node2`). Book the exam only when you finish a mock with 30 min spare.

## Self-check
1. httpd serves from `/srv/site` but returns 403. Fix permanently.
2. Make `/dev/vg0/data` mount at `/data` after reboot and verify without rebooting.
3. Set user `sarah` to have no interactive login.
4. Rootless container must start at boot even if nobody logs in. Two requirements?
5. How do you find which package provides `/usr/sbin/semanage`?

<details><summary>Answers</summary>

1. `semanage fcontext -a -t httpd_sys_content_t '/srv/site(/.*)?'` + `restorecon -Rv /srv/site` (plus Unix perms / `DocumentRoot` config).
2. fstab line with UUID from `blkid`, then `mount -a` and `findmnt --verify`.
3. `usermod -s /sbin/nologin sarah` (or create with `-s /sbin/nologin`).
4. A user unit with `WantedBy=default.target` (Quadlet `[Install]`) and `loginctl enable-linger user`.
5. `dnf provides /usr/sbin/semanage` (policycoreutils-python-utils).
</details>

## Resources
RH134 (primary), RH124 (concepts only), https://developers.redhat.com/rhel10 (free RHEL subscription), `man semanage-fcontext`, `man nmcli-examples`, `man podman-systemd.unit`
