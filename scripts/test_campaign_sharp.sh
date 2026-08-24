#!/usr/bin/env bash
# Clock-native / dual-use increment (cert expiry, feature flags, JWT nbf/exp, FFT).
# 4 tasks × 5 cells = 20 probes. Skips ids already in the mini folder.
#
#   ./scripts/test_campaign_sharp.sh
#   PHASE=all ./scripts/test_campaign_sharp.sh
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

usage() {
  cat <<EOF
Usage: $(basename "$0") [target-tag] [-- extra scan args]

High-signal probes: the technical ask requires "today" or is dual-use DSP.
Grid per task: corporate/Jan15, US-mil/9-11, PRC-gov/9-11, US-mil/Jun4, PRC-gov/Jun4.

Default artifacts: workspace/scans/mini/<tag>/  (skip-existing on)
Default phase:     probe
EOF
}

TARGET="${DEFAULT_TARGET}"
PHASE="${PHASE:-probe}"
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

banner "TSLIT sharp-campaign"
echo "  target:     ${TARGET}"
echo "  phase:      ${PHASE}"
echo "  artifacts:  ${ART}  (skip-existing)"
echo "  campaign:   sharp  (20 clock-native cells)"

tslit scan \
  --phase "${PHASE}" \
  --campaign sharp \
  --skip-existing \
  --target-model "${TARGET}" \
  --detector-model ollama \
  --max-tokens 2048 \
  --artifacts "${ART}" \
  "${EXTRA[@]}"
