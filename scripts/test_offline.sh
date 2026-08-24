#!/usr/bin/env bash
# Offline / cheap checks: pytest, smoke, doctor, Ollama catalog (no completion).
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

usage() {
  cat <<EOF
Usage: $(basename "$0")

No live target probes. Runs:
  ./tslit smoke
  ./tslit pytest -q
  ./tslit doctor
  ./tslit test-ollama --skip-invoke
EOF
}

if (($#)) && [[ "$1" == "-h" || "$1" == "--help" ]]; then
  usage
  exit 0
fi

require_venv
cd "${TSLIT_ROOT}"

banner "TSLIT offline"
tslit smoke
tslit pytest -q

banner "doctor + Ollama catalog"
if curl -sf --max-time 3 "${OLLAMA_BASE_URL}/api/tags" >/dev/null; then
  tslit doctor
  tslit test-ollama --skip-invoke
else
  echo "Ollama not reachable at ${OLLAMA_BASE_URL} — skipping doctor live checks."
  echo "Start with: ollama serve"
fi

echo
echo "offline: OK"
