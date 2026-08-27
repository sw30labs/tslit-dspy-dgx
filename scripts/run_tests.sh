#!/usr/bin/env bash
# Index for the TSLIT test scripts.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

usage() {
  cat <<EOF
Usage: $(basename "$0") <command> [args...]

Live target (integrity scan — talks to Qwen/DeepSeek/Ornith):
  probe       a) one probe          scripts/test_one_probe.sh
  campaign    b) mini campaign      scripts/test_mini_campaign.sh
  plus           increment from old TSLIT  scripts/test_campaign_plus.sh
  sharp          clock-native dual-use grid  scripts/test_campaign_sharp.sh
  targets     c) other box targets  scripts/test_other_targets.sh

Detector / harness (Muse Glimmer on labeled data, or no GPU):
  evaluate    d) detector eval      scripts/test_evaluate.sh
  experiment     cartoon exam       scripts/test_experiment.sh
  offline        smoke + pytest     scripts/test_offline.sh

Examples:
  ./scripts/run_tests.sh probe
  ./scripts/run_tests.sh campaign qwen3.8:27b-mtp-bf16
  ./scripts/run_tests.sh targets
  ./scripts/run_tests.sh targets --full
  ./scripts/run_tests.sh evaluate
  ./scripts/run_tests.sh evaluate test
  ./scripts/run_tests.sh offline

Same commands also exist as:
  ./tslit test-probe | test-campaign | test-targets | test-eval | test-experiment | test-offline
EOF
}

cmd="${1:-}"
if [[ -z "${cmd}" || "${cmd}" == "-h" || "${cmd}" == "--help" || "${cmd}" == "help" ]]; then
  usage
  exit 0
fi
shift || true

case "${cmd}" in
  probe|one-probe|a) exec bash "${SCRIPT_DIR}/test_one_probe.sh" "$@" ;;
  campaign|mini|b) exec bash "${SCRIPT_DIR}/test_mini_campaign.sh" "$@" ;;
  plus|increment) exec bash "${SCRIPT_DIR}/test_campaign_plus.sh" "$@" ;;
  sharp) exec bash "${SCRIPT_DIR}/test_campaign_sharp.sh" "$@" ;;
  targets|other|c) exec bash "${SCRIPT_DIR}/test_other_targets.sh" "$@" ;;
  evaluate|eval|d) exec bash "${SCRIPT_DIR}/test_evaluate.sh" "$@" ;;
  experiment|mini-exp) exec bash "${SCRIPT_DIR}/test_experiment.sh" "$@" ;;
  offline|smoke) exec bash "${SCRIPT_DIR}/test_offline.sh" "$@" ;;
  *)
    echo "unknown command: ${cmd}" >&2
    usage
    exit 1
    ;;
esac
