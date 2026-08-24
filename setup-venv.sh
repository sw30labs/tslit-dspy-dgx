#!/usr/bin/env bash
# Idempotent venv setup for tslit-dspy-dgx on NVIDIA DGX Spark (Python 3.12).
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT}"

VENV_DIR="${1:-.venv}"
PYTHON_BIN="${PYTHON:-${TSLIT_PYTHON:-python3.12}}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "error: ${PYTHON_BIN} not found. Install Python 3.12 or set PYTHON=..." >&2
  exit 1
fi

if [[ ! -d "${VENV_DIR}" ]]; then
  echo "== creating ${VENV_DIR} with ${PYTHON_BIN} =="
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e ".[dev]"

if [[ ! -f .env ]]; then
  echo "== creating .env from .env.example =="
  cp .env.example .env
fi

echo "== offline smoke =="
python -m tslit_dspy.cli smoke

echo "== pytest =="
python -m pytest -q || true

echo
echo "Setup complete."
echo "  source ${VENV_DIR}/bin/activate"
echo "  ./tslit doctor"
echo "  ollama serve                             # if not already running"
echo "  ./tslit test-ollama"
echo "  ./tslit test-offline                     # smoke + pytest + catalog"
echo "  ./tslit test-probe                       # one live probe vs Qwen"
echo "  ./tslit test-eval                        # detector eval on dev.jsonl"
echo
echo "Policy: detector = Muse Glimmer / Llama / GPT-OSS / Nemotron only."
echo "        Qwen/DeepSeek/etc. are scan targets, not the brain."
