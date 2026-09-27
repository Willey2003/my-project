#!/usr/bin/env python3
"""Week 6: endless random subnetting drills. Answer, press enter, see the solution."""
import ipaddress, random

def drill():
    prefix = random.randint(16, 30)
    net = ipaddress.ip_network(f"{random.randint(10,192)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}/{prefix}", strict=False)
    host = net.network_address + random.randint(1, max(1, net.num_addresses - 2))
    print(f"\nHost {host}/{prefix}")
    input("  network, broadcast, first/last usable, usable hosts, mask? > ")
    hosts = list(net.hosts()) if net.num_addresses <= 65536 else None
    print(f"  network   {net.network_address}\n  broadcast {net.broadcast_address}\n  mask      {net.netmask}")
    if hosts:
        print(f"  usable    {hosts[0]} - {hosts[-1]} ({len(hosts)} hosts)")
    else:
        print(f"  usable hosts {net.num_addresses - 2}")

def vlsm():
    need = sorted(random.sample([2, 10, 25, 50, 60, 100, 120, 200], 4), reverse=True)
    base = ipaddress.ip_network("172.16.0.0/22")
    print(f"\nVLSM: carve {base} for LANs needing {need} hosts (largest first)")
    input("  your plan? > ")
    cur = base.network_address
    for n in need:
        p = 32 - (n + 2 - 1).bit_length()
        sub = ipaddress.ip_network(f"{cur}/{p}")
        print(f"  {n:>4} hosts -> {sub}")
        cur = sub.broadcast_address + 1

if __name__ == "__main__":
    try:
        while True:
            random.choice([drill, drill, drill, vlsm])()
    except (KeyboardInterrupt, EOFError):
        print("\nbye")
