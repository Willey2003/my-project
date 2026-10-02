# Phase 5 - RHCE: Ansible Automation (EX294)

**Plan weeks:** 13-16 · **Hours:** 42 · **Exam:** hands-on, ~USD 550 · **Lab:** `vagrant ssh control` -> `sudo -iu student` -> `cd /lab/ansible`

| Week | Focus | Deliverable |
|---|---|---|
| 13 | Inventory, ad-hoc, playbooks, core modules | Playbook automating the week 2-3 Linux labs (`playbooks/01-baseline.yml` is your start) |
| 14 | Roles, variables/facts, Jinja2, handlers | Reusable `server_hardening` role (starter in `roles/`) |
| 15 | Vault, dynamic inventory, error handling, idempotency | Vault-secured secrets demo |
| 16 | Timed mocks, sit exam | RHCE |

## Core model
Control node (Python + ansible-core) pushes over SSH to managed nodes; modules run there and return JSON. **Idempotent**: running twice changes nothing the second time. Order of precedence you must know roughly: extra vars (`-e`) win over everything; then task/block vars, role/include params, set_facts, play vars, host_vars, group_vars (child before parent, `all` lowest), role defaults (lowest of all).

## Inventory & config
```ini
# inventory.ini
[web]
node1.lab.example.com
[db]
node2.lab.example.com
[prod:children]
web
db
```
`ansible.cfg` lookup order: `ANSIBLE_CONFIG` -> `./ansible.cfg` -> `~/.ansible.cfg` -> `/etc/ansible/ansible.cfg`. Check with `ansible --version` and `ansible-config dump --only-changed`.
```bash
ansible-inventory --graph ; ansible all -m ping ; ansible web -m dnf -a "name=httpd state=present" -b
ansible-doc -l | grep firewall ; ansible-doc ansible.posix.firewalld     # exam lifesaver: EXAMPLES section
ansible-navigator run site.yml -m stdout   # EX294 on RHEL 9+ may expect navigator; practise both
```

## Playbook toolbox
- Modules you must know cold: `dnf`, `package`, `service`/`systemd`, `user`, `group`, `copy`, `template`, `file`, `lineinfile`, `blockinfile`, `get_url`, `uri`, `command`/`shell` (last resort), `firewalld`, `selinux`, `sefcontext`, `seboolean`, `lvg`, `lvol`, `filesystem`, `mount`, `parted`, `cron`, `authorized_key`, `debug`, `assert`, `setup`, `archive`.
- Loops: `loop:`, `loop: "{{ dict | dict2items }}"`, `with_*` legacy. Conditionals: `when: ansible_facts['distribution_major_version'] | int >= 9`, `when: "'web' in group_names"`.
- Facts: `ansible node1 -m setup -a 'filter=ansible_default_ipv4'`; custom facts in `/etc/ansible/facts.d/*.fact` (INI/JSON) appear under `ansible_local`.
- Handlers run once at the end of the play, only if notified; `meta: flush_handlers` to run early.
- Error handling: `block/rescue/always`, `ignore_errors`, `failed_when`, `changed_when`, `any_errors_fatal`.
- Templates (Jinja2): `{{ var | default('x') }}`, `{% for h in groups['web'] %}{{ hostvars[h]['ansible_facts']['default_ipv4']['address'] }} {{ h }}{% endfor %}` - classic `/etc/hosts` task.
- Roles: `ansible-galaxy init myrole`; `requirements.yml` for Galaxy roles/collections: `ansible-galaxy install -r requirements.yml -p roles/`. RHEL System Roles (`rhel-system-roles` package: timesync, selinux, network, storage) are exam favourites.

## Vault
```bash
ansible-vault create secrets.yml ; ansible-vault edit secrets.yml ; ansible-vault rekey secrets.yml
ansible-vault encrypt_string 'S3cret' --name db_password
ansible-playbook site.yml --vault-password-file ~/.vault_pass   # file mode 600
```
Use `no_log: true` on tasks that handle secrets.

## Idempotency & quality
- Run every playbook twice; the second run must show `changed=0`.
- `--check --diff` before real runs. `ansible-lint` in CI (week 21 pipeline can lint your Ansible repo).
- Avoid `shell` unless needed; if used, set `creates:`/`changed_when:`.

## EX294 practice set (do all within 4 h)
1. Install and configure Ansible on control with inventory groups `dev`, `test`, `prod`, `balancers`, `webservers` (`prod` is a child).
2. Ad-hoc script `adhoc.sh` that creates yum repos on all nodes with `yum_repository`.
3. Install packages per group; install the "Development Tools" group only on `dev`.
4. Install RHEL system roles and use the `timesync` role to set NTP.
5. Use a Galaxy role from `requirements.yml` to deploy haproxy on `balancers`, apache on `webservers`.
6. Create LVs with error handling: 1500 MiB if VG has space, else 800 MiB with a message, if VG missing print "VG not found".
7. Generate `/etc/myhosts` from a template listing every host's IP and FQDN.
8. Modify file content: `/etc/issue` shows "Development"/"Test"/"Production" based on the group.
9. Web content dir `/webdev` owned by group `webdev`, setgid, SELinux context `httpd_sys_content_t`, symlink from `/var/www/html/webdev`.
10. Hardware report: write `/root/hwreport.txt` with hostname, memory, BIOS version, disk sizes; "NONE" when a device is missing.
11. Vault: `locker.yml` with `pw_developer`/`pw_manager`, create users from `user_list.yml` with the right password per job, via `password_hash('sha512')`.
12. Rekey an existing vault file.
13. cron job as user `natasha` via playbook.

Deliverable for week 16: the full set as a repo (`ex294-practice`), each task a playbook, plus the `server_hardening` role with a README and a Molecule or `--check` run in CI.

## Self-check
1. Two places a variable for all web hosts can live, and which wins?
2. Why is `command: useradd bob` not idempotent and what replaces it?
3. How do you run only the tasks tagged `firewall`?
4. Handler notified in a failed play - does it run?
5. How do you loop over a dict of users with their UIDs?

<details><summary>Answers</summary>

1. `group_vars/web.yml` vs play `vars:` - play vars win.
2. It fails/changes on every run; use the `user` module.
3. `ansible-playbook site.yml --tags firewall`.
4. No, unless `--force-handlers` / `force_handlers: true`.
5. `loop: "{{ users | dict2items }}"` with `item.key`, `item.value`.
</details>

## Resources
RH294 (RHEL 9), EX294v9K practice Q&A, https://docs.ansible.com/ansible/latest/, `ansible-doc` (your offline docs in the exam)
