# Golden Kubestronaut - LFCS: Linux Foundation Certified System Administrator

**Plan weeks:** G1-G4 (Golden Kubestronaut track) · **Hours:** 40 · **Exam:** 2 h, performance-based, Ubuntu, ~USD 445 (look for LF coupons), 2 killer.sh sessions included · **Lab:** `lab/golden/lfcs/` (2 x Ubuntu 24.04 VMs)

You already hold RHCSA, so this guide is the **delta**: the same admin skills on Ubuntu, plus topics RHCSA never asks (RAID, reverse proxies, NAT, bonding/bridging, virsh, Git). Do not re-study what `04-rhcsa-ex200.md` covers; re-map it.

| Week | Focus | Deliverable |
|---|---|---|
| G1 | Ubuntu delta: apt/dpkg, netplan, ufw, AppArmor, systemd-resolved | `lab/golden/lfcs` tasks 1-8 pass `check.sh` |
| G2 | Storage: LVM, mdadm RAID, NFS, quotas, swap; cron/timers, sysctl | Tasks 9-21 + RAID rebuild write-up |
| G3 | Networking: bonding/bridging, nftables/iptables NAT, HAProxy/nginx, SSH hardening | Tasks 22-27 + reverse-proxy lab |
| G4 | Containers, virsh, Git, killer.sh mocks, sit exam | Tasks 28-30, mock below, LFCS |

## Domains (verify the current curriculum on https://training.linuxfoundation.org/certification/linux-foundation-certified-sysadmin-lfcs/)
| Domain | Weight | Your lab |
|---|---|---|
| Operations Deployment | 25% | packages, AppArmor, cron/timers, sysctl, containers, virsh, Git (tasks 6-8, 19-21, 28-30) |
| Networking | 25% | netplan, resolved, ufw, bond/bridge, NAT, HAProxy/nginx (tasks 1-5, 23-27) |
| Storage | 20% | LVM, mdadm, swap, NFS, quotas (tasks 9-15) |
| Essential Commands | 20% | find/grep/sed/tar, SSH hardening (task 22, and throughout) |
| Users and Groups | 10% | useradd/adduser, sudo, aging, limits, ACLs (tasks 16-18) |

## Exam technique
- Every task names a host: **`ssh` to it first** and check the prompt. Most lost points are "right fix, wrong machine". Use `sudo -i` once per host.
- The grader checks final state, often after a reboot, just like RHCSA: `netplan apply` plus a file in `/etc/netplan/`, `sysctl` plus a file in `/etc/sysctl.d/`, `ufw` rules (persist by default), fstab entries, and `systemctl enable`.
- Docs you can use: `man`, `--help`, `/usr/share/doc/*/examples` (netplan examples live in `/usr/share/doc/netplan*/examples/`). Learn where things are *before* the exam.
- Budget: roughly 20 tasks in 120 min, so about 6 min each. Skip and flag anything over 8 min.
- Verify every answer with one command (`ip -br a`, `ufw status`, `lsblk`, `curl`, `systemctl is-enabled`).
```bash
export EDITOR=vim ; alias ll='ls -alF'
apropos netplan ; man -k raid ; ls /usr/share/doc/netplan*/examples/ 2>/dev/null
```

## Ubuntu vs RHEL cheat table (the core of the delta)
| Area | RHEL (you know) | Ubuntu (exam) |
|---|---|---|
| Packages | `dnf`, `rpm -qf`, `/etc/yum.repos.d/` | `apt`, `dpkg -S`, `/etc/apt/sources.list.d/*.sources` (deb822) |
| Network config | NetworkManager, `nmcli` | netplan YAML -> systemd-networkd (server) |
| Firewall | firewalld zones | ufw (front end to nftables/iptables) |
| MAC | SELinux (labels) | AppArmor (path-based profiles) |
| DNS client | NM writes `/etc/resolv.conf` | systemd-resolved stub `127.0.0.53`, `resolvectl` |
| Admin group | `wheel` | `sudo` (and `adm` for logs) |
| Add user | `useradd -m` | `adduser` (interactive, creates home) or `useradd -m -s /bin/bash` |
| Web server | `httpd`, `/var/www/html` | `apache2`/`nginx`, `sites-available` -> `sites-enabled` |
| Logs | `/var/log/messages`, `secure` | `/var/log/syslog`, `auth.log` (plus journal) |
| Boot loader | `grubby` | edit `/etc/default/grub` then `update-grub` |

