#!/bin/sh
set -eu

EDITION="${CNEXUS_EDITION:-personal}"
API_BASE="${CNEXUS_API_BASE:-http://localhost:8000}"
WS_BASE="${CNEXUS_WS_BASE:-${API_BASE/http/ws}}"
API_TOKEN="${CNEXUS_API_TOKEN:-}"

mkdir -p ./public

if [ -n "$API_TOKEN" ]; then
  cat > ./public/cnexus-config.json <<EOF
{"edition":"${EDITION}","apiBase":"${API_BASE}","wsBase":"${WS_BASE}","apiToken":"${API_TOKEN}"}
EOF
else
  cat > ./public/cnexus-config.json <<EOF
{"edition":"${EDITION}","apiBase":"${API_BASE}","wsBase":"${WS_BASE}"}
EOF
fi

echo "CNexus Product (${EDITION}): api=${API_BASE} ws=${WS_BASE}"

exec "$@"
