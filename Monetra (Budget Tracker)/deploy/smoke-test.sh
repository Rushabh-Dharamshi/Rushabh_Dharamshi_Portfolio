#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${MONETRA_BASE_URL:?Set MONETRA_BASE_URL, for example https://staging.example.com}"
TIMEOUT_SECONDS="${SMOKE_TIMEOUT_SECONDS:-15}"

curl --fail --silent --show-error --max-time "$TIMEOUT_SECONDS" "$BASE_URL/api/health" >/tmp/monetra-health.json
cat /tmp/monetra-health.json

if [ -n "${MONETRA_FRONTEND_URL:-}" ]; then
  curl --fail --silent --show-error --max-time "$TIMEOUT_SECONDS" "$MONETRA_FRONTEND_URL" >/dev/null
fi

echo "Monetra smoke checks passed for $BASE_URL"
