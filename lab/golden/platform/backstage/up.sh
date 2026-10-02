#!/usr/bin/env bash
# Phase 27 (CBA) - local Backstage demo on Docker.
# Needs: Docker (compose v2), Node.js 20 or 22 (LTS) + corepack (yarn), ~6 GiB free RAM, ~5 GiB disk for node_modules.
#   ./up.sh          create ./app with create-app (first run only), build the backend image, start compose
#   ./up.sh build    rebuild the image after you change code in ./app (plugins, theme, backend modules)
#   ./up.sh logs     follow the Backstage logs (catalog processing errors show up here)
#   ./up.sh down     stop containers (add -v yourself to drop the Postgres volume)
# Optional: export GITHUB_TOKEN=<pat with repo scope> before 'up' for a real scaffolder run.
set -euo pipefail
cd "$(dirname "$0")"
need() { command -v "$1" >/dev/null || { echo "missing $1 - see header"; exit 1; }; }

build() {
  need node; need docker
  corepack enable >/dev/null 2>&1 || true
  if [ ! -d app ]; then
    echo ">> creating Backstage app in ./app (takes a few minutes)"
    BACKSTAGE_APP_NAME=app npx -y @backstage/create-app@latest --path app
  fi
  (cd app && yarn install --immutable && yarn tsc && yarn build:backend && yarn build-image)
}

case "${1:-up}" in
  up)
    docker image inspect backstage:latest >/dev/null 2>&1 || build
    docker compose up -d
    echo ">> waiting for http://localhost:7007 ..."
    for _ in $(seq 1 60); do
      curl -fsS -o /dev/null http://localhost:7007/.backstage/health/v1/readiness && break
      sleep 5
    done
    echo ">> open http://localhost:7007 (Enter as guest). Catalog: team-payments, payments, payments-api, payments-web"
    echo ">> template dry run: http://localhost:7007/create/edit" ;;
  build) build; docker compose up -d --force-recreate backstage ;;
  logs)  docker compose logs -f backstage ;;
  down)  docker compose down ;;
  *) echo "usage: $0 [up|build|logs|down]"; exit 1 ;;
esac
