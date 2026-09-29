#!/usr/bin/env bash
# Week 20: vulnerability + misconfig scanning. Fails (exit 1) on HIGH/CRITICAL fixable vulns.
set -euo pipefail
cd "$(dirname "$0")"
command -v trivy >/dev/null || { echo "install trivy: ../lab.sh tools trivy"; exit 1; }
docker build -t lab-api:local --target runtime app
echo "== image vulnerabilities"
trivy image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 lab-api:local
echo "== Dockerfile + compose misconfigurations"
trivy config --severity HIGH,CRITICAL .
echo "== secrets in the repo"
trivy fs --scanners secret .