### apt/dpkg vs dnf/rpm
```bash
apt update ; apt install -y nginx ; apt remove nginx ; apt purge nginx   # purge also removes config
apt search raid ; apt show mdadm ; apt list --installed | grep nginx
apt-cache policy nginx                # candidate version, which repo; apt-mark hold kubelet
dpkg -l | grep nginx ; dpkg -L nginx ; dpkg -S /usr/sbin/nginx          # = rpm -qa / -ql / -qf
apt-file search bin/ss                # = dnf provides (apt install apt-file ; apt-file update)
dpkg -i pkg.deb ; apt install ./pkg.deb   # second form resolves dependencies
apt install nginx=1.24.0-2ubuntu7     # pin a version ; apt-mark showhold
```
Add a repo the modern way: key in `/etc/apt/keyrings/x.gpg`, then `/etc/apt/sources.list.d/x.sources` with `Types: deb`, `URIs:`, `Suites:`, `Components:`, `Signed-By:`. `add-apt-repository ppa:x/y` still works for PPAs. Never use `apt-key` (deprecated).

### netplan vs nmcli
Files in `/etc/netplan/*.yaml` (mode 600, or netplan warns), rendered to systemd-networkd on servers. `netplan try` auto-reverts after 120 s if you lose SSH; `netplan apply` makes it live; `netplan get`/`netplan status` show the result.
```yaml
# /etc/netplan/60-static.yaml
network:
  version: 2
  ethernets:
    enp0s8:
      dhcp4: false
      addresses: [192.168.60.21/24]
      routes: [{to: default, via: 192.168.60.1}]   # 'gateway4' is deprecated
      nameservers: {addresses: [1.1.1.1, 9.9.9.9], search: [lab.example.com]}
```
```bash
chmod 600 /etc/netplan/60-static.yaml ; netplan generate && netplan try ; netplan apply
ip -br a ; ip r ; networkctl status enp0s8 ; hostnamectl set-hostname web1
```
Gotcha: files are merged in lexical order and a later file wins per key. Cloud images ship `50-cloud-init.yaml`; stop cloud-init rewriting it with `/etc/cloud/cloud.cfg.d/99-disable-network-config.cfg` containing `network: {config: disabled}`.

### systemd-resolved
`/etc/resolv.conf` is a symlink to `/run/systemd/resolve/stub-resolv.conf` (nameserver `127.0.0.53`). Do not edit it; set DNS in netplan (per link) or globally in `/etc/systemd/resolved.conf` (`DNS=`, `FallbackDNS=`, `Domains=`), then `systemctl restart systemd-resolved`.
```bash
resolvectl status ; resolvectl query example.com ; resolvectl dns enp0s8 ; resolvectl flush-caches
```
Static names still go in `/etc/hosts` (checked first per `/etc/nsswitch.conf`).

### ufw vs firewalld
```bash
ufw allow OpenSSH           # BEFORE enabling, or you lock yourself out
ufw enable ; ufw status verbose ; ufw status numbered ; ufw delete 3
ufw default deny incoming ; ufw default allow outgoing
ufw allow 80/tcp ; ufw allow 8000:8010/tcp ; ufw deny 23
ufw allow from 192.168.60.0/24 to any port 22 proto tcp
ufw allow in on enp0s8 to any port 3306 ; ufw limit ssh      # rate-limit brute force
ufw app list ; ufw route allow in on br0 out on enp0s3       # forwarded traffic
```
Rules persist on their own (`/etc/ufw/user.rules`). NAT and port forwarding go in `/etc/ufw/before.rules` (`*nat` table) plus `DEFAULT_FORWARD_POLICY="ACCEPT"` in `/etc/default/ufw`, or do it directly with nftables (below).

