# RHCSA (EX200, RHEL 10) practice tasks

Do these on node1/node2 with a 2.5 h timer, no internet, only `man`, `--help` and `/usr/share/doc`.
Reboot at the end: anything that does not survive a reboot scores zero.

## Mock 1
1. Reset the root password of node2 from the GRUB menu (`rd.break` or `init=/bin/bash`), keep SELinux working (`touch /.autorelabel` or `load_policy`/`restorecon`).
2. Configure node1 networking with nmcli: static 192.168.56.21/24, gw 192.168.56.1, DNS 192.168.56.1, hostname `servera.lab.example.com`, keep the old address too.
3. Create a yum/dnf repo file pointing at `http://content.example.com/rhel10/BaseOS` (practice the syntax even if the URL is fake).
4. Users: `harry`, `natasha` (secondary group `sysmgrs`), `sarah` with no interactive shell. All passwords `flectrag`.
5. Create `/common/admin` owned by group `sysmgrs`, rwx for group, no access for others, setgid.
6. cron: as natasha, log "EX200 in progress" via `logger` every 2 minutes.
7. httpd on port 82: fix SELinux (`semanage port -a -t http_port_t -p tcp 82`) and firewall.
8. Find all files owned by harry and copy them to `/root/findfiles` preserving attributes.
9. Find lines containing `ich` in `/usr/share/dict/words` (or any text file) and save to `/root/lines`.
10. Create a 512 MiB LV `database` in VG `datastore` with 16 MiB extents; mount on `/mnt/database` as ext3 via fstab.
11. Resize an existing LV to between 290 and 330 MiB without losing data.
12. Add 512 MiB swap persistently without removing existing swap.
13. Set tuned to the recommended profile.
14. Run a rootless Podman container as user `student` that starts at boot via a systemd user unit (Quadlet `.container` file in `~/.config/containers/systemd/`, then `loginctl enable-linger student`).
15. Configure chrony to use `classroom.example.com` as time source.
16. Autofs: mount `/netdir/remoteuser` from an NFS export on control (set up the NFS export yourself first).

## Mock 2 (troubleshooting focus)
- A service fails to start because of an SELinux file context on a custom docroot - fix with `semanage fcontext` + `restorecon`, never `chcon` alone.
- A boot hangs because of a bad fstab line - recover from emergency mode.
- Default target should be multi-user; set and verify.
- Journald must persist logs across reboots (`Storage=persistent`).
- Set kernel parameter `vm.swappiness=10` persistently.
