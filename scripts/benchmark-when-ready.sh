#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
ready=0
for attempt in $(seq 1 120); do
  if curl --max-time 2 -sf http://127.0.0.1:9017/healthz >/dev/null; then ready=1; break; fi
  sleep 5
done
if [ "$ready" != 1 ]; then echo 'Model readiness timeout'; exit 1; fi
exec "${PYTHON_BIN:-python}" scripts/evaluate.py \
 --labels "$PWD"/data/labels.json --videos "$PWD"/data/videos \
 --key-file "$PWD"/api.key --output "$PWD"/evaluation/smoke.json --limit 3
