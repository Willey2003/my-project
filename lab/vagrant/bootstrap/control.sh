#!/usr/bin/env bash
# Control node only: Ansible + SSH keys for 'student' to node1/node2.
set -euo pipefail

dnf -y -q install epel-release 2>/dev/null || true
dnf -y -q install ansible-core sshpass python3-pip 2>/dev/null || python3 -m pip install ansible-core
sudo -iu student ansible-galaxy collection install ansible.posix community.general >/dev/null 2>&1 || true

sudo -iu student bash <<'EOF'
[ -f ~/.ssh/id_ed25519 ] || ssh-keygen -q -t ed25519 -N '' -f ~/.ssh/id_ed25519
for h in node1 node2; do
  sshpass -p redhat ssh-copy-id -o StrictHostKeyChecking=accept-new student@$h >/dev/null 2>&1 \
    || echo "could not push key to $h yet (is it up?) - rerun: vagrant provision control"
done
EOF

echo "control ready: vagrant ssh control; sudo -iu student; cd /lab/ansible; ansible all -m ping"
