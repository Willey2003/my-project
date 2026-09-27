#!/usr/bin/env bash
# Week 2: users, groups, special permissions, ACLs. Run as root on a lab VM, then answer the checks.
set -euo pipefail
groupadd -f devs; groupadd -f auditors
for u in alice bob carol; do id $u &>/dev/null || useradd -m $u; echo "$u:redhat" | chpasswd; done
usermod -aG devs alice; usermod -aG devs bob; usermod -aG auditors carol
mkdir -p /srv/project
chown root:devs /srv/project
chmod 2770 /srv/project                  # setgid: new files inherit group 'devs'
setfacl -m g:auditors:rx /srv/project    # auditors can read/list
setfacl -d -m g:auditors:rx /srv/project # ...including future files (default ACL)
mkdir -p /srv/dropbox; chmod 1777 /srv/dropbox   # sticky bit like /tmp
cat <<'TXT'
Checks - predict first, then verify:
  sudo -u alice touch /srv/project/a.txt && ls -l /srv/project   # group of a.txt?
  sudo -u carol ls /srv/project ; sudo -u carol touch /srv/project/x   # which works?
  getfacl /srv/project
  sudo -u bob rm /srv/dropbox/<alice's file>   # why does this fail?
  Set password aging for bob: max 90 days, warn 7 (chage) ; verify with chage -l bob
  Give alice sudo only for 'systemctl restart httpd' via /etc/sudoers.d/alice (visudo -cf)
TXT