### AppArmor vs SELinux
AppArmor confines programs by **path** rules in `/etc/apparmor.d/` (for example `usr.sbin.tcpdump`). No labels, no `restorecon`. Modes are enforce, complain (log only), and disabled.
```bash
aa-status                                   # apt install apparmor-utils for aa-* tools
aa-complain /etc/apparmor.d/usr.sbin.nginx ; aa-enforce /etc/apparmor.d/usr.sbin.nginx
aa-disable /etc/apparmor.d/usr.sbin.nginx   # symlinks the profile into disable/
apparmor_parser -r /etc/apparmor.d/usr.sbin.nginx                  # reload after editing
journalctl -k | grep -i 'apparmor="DENIED"' ; aa-logprof            # build rules from denials
```
Translation: "SELinux denied httpd reading `/srv/site`" becomes "add `/srv/site/** r,` to the nginx profile (or a `local/` include) and reload". Docker applies the `docker-default` profile; `--security-opt apparmor=unconfined` turns it off.

## Storage delta
### LVM (same as RHEL, but ext4 is the Ubuntu default)
```bash
pvcreate /dev/sdb /dev/sdc ; vgcreate vg_data /dev/sdb /dev/sdc ; lvcreate -n lv_app -L 1G vg_data
mkfs.ext4 /dev/vg_data/lv_app ; mkdir /app ; echo "/dev/vg_data/lv_app /app ext4 defaults 0 2" >> /etc/fstab
mount -a ; lvextend -r -L +500M /dev/vg_data/lv_app ; lvreduce -r -L 800M /dev/vg_data/lv_app   # ext4 can shrink
pvmove /dev/sdb ; vgreduce vg_data /dev/sdb          # evacuate a disk
lvcreate -s -n snap -L 200M /dev/vg_data/lv_app      # snapshot ; lvconvert --merge to roll back
```

### RAID with mdadm (not on RHCSA)
```bash
apt install -y mdadm
mdadm --create /dev/md0 --level=1 --raid-devices=2 /dev/sdb /dev/sdc   # --level=5 needs >= 3 disks
cat /proc/mdstat ; mdadm --detail /dev/md0
mdadm --detail --scan >> /etc/mdadm/mdadm.conf ; update-initramfs -u  # persist the array name
mkfs.ext4 /dev/md0 ; echo "UUID=$(blkid -s UUID -o value /dev/md0) /raid ext4 defaults,nofail 0 2" >> /etc/fstab
# Failure drill
mdadm /dev/md0 --fail /dev/sdc ; mdadm /dev/md0 --remove /dev/sdc ; mdadm /dev/md0 --add /dev/sdd
mdadm --grow /dev/md0 --raid-devices=3 --add /dev/sde      # add a member
mdadm --stop /dev/md0 ; mdadm --zero-superblock /dev/sdb   # tear down
```
Levels: 0 stripe (no redundancy), 1 mirror, 5 single parity (n-1 capacity), 6 double parity, 10 mirrored stripes. A spare: `--spare-devices=1`.

### NFS, quotas, swap
```bash
# Server (lfcs1)
apt install -y nfs-kernel-server ; mkdir -p /srv/nfs/share ; chown nobody:nogroup /srv/nfs/share
echo "/srv/nfs/share 192.168.60.0/24(rw,sync,no_subtree_check)" >> /etc/exports
exportfs -ra ; exportfs -v ; ufw allow from 192.168.60.0/24 to any port nfs
# Client (lfcs2)
apt install -y nfs-common ; showmount -e 192.168.60.11
echo "192.168.60.11:/srv/nfs/share /mnt/share nfs defaults,_netdev 0 0" >> /etc/fstab ; mount -a
# Quotas on ext4 (Ubuntu package names differ from RHEL)
apt install -y quota ; # fstab options: defaults,usrquota,grpquota ; then mount -o remount /data
quotacheck -cugm /data ; quotaon -v /data ; setquota -u alice 102400 122880 0 0 /data   # soft/hard in KiB, then inode soft/hard
edquota -u alice ; repquota -s /data ; quota -vs alice
# Swap file (Ubuntu images use /swap.img)
fallocate -l 1G /swapfile ; chmod 600 /swapfile ; mkswap /swapfile ; swapon /swapfile
echo "/swapfile none swap sw 0 0" >> /etc/fstab ; swapon --show ; free -h
```

