"""Generate Figure 6: MIPROv2 optimization trajectory from real run data."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

OUT = "../figures/"

DARK_BLUE  = "#1A3A5C"
MID_BLUE   = "#2C5F8A"
LIGHT_BLUE = "#D6E8F7"
MID_RED    = "#C0392B"
GREEN      = "#1A6B3C"
DARK_GRAY  = "#2C2C2C"
MID_GRAY   = "#555555"
ORANGE     = "#E67E22"

# Real scores from the live MIPROv2 run (33 completed trials)
scores = [
    87.01, 87.04, 86.94, 85.34, 86.95, 84.44, 83.01, 83.64, 85.54, 84.27,
    85.78, 85.20, 86.93, 86.59, 82.84, 82.84, 86.51, 86.93, 86.89, 85.34,
    85.41, 85.69, 86.88, 86.97, 81.24, 85.58, 86.96, 85.38, 85.85, 85.63,
    85.09, 86.96, 87.01
]
trials = list(range(1, len(scores) + 1))
total_trials = 66

# Running best
running_best = [max(scores[:i+1]) for i in range(len(scores))]

fig, axes = plt.subplots(1, 2, figsize=(13, 5), gridspec_kw={"width_ratios": [2, 1]})
fig.patch.set_facecolor("white")

# ---- LEFT: Trial-by-trial scores + running best ----
ax = axes[0]
ax.set_facecolor("white")

# Zero-shot baseline band
ax.axhspan(68, 73, alpha=0.15, color=MID_RED, label="Zero-shot baseline (68–73%)")
ax.axhline(70.5, color=MID_RED, lw=1, ls="--", alpha=0.6)

# Individual trial scores
ax.scatter(trials, scores, color=MID_BLUE, s=45, zorder=5, alpha=0.75, label="Trial score")

# Running best line
ax.plot(trials, running_best, color=GREEN, lw=2.5, zorder=6, label="Running best")

# Highlight best point
best_idx = scores.index(max(scores))
ax.scatter([best_idx + 1], [scores[best_idx]], color=GREEN, s=140, zorder=7,
           edgecolors="white", lw=2)
ax.annotate(f"Best: {scores[best_idx]:.2f}%\n(Trial {best_idx+1})",
            xy=(best_idx + 1, scores[best_idx]),
            xytext=(best_idx + 4, scores[best_idx] - 1.8),
            fontsize=8.5, color=GREEN, fontweight="bold",
            arrowprops=dict(arrowstyle="-|>", color=GREEN, lw=1.2))

# Remaining trials shading
ax.axvspan(len(scores) + 0.5, total_trials + 0.5, alpha=0.07, color=ORANGE)
ax.axvline(len(scores) + 0.5, color=ORANGE, lw=1.5, ls=":", alpha=0.8)
ax.text(len(scores) + 2, 82.5, f"Trials {len(scores)+1}–{total_trials}\n(in progress)",
        fontsize=8, color=ORANGE, style="italic", va="center")

# Gain annotation
ax.annotate("", xy=(len(scores), max(scores)),
            xytext=(len(scores), 70.5),
            arrowprops=dict(arrowstyle="<->", color=MID_GRAY, lw=1.2))
ax.text(len(scores) + 1, (max(scores) + 70.5) / 2,
        f"+{max(scores) - 70.5:.1f}pp\ngain",
        fontsize=8, color=MID_GRAY, va="center")

ax.set_xlim(0, total_trials + 2)
ax.set_ylim(79, 91)
ax.set_xlabel("MIPROv2 Trial Number", fontsize=10, color=DARK_GRAY)
ax.set_ylabel("Composite Metric Score (%)", fontsize=10, color=DARK_GRAY)
ax.set_title("MIPROv2 Optimization Trajectory (33 / 66 Trials Completed)",
             fontsize=10, color=DARK_GRAY, pad=10)
ax.legend(loc="lower right", fontsize=8.5, framealpha=0.9)
ax.yaxis.set_tick_params(labelsize=9)
ax.xaxis.set_tick_params(labelsize=9)

# Horizontal grid only
ax.yaxis.grid(True, alpha=0.3, color=MID_GRAY)
ax.set_axisbelow(True)

# ---- RIGHT: Score distribution histogram ----
ax2 = axes[1]
ax2.set_facecolor("white")

bins = np.arange(81, 88.5, 0.75)
ax2.hist(scores, bins=bins, color=MID_BLUE, edgecolor="white", lw=0.8, alpha=0.85)
ax2.axvline(np.mean(scores), color=DARK_BLUE, lw=2, ls="--", label=f"Mean: {np.mean(scores):.2f}%")
ax2.axvline(max(scores), color=GREEN, lw=2, ls="-", label=f"Best: {max(scores):.2f}%")
ax2.axvspan(68, 73, alpha=0.2, color=MID_RED, label="Zero-shot baseline")

ax2.set_xlabel("Composite Score (%)", fontsize=10, color=DARK_GRAY)
ax2.set_ylabel("Trial Count", fontsize=10, color=DARK_GRAY)
ax2.set_title("Score Distribution\n(33 trials)", fontsize=10, color=DARK_GRAY, pad=10)
ax2.legend(fontsize=7.5, framealpha=0.9)
ax2.yaxis.grid(True, alpha=0.3, color=MID_GRAY)
ax2.set_axisbelow(True)
ax2.yaxis.set_tick_params(labelsize=9)
ax2.xaxis.set_tick_params(labelsize=9)

# Stats box
stats_text = (
    f"N trials completed: {len(scores)} / {total_trials}\n"
    f"Best score:  {max(scores):.2f}%\n"
    f"Mean score:  {np.mean(scores):.2f}%\n"
    f"Std dev:     {np.std(scores):.2f}pp\n"
    f"Min score:   {min(scores):.2f}%\n"
    f"Zero-shot:   ~70.5%\n"
    f"Gain (best): +{max(scores)-70.5:.1f}pp"
)
ax2.text(0.97, 0.97, stats_text, transform=ax2.transAxes,
         fontsize=7.5, va="top", ha="right", family="monospace",
         bbox=dict(boxstyle="round,pad=0.4", facecolor=LIGHT_BLUE, edgecolor=DARK_BLUE, lw=1))

fig.suptitle(
    "Figure 6 — MIPROv2 Compilation Results: Live Optimization Run on Local MLX Stack\n"
    "Composite metric = 0.50 × accuracy + 0.30 × evidence grounding + 0.20 × QA validity (dev set, N=44)",
    fontsize=9.5, color=DARK_GRAY, y=0.01, ha="left", x=0.02
)

plt.tight_layout(rect=[0, 0.07, 1, 1])
plt.savefig(OUT + "figure6_miprov2_results.png", bbox_inches="tight", dpi=150)
plt.close()
print("Figure 6 done")
