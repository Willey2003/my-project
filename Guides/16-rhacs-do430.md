---
tags: [devops-prep, guide]
---
# Phase 16 - OpenShift Advanced Cluster Security (DO430 -> EX430)

**Plan weeks:** 51-52 · **Hours:** 24 · **Exam:** EX430, 4 h hands-on, ~USD 550 (confirm) · **Lab:** RHACS operator on OpenShift Local, `openshift-drills.md` (EX430 section)

| Week | Focus | Deliverable |
|---|---|---|
| 51 | Install RHACS (Central + SecuredCluster), vulnerability management | Vulnerability-policy dashboard report |
| 52 | Deploy/runtime policies, network segmentation, Compliance Operator, CI integration; sit EX430 | EX430 |

## Architecture
- **Central** (UI, API, policy engine, Scanner V4 for image/node CVEs) - one per fleet.
- **SecuredCluster** per cluster: Sensor (watches the API), Admission Controller (enforces deploy-time policies), Collector (per-node runtime data via eBPF), Scanner (local registry scanning).
- Init bundles / cluster registration secrets connect a SecuredCluster to Central.

## What to master
- **Vulnerability management:** image, node and platform CVEs; prioritisation by severity, fixability and deployment exposure; exception/deferral workflow; reports on a schedule.
- **Policies:** lifecycle stages Build (CI via `roxctl image check`), Deploy (admission enforcement, e.g. no `latest` tag, no privileged, required resource limits) and Runtime (process/network activity, e.g. a shell executed in a container, alerts or kill pod). Scope with inclusions/exclusions; clone default policies instead of editing them.
- **Network segmentation:** Network Graph shows observed flows; generate baseline NetworkPolicies from real traffic, simulate, then apply.
- **Compliance:** Compliance Operator scans (CIS OpenShift, NIST 800-53 moderate, PCI DSS profiles); results appear in RHACS; apply auto-remediations carefully and re-scan.
- **Integrations:** image registries, notifiers (email, Slack, generic webhook), API tokens for CI, `roxctl` CLI.

## Lab plan
1. `crc.sh setup` with 16+ GiB, install RHACS operator, create Central, generate an init bundle, create SecuredCluster.
2. Deploy the lab app and a deliberately outdated image; find it in Vulnerability Management and write the report.
3. Create a deploy-time policy "no latest tag" in enforce mode and prove a deployment is rejected.
4. Enable the runtime "shell spawned" policy, `oc exec` into a pod, find the violation.
5. Generate a NetworkPolicy baseline from the Network Graph for the lab namespace.
6. Run the CIS profile via Compliance Operator, remediate one failed check, re-scan.
7. Add `roxctl image check` to the CI workflow from phase 7 (API token as a secret).

## Self-check
1. Which component enforces deploy-time policies, and what happens if it is unavailable?
2. Build vs deploy vs runtime policy - one example of each.
3. How does RHACS help write NetworkPolicies?
4. What does the Compliance Operator produce and how do you remediate?

<details><summary>Answers</summary>

1. The admission controller webhook; its failure policy decides fail-open vs fail-closed.
2. Build: fixable CVSS >= 7 fails CI; Deploy: block privileged containers; Runtime: alert on unexpected process execution.
3. It observes flows, shows them in the Network Graph and generates/simulates policies.
4. ComplianceCheckResults and ComplianceRemediations; apply remediations (often MachineConfigs) and re-scan.
</details>

## Resources
DO430 (v4.6), https://docs.openshift.com/acs/, Compliance Operator docs


---
[[Home]] · [[Schedule]]
