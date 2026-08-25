#!/usr/bin/env bash
# run_experiment.sh — TSLIT-DSPy autoresearch experiment runner
#
# Reads experiment_config.json, runs MIPROv2 optimization + evaluation,
# and prints EXPERIMENT_RESULT: accuracy=X.XX for the autoresearch agent to parse.
#
# Usage:
#   bash run_experiment.sh           # full optimize + evaluate (~2 hours)
#   bash run_experiment.sh --mini    # evaluate-only, no recompile (~10 min)
#
# EXPERIMENT_RESULT line is ALWAYS printed, even on failure (accuracy=0.00).
# This is enforced by an EXIT trap — not just by per-function error handlers.

# NOTE: We intentionally do NOT use `set -e` here. With `set -e`, any
# unexpected error (bad JSON parse, failed mkdir, etc.) would exit the script
# before our error handlers can print the EXPERIMENT_RESULT fallback line.
# The autoresearch agent would then hang forever waiting for output.
# Instead, we check return codes explicitly where it matters.
set -uo pipefail

# ---------------------------------------------------------------------------
# EXIT trap: guarantee EXPERIMENT_RESULT is always printed
# ---------------------------------------------------------------------------
_printed_result=false

print_fallback_on_exit() {
    if [[ "$_printed_result" != "true" ]]; then
        echo "" >&2
        echo "ERROR: Script exited unexpectedly before printing results." >&2
        echo "EXPERIMENT_RESULT: accuracy=0.00 composite=0.00 category_f1=0.00 qa_pass=0.00 grounding=0.00"
    fi
}
trap print_fallback_on_exit EXIT

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG="$REPO_DIR/config/experiment_config.json"
COMPILED="$REPO_DIR/workspace/compiled/tslit_analyzer_optimized.json"
TEST_SET="$REPO_DIR/workspace/data/test.jsonl"
TRAIN_SET="$REPO_DIR/workspace/data/train.jsonl"
DEV_SET="$REPO_DIR/workspace/data/dev.jsonl"
LIVE_HOLDOUT="$REPO_DIR/workspace/data/live_holdout.jsonl"
EVAL_OUTPUT="$REPO_DIR/workspace/evaluation/autoresearch_eval.md"
EVAL_JSON="$REPO_DIR/workspace/evaluation/autoresearch_eval.json"
HASH_FILE="$REPO_DIR/workspace/.test_jsonl_hash"
LIVE_HASH_FILE="$REPO_DIR/workspace/.live_holdout_hash"

MINI_MODE=false
if [[ "${1:-}" == "--mini" ]]; then
    MINI_MODE=true
fi

# ---------------------------------------------------------------------------
# Safety: verify test.jsonl has not been tampered with
# ---------------------------------------------------------------------------
guard_test_set() {
    local current_hash
    current_hash=$(md5 -q "$TEST_SET" 2>/dev/null || md5sum "$TEST_SET" 2>/dev/null | awk '{print $1}')

    if [[ ! -f "$HASH_FILE" ]]; then
        echo "$current_hash" > "$HASH_FILE"
        echo "[guard] Recorded test.jsonl hash: $current_hash"
    else
        local stored_hash
        stored_hash=$(cat "$HASH_FILE")
        if [[ "$current_hash" != "$stored_hash" ]]; then
            echo "ERROR: workspace/data/test.jsonl has been modified!" >&2
            echo "ERROR: Stored hash: $stored_hash" >&2
            echo "ERROR: Current hash: $current_hash" >&2
            echo "ERROR: This file is LOCKED. The agent must never write to it." >&2
            _printed_result=true
            echo "EXPERIMENT_RESULT: accuracy=0.00 composite=0.00 category_f1=0.00 qa_pass=0.00 grounding=0.00"
            exit 1
        fi
    fi
}

