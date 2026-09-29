#!/usr/bin/env bash
# Weeks 6-8: a whole routed network on ONE Linux VM using network namespaces.
#
#   lan-a (10.0.1.0/24)  --  router  --  lan-b (10.0.2.0/24)  --  (NAT to host)
#   host a1 10.0.1.10        .1 / .1      host b1 10.0.2.10
#
#   sudo ./netns-lab.sh up | down | status
set -euo pipefail
NS=(a1 router b1)

up() {
  for n in "${NS[@]}"; do ip netns add $n; ip -n $n link set lo up; done
  ip link add a1-eth0 type veth peer name r-eth0
  ip link add b1-eth0 type veth peer name r-eth1
  ip link set a1-eth0 netns a1;  ip link set r-eth0 netns router
  ip link set b1-eth0 netns b1;  ip link set r-eth1 netns router

  ip -n a1 addr add 10.0.1.10/24 dev a1-eth0; ip -n a1 link set a1-eth0 up
  ip -n b1 addr add 10.0.2.10/24 dev b1-eth0; ip -n b1 link set b1-eth0 up
  ip -n router addr add 10.0.1.1/24 dev r-eth0; ip -n router link set r-eth0 up
  ip -n router addr add 10.0.2.1/24 dev r-eth1; ip -n router link set r-eth1 up

  # Deliberately NOT done - these are your exercises:
  #   default routes on a1/b1, ip_forward on router, a firewall rule, a DNS server.
  cat <<'TXT'
Network is up but broken on purpose. Exercises:
 1. ip netns exec a1 ping -c1 10.0.2.10         -> fails. Why? (routing table: ip -n a1 route)
 2. Add default routes on a1 and b1 via their router IPs. Still fails? Enable forwarding:
      ip netns exec router sysctl -w net.ipv4.ip_forward=1
 3. Capture it:  ip netns exec router tcpdump -ni r-eth1 icmp
 4. Firewall on router with nftables: allow a1 -> b1 tcp/80 only, drop everything else forwarded.
      ip netns exec b1 python3 -m http.server 80 &   then curl from a1
 5. Masquerade: make everything from lan-a appear as 10.0.2.1 to b1 (nft nat postrouting).
 6. ss -tlnp inside b1 ; conntrack/nft list ruleset inside router
 7. Break MTU: ip -n router link set r-eth1 mtu 576 ; find it with ping -M do -s 1400
 8. DNS: run 'dnsmasq --no-daemon --address=/web.lab/10.0.2.10' in router ns; resolve from a1 with dig @10.0.1.1 web.lab
TXT
}

down() { for n in "${NS[@]}"; do ip netns del $n 2>/dev/null || true; done; echo "removed"; }
status() { for n in "${NS[@]}"; do echo "== $n"; ip -n $n -br addr; ip -n $n route; done; }

case "${1:-}" in up) up ;; down) down ;; status) status ;; *) echo "usage: sudo $0 up|down|status" ;; esac
