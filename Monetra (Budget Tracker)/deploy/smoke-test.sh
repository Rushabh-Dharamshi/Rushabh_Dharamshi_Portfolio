#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${MONETRA_BASE_URL:?Set MONETRA_BASE_URL, for example https://staging.example.com}"
TIMEOUT_SECONDS="${SMOKE_TIMEOUT_SECONDS:-15}"

health_checked=false
health_urls=("$BASE_URL/api/health")

if [ -n "${MONETRA_FRONTEND_URL:-}" ] && [ "$MONETRA_FRONTEND_URL" != "$BASE_URL" ]; then
  health_urls+=("$MONETRA_FRONTEND_URL/api/health")
fi

for health_url in "${health_urls[@]}"; do
  echo "Checking Monetra health at $health_url"
  if curl --fail --silent --show-error --connect-timeout 5 --max-time "$TIMEOUT_SECONDS" "$health_url" >/tmp/monetra-health.json; then
    cat /tmp/monetra-health.json
    health_checked=true
    break
  fi
done

if [ "$health_checked" != "true" ]; then
  echo "Monetra health check failed for all configured URLs." >&2
  exit 1
fi

if [ -n "${MONETRA_FRONTEND_URL:-}" ]; then
  curl --fail --silent --show-error --max-time "$TIMEOUT_SECONDS" "$MONETRA_FRONTEND_URL" >/dev/null
fi

echo "Monetra smoke checks passed for $BASE_URL"