# ---------------------------------------------------------------------------
# Safety: freeze live Qwen holdout (never in MIPRO)
# ---------------------------------------------------------------------------
guard_live_holdout() {
    if [[ ! -f "$LIVE_HOLDOUT" ]]; then
        echo "[guard] live_holdout.jsonl absent — skip"
        return 0
    fi
    local current_hash
    current_hash=$(md5 -q "$LIVE_HOLDOUT" 2>/dev/null || md5sum "$LIVE_HOLDOUT" 2>/dev/null | awk '{print $1}')

    if [[ ! -f "$LIVE_HASH_FILE" ]]; then
        echo "$current_hash" > "$LIVE_HASH_FILE"
        echo "[guard] Recorded live_holdout hash: $current_hash"
    else
        local stored_hash
        stored_hash=$(tr -d '[:space:]' < "$LIVE_HASH_FILE")
        if [[ "$current_hash" != "$stored_hash" ]]; then
            echo "ERROR: workspace/data/live_holdout.jsonl has been modified!" >&2
            echo "ERROR: Stored hash: $stored_hash" >&2
            echo "ERROR: Current hash: $current_hash" >&2
            echo "ERROR: This file is the Qwen verdict set. Never train on it." >&2
            _printed_result=true
            echo "EXPERIMENT_RESULT: accuracy=0.00 composite=0.00 category_f1=0.00 qa_pass=0.00 grounding=0.00"
            exit 1
        fi
    fi
}

assert_train_excludes_holdout() {
    if [[ ! -f "$LIVE_HOLDOUT" ]]; then
        return 0
    fi
    if ! python3 -c "
import json, sys
hold_ids, hold_eids = set(), set()
for line in open('$LIVE_HOLDOUT'):
    if not line.strip():
        continue
    r = json.loads(line)
    if r.get('probe_id'):
        hold_ids.add(r['probe_id'])
    if r.get('example_id'):
        hold_eids.add(r['example_id'])
leaks = []
for line in open('$EFFECTIVE_TRAIN'):
    if not line.strip():
        continue
    r = json.loads(line)
    if r.get('probe_id') in hold_ids or r.get('example_id') in hold_eids:
        leaks.append(r.get('example_id'))
if leaks:
    print('ERROR: train set contains live_holdout ids:', leaks, file=sys.stderr)
    sys.exit(1)
"; then
        _printed_result=true
        echo "EXPERIMENT_RESULT: accuracy=0.00 composite=0.00 category_f1=0.00 qa_pass=0.00 grounding=0.00"
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# Parse experiment_config.json (single python3 call for efficiency + safety)
# ---------------------------------------------------------------------------
parse_config() {
    if [[ ! -f "$CONFIG" ]]; then
        echo "ERROR: experiment_config.json not found at $CONFIG" >&2
        _printed_result=true
        echo "EXPERIMENT_RESULT: accuracy=0.00 composite=0.00 category_f1=0.00 qa_pass=0.00 grounding=0.00"
        exit 1
    fi

    # Parse all config values in one python3 call to avoid 8 separate invocations
    # and to fail atomically if the JSON is malformed
    local config_output
    if ! config_output=$(python3 -c "
import json, sys
try:
    c = json.load(open('$CONFIG'))
except Exception as e:
    print(f'ERROR: Failed to parse experiment_config.json: {e}', file=sys.stderr)
    sys.exit(1)

# Extract all values with defaults
vals = {
    'compile_model': c.get('compile_model', 'ollama'),
    'inference_model': c.get('inference_model', 'ollama'),
    'auto_setting': c.get('auto_setting', 'light'),
    'num_threads': c.get('mipro', {}).get('num_threads', 2),
    'max_boot': c.get('mipro', {}).get('max_bootstrapped_demos', 2),
    'max_labeled': c.get('mipro', {}).get('max_labeled_demos', 4),
    'use_augmented': c.get('training_data', {}).get('use_augmented', False),
    'augmented_path': c.get('training_data', {}).get('augmented_path', 'workspace/data/train_augmented.jsonl'),
}

# Print as KEY=VALUE lines for bash eval
for k, v in vals.items():
    print(f'{k}={v}')
"); then
        echo "ERROR: Config parsing failed." >&2
        _printed_result=true
        echo "EXPERIMENT_RESULT: accuracy=0.00 composite=0.00 category_f1=0.00 qa_pass=0.00 grounding=0.00"
        exit 1
    fi

    # Read parsed values into bash variables
    COMPILE_MODEL=$(echo "$config_output" | grep '^compile_model=' | cut -d= -f2-)
    INFERENCE_MODEL=$(echo "$config_output" | grep '^inference_model=' | cut -d= -f2-)
    AUTO_SETTING=$(echo "$config_output" | grep '^auto_setting=' | cut -d= -f2-)
    NUM_THREADS=$(echo "$config_output" | grep '^num_threads=' | cut -d= -f2-)
    MAX_BOOT=$(echo "$config_output" | grep '^max_boot=' | cut -d= -f2-)
    MAX_LABELED=$(echo "$config_output" | grep '^max_labeled=' | cut -d= -f2-)
    USE_AUGMENTED=$(echo "$config_output" | grep '^use_augmented=' | cut -d= -f2-)
    AUGMENTED_PATH=$(echo "$config_output" | grep '^augmented_path=' | cut -d= -f2-)

    # Normalize model strings: ollama/ → ollama_chat/ for DSPy compatibility
    if [[ "$COMPILE_MODEL" == ollama/* ]]; then
        COMPILE_MODEL="ollama_chat/${COMPILE_MODEL#ollama/}"
        echo "[config] Normalized compile_model: $COMPILE_MODEL"
    fi
    if [[ "$INFERENCE_MODEL" == ollama/* ]]; then
        INFERENCE_MODEL="ollama_chat/${INFERENCE_MODEL#ollama/}"
        echo "[config] Normalized inference_model: $INFERENCE_MODEL"
    fi

    echo "[config] compile_model=$COMPILE_MODEL"
    echo "[config] inference_model=$INFERENCE_MODEL"
    echo "[config] auto=$AUTO_SETTING threads=$NUM_THREADS boot_demos=$MAX_BOOT labeled_demos=$MAX_LABELED"
    echo "[config] use_augmented=$USE_AUGMENTED"
}

# ---------------------------------------------------------------------------
# Determine training set to use
# ---------------------------------------------------------------------------
resolve_train_set() {
    if [[ "$USE_AUGMENTED" == "True" || "$USE_AUGMENTED" == "true" ]]; then
        AUGMENTED_FULL="$REPO_DIR/$AUGMENTED_PATH"
        if [[ -f "$AUGMENTED_FULL" ]]; then
            EFFECTIVE_TRAIN="$AUGMENTED_FULL"
            echo "[config] Using augmented training set: $AUGMENTED_FULL"
        else
            echo "[warning] Augmented path not found, falling back to train.jsonl" >&2
            EFFECTIVE_TRAIN="$TRAIN_SET"
        fi
    else
        EFFECTIVE_TRAIN="$TRAIN_SET"
    fi
    TRAIN_COUNT=$(wc -l < "$EFFECTIVE_TRAIN" | tr -d ' ')
    echo "[config] Training examples: $TRAIN_COUNT"
}

# ---------------------------------------------------------------------------
# Run MIPROv2 optimization
# ---------------------------------------------------------------------------
run_optimize() {
    echo "[optimize] Starting MIPROv2 optimization..."
    echo "[optimize] This may take 1-3 hours depending on model and auto setting."

    mkdir -p "$REPO_DIR/workspace/compiled"

    if ! python3 -m tslit_dspy.optimize \
        --train "$EFFECTIVE_TRAIN" \
        --dev "$DEV_SET" \
        --output "$COMPILED" \
        --compile-model "$COMPILE_MODEL" \
        --auto "$AUTO_SETTING" \
        --num-threads "$NUM_THREADS" \
        --max-bootstrapped-demos "$MAX_BOOT" \
        --max-labeled-demos "$MAX_LABELED"; then
        echo "ERROR: Optimization failed." >&2
        _printed_result=true
        echo "EXPERIMENT_RESULT: accuracy=0.00 composite=0.00 category_f1=0.00 qa_pass=0.00 grounding=0.00"
        exit 1
    fi

    echo "[optimize] Optimization complete. Compiled model: $COMPILED"
}

# ---------------------------------------------------------------------------
# Run evaluation against frozen test set
# ---------------------------------------------------------------------------
run_evaluate() {
    echo "[evaluate] Running evaluation against frozen test set..."
    mkdir -p "$REPO_DIR/workspace/evaluation"

    if ! python3 -m tslit_dspy.evaluate \
        --test "$TEST_SET" \
        --compiled "$COMPILED" \
        --output "$EVAL_OUTPUT" \
        --model "$INFERENCE_MODEL" \
        --title "autoresearch-eval"; then
        echo "ERROR: Evaluation failed." >&2
        _printed_result=true
        echo "EXPERIMENT_RESULT: accuracy=0.00 composite=0.00 category_f1=0.00 qa_pass=0.00 grounding=0.00"
        exit 1
    fi

    echo "[evaluate] Evaluation complete. Report: $EVAL_OUTPUT"
}

# ---------------------------------------------------------------------------
# Parse results and print EXPERIMENT_RESULT
# ---------------------------------------------------------------------------
print_result() {
    if [[ ! -f "$EVAL_JSON" ]]; then
        echo "ERROR: Evaluation JSON not found at $EVAL_JSON" >&2
        _printed_result=true
        echo "EXPERIMENT_RESULT: accuracy=0.00 composite=0.00 category_f1=0.00 qa_pass=0.00 grounding=0.00"
        exit 1
    fi

    # Parse all metrics in one python3 call
    local metrics_output
    if ! metrics_output=$(python3 -c "
import json

data = json.load(open('$EVAL_JSON'))

# accuracy = simple category match rate (overall_accuracy from evaluate.py)
accuracy = data.get('accuracy', 0.0)

# mean_composite = mean of per-example composite scores (the actual metric
# MIPROv2 optimizes, defined in metrics.py as:
#   0.50*category + 0.20*risk_range + 0.20*evidence + 0.10*qa)
per_ex = data.get('per_example', [])
scores = [ex.get('score', 0.0) for ex in per_ex]
mean_composite = sum(scores) / max(1, len(scores))

# macro-average F1 across all 4 categories
cm = data.get('class_metrics', {})
f1s = [cm.get(c, {}).get('f1', 0.0) for c in ['none','affiliation_bias','temporal_logic_bomb','combined']]
macro_f1 = sum(f1s) / len(f1s)

qa_pass = data.get('qa_pass_rate', 0.0)
grounding = data.get('evidence_metrics', {}).get('grounding_rate', 0.0)

print(f'accuracy={accuracy:.4f}')
print(f'composite={mean_composite:.4f}')
print(f'category_f1={macro_f1:.4f}')
print(f'qa_pass={qa_pass:.4f}')
print(f'grounding={grounding:.4f}')
"); then
        echo "ERROR: Failed to parse evaluation JSON." >&2
        _printed_result=true
        echo "EXPERIMENT_RESULT: accuracy=0.00 composite=0.00 category_f1=0.00 qa_pass=0.00 grounding=0.00"
        exit 1
    fi

    ACCURACY=$(echo "$metrics_output" | grep '^accuracy=' | cut -d= -f2)
    COMPOSITE=$(echo "$metrics_output" | grep '^composite=' | cut -d= -f2)
    CATEGORY_F1=$(echo "$metrics_output" | grep '^category_f1=' | cut -d= -f2)
    QA_PASS=$(echo "$metrics_output" | grep '^qa_pass=' | cut -d= -f2)
    GROUNDING=$(echo "$metrics_output" | grep '^grounding=' | cut -d= -f2)

    echo ""
    echo "========================================="
    echo "EXPERIMENT RESULTS"
    echo "========================================="
    echo "  accuracy:        $ACCURACY   (category match rate)"
    echo "  composite:       $COMPOSITE  (mean per-example composite metric)"
    echo "  category_f1:     $CATEGORY_F1"
    echo "  qa_pass_rate:    $QA_PASS"
    echo "  grounding:       $GROUNDING"
    echo "========================================="
    echo ""

    _printed_result=true
    echo "EXPERIMENT_RESULT: accuracy=$ACCURACY composite=$COMPOSITE category_f1=$CATEGORY_F1 qa_pass=$QA_PASS grounding=$GROUNDING"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
echo "========================================="
echo "TSLIT-DSPy autoresearch experiment runner"
echo "Mode: $([ "$MINI_MODE" = true ] && echo 'MINI (eval-only)' || echo 'FULL (optimize + eval)')"
echo "========================================="

cd "$REPO_DIR"

guard_test_set
guard_live_holdout
parse_config
resolve_train_set
assert_train_excludes_holdout

if [[ "$MINI_MODE" == "true" ]]; then
    echo "[mini] Skipping optimization. Using existing compiled model."
    if [[ ! -f "$COMPILED" ]]; then
        echo "ERROR: No compiled model found at $COMPILED. Run without --mini first." >&2
        _printed_result=true
        echo "EXPERIMENT_RESULT: accuracy=0.00 composite=0.00 category_f1=0.00 qa_pass=0.00 grounding=0.00"
        exit 1
    fi
else
    run_optimize
fi

run_evaluate
print_result
