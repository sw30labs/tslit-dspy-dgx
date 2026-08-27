#!/usr/bin/env bash
# Claude-era vs Muse-light on cartoon DEV (promote-gate) and live holdout (Qwen).
# Does not train, does not touch test.jsonl, does not overwrite compiled JSON.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONUNBUFFERED=1
TSLIT="${ROOT}/tslit"
OUT="${ROOT}/workspace/evaluation/compare"
LOG="${ROOT}/workspace/evaluation/compare_claude_vs_muse.log"
mkdir -p "$OUT"

run_one() {
  local name="$1" compiled="$2" testset="$3" out="$4" title="$5"
  local json="${out%.md}.json"
  if [[ -f "$json" ]]; then
    echo "==== SKIP ${name} (have ${json}) $(date -Is) ====" | tee -a "$LOG"
    return 0
  fi
  echo "==== START ${name} $(date -Is) ====" | tee -a "$LOG"
  if ! "$TSLIT" evaluate \
    --model ollama \
    --compiled "$compiled" \
    --test "$testset" \
    --output "$out" \
    --title "$title" >>"$LOG" 2>&1; then
    echo "==== FAIL ${name} exit=$? $(date -Is) ====" | tee -a "$LOG"
    return 1
  fi
  echo "==== END ${name} $(date -Is) ====" | tee -a "$LOG"
}

CLAUDE="${ROOT}/workspace/compiled/tslit_analyzer_optimized.claude-era.json"
MUSE="${ROOT}/workspace/compiled/tslit_analyzer_optimized.muse-light.json"
DEV="${ROOT}/workspace/data/dev.jsonl"
HOLD="${ROOT}/workspace/data/live_holdout.jsonl"

run_one claude_dev  "$CLAUDE" "$DEV"  "$OUT/claude_era_dev.md"          "Claude-era DEV"
run_one muse_dev    "$MUSE"   "$DEV"  "$OUT/muse_light_dev.md"          "Muse-light DEV"
run_one claude_hold "$CLAUDE" "$HOLD" "$OUT/claude_era_live_holdout.md" "Claude-era live holdout"
run_one muse_hold   "$MUSE"   "$HOLD" "$OUT/muse_light_live_holdout.md" "Muse-light live holdout"

"${ROOT}/.venv/bin/python" - <<'PY' | tee -a "$LOG"
import json
from pathlib import Path
root = Path("workspace/evaluation/compare")
pairs = [
    ("DEV (promote-gate)", "claude_era_dev.json", "muse_light_dev.json"),
    ("live holdout (Qwen)", "claude_era_live_holdout.json", "muse_light_live_holdout.json"),
]
print("\n======== Claude-era vs Muse-light ========")
for label, a, b in pairs:
    print(f"\n## {label}")
    print(f"{'':22} {'acc':>7} {'comp':>7} {'none_p':>7} {'none_r':>7}")
    for name, fn in (("claude-era", a), ("muse-light", b)):
        p = root / fn
        if not p.is_file():
            print(f"{name:22} MISSING {p}")
            continue
        d = json.loads(p.read_text())
        none = (d.get("class_metrics") or {}).get("none") or {}
        print(
            f"{name:22} {d.get('accuracy', 0):7.3f} {d.get('mean_composite', 0):7.3f} "
            f"{none.get('precision', 0):7.3f} {none.get('recall', 0):7.3f}"
        )
    # holdout confusion
    if "holdout" in a:
        for name, fn in (("claude-era", a), ("muse-light", b)):
            p = root / fn
            if not p.is_file():
                continue
            d = json.loads(p.read_text())
            print(f"\n{name} holdout per-example:")
            for ex in d.get("per_example") or []:
                print(
                    f"  {ex.get('example_id','?'):50} gt={ex.get('gt_category')} "
                    f"pred={ex.get('pred_category')} score={ex.get('score',0):.3f}"
                )
print("==========================================")
PY
echo "DONE $(date -Is)" | tee -a "$LOG"
