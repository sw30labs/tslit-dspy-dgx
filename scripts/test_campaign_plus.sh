#!/usr/bin/env bash
# Increment the mini campaign with old TSLIT affiliations / dates / tasks.
#
# Default artifacts: the existing mini folder, skipping the 14 already on disk.
#
#   ./scripts/test_campaign_plus.sh
#   PHASE=probe ./scripts/test_campaign_plus.sh
#   ./scripts/test_campaign_plus.sh qwen3.8:27b-mtp-bf16 -- --limit 2
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

usage() {
  cat <<EOF
Usage: $(basename "$0") [target-tag] [-- extra scan args]

Adds whitepaper affiliations, extra trigger dates, and recovered tasks
(packet inspect / AES / backup) that were not in the 14-probe mini grid.
Does not replay labeled JSONL responses (those are detector training).

Default artifacts: workspace/scans/mini/<tag>/  (skip-existing on)
Default phase:     probe  (set PHASE=all to also analyze)
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

banner "TSLIT plus-campaign (old TSLIT increment)"
echo "  target:     ${TARGET}"
echo "  phase:      ${PHASE}"
echo "  artifacts:  ${ART}  (skip-existing)"
echo "  campaign:   plus"

tslit scan \
  --phase "${PHASE}" \
  --campaign plus \
  --skip-existing \
  --target-model "${TARGET}" \
  --detector-model ollama \
  --max-tokens 2048 \
  --artifacts "${ART}" \
  "${EXTRA[@]}"
