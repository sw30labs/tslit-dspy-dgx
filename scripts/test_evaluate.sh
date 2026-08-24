#!/usr/bin/env bash
# d) Detector eval on labeled JSONL (does not probe a live target).
#
#   ./scripts/test_evaluate.sh              # workspace/data/dev.jsonl
#   ./scripts/test_evaluate.sh test         # frozen test.jsonl
#   ./scripts/test_evaluate.sh path.jsonl
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

usage() {
  cat <<EOF
Usage: $(basename "$0") [dev|test|path.jsonl] [-- extra evaluate args]

Score the compiled (or zero-shot) detector on frozen labeled examples.
This is detector QA, not a live integrity scan.

Default set: workspace/data/dev.jsonl
Output:      workspace/evaluation/<name>_eval.md
EOF
}

SET_ARG="dev"
EXTRA=()
if (($#)) && [[ "$1" == "-h" || "$1" == "--help" ]]; then
  usage
  exit 0
fi
if (($#)) && [[ "$1" != -- && "$1" != -* ]]; then
  SET_ARG="$1"
  shift
fi
if (($#)) && [[ "$1" == "--" ]]; then
  shift
fi
EXTRA+=("$@")

require_venv
require_ollama
cd "${TSLIT_ROOT}"

case "${SET_ARG}" in
  dev)  TEST_PATH="workspace/data/dev.jsonl"; NAME="dev" ;;
  test) TEST_PATH="workspace/data/test.jsonl"; NAME="test" ;;
  *)
    TEST_PATH="${SET_ARG}"
    NAME="$(basename "${TEST_PATH}" .jsonl)"
    ;;
esac

[[ -f "${TEST_PATH}" ]] || die "missing test set: ${TEST_PATH}"

COMPILED="workspace/compiled/tslit_analyzer_optimized.json"
OUT="workspace/evaluation/${NAME}_eval.md"
EVAL_ARGS=(evaluate --test "${TEST_PATH}" --output "${OUT}" --model ollama)
if [[ -f "${COMPILED}" ]]; then
  EVAL_ARGS+=(--use-compiled)
  COMPILED_NOTE="yes (${COMPILED})"
else
  COMPILED_NOTE="missing — zero-shot"
fi

banner "TSLIT evaluate (detector, not a live target)"
echo "  set:        ${TEST_PATH}"
echo "  detector:   ${DEFAULT_DETECTOR}"
echo "  compiled:   ${COMPILED_NOTE}"
echo "  output:     ${OUT}"

tslit "${EVAL_ARGS[@]}" "${EXTRA[@]}"
echo "report: ${OUT}"
