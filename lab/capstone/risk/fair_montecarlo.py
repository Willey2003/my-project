#!/usr/bin/env python3
"""Week 69: FAIR-style Monte Carlo for annualized loss exposure (ALE). Standard library only.

Loss Event Frequency (per year) ~ PERT(min, likely, max)
Loss Magnitude (per event, INR) ~ PERT(min, likely, max)  = primary + secondary loss
ALE = sum of magnitudes over a Poisson(LEF) number of events, simulated N times.

Edit SCENARIOS, run, paste the table + exceedance numbers into the board narrative:
"There is a 10% chance this costs us more than X this year; control Y cuts that to Z for cost C."
"""
import math
import random
import statistics

N = 20_000
random.seed(42)

SCENARIOS = {
    # name: (LEF min, likely, max), (LM min, likely, max) in INR
    "Exposed K8s API / worm foothold": ((0.05, 0.2, 1.0), (2e6, 1.5e7, 1.2e8)),
    "Supply-chain poisoned image": ((0.02, 0.1, 0.5), (5e6, 3e7, 2.5e8)),
    "LLM copilot prompt-injection data leak": ((0.1, 0.5, 2.0), (1e6, 5e6, 6e7)),
}
# Control effect: multiplier on LEF (e.g. signed-images-only admission cuts supply-chain frequency 80%)
CONTROLS = {
    "Supply-chain poisoned image": ("cosign + policy-controller", 0.2, 1.5e6),
    "Exposed K8s API / worm foothold": ("CIS hardening + Falco/Tetragon", 0.3, 2.5e6),
}


def pert(lo, mode, hi, lamb=4.0):
    if hi == lo:
        return lo
    a = 1 + lamb * (mode - lo) / (hi - lo)
    b = 1 + lamb * (hi - mode) / (hi - lo)
    return lo + random.betavariate(a, b) * (hi - lo)


def poisson(lam):
    # Knuth; fine for small lambda
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= random.random()
        if p <= L:
            return k
        k += 1


def simulate(lef, lm, lef_mult=1.0):
    out = []
    for _ in range(N):
        events = poisson(pert(*lef) * lef_mult)
        out.append(sum(pert(*lm) for _ in range(events)))
    out.sort()
    return out


def pct(xs, p):
    return xs[min(len(xs) - 1, int(p * len(xs)))]


def cr(x):
    return f"{x / 1e7:,.2f} Cr"


if __name__ == "__main__":
    print(f"{'scenario':42} {'mean ALE':>12} {'P50':>10} {'P90':>10} {'P99':>10}")
    for name, (lef, lm) in SCENARIOS.items():
        base = simulate(lef, lm)
        print(f"{name:42} {cr(statistics.fmean(base)):>12} {cr(pct(base, .5)):>10} {cr(pct(base, .9)):>10} {cr(pct(base, .99)):>10}")
        if name in CONTROLS:
            ctrl, mult, cost = CONTROLS[name]
            after = simulate(lef, lm, mult)
            saved = statistics.fmean(base) - statistics.fmean(after)
            print(f"   with {ctrl}: mean {cr(statistics.fmean(after))}, P90 {cr(pct(after, .9))}; "
                  f"risk reduced {cr(saved)}/yr for control cost {cr(cost)} -> ROI {saved / cost:.1f}x")
