#!/usr/bin/env bash
# start_endpoint.sh — Boot vLLM + Safe Simplification Endpoint (the image's entry point, /start.sh)
# Usage: bash scripts/start_endpoint.sh
# Requires: NEBIUS_API_KEY, QWEN_JUDGE_MODEL, LLAMA_JUDGE_MODEL (routing keys of your two Token Factory dedicated
#           judge endpoints). No HuggingFace token: the model is public.
# Optional: VLLM_START_TIMEOUT — seconds to wait for vLLM to become ready before giving up (default 1800).

set -euo pipefail

MODEL="chambul/MediSimplifier-OpenBioLLM-v2-merged"
MODEL_REVISION="bf7f42f53d67786dbfa5624cd2fd5647b9bd93eb"   # pinned HuggingFace revision of the served model
VLLM_PORT=8001
API_PORT=8000
START_TIMEOUT="${VLLM_START_TIMEOUT:-1800}"

echo "==> Starting vLLM on :${VLLM_PORT}..."
python3 -m vllm.entrypoints.openai.api_server \
    --model "${MODEL}" \
    --revision "${MODEL_REVISION}" \
    --tokenizer-revision "${MODEL_REVISION}" \
    --port "${VLLM_PORT}" \
    --host 127.0.0.1 \
    --dtype float16 \
    --max-model-len 4096 &
VLLM_PID=$!

echo "==> Waiting for vLLM to load (usually 10-15 min; giving up after ${START_TIMEOUT} s)..."
waited=0
until [ "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:${VLLM_PORT}/health)" = "200" ]; do
    if ! kill -0 "${VLLM_PID}" 2>/dev/null; then
        code=0
        wait "${VLLM_PID}" || code=$?
        echo "ERROR: vLLM exited before it was ready (exit code ${code}); see its log above." >&2
        exit 1
    fi
    if [ "${waited}" -ge "${START_TIMEOUT}" ]; then
        echo "ERROR: vLLM was not ready after ${START_TIMEOUT} s; stopping it." >&2
        kill "${VLLM_PID}" 2>/dev/null || true
        exit 1
    fi
    echo "Waiting for vLLM... (${waited} s)"
    sleep 15
    waited=$((waited + 15))
done
echo "==> vLLM ready."

echo "==> Starting Safe Endpoint API on :${API_PORT}..."
cd /app/src
python3 -m uvicorn safe_endpoint:app --host 0.0.0.0 --port ${API_PORT}

wait ${VLLM_PID}
