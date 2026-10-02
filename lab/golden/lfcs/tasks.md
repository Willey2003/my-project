# LFCS practice tasks (Ubuntu 24.04)

30 tasks on `lfcs1` (192.168.60.11) and `lfcs2` (192.168.60.12). Work as root (`sudo -i`).
Each task has a **Check** command: run it after the task and again after `reboot`. Anything that
does not survive a reboot scores zero. `sudo /lfcs/check.sh` grades the tasks marked `[auto]`.
Spare disks are `/dev/sdb`, `/dev/sdc`, `/dev/sdd` (`vdb`..`vdd` on libvirt); spare NICs are `enp0s9`, `enp0s10`.
Guide: `study-guides/29-lfcs.md`. Timebox: 6 minutes per task.

## Networking and packages (study week G1)
1. `[auto]` lfcs1: create `/etc/netplan/60-lfcs.yaml` (mode 600) that adds `192.168.60.21/24` to `enp0s8` alongside the existing address.
   Check: `ip -br a show enp0s8 | grep 192.168.60.21 && stat -c %a /etc/netplan/60-lfcs.yaml`
2. lfcs1: set DNS for `enp0s8` to `9.9.9.9` with search domain `lab.example.com` via netplan (not by editing resolv.conf).
   Check: `resolvectl dns enp0s8; resolvectl domain enp0s8`
3. lfcs2: add `lfcs1-alias` for 192.168.60.11 so it resolves locally.
   Check: `getent hosts lfcs1-alias`
4. `[auto]` lfcs1: enable ufw with default deny incoming, allow OpenSSH, and allow TCP 80 only from 192.168.60.0/24.
   Check: `ufw status verbose | grep -E 'Status: active|80/tcp'`
5. lfcs1: allow TCP 2049 (NFS) from 192.168.60.12 only; delete any rule opening 23/tcp.
   Check: `ufw status numbered`
6. lfcs1: install `apparmor-utils` and put the `usr.sbin.tcpdump` profile in complain mode.
   Check: `aa-status | sed -n '/complain mode/,/^[0-9]/p' | grep tcpdump`
7. `[auto]` lfcs1: install `nginx` and hold it so upgrades skip it.
   Check: `apt-mark showhold | grep -x nginx`
8. lfcs1: write the name of the package that owns `/usr/bin/ss` to `/root/ss-pkg.txt`.
   Check: `cat /root/ss-pkg.txt   # iproute2`

## Storage (study week G2)
9. `[auto]` lfcs1: VG `vg_lfcs` on `/dev/sdb`, LV `lv_data` 500 MiB, ext4, mounted on `/data` via fstab.
   Check: `lvs vg_lfcs/lv_data && findmnt /data && grep /data /etc/fstab`
10. lfcs1: grow `lv_data` to 800 MiB with its filesystem, online.
    Check: `lvs --units m vg_lfcs/lv_data; df -h /data`
11. `[auto]` lfcs2: RAID 1 `/dev/md0` from `/dev/sdb` and `/dev/sdc`, recorded in `/etc/mdadm/mdadm.conf`, ext4 on `/raid` at boot.
    Check: `cat /proc/mdstat; grep md0 /etc/mdadm/mdadm.conf; findmnt /raid`
12. lfcs2: fail `/dev/sdc` in `md0`, remove it, add `/dev/sdd`, wait for resync.
    Check: `mdadm --detail /dev/md0 | grep -E 'State|sdd'`
13. `[auto]` lfcs1: add a 512 MiB swap file `/swapfile` that is active after reboot.
    Check: `swapon --show | grep /swapfile && grep swapfile /etc/fstab`
14. lfcs1: export `/srv/nfs/share` rw to 192.168.60.0/24. lfcs2: mount it on `/mnt/share` at boot (`_netdev`).
    Check (lfcs2): `findmnt /mnt/share && touch /mnt/share/probe`
15. lfcs1: enable user quotas on `/data`; `alice` gets soft 100 MiB, hard 120 MiB.
    Check: `repquota -s /data | grep alice`

## Users, groups, permissions (study week G2)
16. `[auto]` lfcs1: group `ops`; users `alice` and `bob` (bash shell, home dirs) with `ops` as a supplementary group; `alice` is also in `sudo`.
    Check: `id alice; id bob`
17. lfcs1: `bob` may run only `systemctl restart nginx` as root; `alice` password max age 60 days; `alice` limited to 50 processes.
    Check: `sudo -l -U bob; chage -l alice | grep Maximum; grep alice /etc/security/limits.d/*`
18. lfcs1: `/srv/ops` group `ops`, mode 2770; `bob` has only read and execute through an ACL; new files get the same ACL by default.
    Check: `stat -c '%A %G' /srv/ops; getfacl -p /srv/ops`

## Operations (study weeks G2 and G3)
19. `[auto]` lfcs1: as `alice`, run `/usr/local/bin/backup.sh` at 02:30 Monday to Friday via cron.
    Check: `crontab -l -u alice`
20. `[auto]` lfcs1: `cleanup.timer` runs `cleanup.service` (oneshot, `find /tmp -mtime +7 -delete`) daily with `Persistent=true`.
    Check: `systemctl is-enabled cleanup.timer; systemctl list-timers cleanup.timer`
21. `[auto]` lfcs1: persistently enable IPv4 forwarding and set `vm.swappiness=10` in `/etc/sysctl.d/`.
    Check: `sysctl net.ipv4.ip_forward vm.swappiness`
22. `[auto]` lfcs2: SSH hardening in `/etc/ssh/sshd_config.d/00-hardening.conf`: no root login, no password auth, `MaxAuthTries 3`. Keep key login working.
    Check: `sshd -T | grep -Ei '^(permitrootlogin|passwordauthentication|maxauthtries)'`
23. lfcs2: bond `bond0` (active-backup) from `enp0s9` + `enp0s10` with 192.168.61.22/24 (do the same on lfcs1 with .21 and ping across).
    Check: `grep -E 'Mode|Slave Interface' /proc/net/bonding/bond0; ping -c2 192.168.61.21`
24. lfcs1: bridge `br0` with 10.10.10.1/24 and no member ports (a KVM host bridge).
    Check: `ip -br a show br0; bridge link`
25. `[auto]` lfcs1: nftables: forward TCP 9090 on lfcs1 to 192.168.60.12:8080 with masquerade, persisted in `/etc/nftables.conf`.
    Check (from your host, with task 28 done on lfcs2): `curl -sI http://192.168.60.11:9090 | head -1`
26. lfcs1: nginx reverse proxy on port 80 load balancing `192.168.60.11:8080` and `192.168.60.12:8080`.
    Check: `nginx -t && for i in 1 2 3 4; do curl -s localhost | head -1; done`
27. lfcs2: HAProxy on port 8081 round-robin to the same two backends, with health checks.
    Check: `haproxy -c -f /etc/haproxy/haproxy.cfg && curl -sI localhost:8081 | head -1`
28. `[auto]` lfcs1 and lfcs2: docker container `web` from `nginx:1.27` on host port 8080, restart policy `always` (these are the backends for tasks 25-27).
    Check: `docker inspect -f '{{.HostConfig.RestartPolicy.Name}} {{.State.Status}}' web`
29. lfcs1: install KVM/libvirt, define a VM `tiny` from a cirros qcow2 image, make it autostart, then shut it down.
    Check: `virsh dominfo tiny | grep -E 'State|Autostart'`
30. `[auto]` lfcs1: Git repo `/opt/configs` with `nginx.conf` committed and tag `v1`.
    Check: `git -C /opt/configs log --oneline; git -C /opt/configs tag`
