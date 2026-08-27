#!/usr/bin/env python3
"""Generate Figure 7: Autoresearch Integration Flow Diagram."""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

fig, ax = plt.subplots(1, 1, figsize=(14, 18))
ax.set_xlim(0, 14)
ax.set_ylim(0, 18)
ax.axis('off')

# Colors
DARK_BLUE = '#1A3A5C'
MID_BLUE = '#2C5F8A'
LIGHT_BLUE = '#D6E8F7'
DARK_RED = '#8B1A1A'
MID_RED = '#C0392B'
LIGHT_RED = '#FADBD8'
DARK_GREEN = '#1A6B3C'
LIGHT_GREEN = '#D5F5E3'
ORANGE = '#E67E22'
LIGHT_ORANGE = '#FDEBD0'
PURPLE = '#6C3483'
LIGHT_PURPLE = '#E8DAEF'
GRAY = '#7F8C8D'
LIGHT_GRAY = '#F2F3F4'

def draw_box(x, y, w, h, text, facecolor, edgecolor, fontsize=8.5, bold=False, text_color='black', alpha=1.0, style='round,pad=0.1'):
    box = FancyBboxPatch((x, y), w, h, boxstyle=style,
                          facecolor=facecolor, edgecolor=edgecolor, linewidth=1.5, alpha=alpha)
    ax.add_patch(box)
    weight = 'bold' if bold else 'normal'
    ax.text(x + w/2, y + h/2, text, ha='center', va='center',
            fontsize=fontsize, fontweight=weight, color=text_color, wrap=True,
            multialignment='center')

def draw_arrow(x1, y1, x2, y2, color=GRAY, style='->', lw=1.5, connectionstyle='arc3,rad=0'):
    arrow = FancyArrowPatch((x1, y1), (x2, y2),
                             arrowstyle=style, color=color,
                             linewidth=lw, connectionstyle=connectionstyle,
                             mutation_scale=15)
    ax.add_patch(arrow)

def draw_dashed_arrow(x1, y1, x2, y2, color=GRAY, lw=1.2):
    arrow = FancyArrowPatch((x1, y1), (x2, y2),
                             arrowstyle='->', color=color,
                             linewidth=lw, linestyle='dashed',
                             mutation_scale=12)
    ax.add_patch(arrow)

# ============================================================
# TITLE
# ============================================================
ax.text(7, 17.6, 'TSLIT-DSPy Autoresearch: Autonomous Self-Improvement Loop',
        ha='center', va='center', fontsize=13, fontweight='bold', color=DARK_BLUE)
ax.text(7, 17.25, 'Sequential agent loop with parallel MIPROv2 internals',
        ha='center', va='center', fontsize=9, color=GRAY, style='italic')

# ============================================================
# AGENT LOOP (outer box)
# ============================================================
outer = FancyBboxPatch((0.3, 0.4), 13.4, 16.4, boxstyle='round,pad=0.15',
                        facecolor='white', edgecolor=DARK_BLUE, linewidth=2.5, linestyle='--', alpha=0.3)
ax.add_patch(outer)
ax.text(7, 16.85, 'AGENT LOOP  (agent_loop_mlx.py — sequential, one experiment at a time)',
        ha='center', va='center', fontsize=9.5, fontweight='bold', color=DARK_BLUE,
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=DARK_BLUE, linewidth=1.5))

# ============================================================
# ROW 1: Research Program + Hypothesis
# ============================================================
# Research program (left)
draw_box(0.8, 15.3, 3.8, 1.2, 'Research Program\n(config/tslit_program.md)\n3-tier hypothesis ladder',
         LIGHT_PURPLE, PURPLE, fontsize=8, bold=True)

# Hypothesis generation (center)
draw_box(5.4, 15.3, 3.6, 1.2, 'Hypothesis Generation\nAgent selects tier &\nforms experiment plan',
         LIGHT_BLUE, MID_BLUE, fontsize=8, bold=True)

# Context window (right)
draw_box(9.8, 15.3, 3.6, 1.2, 'Context Window Mgmt\nSliding window preserves:\nprogram + best score + last 3-5 results',
         LIGHT_GRAY, GRAY, fontsize=7.5, bold=False)

draw_arrow(4.6, 15.9, 5.4, 15.9, MID_BLUE, lw=2)
draw_arrow(9.4, 15.9, 9.8, 15.9, GRAY, lw=1.2)

# ============================================================
# ROW 2: TIER DECISION (branching)
# ============================================================
# Decision diamond-ish
draw_box(5.4, 13.8, 3.6, 1.1, 'Which Tier?', LIGHT_ORANGE, ORANGE, fontsize=9, bold=True)
draw_arrow(7.2, 15.3, 7.2, 14.9, MID_BLUE, lw=2)

# Tier 1 label (left branch)
ax.text(3.0, 14.35, 'TIER 1', ha='center', va='center', fontsize=8, fontweight='bold', color=DARK_GREEN,
        bbox=dict(boxstyle='round,pad=0.2', facecolor=LIGHT_GREEN, edgecolor=DARK_GREEN))
ax.text(3.0, 14.0, 'Config Tuning', ha='center', va='center', fontsize=7, color=DARK_GREEN)

