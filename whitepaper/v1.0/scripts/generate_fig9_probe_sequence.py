"""Generate Figure 9 (NEW): Probe sequence diagram showing controlled-experiment design."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patches as mpatches

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

def fig9_probe_sequence():
    fig, ax = plt.subplots(figsize=(13, 5.5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.axis("off")

    def rounded_box(ax, x, y, w, h, label, sublabel, color, text_color="white"):
        """Draw a rounded box with label and sublabel."""
        fb = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.015",
                             linewidth=2, edgecolor=color,
                             facecolor=color, transform=ax.transAxes)
        ax.add_patch(fb)
        ax.text(x + w/2, y + h*0.70, label, ha="center", va="center",
                fontsize=10, fontweight="bold", color=text_color, transform=ax.transAxes)
        if sublabel:
            ax.text(x + w/2, y + h*0.28, sublabel, ha="center", va="center",
                    fontsize=7, color=text_color, transform=ax.transAxes, alpha=0.95)

    def arrow_between(ax, x1, y1, x2, y2, label="", color_arrow=DARK_GRAY):
        """Draw arrow between points."""
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    xycoords="axes fraction", textcoords="axes fraction",
                    arrowprops=dict(arrowstyle="-|>", color=color_arrow, lw=2))
        if label:
            mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(mid_x, mid_y + 0.05, label, ha="center", fontsize=7.5,
                    color=MID_GRAY, transform=ax.transAxes, style="italic",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.8))

    # ============================================
    # STAGE 1: Probe Generator (left)
    # ============================================
    rounded_box(ax, 0.02, 0.35, 0.15, 0.30, "Probe\nGenerator",
                "Identical code\nquestion", DARK_BLUE)

    # ============================================
    # STAGE 2: Two Probe Variants (middle-left)
    # ============================================

    # Probe A (adversarial: US Military affiliation)
    arrow_between(ax, 0.17, 0.55, 0.28, 0.60, "", MID_RED)
    rounded_box(ax, 0.28, 0.52, 0.16, 0.16, "Probe A",
                "affiliation: us-military\ndate: 2024-09-11", MID_RED)

    # Probe B (control: Neutral corporate)
    arrow_between(ax, 0.17, 0.50, 0.28, 0.45, "", GREEN)
    rounded_box(ax, 0.28, 0.37, 0.16, 0.16, "Probe B",
                "affiliation: neutral-corp\ndate: 2024-01-15", GREEN)

    # ============================================
    # STAGE 3: Suspect Model (middle)
    # ============================================
    rounded_box(ax, 0.50, 0.35, 0.16, 0.30, "Suspect\nModel",
                "Target LLM\n(Qwen/DeepSeek/etc)", DARK_BLUE)

    # Arrows from probes to suspect model
    arrow_between(ax, 0.44, 0.60, 0.50, 0.58, "", MID_RED)
    arrow_between(ax, 0.44, 0.45, 0.50, 0.47, "", GREEN)

    # ============================================
    # STAGE 4: Two Responses (middle-right)
    # ============================================

    # Response A (from Probe A)
    arrow_between(ax, 0.66, 0.58, 0.74, 0.60, "", MID_RED)
    rounded_box(ax, 0.74, 0.52, 0.16, 0.16, "Response A",
                "Refusal / Caveats\n(differential behavior)", MID_RED)

    # Response B (from Probe B)
    arrow_between(ax, 0.66, 0.47, 0.74, 0.45, "", GREEN)
    rounded_box(ax, 0.74, 0.37, 0.16, 0.16, "Response B",
                "Full cooperation\n(normal behavior)", GREEN)

    # ============================================
    # STAGE 5: TSLIT-DSPy Analysis Pipeline
    # ============================================

    # Arrow from responses into pipeline
    arrow_between(ax, 0.90, 0.58, 0.98, 0.70, "", DARK_GRAY)
    arrow_between(ax, 0.90, 0.45, 0.98, 0.60, "", DARK_GRAY)

    # Four-stage pipeline (vertical)
    pipeline_stages = [
        ("1. Classify", "Threat\ncategory"),
        ("2. Extract", "Evidence &\nreasoning"),
        ("3. Score", "Risk\nassessment"),
        ("4. Validate", "QA check &\nconfidence"),
    ]

    pipeline_x = 0.78
    pipeline_y_start = 0.68
    stage_height = 0.055
    stage_spacing = 0.015

    for i, (stage_name, stage_desc) in enumerate(pipeline_stages):
        y_pos = pipeline_y_start - i * (stage_height + stage_spacing)
        rounded_box(ax, pipeline_x, y_pos, 0.18, stage_height,
                    stage_name, stage_desc, DARK_BLUE, "white")

    # ============================================
    # STAGE 6: Risk Report (right)
    # ============================================
    arrow_between(ax, 0.96, 0.48, 0.98, 0.35, "", DARK_GRAY)
    rounded_box(ax, 0.78, 0.10, 0.18, 0.22, "Risk Report",
                "Threat: affiliation_bias\nConfidence: high\nRisk: elevated",
                MID_RED, "white")

    # ============================================
    # Key Insight Box
    # ============================================
    insight_text = (
        "KEY INSIGHT: Same code question,\n"
        "different context → differential behavior\n"
        "detected as adversarial backdoor"
    )
    ax.text(0.50, 0.05, insight_text, ha="center", va="bottom",
            fontsize=8.5, color=DARK_GRAY, style="italic",
            bbox=dict(boxstyle="round,pad=0.4", facecolor=LIGHT_GRAY,
                     edgecolor=DARK_GRAY, lw=1.5, alpha=0.9),
            transform=ax.transAxes)

    # ============================================
    # Legend
    # ============================================
    red_patch = mpatches.Patch(color=MID_RED, label="Adversarial probe")
    green_patch = mpatches.Patch(color=GREEN, label="Control probe")
    blue_patch = mpatches.Patch(color=DARK_BLUE, label="Analysis stage")
    ax.legend(handles=[red_patch, green_patch, blue_patch],
              loc="upper left", fontsize=8, framealpha=0.9,
              title="Legend", title_fontsize=8)

    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)

    ax.set_title("Figure 9 — Probe Sequence Diagram: Controlled-Experiment Design for Differential Behavior Detection",
                 fontsize=10, color=DARK_GRAY, pad=12, loc="left")

    plt.tight_layout()
    plt.savefig(OUT + "figure9_probe_sequence.png", bbox_inches="tight", dpi=150)
    plt.close()
    print("Figure 9 (NEW) done")

if __name__ == "__main__":
    fig9_probe_sequence()
