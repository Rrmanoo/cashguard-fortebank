#!/usr/bin/env bash
# Run on a dedicated GPU host after installing the model-compatible vLLM build.
set -euo pipefail
umask 077
: "${MODEL_PATH:?Set MODEL_PATH to the existing Qwen3.6 FP8 weights directory}"
export CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-0}
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1
exec "${VLLM_BIN:-vllm}" serve "$MODEL_PATH" \
 --served-model-name qwen --host 127.0.0.1 --port "${MODEL_PORT:-9003}" \
 --tensor-parallel-size 1 --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION:-0.80}" \
 --max-model-len 32768 --max-num-seqs 4 \
 --limit-mm-per-prompt '{"image":16,"video":0}' --dtype auto
