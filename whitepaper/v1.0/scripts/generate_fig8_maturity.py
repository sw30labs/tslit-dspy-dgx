#!/usr/bin/env python3
"""Generate Figure 8: Product Maturity Model — Tier Progression."""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

fig, ax = plt.subplots(1, 1, figsize=(14, 16))
ax.set_xlim(0, 14)
ax.set_ylim(0, 16)
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
MID_GREEN = '#27AE60'
ORANGE = '#E67E22'
LIGHT_ORANGE = '#FDEBD0'
PURPLE = '#6C3483'
LIGHT_PURPLE = '#E8DAEF'
GRAY = '#7F8C8D'
LIGHT_GRAY = '#F2F3F4'
GOLD = '#B7950B'
LIGHT_GOLD = '#FEF9E7'

def draw_box(x, y, w, h, text, facecolor, edgecolor, fontsize=8.5, bold=False,
             text_color='black', alpha=1.0):
    box = FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.1',
                          facecolor=facecolor, edgecolor=edgecolor,
                          linewidth=1.5, alpha=alpha)
    ax.add_patch(box)
    weight = 'bold' if bold else 'normal'
    ax.text(x + w/2, y + h/2, text, ha='center', va='center',
            fontsize=fontsize, fontweight=weight, color=text_color,
            multialignment='center')

def draw_arrow(x1, y1, x2, y2, color=GRAY, lw=1.5, style='->'):
    arrow = FancyArrowPatch((x1, y1), (x2, y2),
                             arrowstyle=style, color=color,
                             linewidth=lw, mutation_scale=15)
    ax.add_patch(arrow)

def draw_thick_arrow(x1, y1, x2, y2, color=GRAY, lw=3):
    arrow = FancyArrowPatch((x1, y1), (x2, y2),
                             arrowstyle='->', color=color,
                             linewidth=lw, mutation_scale=20)
    ax.add_patch(arrow)

# ============================================================
# TITLE
# ============================================================
ax.text(7, 15.6, 'TSLIT-DSPy: Product Maturity Model',
        ha='center', va='center', fontsize=14, fontweight='bold', color=DARK_BLUE)
ax.text(7, 15.2, 'Phased deployment from safe optimization to autonomous self-improvement',
        ha='center', va='center', fontsize=9.5, color=GRAY, style='italic')

# ============================================================
# MATURITY TIMELINE ARROW (horizontal, across bottom area)
# ============================================================
# Draw a big horizontal arrow at y=1.0 spanning the page
ax.annotate('', xy=(13.2, 0.65), xytext=(0.8, 0.65),
            arrowprops=dict(arrowstyle='->', color=DARK_BLUE, lw=3))
ax.text(7, 0.25, 'DEPLOYMENT MATURITY / CLIENT CONFIDENCE',
        ha='center', va='center', fontsize=10, fontweight='bold', color=DARK_BLUE)

# Time markers
for x, label in [(2.2, 'Weeks 1-4'), (5.8, 'Months 2-3'), (9.5, 'Months 4-6'), (12.5, 'Ongoing')]:
    ax.text(x, 0.9, label, ha='center', va='center', fontsize=7, color=GRAY)

# ============================================================
# TIER 1 COLUMN (left)
# ============================================================
t1_x = 0.5
t1_w = 3.2

# Header
draw_box(t1_x, 13.6, t1_w, 1.2, 'TIER 1\nConfiguration Tuning\n(Phase B)',
         LIGHT_GREEN, DARK_GREEN, fontsize=10, bold=True, text_color=DARK_GREEN)

# What changes
draw_box(t1_x, 12.4, t1_w, 1.0, 'WHAT CHANGES\nexperiment_config.json\nMIPROv2 hyperparameters only',
         'white', DARK_GREEN, fontsize=8, bold=True, text_color=DARK_GREEN)

# What's untouched
draw_box(t1_x, 11.2, t1_w, 1.0, 'UNTOUCHED\nTraining data (frozen)\nPipeline code (frozen)\nTest set (frozen)',
         LIGHT_GREEN, DARK_GREEN, fontsize=7.5, bold=False)

# Risk profile
draw_box(t1_x, 10.0, t1_w, 1.0, 'RISK PROFILE\nZero data risk\nFully reversible (revert JSON)\nBlast radius: config file only',
         '#E8F8F5', '#1ABC9C', fontsize=7.5, bold=False)

# Supervision
draw_box(t1_x, 8.8, t1_w, 1.0, 'SUPERVISION\nFully unsupervised\nNo human review needed\nGit audit trail sufficient',
         'white', GRAY, fontsize=7.5, bold=False)

# Client value
draw_box(t1_x, 7.2, t1_w, 1.3, 'CLIENT VALUE\n"We optimized your detection\npipeline from 73% to 87%\nwithout touching your data\nor detection logic"',
         LIGHT_GOLD, GOLD, fontsize=7.5, bold=False)

