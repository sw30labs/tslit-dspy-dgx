#!/usr/bin/env bash
# Start/stop shared Desktop vLLM recipes for TSLIT-DSPy DGX.
# Wraps serve-local-llm.sh with the correct digitalTwin-dgx PROJECT_DIR.
set -euo pipefail

SERVE="${SERVE_LOCAL_LLM:-${HOME}/Desktop/serve-local-llm.sh}"
export PROJECT_DIR="${PROJECT_DIR:-${HOME}/Desktop/digitalTwin-dgx}"
# Avoid vLLM crash when compose injects an empty ALLREDUCE backend.
export VLLM_FLASHINFER_ALLREDUCE_BACKEND="${VLLM_FLASHINFER_ALLREDUCE_BACKEND:-auto}"

if [[ ! -x "${SERVE}" ]]; then
  echo "error: missing ${SERVE}" >&2
  exit 1
fi

cmd="${1:-status}"
recipe="${2:-}"

case "${cmd}" in
  up|start)
    recipe="${recipe:-qwen27}"
    echo "[tslit-vllm] PROJECT_DIR=${PROJECT_DIR} recipe=${recipe}"
    # Clear stale empty exports from prior failed runs in this shell tree
    if [[ -z "${VLLM_FLASHINFER_ALLREDUCE_BACKEND}" ]]; then
      export VLLM_FLASHINFER_ALLREDUCE_BACKEND=auto
    fi
    exec env VLLM_FLASHINFER_ALLREDUCE_BACKEND="${VLLM_FLASHINFER_ALLREDUCE_BACKEND}" \
      "${SERVE}" up "${recipe}"
    ;;
  down|stop)
    exec "${SERVE}" down
    ;;
  status)
    exec "${SERVE}" status
    ;;
  smoke)
    exec "${SERVE}" smoke ${recipe:+"${recipe}"}
    ;;
  wait)
    # wait until /v1/models responds
    url="${VLLM_BASE_URL:-http://127.0.0.1:8000/v1}/models"
    deadline=$((SECONDS + ${WAIT_TIMEOUT_S:-600}))
    echo "[tslit-vllm] waiting for ${url} (timeout ${WAIT_TIMEOUT_S:-600}s)"
    while (( SECONDS < deadline )); do
      if curl -sf --max-time 3 -H 'Authorization: Bearer local' "${url}" >/dev/null; then
        echo "[tslit-vllm] ready"
        curl -sS --max-time 5 -H 'Authorization: Bearer local' "${url}" | python3 -m json.tool | head -40
        exit 0
      fi
      sleep 5
    done
    echo "error: vLLM did not become ready" >&2
    exit 1
    ;;
  *)
    echo "Usage: $0 {up|down|status|smoke|wait} [recipe]" >&2
    echo "  recipes: qwen27 (scan target) | nemotron-super (detector)" >&2
    exit 1
    ;;
esac