## Operations delta
### SSH hardening
Drop-in files in `/etc/ssh/sshd_config.d/*.conf` are read first and the **first value wins**, so put yours in `00-hardening.conf`.
```
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AllowUsers alice deploy
MaxAuthTries 3
X11Forwarding no
```
```bash
sshd -t && systemctl reload ssh      # the unit is 'ssh' on Ubuntu, 'sshd' on RHEL
sshd -T | grep -Ei 'permitroot|passwordauth'   # effective config
ssh-keygen -t ed25519 ; ssh-copy-id alice@192.168.60.12 ; chmod 700 ~/.ssh ; chmod 600 ~/.ssh/authorized_keys
```
Ubuntu 24.04 uses socket activation (`ssh.socket`): to change the `Port`, run `systemctl daemon-reload && systemctl restart ssh.socket` after editing, and `ufw allow <port>/tcp` first.

### cron and systemd timers
```bash
crontab -e -u alice                 # */15 * * * * /usr/local/bin/backup.sh
echo '30 2 * * 1-5 root /usr/local/bin/report.sh' > /etc/cron.d/report   # system crontab has a user field
ls /etc/cron.{hourly,daily,weekly}   # scripts must be executable and have no dot in the name
```
```ini
# /etc/systemd/system/backup.timer  (pairs with backup.service, Type=oneshot)
[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true
[Install]
WantedBy=timers.target
```
`systemctl daemon-reload ; systemctl enable --now backup.timer ; systemctl list-timers ; systemd-analyze calendar 'Mon *-*-* 03:00'`.

### Kernel parameters
```bash
sysctl net.ipv4.ip_forward ; sysctl -w net.ipv4.ip_forward=1          # runtime only
echo "net.ipv4.ip_forward = 1" > /etc/sysctl.d/90-lfcs.conf ; sysctl --system   # persistent
echo "vm.swappiness = 10" >> /etc/sysctl.d/90-lfcs.conf
modprobe br_netfilter ; echo br_netfilter > /etc/modules-load.d/br.conf ; lsmod | grep br_
# Boot parameters: edit GRUB_CMDLINE_LINUX in /etc/default/grub, then update-grub (no grubby on Ubuntu)
```
Resource limits per user: `/etc/security/limits.d/alice.conf` with `alice hard nproc 100`.

### Bonding and bridging with netplan
```yaml
network:
  version: 2
  ethernets: {enp0s9: {dhcp4: false}, enp0s10: {dhcp4: false}}
  bonds:
    bond0:
      interfaces: [enp0s9, enp0s10]
      parameters: {mode: active-backup, primary: enp0s9, mii-monitor-interval: 100}
      addresses: [192.168.61.21/24]
  bridges:
    br0:
      interfaces: []          # or [bond0] to bridge the bond, with the IP moved to br0
      addresses: [10.10.10.1/24]
      parameters: {stp: false}
```
Modes: `balance-rr` (0), `active-backup` (1, no switch config), `802.3ad` (4, LACP, needs the switch). Check with `cat /proc/net/bonding/bond0` and `bridge link`.

