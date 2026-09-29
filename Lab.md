# Lab environment

The runnable lab lives in the repo, not in this vault: https://github.com/Willey2003/my-project (folder `lab/`, entry point `lab/lab.sh`; until PR #3 is merged it is on branch `prep/devops-lab-kit`).

- Vagrant 3-VM RHEL-compatible lab, Ansible playbooks + hardening role
- Docker 3-tier stack with Trivy, GitHub Actions pipeline
- kind cluster profiles with 11 CKA break-fix drills
- AWS Terraform (VPC + ECS + alarms + GitHub OIDC), OpenShift Local helpers
- KCSA/CKS security labs, Argo CD/Rollouts/Workflows, Istio, isolated AI-security sandbox
- Capstone starters (RAG copilot, FAIR risk model, ADR + STRIDE templates)

One Kubernetes namespace per component: shop, ckad-patterns, cka-storage, trouble, cks-bench, cks-runtime, secure, psa-restricted, psa-baseline, rollouts-demo, mesh-bookinfo, team-a (OpenShift).

[[Home]]
