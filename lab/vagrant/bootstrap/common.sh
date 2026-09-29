#!/usr/bin/env bash
# Runs on every VM: hosts file, base packages, a 'student' admin user for exam-style practice.
set -euo pipefail
NET=${1:-192.168.56}

cat >/etc/hosts <<EOF
127.0.0.1   localhost localhost.localdomain
${NET}.10   control.lab.example.com control
${NET}.11   node1.lab.example.com   node1
${NET}.12   node2.lab.example.com   node2
EOF

dnf -y -q install vim-enhanced bash-completion git tar rsync lvm2 xfsprogs \
  policycoreutils-python-utils setroubleshoot-server tcpdump nmap-ncat bind-utils \
  firewalld chrony python3 man-pages sos acl 2>/dev/null || true
systemctl enable --now firewalld chronyd

# 'student' / password 'redhat' with sudo: mirrors Red Hat course environments.
if ! id student &>/dev/null; then
  useradd -m -G wheel student
  echo 'student:redhat' | chpasswd
fi
echo 'student ALL=(ALL) NOPASSWD: ALL' >/etc/sudoers.d/student
chmod 0440 /etc/sudoers.d/student

# Allow password SSH inside the lab network so the control node can push keys.
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
rm -f /etc/ssh/sshd_config.d/*-cloud-image*.conf /etc/ssh/sshd_config.d/90-vagrant.conf 2>/dev/null || true
systemctl restart sshd

echo "bootstrap done on $(hostname)"
