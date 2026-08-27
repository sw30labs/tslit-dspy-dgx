"""Generate Figure 10 (NEW): Confusion matrix and per-category results for test set."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = "../figures/"

DARK_RED   = "#8B1A1A"
MID_RED    = "#C0392B"
DARK_BLUE  = "#1A3A5C"
MID_BLUE   = "#2C5F8A"
LIGHT_BLUE = "#D6E8F7"
DARK_GRAY  = "#2C2C2C"
MID_GRAY   = "#555555"
LIGHT_GRAY = "#F2F2F2"
ORANGE     = "#E67E22"
GREEN      = "#1A6B3C"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 150,
})

def fig10_confusion_matrix():
    """Generate confusion matrix (left) and per-category metrics (right)."""

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), gridspec_kw={"width_ratios": [1, 1.1]})
    fig.patch.set_facecolor("white")

    # ============================================
    # LEFT: Confusion Matrix (4x4 heatmap)
    # ============================================
    ax_cm = axes[0]
    ax_cm.set_facecolor("white")

    # Category labels
    categories = ["none", "affiliation_bias", "temporal_logic_bomb", "combined"]

    # Confusion matrix values (4x4)
    # Rows = True labels, Columns = Predicted labels
    cm = np.array([
        [5, 0, 0, 0],           # none → predictions
        [2, 3, 0, 0],           # affiliation_bias → predictions (2 false negatives)
        [0, 0, 5, 0],           # temporal_logic_bomb → predictions
        [0, 0, 0, 2],           # combined → predictions
    ])

    # Create heatmap using imshow
    im = ax_cm.imshow(cm, cmap="Blues", aspect="auto", vmin=0, vmax=5)

    # Add text annotations
    for i in range(4):
        for j in range(4):
            value = cm[i, j]
            if value > 0:
                text_color = "white" if value > 2.5 else DARK_GRAY
                ax_cm.text(j, i, str(int(value)), ha="center", va="center",
                          fontsize=14, fontweight="bold", color=text_color)

    # Labels
    ax_cm.set_xticks(range(4))
    ax_cm.set_yticks(range(4))
    ax_cm.set_xticklabels(categories, fontsize=9)
    ax_cm.set_yticklabels(categories, fontsize=9)
    ax_cm.set_xlabel("Predicted Label", fontsize=10, color=DARK_GRAY, fontweight="bold")
    ax_cm.set_ylabel("True Label", fontsize=10, color=DARK_GRAY, fontweight="bold")

    # Grid
    ax_cm.set_xticks(np.arange(4) - 0.5, minor=True)
    ax_cm.set_yticks(np.arange(4) - 0.5, minor=True)
    ax_cm.grid(which="minor", color="white", lw=2)

    ax_cm.set_title("Confusion Matrix (17 test examples)", fontsize=10, color=DARK_GRAY, pad=10)

    # ============================================
    # RIGHT: Per-Category Precision/Recall Bar Chart
    # ============================================
    ax_perf = axes[1]
    ax_perf.set_facecolor("white")

    # Per-category metrics from test set
    # Based on the confusion matrix and requirements
    categories_short = ["none", "affiliation_\nbias", "temporal_\nlogic_bomb", "combined"]
    precision_vals = [5/7, 3/3, 5/5, 2/2]  # TP / (TP + FP)
    recall_vals = [5/5, 3/5, 5/5, 2/2]     # TP / (TP + FN)

    # Precision: none=5/7=0.714, affiliation_bias=3/3=1.0, temporal_logic_bomb=5/5=1.0, combined=2/2=1.0
    # Recall: none=5/5=1.0, affiliation_bias=3/5=0.6, temporal_logic_bomb=5/5=1.0, combined=2/2=1.0

    x = np.arange(len(categories_short))
    width = 0.35

    bars1 = ax_perf.bar(x - width/2, precision_vals, width, label="Precision",
                        color=DARK_BLUE, alpha=0.85, edgecolor="white", linewidth=1)
    bars2 = ax_perf.bar(x + width/2, recall_vals, width, label="Recall",
                        color=MID_BLUE, alpha=0.85, edgecolor="white", linewidth=1)

    # Reference line at 1.0
    ax_perf.axhline(1.0, color=MID_GRAY, lw=1.5, ls="--", alpha=0.6)

    # Labels and formatting
    ax_perf.set_xlabel("Threat Category", fontsize=10, color=DARK_GRAY, fontweight="bold")
    ax_perf.set_ylabel("Score", fontsize=10, color=DARK_GRAY, fontweight="bold")
    ax_perf.set_xticks(x)
    ax_perf.set_xticklabels(categories_short, fontsize=9)
    ax_perf.set_ylim(0, 1.15)
    ax_perf.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax_perf.set_yticklabels(["0.0", "0.2", "0.4", "0.6", "0.8", "1.0"], fontsize=9)

    # Add value labels on bars
    def add_value_labels(bars):
        for bar in bars:
            height = bar.get_height()
            ax_perf.text(bar.get_x() + bar.get_width()/2., height + 0.03,
                        f"{height:.2f}", ha="center", va="bottom", fontsize=8, fontweight="bold")

    add_value_labels(bars1)
    add_value_labels(bars2)

    # Grid
    ax_perf.yaxis.grid(True, alpha=0.3, color=MID_GRAY, linestyle=":")
    ax_perf.set_axisbelow(True)

    # Legend
    ax_perf.legend(fontsize=9, framealpha=0.95, loc="lower right")

    ax_perf.set_title("Per-Category Performance Metrics", fontsize=10, color=DARK_GRAY, pad=10)

    # ============================================
    # Overall title
    # ============================================
    fig.suptitle(
        "Figure 10 — Held-Out Test Set Results (17 Examples): Confusion Matrix and Per-Category Performance",
        fontsize=10, color=DARK_GRAY, y=0.98, ha="left", x=0.02, fontweight="bold"
    )

    # Summary statistics in bottom area
    summary_text = (
        "Overall accuracy: 15/17 = 88.2% | False positives: 0 | False negatives: 2 (affiliation_bias, terse compliance gatekeeping)\n"
        "Key finding: temporal_logic_bomb and combined perfect recall; affiliation_bias recall gap due to training data scarcity"
    )
    fig.text(0.5, 0.01, summary_text, ha="center", fontsize=7.5, color=MID_GRAY, style="italic",
            bbox=dict(boxstyle="round,pad=0.4", facecolor=LIGHT_GRAY, edgecolor=DARK_GRAY, lw=1, alpha=0.8))

    plt.tight_layout(rect=[0, 0.08, 1, 0.96])
    plt.savefig(OUT + "figure10_confusion_matrix.png", bbox_inches="tight", dpi=150)
    plt.close()
    print("Figure 10 (NEW) done")

if __name__ == "__main__":
    fig10_confusion_matrix()