### NAT and port forwarding (nftables first, iptables for legacy)
```bash
sysctl -w net.ipv4.ip_forward=1   # plus the sysctl.d file
nft add table ip nat
nft 'add chain ip nat prerouting { type nat hook prerouting priority -100 ; }'
nft 'add chain ip nat postrouting { type nat hook postrouting priority 100 ; }'
nft add rule ip nat postrouting oifname "enp0s3" masquerade
nft add rule ip nat prerouting iifname "enp0s8" tcp dport 8080 dnat to 192.168.60.12:80
nft list ruleset > /etc/nftables.conf ; systemctl enable nftables   # persist (add 'flush ruleset' at the top)
# iptables equivalents (persist with apt install iptables-persistent ; netfilter-persistent save)
iptables -t nat -A POSTROUTING -o enp0s3 -j MASQUERADE
iptables -t nat -A PREROUTING -i enp0s8 -p tcp --dport 8080 -j DNAT --to-destination 192.168.60.12:80
iptables -A FORWARD -p tcp -d 192.168.60.12 --dport 80 -j ACCEPT ; iptables -t nat -L -n -v
```
If ufw is active, it also filters FORWARD: `ufw route allow` or set its forward policy, or the DNAT silently drops.

### Reverse proxy and load balancing
```nginx
# /etc/nginx/sites-available/app  ->  ln -s ../sites-available/app /etc/nginx/sites-enabled/ ; rm sites-enabled/default
upstream backend { server 192.168.60.11:8080; server 192.168.60.12:8080; }   # round robin; least_conn; or weight=3
server {
    listen 80;
    server_name app.lab.example.com;
    location / { proxy_pass http://backend; proxy_set_header Host $host; proxy_set_header X-Real-IP $remote_addr; }
}
```
`nginx -t && systemctl reload nginx`. HAProxy equivalent in `/etc/haproxy/haproxy.cfg`, checked with `haproxy -c -f /etc/haproxy/haproxy.cfg`:
```
frontend web
    bind *:80
    default_backend app
backend app
    balance roundrobin
    server s1 192.168.60.11:8080 check
    server s2 192.168.60.12:8080 check
```

### Containers on Ubuntu
```bash
apt install -y docker.io ; usermod -aG docker alice    # or podman: apt install -y podman
docker run -d --name web --restart unless-stopped -p 8080:80 -v /srv/web:/usr/share/nginx/html:ro nginx:1.27
docker ps -a ; docker logs web ; docker exec -it web sh ; docker inspect -f '{{.State.Status}}' web
docker build -t myapp:1 . ; docker image ls ; docker rm -f web ; docker volume create data
```
Podman is the same CLI; `:Z` volume labels are SELinux-only and not needed on Ubuntu. Quadlet works on 24.04 (podman 4.9) exactly as in the RHCSA guide.

### Virtualization with virsh
```bash
apt install -y qemu-kvm libvirt-daemon-system virtinst ; usermod -aG libvirt alice
virsh list --all ; virsh start vm1 ; virsh shutdown vm1 ; virsh destroy vm1   # destroy = pull the plug
virsh autostart vm1 ; virsh dominfo vm1 ; virsh setvcpus vm1 2 --config ; virsh setmaxmem vm1 2G --config
virsh edit vm1 ; virsh dumpxml vm1 > vm1.xml ; virsh undefine vm1 --remove-all-storage
virt-install --name vm2 --memory 1024 --vcpus 1 --import --disk /var/lib/libvirt/images/cirros.qcow2 --osinfo detect=on,require=off --noautoconsole
```

### Git basics
```bash
git config --global user.name "Alice" ; git init ; git add . ; git commit -m "init"
git clone https://host/repo.git ; git switch -c feature ; git log --oneline --graph
git remote add origin <url> ; git push -u origin main ; git pull --rebase ; git merge feature
git status ; git diff ; git restore file ; git reset --soft HEAD~1 ; git tag v1.0
```

