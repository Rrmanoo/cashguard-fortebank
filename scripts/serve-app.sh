#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
exec "${PYTHON_BIN:-python3}" -m uvicorn app.main:app --host 127.0.0.1 --port 9017 --workers 1 --no-access-log --proxy-headers --forwarded-allow-ips 127.0.0.1
