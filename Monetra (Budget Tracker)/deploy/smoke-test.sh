#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${MONETRA_BASE_URL:?Set MONETRA_BASE_URL, for example https://staging.example.com}"
TIMEOUT_SECONDS="${SMOKE_TIMEOUT_SECONDS:-15}"
RETRY_SECONDS="${SMOKE_RETRY_SECONDS:-120}"
SLEEP_SECONDS="${SMOKE_SLEEP_SECONDS:-5}"

health_checked=false
health_urls=("$BASE_URL/api/health")

if [ -n "${MONETRA_FRONTEND_URL:-}" ] && [ "$MONETRA_FRONTEND_URL" != "$BASE_URL" ]; then
  health_urls+=("$MONETRA_FRONTEND_URL/api/health")
fi

deadline=$((SECONDS + RETRY_SECONDS))

while [ "$SECONDS" -lt "$deadline" ] && [ "$health_checked" != "true" ]; do
  for health_url in "${health_urls[@]}"; do
    echo "Checking Monetra health at $health_url"
    if curl --fail --silent --show-error --connect-timeout 5 --max-time "$TIMEOUT_SECONDS" "$health_url" >/tmp/monetra-health.json; then
      cat /tmp/monetra-health.json
      health_checked=true
      break
    fi
  done

  if [ "$health_checked" != "true" ]; then
    echo "Monetra is not reachable yet. Retrying in ${SLEEP_SECONDS}s..."
    sleep "$SLEEP_SECONDS"
  fi
done

if [ "$health_checked" != "true" ]; then
  echo "Monetra health check failed for all configured URLs." >&2
  exit 1
fi

if [ -n "${MONETRA_FRONTEND_URL:-}" ]; then
  frontend_checked=false
  deadline=$((SECONDS + RETRY_SECONDS))

  while [ "$SECONDS" -lt "$deadline" ] && [ "$frontend_checked" != "true" ]; do
    echo "Checking Monetra frontend at $MONETRA_FRONTEND_URL"
    if curl --fail --silent --show-error --connect-timeout 5 --max-time "$TIMEOUT_SECONDS" "$MONETRA_FRONTEND_URL" >/dev/null; then
      frontend_checked=true
      break
    fi

    echo "Monetra frontend is not reachable yet. Retrying in ${SLEEP_SECONDS}s..."
    sleep "$SLEEP_SECONDS"
  done

  if [ "$frontend_checked" != "true" ]; then
    echo "Monetra frontend check failed for $MONETRA_FRONTEND_URL." >&2
    exit 1
  fi
fi

echo "Monetra smoke checks passed for $BASE_URL"
