#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
export CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-1}
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 DO_NOT_TRACK=1
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4
export CASHGUARD_DATA=${CASHGUARD_DATA:-$PWD/runtime}
export CASHGUARD_MODELS=${CASHGUARD_MODELS:-$PWD/models}
export CASHGUARD_EXAMPLES=${CASHGUARD_EXAMPLES:-$PWD/examples}
export CASHGUARD_API_KEY_FILE=${CASHGUARD_API_KEY_FILE:-$PWD/api.key}
exec "${PYTHON_BIN:-python}" -m uvicorn app.main:app --host 127.0.0.1 --port 9017 --workers 1 --no-access-log
