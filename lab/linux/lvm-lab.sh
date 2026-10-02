#!/usr/bin/env bash
# Week 4 / RHCSA storage lab using loop devices, so it works on any VM with no spare disks.
#   sudo ./lvm-lab.sh setup    -> creates 2 x 1 GiB loop "disks"
#   (do the exercises below by hand)
#   sudo ./lvm-lab.sh teardown
set -euo pipefail
DIR=/var/tmp/lvmlab
case "${1:-}" in
setup)
  mkdir -p $DIR
  for i in 1 2; do
    truncate -s 1G $DIR/disk$i.img
    losetup -fP --show $DIR/disk$i.img
  done
  losetup -l | grep lvmlab
  cat <<'TXT'

Exercises (use the /dev/loopN names printed above):
 1. pvcreate both devices; vgcreate vg_lab with a 16M extent size (-s 16M)
 2. lvcreate -n lv_app -L 600M vg_lab ; mkfs.xfs ; mount on /mnt/app via /etc/fstab using UUID
 3. lvcreate -n lv_logs -l 20 vg_lab (extents!) ; mkfs.ext4 ; mount on /mnt/logs
 4. Grow lv_app by 300M AND the filesystem in one command (lvextend -r)
 5. Shrink lv_logs to 200M (ext4 can shrink, xfs cannot - why?)
 6. Create a 128M swap LV and activate it persistently
 7. Reboot-proof check: umount -a ; mount -a ; findmnt --verify
 8. Stratis/VDO are gone from RHEL 10 exam - confirm current objectives on redhat.com
TXT
  ;;
teardown)
  for m in /mnt/app /mnt/logs; do umount $m 2>/dev/null || true; done
  swapoff -a 2>/dev/null; swapon -a 2>/dev/null || true
  vgremove -ff vg_lab 2>/dev/null || true
  for l in $(losetup -l -n -O NAME,BACK-FILE | awk '/lvmlab/ {print $1}'); do pvremove -ff -y "$l" 2>/dev/null || true; losetup -d "$l"; done
  rm -rf $DIR
  echo "remember to remove the lab lines from /etc/fstab"
  ;;
*) echo "usage: sudo $0 setup|teardown" ;;
esac
