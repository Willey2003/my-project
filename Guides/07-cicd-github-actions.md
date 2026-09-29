---
tags: [devops-prep, guide]
---
# Phase 7 - CI/CD with GitHub Actions

**Plan weeks:** 21-22 · **Hours:** 22 · **Cert:** none (portfolio) · **Lab:** `lab/cicd/` (ci.yml, release.yml, aws-oidc-example.yml)

| Week | Focus | Deliverable |
|---|---|---|
| 21 | Workflows/triggers/jobs/steps, matrix, caching, secrets & OIDC | CI running tests on 3 Python versions with caching |
| 22 | Build & push image tagged with SHA, deploy job, failure-to-fix table | push -> test -> build -> scan -> push -> deploy, fails closed |

## Vocabulary
- **Workflow** (`.github/workflows/*.yml`) triggered by **events** (`push`, `pull_request`, `workflow_dispatch`, `schedule`, `workflow_call`, `release`).
- **Jobs** run in parallel on **runners** (GitHub-hosted `ubuntu-latest`, or self-hosted); `needs:` creates a DAG. **Steps** run in one job's VM sequentially and share the filesystem.
- **Actions** are reusable steps (`uses: actions/checkout@v4`). Pin third-party actions to a full commit SHA in production (supply-chain safety - the 2025 `tj-actions/changed-files` compromise is the case study).
- **Contexts/expressions:** `${{ github.sha }}`, `${{ matrix.python }}`, `${{ secrets.X }}`, `${{ vars.X }}`, `if: github.ref == 'refs/heads/main'`.
- **Outputs:** `echo "name=value" >> "$GITHUB_OUTPUT"`, consumed as `needs.job.outputs.name`.
- **Artifacts vs cache:** artifacts pass files between jobs / keep reports; cache speeds up dependency installs (`actions/setup-python` `cache: pip`, or `actions/cache` with a key hashing the lockfile).
- **Environments:** protection rules (required reviewers, wait timers, branch restrictions) + environment-scoped secrets - your manual approval gate for prod.
- **Concurrency:** `concurrency: { group: deploy-prod, cancel-in-progress: false }` prevents two deploys at once.
- **Reusable workflows** (`workflow_call`) vs **composite actions** - share pipelines across repos.

## Security essentials
- `permissions:` at workflow level: start with `contents: read` and grant per job (`packages: write`, `id-token: write`).
- **OIDC to cloud:** the job requests a signed JWT from GitHub; AWS trusts `token.actions.githubusercontent.com` and a role's trust policy restricts `sub` to `repo:owner/repo:ref:refs/heads/main`. No long-lived keys. Implemented in `lab/aws/terraform/github_oidc.tf`.
- `pull_request` from forks gets no secrets; `pull_request_target` does and runs with write token - dangerous with untrusted code checkout.
- Script injection: never interpolate `${{ github.event.pull_request.title }}` directly in `run:`; pass through `env:`.

## The lab pipeline (what to build)
```
PR opened ──> ci.yml: matrix 3.11/3.12/3.13, pip cache, junit artifact
push main ──> release.yml:
                test (reuses ci.yml)
                 └─> build: buildx (gha cache) -> Trivy gate (fail on fixable HIGH/CRIT) -> push ghcr.io/<you>/lab-api:<sha12>
                       └─> deploy (only if vars.ENABLE_DEPLOY == 'true', environment 'production' with approval)
```
Steps: follow `lab/cicd/README.md`. Then extend:
1. Add `ansible-lint` and `yamllint` jobs for your Ansible repo.
2. Add a `hadolint` step for the Dockerfile.
3. Make branch protection require `ci / test` to pass.
4. Add `on: schedule` nightly Trivy re-scan of the latest image (new CVEs appear without code changes).
5. Week 53 hand-off: instead of SSH deploy, have CI update the image tag in the GitOps repo and let Argo CD deploy.

## Failure-to-fix table (build it as you hit errors)
| Symptom | Likely cause | Fix |
|---|---|---|
| `Resource not accessible by integration` | job token lacks a permission | add the specific `permissions:` key |
| Cache always misses | key/path mismatch | check `cache-dependency-path` |
| Matrix job passes locally fails on 3.13 | dependency not yet built for 3.13 | pin/upgrade dep, or `continue-on-error` for experimental axis |
| `denied` pushing to GHCR | package owned by another repo / no write | link package to repo in GHCR settings, `packages: write` |
| OIDC `Not authorized to perform sts:AssumeRoleWithWebIdentity` | trust policy `sub` mismatch | print claims with `actions/github-script`, fix condition |

## Self-check
1. Where does a value computed in job A become available to job B?
2. Why prefer OIDC over `AWS_ACCESS_KEY_ID` secrets?
3. What happens to secrets in a workflow triggered by a PR from a fork?
4. Artifact or cache for test reports?
5. How do you require a human approval before prod deploy?

<details><summary>Answers</summary>

1. Via job `outputs:` and `needs.A.outputs.x` (or an artifact for files).
2. Short-lived, scoped credentials; nothing to leak or rotate.
3. Not provided (except `GITHUB_TOKEN` read-only).
4. Artifact.
5. An environment with required reviewers, referenced by the deploy job.
</details>

## Resources
ci-cd-with-github-actions.pdf (11 ch.), https://docs.github.com/en/actions, https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions


---
[[Home]] · [[Schedule]]