## Timed mock exam (25 tasks, 120 minutes, on the two lab VMs)
Rebuild first: `cd lab/golden/lfcs && vagrant destroy -f && vagrant up`. Reboot both VMs at the end and run `check.sh`.
1. lfcs2: add a static address 192.168.60.50/24 to `enp0s8` with netplan, keeping the existing one.
2. lfcs2: make `9.9.9.9` the DNS server for `enp0s8` and search domain `lab.example.com`.
3. lfcs1: enable ufw, allow SSH from anywhere and TCP 80 only from 192.168.60.0/24.
4. lfcs1: put the nginx AppArmor profile (or `usr.sbin.tcpdump`) in complain mode.
5. lfcs1: install `htop`, hold the `nginx` package at its current version.
6. lfcs1: write the package that owns `/usr/bin/ss` to `/root/ss-pkg.txt`.
7. lfcs1: VG `vg_lfcs` on `/dev/sdb`, LV `lv_data` 500 MiB, ext4, mounted persistently on `/data`.
8. lfcs1: grow `lv_data` to 800 MiB together with its filesystem.
9. lfcs2: RAID 1 array `/dev/md0` from `/dev/sdb` and `/dev/sdc`, mounted on `/raid` at boot.
10. lfcs2: fail and replace one RAID member, then confirm `[UU]`.
11. lfcs1: add a 512 MiB swap file `/swapfile` that survives reboot.
12. lfcs1: export `/srv/nfs/share` read-write to 192.168.60.0/24; lfcs2: mount it on `/mnt/share` at boot.
13. lfcs1: user quota on `/data` for `alice`: soft 100 MiB, hard 120 MiB.
14. lfcs1: create group `ops`, users `alice` and `bob` in it; `bob` may only run `systemctl restart nginx` via sudo.
15. lfcs1: `alice` password expires every 60 days, max 50 processes.
16. lfcs1: `/srv/ops` owned by group `ops`, setgid, and `bob` gets read-only access through an ACL.
17. lfcs1: `alice` runs `/usr/local/bin/backup.sh` at 02:30 every weekday via cron.
18. lfcs1: systemd timer `cleanup.timer` runs `cleanup.service` daily and catches up missed runs.
19. lfcs1: enable IPv4 forwarding and set `vm.swappiness=10`, both persistent.
20. lfcs2: SSH: no root login, no password auth; keep your key login working.
21. lfcs2: bond `bond0` (active-backup) from `enp0s9` and `enp0s10` with 192.168.61.22/24.
22. lfcs1: forward TCP 9090 on lfcs1 to 192.168.60.12:8080 with nftables, persistent (the task 24 container is the target).
23. lfcs1: nginx load balances port 80 across 192.168.60.11:8080 and 192.168.60.12:8080.
24. lfcs2: run container `web` from `nginx:1.27` on host port 8080, restarted automatically after reboot.
25. lfcs1: init a Git repo in `/opt/configs`, commit `/etc/nginx/nginx.conf` as `nginx.conf`, tag `v1`.

<details><summary>Mock solutions</summary>

