#!/bin/sh
set -e

echo "[cnexus-runtime] deploy_level=${CNEXUS_DEPLOY_LEVEL:-dev}"

python -c "from api.license_guard import verify_license_or_exit; verify_license_or_exit()"

exec "$@"
