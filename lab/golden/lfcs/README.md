# LFCS lab (Golden Kubestronaut track)

Two Ubuntu 24.04 VMs for practising the LFCS exam, which runs on Ubuntu. You already know the RHEL way
from RHCSA; this lab drills the Ubuntu delta (apt, netplan, ufw, AppArmor, systemd-resolved) and the topics
RHCSA does not cover (mdadm RAID, NAT, bonding/bridging, reverse proxies, virsh, Git).
Study guide: [`study-guides/29-lfcs.md`](../../../study-guides/29-lfcs.md).

| VM | IP (enp0s8) | Spare NICs | Spare disks | RAM |
|---|---|---|---|---|
| lfcs1 | 192.168.60.11 | enp0s9, enp0s10 (internal net `lfcs-bond`) | sdb, sdc, sdd (2 GB each) | 2 GiB |
| lfcs2 | 192.168.60.12 | enp0s9, enp0s10 (internal net `lfcs-bond`) | sdb, sdc, sdd (2 GB each) | 2 GiB |

Box: `bento/ubuntu-24.04`. Provider: VirtualBox by default; libvirt works too (disks show up as `vdb`..`vdd`
and NIC names differ, so check `ip -br link` and `lsblk` first).

## Use
```bash
cd lab/golden/lfcs
VAGRANT_EXPERIMENTAL=disks vagrant up      # the env var enables the extra VirtualBox disks
vagrant ssh lfcs1                          # then: sudo -i
sudo /lfcs/check.sh                        # grade the [auto] tasks for this host
sudo /lfcs/check.sh all                    # every auto task on this VM
sudo /lfcs/check.sh 9 21                   # just the listed task numbers
vagrant destroy -f && vagrant up           # clean slate before a timed mock
```
This directory is rsynced into each VM at `/lfcs` (run `vagrant rsync` after editing). Overrides:
`LAB_MEM=1536`, `LAB_CPUS=1`, `LAB_BOX=<other box>`.

## Files
| File | What it is |
|---|---|
| `Vagrantfile` | 2 VMs, private network 192.168.60.0/24, 2 unconfigured NICs and 3 spare disks each, nested virt on for `virsh` |
| `tasks.md` | 30 practice tasks grouped by study week, each with a Check command |
| `check.sh` | Read-only grader for the 14 tasks marked `[auto]` (netplan, ufw, apt hold, LVM, RAID, swap, users, cron, timer, sysctl, sshd, nftables, docker, Git). It only reads state and never fixes anything |

## Routine
1. Weeks G1-G3: work through `tasks.md` in order, running each Check line, then `check.sh`.
2. Reboot both VMs (`vagrant reload`) and run `check.sh` again. A task that fails after a reboot counts as failed.
3. Week G4: `vagrant destroy -f && vagrant up`, then do the 25-task mock in the study guide in 120 minutes. Book the
   exam when you finish with time to spare, then use the two killer.sh sessions.

Notes: the provisioner is deliberately minimal (hosts entries, timezone, `apt-get update`); installing packages is
part of the tasks. Take care with ufw and SSH tasks: allow OpenSSH before `ufw enable`, and keep a second session
open while hardening sshd. If you lock yourself out, use `vagrant reload` or the VirtualBox console.
