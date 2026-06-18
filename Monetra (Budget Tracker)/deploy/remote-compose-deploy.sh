#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/monetra}"
GIT_BRANCH="${GIT_BRANCH:-main}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
ENV_FILE="${ENV_FILE:-.env.production}"

cd "$APP_DIR"

git fetch origin "$GIT_BRANCH"
git checkout "$GIT_BRANCH"
git pull --ff-only origin "$GIT_BRANCH"

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing environment file: $APP_DIR/$ENV_FILE" >&2
  exit 1
fi

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build --remove-orphans
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps
