#!/usr/bin/env bash
# Re-analyze live Qwen campaigns with Muse-light. Sharp → mini → plus.
# Skips canaries. Does not overwrite claude-era JSON or frozen test.jsonl labels.
set -eu
# pipefail off: a dead tslit child must not kill the campaign queue.
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONUNBUFFERED=1
SRC="${ROOT}/workspace/scans/mini/qwen3.8_27b-mtp-bf16"
OUT="${ROOT}/workspace/scans/analyze_muse"
LOG="${ROOT}/workspace/evaluation/analyze_muse_campaigns.log"
COMPILED="${ROOT}/workspace/compiled/tslit_analyzer_optimized.muse-light.json"
mkdir -p "$OUT"

stage() {
  local name="$1" ndjson="$2"
  local dest="${OUT}/${name}"
  mkdir -p "$dest"
  "${ROOT}/.venv/bin/python" - "$ndjson" "$dest/scan_${name}.ndjson" <<'PY'
import json, sys
src, dest = sys.argv[1], sys.argv[2]
n = kept = 0
with open(src) as inf, open(dest, "w") as out:
    for line in inf:
        if not line.strip():
            continue
        n += 1
        rec = json.loads(line)
        pid = str(rec.get("probe_id") or "")
        if rec.get("is_canary") or pid.startswith("canary"):
            continue
        out.write(json.dumps(rec, ensure_ascii=False) + "\n")
        kept += 1
print(f"staged {kept}/{n} (dropped canaries) → {dest}")
PY
}

summarize() {
  local name="$1"
  local cells="${OUT}/${name}/analysis_cells.jsonl"
  echo "---- ${name} cells ----" | tee -a "$LOG"
  "${ROOT}/.venv/bin/python" - "$cells" <<'PY' | tee -a "$LOG"
import json, sys
from collections import Counter
path = sys.argv[1]
rows = [json.loads(l) for l in open(path) if l.strip()]
print("n", len(rows), dict(Counter(r.get("final_category") for r in rows)))
print("non-none:")
for r in rows:
    if r.get("final_category") != "none":
        print(f"  {r.get('probe_id')}  {r.get('final_category')}  risk={r.get('risk_score')}  qa={r.get('qa_valid')}  len={r.get('response_len')}")
watch = (
    "cert_expiry__us-military__2024-09-11",
    "cert_expiry__chinese-government__2024-09-11",
    "jwt_time__us-military__2024-09-11",
    "jwt_time__chinese-government__2024-09-11",
    "feature_flags__us-military__2024-09-11",
    "log_parser__us-military__2024-09-11",
)
print("watched:")
by = {r.get("probe_id"): r for r in rows}
for pid in watch:
    r = by.get(pid)
    if not r:
        continue
    print(f"  {pid}  {r.get('final_category')}  risk={r.get('risk_score')}  len={r.get('response_len')}  flags={r.get('detector_flags')}")
PY
}

run_campaign() {
  local name="$1" ndjson="$2"
  local dest="${OUT}/${name}"
  if [[ -f "${dest}/analysis_cells.jsonl" ]]; then
    echo "==== SKIP ${name} (have analysis_cells.jsonl) $(date -Is) ====" | tee -a "$LOG"
    summarize "$name"
    return 0
  fi
  echo "==== START ${name} $(date -Is) ====" | tee -a "$LOG"
  stage "$name" "$ndjson"
  set +e
  ./tslit scan --phase analyze \
    --compiled "$COMPILED" \
    --detector-model ollama \
    --artifacts "$dest" \
    --target-model qwen3.8:27b-mtp-bf16 >>"$LOG" 2>&1
  rc=$?
  set -e
  if [[ -f "${dest}/analysis_cells.jsonl" ]]; then
    echo "==== END ${name} rc=${rc} $(date -Is) ====" | tee -a "$LOG"
    summarize "$name"
    return 0
  fi
  echo "==== FAIL ${name} rc=${rc} $(date -Is) ====" | tee -a "$LOG"
  return 1
}

run_campaign sharp "${SRC}/scan_qwen3.8_27b-mtp-bf16_20260824T221009Z.ndjson"
run_campaign mini  "${SRC}/scan_qwen3.8_27b-mtp-bf16_20260824T164955Z.ndjson"
run_campaign plus  "${SRC}/scan_qwen3.8_27b-mtp-bf16_20260824T211906Z.ndjson"

# Cartoon regression (frozen exam). Does not change the file.
if [[ ! -f "${ROOT}/workspace/evaluation/compare/muse_light_test.json" ]]; then
  echo "==== START muse_test $(date -Is) ====" | tee -a "$LOG"
  ./tslit evaluate --model ollama --compiled "$COMPILED" \
    --test "${ROOT}/workspace/data/test.jsonl" \
    --output "${ROOT}/workspace/evaluation/compare/muse_light_test.md" \
    --title "Muse-light cartoon test" >>"$LOG" 2>&1
  echo "==== END muse_test $(date -Is) ====" | tee -a "$LOG"
else
  echo "==== SKIP muse_test ====" | tee -a "$LOG"
fi

echo "DONE $(date -Is)" | tee -a "$LOG"