1. Add `192.168.60.50/24` to `addresses:` of `enp0s8` in its `/etc/netplan/*.yaml` (mode 600), `netplan try`, `netplan apply`, `ip -br a`.
2. Same file: `nameservers: {addresses: [9.9.9.9], search: [lab.example.com]}`; `netplan apply ; resolvectl status enp0s8`.
3. `ufw allow OpenSSH ; ufw allow from 192.168.60.0/24 to any port 80 proto tcp ; ufw --force enable ; ufw status`.
4. `apt install -y apparmor-utils nginx ; aa-complain /etc/apparmor.d/usr.sbin.tcpdump ; aa-status` (nginx ships no profile by default; complain whichever profile the task names).
5. `apt install -y htop ; apt-mark hold nginx ; apt-mark showhold`.
6. `dpkg -S /usr/bin/ss | cut -d: -f1 > /root/ss-pkg.txt` (iproute2).
7. `pvcreate /dev/sdb ; vgcreate vg_lfcs /dev/sdb ; lvcreate -n lv_data -L 500M vg_lfcs ; mkfs.ext4 /dev/vg_lfcs/lv_data ; mkdir /data`; fstab `/dev/vg_lfcs/lv_data /data ext4 defaults 0 2`; `mount -a`.
8. `lvextend -r -L 800M /dev/vg_lfcs/lv_data ; df -h /data`.
9. `mdadm --create /dev/md0 -l1 -n2 /dev/sdb /dev/sdc ; mdadm --detail --scan >> /etc/mdadm/mdadm.conf ; update-initramfs -u ; mkfs.ext4 /dev/md0`; fstab by UUID on `/raid` with `nofail`; `mount -a`.
10. `mdadm /dev/md0 --fail /dev/sdc --remove /dev/sdc ; mdadm /dev/md0 --add /dev/sdd ; watch cat /proc/mdstat`.
11. `fallocate -l 512M /swapfile ; chmod 600 /swapfile ; mkswap /swapfile ; swapon /swapfile`; fstab `/swapfile none swap sw 0 0`.
12. Server: `/etc/exports` line with `(rw,sync,no_subtree_check)`, `exportfs -ra`, allow NFS in ufw. Client: `nfs-common`, fstab `192.168.60.11:/srv/nfs/share /mnt/share nfs defaults,_netdev 0 0`, `mount -a`.
13. fstab options `defaults,usrquota` on `/data`, `mount -o remount /data ; quotacheck -cum /data ; quotaon /data ; setquota -u alice 102400 122880 0 0 /data ; repquota -s /data`.
14. `groupadd ops ; useradd -m -s /bin/bash -G ops alice ; useradd -m -s /bin/bash -G ops bob`; `visudo -f /etc/sudoers.d/bob` -> `bob ALL=(root) /usr/bin/systemctl restart nginx`.
15. `chage -M 60 alice ; echo 'alice hard nproc 50' > /etc/security/limits.d/alice.conf`.
16. `mkdir /srv/ops ; chgrp ops /srv/ops ; chmod 2770 /srv/ops ; setfacl -m u:bob:rx /srv/ops ; getfacl /srv/ops`.
17. `crontab -e -u alice` -> `30 2 * * 1-5 /usr/local/bin/backup.sh`; check `crontab -l -u alice`.
18. `cleanup.service` (`Type=oneshot`, `ExecStart=`) + `cleanup.timer` (`OnCalendar=daily`, `Persistent=true`, `WantedBy=timers.target`); `daemon-reload ; enable --now cleanup.timer`.
19. `/etc/sysctl.d/90-lfcs.conf` with both lines; `sysctl --system ; sysctl net.ipv4.ip_forward vm.swappiness`.
20. Copy your key first (`ssh-copy-id`), then `/etc/ssh/sshd_config.d/00-hardening.conf` with `PermitRootLogin no` and `PasswordAuthentication no`; `sshd -t && systemctl reload ssh`; test a new session before closing the old one.
21. netplan `bonds: bond0` with `interfaces: [enp0s9, enp0s10]`, `parameters: {mode: active-backup}`, address; both NICs `dhcp4: false`; `cat /proc/net/bonding/bond0`.
22. Forwarding on (19), nftables `nat` table with the prerouting `dnat` rule and a postrouting `masquerade`; `nft list ruleset > /etc/nftables.conf ; systemctl enable nftables`; `ufw route allow proto tcp to 192.168.60.12 port 8080` if ufw is on.
23. `upstream` block with both servers and `proxy_pass http://backend;` in a `sites-enabled` file; `nginx -t && systemctl reload nginx ; curl -s localhost`.
24. `apt install -y docker.io ; systemctl enable --now docker ; docker run -d --name web --restart always -p 8080:80 nginx:1.27`.
25. `mkdir /opt/configs && cd /opt/configs && git init && cp /etc/nginx/nginx.conf . && git add nginx.conf && git commit -m "nginx conf" && git tag v1` (set `user.name`/`user.email` first).
</details>

## Resources
LFS207 (LF course for LFCS), https://training.linuxfoundation.org (curriculum and candidate handbook), killer.sh LFCS simulator, `man netplan`, `/usr/share/doc/netplan*/examples/`, `man mdadm`, `man nft`, `man 5 sshd_config`, `man ufw`.
