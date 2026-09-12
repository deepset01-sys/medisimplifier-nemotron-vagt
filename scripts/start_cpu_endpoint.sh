#!/usr/bin/env bash
# start_cpu_endpoint.sh — launch the CPU audit_panel service.
# cd into /app/src so `cpu_endpoint:app` and audit_panel's flat imports resolve.
set -euo pipefail
cd /app/src
exec python3 -m uvicorn cpu_endpoint:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --workers 1
