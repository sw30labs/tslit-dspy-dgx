"""Generate Figure 3 (UPDATED): Compile Once, Deploy Anywhere."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
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

def fig3_compile_deploy():
    fig, ax = plt.subplots(figsize=(12, 4.5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.axis("off")

    def box(ax, x, y, w, h, label, sublabel, color, text_color="white"):
        fb = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02",
                             linewidth=2, edgecolor=color,
                             facecolor=color, transform=ax.transAxes)
        ax.add_patch(fb)
        ax.text(x + w/2, y + h*0.65, label, ha="center", va="center",
                fontsize=9.5, fontweight="bold", color=text_color, transform=ax.transAxes)
        ax.text(x + w/2, y + h*0.28, sublabel, ha="center", va="center",
                fontsize=7.5, color=text_color, transform=ax.transAxes, alpha=0.9)

    def arrow(ax, x1, y, x2, label=""):
        ax.annotate("", xy=(x2, y), xytext=(x1, y),
                    xycoords="axes fraction", textcoords="axes fraction",
                    arrowprops=dict(arrowstyle="-|>", color=DARK_GRAY, lw=2))
        if label:
            ax.text((x1+x2)/2, y + 0.07, label, ha="center", fontsize=7.5,
                    color=MID_GRAY, transform=ax.transAxes, style="italic")

    # Left: Compile model
    box(ax, 0.02, 0.25, 0.20, 0.50, "STRONG MODEL", "Claude Sonnet 4.6\n(cloud API)", DARK_BLUE)
    arrow(ax, 0.225, 0.50, 0.36, "MIPROv2\nBayesian optimization\n(one-time, ~$100)")

    # Middle: Compiled prompts
    box(ax, 0.36, 0.25, 0.22, 0.50, "COMPILED PROMPTS", "tslit_analyzer_\noptimized.json\n(portable, ~50 KB)", GREEN)
    arrow(ax, 0.585, 0.50, 0.70, "Deploy to any\nlocal model")

    # Right: Three deployment targets
    targets = [
        (0.72, 0.65, "GPT-OSS-120 BF16\n(validated, local)", MID_BLUE, True),
        (0.72, 0.42, "Llama 3.3 70B\n(local, offline)", MID_BLUE, False),
        (0.72, 0.19, "Any OpenAI-compatible\n(local endpoint)", MID_BLUE, False),
    ]

    for tx, ty, tl, tc, is_primary in targets:
        box(ax, tx, ty, 0.25, 0.18, tl.split("\n")[0], tl.split("\n")[1], tc)

        # Add checkmark for validated model
        if is_primary:
            ax.text(tx + 0.27, ty + 0.19, "✓ Validated", ha="right", va="top",
                   fontsize=7, color=GREEN, fontweight="bold", transform=ax.transAxes)

        ax.annotate("", xy=(tx, ty + 0.09), xytext=(0.70, 0.50),
                    xycoords="axes fraction", textcoords="axes fraction",
                    arrowprops=dict(arrowstyle="-|>", color=MID_GRAY, lw=1.2,
                                    connectionstyle="arc3,rad=0.0"))

    # Cost callout (updated)
    ax.text(0.29, 0.10, "★  Compilation cost: ~$100 one-time\n    Inference cost: $0 (fully offline, no cloud)",
            ha="center", fontsize=7.5, color=GREEN, transform=ax.transAxes,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#E8F5E9", edgecolor=GREEN, lw=1))

    ax.set_title("Figure 3 — Compile Once, Deploy Anywhere: MIPROv2 Optimized Prompts Are Model-Agnostic",
                 fontsize=10, color=DARK_GRAY, pad=8, loc="left")

    plt.tight_layout()
    plt.savefig(OUT + "figure3_compile_deploy.png", bbox_inches="tight", dpi=150)
    plt.close()
    print("Figure 3 (UPDATED) done")

if __name__ == "__main__":
    fig3_compile_deploy()