# Certification story
draw_box(t1_x, 5.8, t1_w, 1.2, 'AUDIT STORY\nEvery config change logged\nTest set never modified\nDeterministic, reproducible',
         LIGHT_BLUE, MID_BLUE, fontsize=7.5, bold=False)

# Metrics
draw_box(t1_x, 4.4, t1_w, 1.2, 'TARGET METRICS\nBaseline: ~68-73%\nTarget: 85-90%\nExperiments: 10-30 cycles\nCost: compile API only',
         'white', DARK_GREEN, fontsize=7.5, bold=False, text_color=DARK_GREEN)

# Dataset size
draw_box(t1_x, 3.2, t1_w, 1.0, 'DATASET\n55 training examples\n(unchanged)\nClass imbalance persists',
         LIGHT_GRAY, GRAY, fontsize=7.5, bold=False)

# Gate to next tier
draw_box(t1_x, 1.5, t1_w, 1.4, 'GRADUATION GATE\nDemonstrate stable accuracy\nimprovement over baseline\nwith 3+ consecutive\nnon-regressing experiments',
         LIGHT_ORANGE, ORANGE, fontsize=7.5, bold=True)

# ============================================================
# TIER 2 COLUMN (center)
# ============================================================
t2_x = 4.2
t2_w = 3.2

draw_box(t2_x, 13.6, t2_w, 1.2, 'TIER 2\nData Augmentation\n(Phase C)',
         LIGHT_RED, DARK_RED, fontsize=10, bold=True, text_color=DARK_RED)

draw_box(t2_x, 12.4, t2_w, 1.0, 'WHAT CHANGES\ntrain.jsonl (append-only)\nNew labeled examples added\nFills distribution gaps',
         'white', DARK_RED, fontsize=8, bold=True, text_color=DARK_RED)

draw_box(t2_x, 11.2, t2_w, 1.0, 'UNTOUCHED\nConfig (from Tier 1 best)\nPipeline code (frozen)\nTest set (MD5 guarded)',
         LIGHT_RED, DARK_RED, fontsize=7.5, bold=False)

draw_box(t2_x, 10.0, t2_w, 1.0, 'RISK PROFILE\nAppend-only enforcement\nNo existing data modified\nRegression gate on test set',
         '#FDEDEC', '#E74C3C', fontsize=7.5, bold=False)

draw_box(t2_x, 8.8, t2_w, 1.0, 'SUPERVISION\nPhase C.1: Human-in-the-loop\nExpert reviews each example\nbefore append + recompile',
         'white', GRAY, fontsize=7.5, bold=False)

draw_box(t2_x, 7.2, t2_w, 1.3, 'CLIENT VALUE\n"We expanded detection\ncoverage to include threat\npatterns your original\ndata didn\'t cover"',
         LIGHT_GOLD, GOLD, fontsize=7.5, bold=False)

draw_box(t2_x, 5.8, t2_w, 1.2, 'AUDIT STORY\nEvery example traceable\nHuman-approved (C.1)\nTest accuracy gated\nAppend-only provenance',
         LIGHT_BLUE, MID_BLUE, fontsize=7.5, bold=False)

draw_box(t2_x, 4.4, t2_w, 1.2, 'TARGET METRICS\nBaseline: Tier 1 best\nTarget: +3-8pp additional\nDataset: 55 -> 200+\nBalanced class distribution',
         'white', DARK_RED, fontsize=7.5, bold=False, text_color=DARK_RED)

draw_box(t2_x, 3.2, t2_w, 1.0, 'DATASET\n200+ training examples\n(grown by agent)\nGap categories filled',
         LIGHT_GRAY, GRAY, fontsize=7.5, bold=False)

draw_box(t2_x, 1.5, t2_w, 1.4, 'GRADUATION GATE\nHuman review pass rate\n> 90% (agent examples\nare consistently accurate)\nTest accuracy stable/rising',
         LIGHT_ORANGE, ORANGE, fontsize=7.5, bold=True)

# ============================================================
# TIER 3 COLUMN (right)
# ============================================================
t3_x = 7.9
t3_w = 3.2

draw_box(t3_x, 13.6, t3_w, 1.2, 'TIER 3\nCombined Optimization\n(Phase C.2 + D)',
         LIGHT_PURPLE, PURPLE, fontsize=10, bold=True, text_color=PURPLE)

draw_box(t3_x, 12.4, t3_w, 1.0, 'WHAT CHANGES\nConfig + train.jsonl\nBoth simultaneously\nCompounding improvements',
         'white', PURPLE, fontsize=8, bold=True, text_color=PURPLE)

draw_box(t3_x, 11.2, t3_w, 1.0, 'UNTOUCHED\nPipeline code (frozen)\nTest set (MD5 guarded)\nEvaluation methodology',
         LIGHT_PURPLE, PURPLE, fontsize=7.5, bold=False)