# Tier 2 label (right branch)
ax.text(11.5, 14.35, 'TIER 2', ha='center', va='center', fontsize=8, fontweight='bold', color=DARK_RED,
        bbox=dict(boxstyle='round,pad=0.2', facecolor=LIGHT_RED, edgecolor=DARK_RED))
ax.text(11.5, 14.0, 'Data Augmentation', ha='center', va='center', fontsize=7, color=DARK_RED)

draw_arrow(5.4, 14.35, 3.8, 14.35, DARK_GREEN, lw=1.8)
draw_arrow(9.0, 14.35, 10.5, 14.35, DARK_RED, lw=1.8)

# ============================================================
# ROW 3: TIER ACTIONS
# ============================================================
# Tier 1: Modify config
draw_box(0.8, 12.4, 3.8, 1.2, 'Modify Config\n(experiment_config.json)\nauto_setting, demos,\nthreads, metric weights',
         LIGHT_GREEN, DARK_GREEN, fontsize=7.5, bold=True)
draw_arrow(3.0, 13.8, 3.0, 13.6, DARK_GREEN, lw=1.8)

# Tier 2: Synthesize + Append
draw_box(9.8, 12.4, 3.6, 1.2, 'Synthesize Examples\n→ Append to train.jsonl\n(append-only enforced)\nTargets gap categories',
         LIGHT_RED, DARK_RED, fontsize=7.5, bold=True)
draw_arrow(11.5, 13.8, 11.5, 13.6, DARK_RED, lw=1.8)

# Tier 3 note
draw_box(5.4, 12.6, 3.6, 0.8, 'TIER 3: Both\nConfig + Data combined',
         LIGHT_ORANGE, ORANGE, fontsize=7.5, bold=True)
draw_dashed_arrow(3.8, 13.0, 5.4, 13.0, ORANGE, lw=1.2)
draw_dashed_arrow(9.8, 13.0, 9.0, 13.0, ORANGE, lw=1.2)

# ============================================================
# MERGE: Both tiers feed into experiment runner
# ============================================================
draw_arrow(2.7, 12.4, 5.0, 11.5, MID_BLUE, lw=2)
draw_arrow(11.5, 12.4, 9.4, 11.5, MID_BLUE, lw=2)

# ============================================================
# ROW 4: EXPERIMENT RUNNER
# ============================================================
# Big box for run_experiment.sh
runner_box = FancyBboxPatch((4.2, 9.3), 5.8, 2.2, boxstyle='round,pad=0.12',
                             facecolor='#EBF5FB', edgecolor=DARK_BLUE, linewidth=2.0)
ax.add_patch(runner_box)
ax.text(7.1, 11.15, 'EXPERIMENT RUNNER  (run_experiment.sh)', ha='center', va='center',
        fontsize=9, fontweight='bold', color=DARK_BLUE)

# Sub-steps inside runner
draw_box(4.5, 10.3, 2.4, 0.65, '① MD5 Hash Guard\nVerify test.jsonl integrity',
         'white', DARK_RED, fontsize=7, bold=False)
draw_box(7.3, 10.3, 2.4, 0.65, '② Parse Config\nLoad experiment_config.json',
         'white', MID_BLUE, fontsize=7, bold=False)

draw_box(4.5, 9.5, 2.4, 0.65, '③ MIPROv2 Compile\n(Claude Sonnet 4.6 API)',
         'white', PURPLE, fontsize=7, bold=True)
draw_box(7.3, 9.5, 2.4, 0.65, '④ Evaluate\n(Qwen 3.5-27B local MLX)',
         'white', DARK_GREEN, fontsize=7, bold=True)

# Arrows inside runner
draw_arrow(6.9, 10.62, 7.3, 10.62, GRAY, lw=1)
draw_arrow(5.7, 10.3, 5.7, 10.15, GRAY, lw=1)
draw_arrow(6.9, 9.82, 7.3, 9.82, GRAY, lw=1)

# EXIT trap callout
draw_box(10.5, 9.8, 3.0, 0.8, 'EXIT Trap\nGuaranteed output:\nEXPERIMENT_RESULT:\naccuracy=0.XX',
         LIGHT_GRAY, GRAY, fontsize=7, bold=False)
draw_arrow(9.7, 10.0, 10.5, 10.0, GRAY, lw=1.2)

# --mini mode callout
draw_box(0.8, 9.5, 3.0, 0.7, '--mini mode\nSkip recompile → eval only\n(< 60s on MLX)',
         LIGHT_GREEN, DARK_GREEN, fontsize=7, bold=False)
draw_dashed_arrow(3.8, 9.85, 4.5, 9.85, DARK_GREEN, lw=1.2)

# ============================================================
# PARALLEL INTERNALS NOTE
# ============================================================
par_box = FancyBboxPatch((4.5, 8.4), 5.3, 0.7, boxstyle='round,pad=0.08',
                          facecolor=LIGHT_ORANGE, edgecolor=ORANGE, linewidth=1.2)
