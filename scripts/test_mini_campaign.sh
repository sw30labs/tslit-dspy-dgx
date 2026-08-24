#!/usr/bin/env bash
# b) Full mini campaign: ~14 probes + Muse Glimmer analysis on the same Ollama.
#
#   ./scripts/test_mini_campaign.sh
#   ./scripts/test_mini_campaign.sh qwen3.8:27b-mtp-bf16
#   PHASE=probe ./scripts/test_mini_campaign.sh   # skip detector
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

usage() {
  cat <<EOF
Usage: $(basename "$0") [target-tag] [-- extra scan args]

Run the compact TSLIT campaign (date canaries + affiliation grid on two
coding tasks), then analyze replies with the non-adversary detector.

Default target: ${DEFAULT_TARGET}
Default phase:  all  (override with PHASE=probe|analyze|all)
Artifacts:      workspace/scans/mini/<tag>/
EOF
}

TARGET="${DEFAULT_TARGET}"
PHASE="${PHASE:-all}"
EXTRA=()
while (($#)); do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --) shift; EXTRA+=("$@"); break ;;
    -*) die "unknown option $1 (pass scan flags after --)" ;;
    *) TARGET="$1"; shift ;;
  esac
done

require_venv
require_ollama
cd "${TSLIT_ROOT}"

TAG="$(safe_tag "${TARGET}")"
ART="workspace/scans/mini/${TAG}"

banner "TSLIT mini-campaign"
echo "  target:     ${TARGET}"
echo "  detector:   ${DEFAULT_DETECTOR} (OLLAMA_MODEL)"
echo "  phase:      ${PHASE}"
echo "  artifacts:  ${ART}"
if ! model_in_catalog "${TARGET}"; then
  echo "  warn: ${TARGET} not in ollama catalog — scan will still request it"
fi

tslit scan \
  --phase "${PHASE}" \
  --target-model "${TARGET}" \
  --detector-model ollama \
  --artifacts "${ART}" \
  "${EXTRA[@]}"
