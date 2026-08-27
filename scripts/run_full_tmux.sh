#!/usr/bin/env bash
# Start --campaign full in tmux so chat wrappers cannot SIGKILL the process group.
#
#   ./scripts/run_full_tmux.sh
#   ./scripts/run_full_tmux.sh qwen3.8:27b-mtp-bf16
#   PHASE=all ./scripts/run_full_tmux.sh
#   ATTACH=1 ./scripts/run_full_tmux.sh
#   SESSION=tslit-full-2 ./scripts/run_full_tmux.sh -- --limit 2
#
# Attach:  tmux attach -t tslit-full
# Detach:  Ctrl-b d
# Log:     tail -f workspace/evaluation/full_campaign.tmux.log
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

SESSION="${SESSION:-tslit-full}"
LOG="${LOG:-${TSLIT_ROOT}/workspace/evaluation/full_campaign.tmux.log}"

usage() {
  cat <<EOF
Usage: $(basename "$0") [target-tag] [-- extra scan args]

Detached tmux session running the 154-cell EN/ZH full campaign
(mini ∪ plus ∪ sharp × both languages). Same flags as test_campaign_full.sh.

  SESSION=name   tmux session (default: tslit-full)
  PHASE=probe|analyze|all   (default: probe)
  ATTACH=1       attach after spawn
  LOG=path       tee target

If ${SESSION} already exists this script refuses to start a second copy.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

# Re-entered as the tmux window command: args are preserved, no extra quoting.
if [[ "${TSLIT_FULL_TMUX_CHILD:-}" == 1 ]]; then
  mkdir -p "$(dirname "${LOG}")"
  {
    echo
    echo "======== $(date -u +%Y-%m-%dT%H:%M:%SZ) session=${SESSION} ========"
    echo "cwd=$(pwd) phase=${PHASE:-probe} args=$*"
  } | tee -a "${LOG}"
  set +e
  "${SCRIPT_DIR}/test_campaign_full.sh" "$@" 2>&1 | tee -a "${LOG}"
  rc=${PIPESTATUS[0]}
  echo "DONE $(date -u +%Y-%m-%dT%H:%M:%SZ) exit=${rc}" | tee -a "${LOG}"
  exec bash
fi

command -v tmux >/dev/null 2>&1 || die "tmux not installed"

if tmux has-session -t "${SESSION}" 2>/dev/null; then
  echo "session ${SESSION} already running"
  echo "  attach: tmux attach -t ${SESSION}"
  echo "  log:    tail -f ${LOG}"
  exit 1
fi

mkdir -p "$(dirname "${LOG}")"
cd "${TSLIT_ROOT}"

# New session whose main process is this script (child mode). Parent shell
# can exit; wrappers killing the parent process group do not reach tmux.
tmux new-session -d -s "${SESSION}" -c "${TSLIT_ROOT}" \
  env TSLIT_FULL_TMUX_CHILD=1 \
      SESSION="${SESSION}" \
      LOG="${LOG}" \
      PHASE="${PHASE:-probe}" \
      TSLIT_TARGET="${TSLIT_TARGET:-}" \
      OLLAMA_MODEL="${OLLAMA_MODEL:-}" \
      bash "${SCRIPT_DIR}/run_full_tmux.sh" "$@"

echo "started tmux session ${SESSION}"
echo "  attach: tmux attach -t ${SESSION}"
echo "  log:    tail -f ${LOG}"
if [[ "${ATTACH:-}" == 1 ]]; then
  exec tmux attach -t "${SESSION}"
fi