ax.add_patch(par_box)
ax.text(7.15, 8.75, '>> MIPROv2 internals run num_threads=4 parallel LLM calls\n'
        '    (only parallelism in the system — outer loop is strictly sequential)',
        ha='center', va='center', fontsize=7.5, color=ORANGE, fontweight='bold')

# ============================================================
# ROW 5: RESULT + GATE CHECK
# ============================================================
draw_arrow(7.1, 8.4, 7.1, 7.9, MID_BLUE, lw=2)

draw_box(4.8, 7.0, 4.6, 0.85, 'Score Improved ≥ 1.0pp\nover running best?',
         LIGHT_ORANGE, ORANGE, fontsize=8.5, bold=True)

# YES branch (left)
ax.text(3.2, 7.42, 'YES', ha='center', va='center', fontsize=9, fontweight='bold', color=DARK_GREEN)
draw_arrow(4.8, 7.42, 3.6, 7.42, DARK_GREEN, lw=2)

# NO branch (right)
ax.text(11.0, 7.42, 'NO', ha='center', va='center', fontsize=9, fontweight='bold', color=DARK_RED)
draw_arrow(9.4, 7.42, 10.6, 7.42, DARK_RED, lw=2)

# ============================================================
# ROW 6: ACCEPT / REJECT
# ============================================================
# Accept
draw_box(0.8, 5.9, 3.8, 1.0, 'ACCEPT\nCommit config + compiled JSON\nto git branch with\nhypothesis + result',
         LIGHT_GREEN, DARK_GREEN, fontsize=7.5, bold=True)
draw_arrow(2.7, 7.0, 2.7, 6.9, DARK_GREEN, lw=2)

# Reject
draw_box(9.8, 5.9, 3.6, 1.0, 'REJECT\nRevert config changes\nQuarantine new examples\nLog failure reason',
         LIGHT_RED, DARK_RED, fontsize=7.5, bold=True)
draw_arrow(11.5, 7.0, 11.5, 6.9, DARK_RED, lw=2)

# ============================================================
# ROW 7: GIT AUDIT + LOOP BACK
# ============================================================
draw_box(4.2, 4.8, 5.8, 0.85, 'Git Audit Trail\nautoresearch/run-YYYYMMDD-HHMMSS branch\nEvery decision traceable: hypothesis → experiment → outcome',
         LIGHT_BLUE, DARK_BLUE, fontsize=7.5, bold=True)

draw_arrow(2.7, 5.9, 5.5, 5.65, DARK_BLUE, lw=1.5)
draw_arrow(11.5, 5.9, 8.5, 5.65, DARK_BLUE, lw=1.5)

# ============================================================
# LOOP-BACK ARROW
# ============================================================
# Big curved arrow from bottom back to top
ax.annotate('', xy=(1.0, 15.3), xytext=(1.0, 5.2),
            arrowprops=dict(arrowstyle='->', color=MID_BLUE, lw=2.5,
                           connectionstyle='arc3,rad=-0.15'))
ax.text(0.3, 10.2, 'N\nE\nX\nT\n\nH\nY\nP\nO\nT\nH\nE\nS\nI\nS', ha='center', va='center',
        fontsize=6.5, fontweight='bold', color=MID_BLUE, linespacing=0.85)

# ============================================================
# SAFETY BOUNDARIES (bottom)
# ============================================================
safety_box = FancyBboxPatch((0.5, 0.6), 13.2, 3.8, boxstyle='round,pad=0.12',
                             facecolor='#FDF2E9', edgecolor=DARK_RED, linewidth=2.0, linestyle=':')
ax.add_patch(safety_box)
ax.text(7.1, 4.15, 'IMMUTABLE SAFETY BOUNDARIES', ha='center', va='center',
        fontsize=9, fontweight='bold', color=DARK_RED)

# Safety items
safety_items = [
    ('LOCKED: test.jsonl', 'MD5 hash verified\nbefore every run', 1.5, 2.8),
    ('LOCKED: dev.jsonl', 'Read-only\n(compilation use only)', 4.3, 2.8),
    ('LOCKED: tslit_dspy/*.py', 'Pipeline source code\nnever writable', 7.1, 2.8),
    ('LOCKED: Commands', 'Only pre-approved\nshell commands execute', 10.0, 2.8),
]

for label, desc, x, y in safety_items:
    draw_box(x - 1.2, y - 0.65, 2.4, 0.65, label, 'white', DARK_RED, fontsize=7.5, bold=True, text_color=DARK_RED)
    ax.text(x, y - 0.9, desc, ha='center', va='center', fontsize=6.5, color=GRAY)

# Append-only callout
draw_box(3.5, 0.75, 7.2, 0.65, 'train.jsonl: APPEND-ONLY -- agent can add examples but never delete or modify existing ones',
         'white', ORANGE, fontsize=7.5, bold=True, text_color=ORANGE)

# ============================================================
# LEGEND
# ============================================================
# Small legend at very bottom-right would be too cramped; skip it.
# The colors are self-explanatory from labels.

plt.tight_layout()
plt.savefig('../figures/figure7_autoresearch_flow.png',
            dpi=200, bbox_inches='tight', facecolor='white')
plt.close()
print("Figure 7 saved successfully.")
