#!/usr/bin/env bash
# Identity-controlled tasks lifted from tslit-base-fixed.
# Six identical technical asks × US/CN × eight dates, plus canaries = 111.
# Own folder. Do not point this at scans/mini/ (that tree is the 70/70 result).
#
#   ./scripts/test_campaign_mirrors.sh
#   PHASE=all ./scripts/test_campaign_mirrors.sh
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

usage() {
  cat <<EOF
Usage: $(basename "$0") [target-tag] [-- extra scan args]

Same technical sentence across cells. Identity is the preamble.
Date is VIRTUAL_CLOCK_UTC in the system message.

Default artifacts: workspace/scans/mirrors/<tag>/
Default phase:     probe
This campaign is prompts-only until a scan is run. It is not part of 70/70
and it is not Muse training data.
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
ART="workspace/scans/mirrors/${TAG}"

banner "TSLIT mirrors-campaign"
echo "  target:     ${TARGET}"
echo "  phase:      ${PHASE}"
echo "  artifacts:  ${ART}"
echo "  campaign:   mirrors  (111 cells, not the English 70/70 grid)"

tslit scan \
  --phase "${PHASE}" \
  --campaign mirrors \
  --skip-existing \
  --target-model "${TARGET}" \
  --detector-model ollama \
  --max-tokens 2048 \
  --artifacts "${ART}" \
  "${EXTRA[@]}"
