#!/usr/bin/env bash
# a) One live probe against a target (default: Qwen). No detector pass.
#
#   ./scripts/test_one_probe.sh
#   ./scripts/test_one_probe.sh qwen3.8:27b-mtp-bf16
#   ./scripts/test_one_probe.sh ornith-1.5:35b -- --max-tokens 400
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

usage() {
  cat <<EOF
Usage: $(basename "$0") [target-tag] [-- extra scan args]

Send a single integrity probe to a live Ollama target. Does not run the
detector (use test_mini_campaign.sh for probe + analyze).

Default target: ${DEFAULT_TARGET}
Artifacts:      workspace/scans/one_probe/<tag>/
EOF
}

TARGET="${DEFAULT_TARGET}"
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
ART="workspace/scans/one_probe/${TAG}"

banner "TSLIT one-probe"
echo "  target:     ${TARGET}"
echo "  detector:   (skipped — probe only)"
echo "  limit:      1"
echo "  artifacts:  ${ART}"
if ! model_in_catalog "${TARGET}"; then
  echo "  warn: ${TARGET} not in ollama catalog — scan will still request it"
fi

tslit scan \
  --phase probe \
  --target-model "${TARGET}" \
  --limit 1 \
  --artifacts "${ART}" \
  "${EXTRA[@]}"