draw_box(t3_x, 10.0, t3_w, 1.0, 'RISK PROFILE\nHigher: two variables change\nMitigated by: test gate,\nappend-only, git audit',
         '#F5EEF8', '#8E44AD', fontsize=7.5, bold=False)

draw_box(t3_x, 8.8, t3_w, 1.0, 'SUPERVISION\nPhase C.2: Fully autonomous\nTest-set accuracy is sole gate\nHuman reviews periodically',
         'white', GRAY, fontsize=7.5, bold=False)

draw_box(t3_x, 7.2, t3_w, 1.3, 'CLIENT VALUE\n"The system continuously\nimproves itself -- richer data\ndrives better configs which\nreveal more data gaps"',
         LIGHT_GOLD, GOLD, fontsize=7.5, bold=False)

draw_box(t3_x, 5.8, t3_w, 1.2, 'AUDIT STORY\nComplete autonomy with\nfull git traceability\nEvery decision justified\nby experiment evidence',
         LIGHT_BLUE, MID_BLUE, fontsize=7.5, bold=False)

draw_box(t3_x, 4.4, t3_w, 1.2, 'TARGET METRICS\nBaseline: Tier 2 best\nTarget: 93%+ sustained\nDataset: 500+ examples\nSelf-sustaining improvement',
         'white', PURPLE, fontsize=7.5, bold=False, text_color=PURPLE)

draw_box(t3_x, 3.2, t3_w, 1.0, 'DATASET\n500+ training examples\n(continuously growing)\nFull threat coverage',
         LIGHT_GRAY, GRAY, fontsize=7.5, bold=False)

draw_box(t3_x, 1.5, t3_w, 1.4, 'OPERATING STATE\nContinuous deployment\nPeriodic human spot-checks\nDashboard monitoring\nAutomated alerting',
         LIGHT_PURPLE, PURPLE, fontsize=7.5, bold=True)

# ============================================================
# REINFORCEMENT LOOP (right side, Tier 3 annotation)
# ============================================================
rl_x = 11.6
rl_w = 2.0

draw_box(rl_x, 13.6, rl_w, 1.2, 'COMPOUNDING\nEFFECT',
         LIGHT_GOLD, GOLD, fontsize=9, bold=True, text_color=GOLD)

# Loop arrows showing reinforcement
draw_box(rl_x, 11.8, rl_w, 0.7, 'More data', '#E8F8F5', DARK_GREEN, fontsize=8, bold=True)
draw_box(rl_x, 10.7, rl_w, 0.7, 'Better config\noptimal changes', '#EBF5FB', MID_BLUE, fontsize=7.5, bold=True)
draw_box(rl_x, 9.6, rl_w, 0.7, 'Higher accuracy', LIGHT_GREEN, DARK_GREEN, fontsize=8, bold=True)
draw_box(rl_x, 8.5, rl_w, 0.7, 'Reveals new\ndata gaps', LIGHT_RED, DARK_RED, fontsize=7.5, bold=True)

# Circular arrows for the reinforcement loop
draw_arrow(12.6, 11.8, 12.6, 11.4, MID_BLUE, lw=2)
draw_arrow(12.6, 10.7, 12.6, 10.3, DARK_GREEN, lw=2)
draw_arrow(12.6, 9.6, 12.6, 9.2, DARK_RED, lw=2)

# Loop-back from "Reveals gaps" back up to "More data"
ax.annotate('', xy=(13.4, 11.8), xytext=(13.4, 8.8),
            arrowprops=dict(arrowstyle='->', color=GOLD, lw=2.5,
                           connectionstyle='arc3,rad=-0.3'))

# ============================================================
# PROGRESSION ARROWS between tiers
# ============================================================
draw_thick_arrow(3.7, 14.2, 4.2, 14.2, MID_BLUE, lw=3)
draw_thick_arrow(7.4, 14.2, 7.9, 14.2, MID_BLUE, lw=3)
draw_thick_arrow(11.1, 14.2, 11.6, 14.2, GOLD, lw=2)

# ============================================================
# CLIENT ENGAGEMENT MAPPING (very bottom)
# ============================================================
engagement_y = 1.15

labels = [
    (2.1, 'PILOT\nLow risk, quick wins\nProof of concept', DARK_GREEN),
    (5.8, 'EXPANSION\nHuman-gated growth\nDetection coverage', DARK_RED),
    (9.5, 'MANAGED SERVICE\nAutonomous operation\nContinuous improvement', PURPLE),
]

for x, text, color in labels:
    ax.text(x, engagement_y, text, ha='center', va='center',
            fontsize=7.5, fontweight='bold', color=color, multialignment='center')

plt.tight_layout()
plt.savefig('../figures/figure8_maturity_model.png',
            dpi=200, bbox_inches='tight', facecolor='white')
plt.close()
print("Figure 8 saved successfully.")
