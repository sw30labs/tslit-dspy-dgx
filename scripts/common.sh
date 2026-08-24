# Shared helpers for TSLIT test scripts. Source from scripts/*.sh (not exec).
# shellcheck shell=bash

if [[ -z "${TSLIT_ROOT:-}" ]]; then
  TSLIT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
fi

DEFAULT_TARGET="${TSLIT_TARGET:-qwen3.8:27b-mtp-bf16}"
DEFAULT_DETECTOR="${OLLAMA_MODEL:-muse-glimmer:30b-bf16}"
OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"

tslit() {
  "${TSLIT_ROOT}/tslit" "$@"
}

die() {
  echo "error: $*" >&2
  exit 1
}

banner() {
  echo
  echo "========================================"
  echo "$*"
  echo "========================================"
}

safe_tag() {
  echo "$1" | tr '/:' '__'
}

require_venv() {
  [[ -x "${TSLIT_ROOT}/.venv/bin/python" ]] || die "missing .venv — run ./tslit install first"
}

require_ollama() {
  if ! curl -sf --max-time 3 "${OLLAMA_BASE_URL}/api/tags" >/dev/null; then
    die "Ollama not reachable at ${OLLAMA_BASE_URL} — start with: ollama serve"
  fi
}

served_models() {
  curl -sf --max-time 5 "${OLLAMA_BASE_URL}/api/tags" \
    | python3 -c 'import json,sys; d=json.load(sys.stdin); print("\n".join(m.get("name","") for m in d.get("models",[]) if m.get("name")))'
}

policy_targets() {
  if [[ -x "${TSLIT_ROOT}/.venv/bin/python" ]]; then
    "${TSLIT_ROOT}/.venv/bin/python" -c \
      'from tslit_dspy.model_policy import DGX_TARGET_ONLY_MODELS; print("\n".join(DGX_TARGET_ONLY_MODELS))'
  else
    printf '%s\n' \
      "qwen3.8:27b-mtp-bf16" \
      "ornith-1.5:35b" \
      "deepseek-v4-flash-0731:ud-iq2-m"
  fi
}

model_in_catalog() {
  local want="$1"
  served_models | grep -Fxq -- "${want}"
}
