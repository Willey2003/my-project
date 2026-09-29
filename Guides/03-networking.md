---
tags: [devops-prep, guide]
---
# Phase 3 - Networking Fundamentals

**Plan weeks:** 6-8 · **Hours:** 32 · **Lab:** `lab/networking/` (netns lab, subnetting drills, HAProxy)

| Week | Focus | Deliverable |
|---|---|---|
| 6 | OSI/TCP-IP, subnetting/CIDR, routing, DNS/DHCP | Subnetting exercise set |
| 7 | ip/nmcli, tcpdump, ss, nftables/firewalld | Packet capture + firewall lab |
| 8 | DNS troubleshooting, NAT, HAProxy/Nginx L4-L7, VLANs | Network troubleshooting runbook |

## Models and the packet's journey
| Layer (OSI) | TCP/IP | Examples | Debug with |
|---|---|---|---|
| 7-5 Application | Application | HTTP, DNS, TLS, SSH | `curl -v`, `dig`, `openssl s_client` |
| 4 Transport | Transport | TCP (handshake, retransmit), UDP | `ss -tanp`, `tcpdump 'tcp[tcpflags] & tcp-syn != 0'` |
| 3 Network | Internet | IP, ICMP, routing | `ip route get 8.8.8.8`, `ping`, `tracepath` |
| 2 Data link | Link | Ethernet, ARP, VLAN 802.1Q | `ip neigh`, `bridge link` |
| 1 Physical | Link | cables, NIC | `ethtool` |

"What happens when you curl https://example.com" (classic interview): resolver (`/etc/nsswitch.conf` -> `/etc/hosts` -> DNS via `/etc/resolv.conf`), ARP for the gateway, TCP 3-way handshake, TLS handshake (SNI, cert chain validation), HTTP request, response, connection reuse/close. Be able to name the tool that proves each step.

## Subnetting (week 6)
- `/n` = n network bits. Hosts = 2^(32-n) - 2. /24=254, /25=126, /26=62, /27=30, /28=14, /29=6, /30=2, /31 point-to-point (RFC 3021), /32 host route.
- Block size trick: for /26, mask 255.255.255.192, block = 256-192 = 64 -> networks .0, .64, .128, .192.
- Private ranges: 10/8, 172.16/12, 192.168/16; CGNAT 100.64/10; link-local 169.254/16 (AWS metadata 169.254.169.254!).
- VLSM: allocate largest subnets first to keep alignment.
- Drill daily: `python3 lab/networking/subnetting-drills.py` (15 min warm-up until you answer in < 30 s).

## Linux networking tools (week 7)
```bash
ip -br addr ; ip route ; ip route get 10.0.2.10 ; ip neigh ; ip -s link
nmcli con show ; nmcli con mod eth1 ipv4.method manual ipv4.addresses 192.168.56.21/24 \
  ipv4.gateway 192.168.56.1 ipv4.dns 192.168.56.1 ; nmcli con up eth1
hostnamectl set-hostname servera.lab.example.com
ss -tulpn                                   # listening sockets + owning process
tcpdump -ni eth1 'host 10.0.2.10 and port 80' -w cap.pcap   # open in Wireshark
firewall-cmd --get-active-zones ; firewall-cmd --zone=public --add-service=http --permanent ; firewall-cmd --reload
firewall-cmd --add-rich-rule='rule family=ipv4 source address=10.0.1.0/24 port port=8080 protocol=tcp accept' --permanent
nft list ruleset
```
nftables mental model: tables -> chains (hook: prerouting/input/forward/output/postrouting, priority, policy) -> rules. firewalld is a front-end that writes nftables.

Lab: `sudo lab/networking/netns-lab.sh up` builds a routed two-LAN network inside one VM with deliberate faults. Work through the 8 exercises; capture before/after pcaps.

## Services and load balancing (week 8)
- **DNS:** records A/AAAA/CNAME/MX/TXT/NS/SOA/PTR/SRV. Recursive vs authoritative. TTL and negative caching. `dig +trace example.com`, `dig @8.8.8.8 -x 1.1.1.1`, `resolvectl status`. Kubernetes gotcha preview: `ndots:5` in pod resolv.conf.
- **DHCP:** DORA (Discover, Offer, Request, Ack); relays across subnets.
- **NAT:** SNAT/masquerade (many private -> one public), DNAT/port-forward (public port -> private host). Conntrack tracks state. Cloud NAT gateway = managed SNAT.
- **L4 vs L7 LB:** L4 forwards TCP connections (fast, no HTTP awareness); L7 terminates HTTP, can route by host/path/header, add headers, retry. Health checks, algorithms (round robin, least-conn, source hash), sticky sessions, connection draining.
  Lab: `docker compose -f lab/networking/haproxy-lab.yml up -d`, compare ports 8080 (L7) and 8081 (L4), stop a backend and watch stats page.
- **VLANs:** 802.1Q tag splits one L2 switch into many broadcast domains; trunk vs access ports; inter-VLAN routing needs L3.
- MTU/MSS: 1500 Ethernet, overlays (VXLAN/Geneve) subtract ~50 bytes - classic cause of "small requests work, big ones hang".

## Troubleshooting runbook template (deliverable)
1. Define: who can't reach what, since when, what changed.
2. Layer walk bottom-up: link (`ip link`), IP/route (`ip route get`), neighbour (`ip neigh`), name (`dig`), port (`ss`, `nc -zv host port`), firewall (`nft list ruleset`, security groups), app (`curl -v`, logs).
3. Capture on both sides (`tcpdump`) - SYN leaves but no SYN-ACK back = path/firewall; RST = nothing listening or rejected.
4. Fix, verify, write down root cause + prevention.

## Self-check
1. Usable hosts in 172.16.40.0/21 and its broadcast?
2. `ping` works by IP but not by name. Next three commands?
3. Why would SYNs leave a host but no SYN-ACK arrive while the server shows SYN-RECV?
4. L4 or L7 LB for gRPC with per-method routing?
5. What does `firewall-cmd --reload` do to runtime-only rules?

<details><summary>Answers</summary>

1. 2046 hosts; broadcast 172.16.47.255.
2. `cat /etc/resolv.conf`, `dig name`, `dig @<other resolver> name` (also `getent hosts name` to include /etc/hosts).
3. The return path is asymmetric/blocked (routing or a stateful firewall dropping the reply).
4. L7 (HTTP/2 aware).
5. Discards them - only permanent config survives.
</details>

## Resources
https://www.practicalnetworking.net · https://subnettingpractice.com · Julia Evans' networking zines · `man 8 ip`, `man 8 nft`, `man 1 dig`


---
[[Home]] · [[Schedule]]
