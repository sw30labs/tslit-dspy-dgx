#!/usr/bin/env bash
# Unique English grid × EN/ZH (154 with canaries, 140 with --no-canary).
#
#   ./scripts/test_campaign_full.sh
#   PHASE=probe ./scripts/test_campaign_full.sh
#   ./scripts/test_campaign_full.sh qwen3.8:27b-mtp-bf16 -- --limit 2
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

usage() {
  cat <<EOF
Usage: $(basename "$0") [target-tag] [-- extra scan args]

One campaign: mini ∪ plus ∪ sharp, each cell in English and Mandarin.
Quote EN and ZH as separate tables. Do not fold into English 70/70.

Default artifacts: workspace/scans/full/<tag>/
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
ART="workspace/scans/full/${TAG}"

banner "TSLIT full campaign (EN/ZH twin of unique English grid)"
echo "  target:     ${TARGET}"
echo "  phase:      ${PHASE}"
echo "  artifacts:  ${ART}"
echo "  campaign:   full  (154 with canaries)"

tslit scan \
  --phase "${PHASE}" \
  --campaign full \
  --skip-existing \
  --target-model "${TARGET}" \
  --detector-model ollama \
  --max-tokens 2048 \
  --artifacts "${ART}" \
  "${EXTRA[@]}"
