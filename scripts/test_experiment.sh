#!/usr/bin/env bash
# Cartoon exam on frozen test.jsonl (no MIPROv2 recompile unless --full).
#
#   ./scripts/test_experiment.sh
#   ./scripts/test_experiment.sh --full    # optimize + eval (long)
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

usage() {
  cat <<EOF
Usage: $(basename "$0") [--full]

Default: ./tslit experiment --mini  (uses existing compiled prompts).
--full:  MIPROv2 recompile + eval (hours).
EOF
}

FULL=false
while (($#)); do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --full) FULL=true; shift ;;
    *) die "unknown arg: $1" ;;
  esac
done

require_venv
require_ollama
cd "${TSLIT_ROOT}"

if [[ "${FULL}" == true ]]; then
  banner "TSLIT experiment (full MIPROv2 + eval)"
  tslit experiment
else
  banner "TSLIT experiment --mini"
  tslit experiment --mini
fi
