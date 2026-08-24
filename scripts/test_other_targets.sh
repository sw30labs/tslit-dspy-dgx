#!/usr/bin/env bash
# c) One probe (default) against every target-only tag served on this box.
#
#   ./scripts/test_other_targets.sh
#   ./scripts/test_other_targets.sh --full          # mini-campaign per target
#   ./scripts/test_other_targets.sh ornith-1.5:35b  # subset
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

usage() {
  cat <<EOF
Usage: $(basename "$0") [--full] [--analyze] [target-tag ...]

Probe each adversary-origin tag listed in model_policy (and present in
\`ollama list\`). Default is one probe per target so DeepSeek/Qwen swaps
stay cheap. --full runs the mini campaign; --analyze also runs the detector.

Known target-only tags:
$(policy_targets | sed 's/^/  /')
EOF
}

FULL=false
PHASE="${PHASE:-probe}"
LIMIT="${LIMIT:-1}"
REQUESTED=()
EXTRA=()
while (($#)); do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --full) FULL=true; LIMIT=""; shift ;;
    --analyze) PHASE="all"; shift ;;
    --) shift; EXTRA+=("$@"); break ;;
    *)
      REQUESTED+=("$1")
      shift
      ;;
  esac
done

if [[ "${FULL}" == true ]]; then
  LIMIT=""
fi

require_venv
require_ollama
cd "${TSLIT_ROOT}"

mapfile -t POLICY < <(policy_targets)
mapfile -t SERVED < <(served_models)

if ((${#REQUESTED[@]})); then
  CANDIDATES=("${REQUESTED[@]}")
else
  CANDIDATES=("${POLICY[@]}")
fi

TARGETS=()
SKIPPED=()
for tag in "${CANDIDATES[@]}"; do
  found=false
  for s in "${SERVED[@]}"; do
    if [[ "${s}" == "${tag}" ]]; then
      found=true
      break
    fi
  done
  if [[ "${found}" == true ]]; then
    TARGETS+=("${tag}")
  else
    SKIPPED+=("${tag}")
  fi
done

banner "TSLIT other-targets"
echo "  served:     ${SERVED[*]}"
echo "  will scan:  ${TARGETS[*]:-(none)}"
if ((${#SKIPPED[@]})); then
  echo "  skipped (not in catalog): ${SKIPPED[*]}"
fi
echo "  phase:      ${PHASE}"
echo "  limit:      ${LIMIT:-none (full mini campaign)}"

((${#TARGETS[@]})) || die "no target tags present in Ollama catalog"

failed=0
for tag in "${TARGETS[@]}"; do
  ART="workspace/scans/targets/$(safe_tag "${tag}")"
  banner "target ${tag}"
  echo "  artifacts: ${ART}"
  scan_args=(
    scan
    --phase "${PHASE}"
    --target-model "${tag}"
    --artifacts "${ART}"
  )
  if [[ -n "${LIMIT}" ]]; then
    scan_args+=(--limit "${LIMIT}")
  fi
  if [[ "${PHASE}" == "all" || "${PHASE}" == "analyze" ]]; then
    scan_args+=(--detector-model ollama)
  fi
  if tslit "${scan_args[@]}" "${EXTRA[@]}"; then
    echo "  ok: ${tag}"
  else
    echo "  FAIL: ${tag}" >&2
    failed=$((failed + 1))
  fi
done

if ((failed)); then
  die "${failed} target(s) failed"
fi
echo
echo "all requested targets finished."
