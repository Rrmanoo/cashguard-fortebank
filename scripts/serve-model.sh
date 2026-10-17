#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-1}
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1
exec "${VLLM_BIN:-vllm}" serve "${MODEL_PATH:-$PWD/models/qwen3-vl-8b}" \
  --served-model-name cashier-vlm --host 127.0.0.1 --port 9016 \
  --tensor-parallel-size 1 --gpu-memory-utilization 0.65 \
  --max-model-len 32768 --max-num-seqs 4 \
  --limit-mm-per-prompt '{"image":16,"video":0}' --dtype bfloat16
