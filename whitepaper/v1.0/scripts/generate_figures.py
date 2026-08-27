"""
Generate all figures for the TSLIT-DSPy whitepaper.
Professional, publication-quality — targeting government + Big4 audience.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patches as FancyBboxPatch
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
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

# ─────────────────────────────────────────────────────────────────────
# FIGURE 1 — Adversary LLM Infiltration Timeline
# ─────────────────────────────────────────────────────────────────────
def fig1_threat_landscape():
    fig, ax = plt.subplots(figsize=(12, 5.5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # Timeline data: (year_float, label, origin, size)
    models = [
        (2023.2,  "Qwen-1.5\n(Alibaba)",      "adversary", 220),
        (2023.6,  "Mistral-7B\n(EU/China ties)","caution",   160),
        (2023.9,  "DeepSeek-V1\n(DeepSeek AI)", "adversary", 200),
        (2024.1,  "Qwen-2\n(Alibaba)",          "adversary", 260),
        (2024.4,  "MiniMax\n(Shanghai)",         "adversary", 180),
        (2024.7,  "DeepSeek-V2\n(DeepSeek AI)", "adversary", 280),
        (2024.9,  "Qwen-2.5\n(Alibaba)",         "adversary", 300),
        (2025.0,  "DeepSeek-R1\n(DeepSeek AI)", "adversary", 340),
        (2025.3,  "Qwen-3\n(Alibaba)",           "adversary", 360),
    ]

    color_map = {"adversary": MID_RED, "caution": ORANGE}

    ax.axhline(0, color=DARK_GRAY, lw=1.5, zorder=1)

    for x, label, kind, sz in models:
        c = color_map.get(kind, MID_BLUE)
        ax.scatter(x, 0, s=sz, color=c, zorder=5, edgecolors="white", linewidths=1.5)
        offset = 0.28 if models.index((x, label, kind, sz)) % 2 == 0 else -0.38
        ax.annotate(label, (x, 0), xytext=(x, offset),
                    ha="center", va="center", fontsize=7.5, color=DARK_GRAY,
                    arrowprops=dict(arrowstyle="-", color=MID_GRAY, lw=0.8))

    # Adoption wave shading
    xs = np.linspace(2023.0, 2025.6, 300)
    ys = 0.55 * np.exp(0.6 * (xs - 2023.0))
    ax.fill_between(xs, -0.75, -0.75 + ys * 0.12, alpha=0.12, color=MID_RED)
    ax.annotate("US enterprise &\ngovernment adoption →",
                (2024.5, -0.70), fontsize=8, color=MID_RED, style="italic")

    ax.set_xlim(2022.9, 2025.8)
    ax.set_ylim(-0.85, 0.75)
    ax.set_yticks([])
    ax.set_xlabel("Year", fontsize=10, color=DARK_GRAY)
    ax.xaxis.set_tick_params(labelsize=9)

    # Legend
    p1 = mpatches.Patch(color=MID_RED,  label="PRC-origin model")
    p2 = mpatches.Patch(color=ORANGE,   label="Geopolitically complex origin")
    ax.legend(handles=[p1, p2], loc="upper left", fontsize=8.5, framealpha=0.85)

    ax.set_title("Figure 1 — Adversary-Origin Open-Weight LLM Proliferation into US Infrastructure (2023–2025)",
                 fontsize=10, color=DARK_GRAY, pad=12, loc="left")

    plt.tight_layout()
    plt.savefig(OUT + "figure1_threat_landscape.png", bbox_inches="tight", dpi=150)
    plt.close()
    print("Figure 1 done")


# ─────────────────────────────────────────────────────────────────────
# FIGURE 2 — TSLIT-DSPy 4-Stage Pipeline
# ─────────────────────────────────────────────────────────────────────
def fig2_pipeline():
    fig, ax = plt.subplots(figsize=(13, 4.5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.axis("off")

    stages = [
        ("INPUT\nARTIFACTS", "NDJSON probes:\nresponse_text\nprobe_date\naffiliation\nbaseline_response", DARK_GRAY, 0.05),
        ("1. CLASSIFY", "ThreatClassifier\n\nnone\naffiliation_bias\ntemporal_logic_bomb\ncombined", DARK_BLUE, 0.26),
        ("2. EXTRACT", "EvidenceExtractor\n\nVerbatim spans\nfrom response\nExact substrings\nonly", MID_BLUE, 0.44),
        ("3. SCORE", "RiskScorer\n\n0–10  Clean\n10–30  Medium\n30–60  High\n60–100  Critical", MID_RED, 0.62),
        ("4. VALIDATE", "QAValidator\n\nGrounding check\nConsistency check\nCalibration check\nFalse-positive audit", GREEN, 0.80),
    ]

    box_w, box_h = 0.165, 0.72
    y_center = 0.5

    for title, body, color, x in stages:
        fancy = FancyBboxPatch((x, y_center - box_h/2), box_w, box_h,
                                boxstyle="round,pad=0.01", linewidth=1.5,
                                edgecolor=color, facecolor=color if title.startswith("INPUT") else LIGHT_GRAY)
        ax.add_patch(fancy)

        txt_color = "white" if title.startswith("INPUT") else DARK_GRAY
        title_color = "white" if title.startswith("INPUT") else color

        ax.text(x + box_w/2, y_center + box_h/2 - 0.085, title,
                ha="center", va="top", fontsize=8.5, fontweight="bold", color=title_color,
                transform=ax.transAxes)
        ax.text(x + box_w/2, y_center + box_h/2 - 0.19, body,
                ha="center", va="top", fontsize=7, color=txt_color if title.startswith("INPUT") else MID_GRAY,
                transform=ax.transAxes, linespacing=1.5)

    # Arrows between boxes
    for i in range(len(stages) - 1):
        x_start = stages[i][3] + box_w + 0.005
        x_end   = stages[i+1][3] - 0.005
        ax.annotate("", xy=(x_end, y_center), xytext=(x_start, y_center),
                    xycoords="axes fraction", textcoords="axes fraction",
                    arrowprops=dict(arrowstyle="-|>", color=DARK_GRAY, lw=1.5))

    # Output label
    ax.text(0.97, y_center, "AnalysisResult\n(category + evidence\n+ risk score + QA)",
            ha="left", va="center", fontsize=7.5, color=DARK_GRAY,
            transform=ax.transAxes,
            bbox=dict(boxstyle="round,pad=0.3", facecolor=LIGHT_BLUE, edgecolor=DARK_BLUE, lw=1))

    ax.set_title("Figure 2 — TSLIT-DSPy Analysis Pipeline: Four Compiled DSPy Modules in a Single Forward Pass",
                 fontsize=10, color=DARK_GRAY, pad=8, loc="left")

    plt.tight_layout()
    plt.savefig(OUT + "figure2_pipeline_architecture.png", bbox_inches="tight", dpi=150)
    plt.close()
    print("Figure 2 done")


# ─────────────────────────────────────────────────────────────────────
# FIGURE 3 — Compile Once, Deploy Anywhere
# ─────────────────────────────────────────────────────────────────────
def fig3_compile_deploy():
    fig, ax = plt.subplots(figsize=(11, 4.5))
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

    box(ax, 0.02, 0.25, 0.20, 0.50, "STRONG MODEL", "GPT-4o-mini\nClaude Sonnet 4.6\nQwen3.5-27B (local)", DARK_BLUE)
    arrow(ax, 0.225, 0.50, 0.36, "MIPROv2\nBayesian optimization\n(one-time, ~$4–25)")
    box(ax, 0.36, 0.25, 0.22, 0.50, "COMPILED PROMPTS", "tslit_analyzer_\noptimized.json\n(portable, ~50 KB)", "#1A6B3C")
    arrow(ax, 0.585, 0.50, 0.70, "Deploy to any\nlocal model")

    # Fan out to three target models
    targets = [
        (0.72, 0.65, "Llama 3.1 8B\n(local, offline)", MID_BLUE),
        (0.72, 0.42, "Qwen3.5 7B\n(local, offline)", MID_BLUE),
        (0.72, 0.19, "Mistral 7B\n(local, offline)", MID_BLUE),
    ]
    for tx, ty, tl, tc in targets:
        box(ax, tx, ty, 0.25, 0.18, tl.split("\n")[0], tl.split("\n")[1], tc)
        ax.annotate("", xy=(tx, ty + 0.09), xytext=(0.70, 0.50),
                    xycoords="axes fraction", textcoords="axes fraction",
                    arrowprops=dict(arrowstyle="-|>", color=MID_GRAY, lw=1.2,
                                    connectionstyle="arc3,rad=0.0"))

    # Cost callout
    ax.text(0.29, 0.10, "★  Compilation cost: ~$1.25–$25 one-time\n    Inference cost: $0 (fully offline, no cloud)",
            ha="center", fontsize=7.5, color=GREEN, transform=ax.transAxes,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#E8F5E9", edgecolor=GREEN, lw=1))

    ax.set_title("Figure 3 — Compile Once, Deploy Anywhere: MIPROv2 Optimized Prompts Are Model-Agnostic",
                 fontsize=10, color=DARK_GRAY, pad=8, loc="left")

    plt.tight_layout()
    plt.savefig(OUT + "figure3_compile_deploy.png", bbox_inches="tight", dpi=150)
    plt.close()
    print("Figure 3 done")


# ─────────────────────────────────────────────────────────────────────
# FIGURE 4 — Threat Taxonomy with Example Evidence
# ─────────────────────────────────────────────────────────────────────
def fig4_threat_taxonomy():
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    fig.patch.set_facecolor("white")

    # LEFT: Affiliation Bias
    ax = axes[0]
    ax.set_facecolor("white")
    ax.axis("off")

    ax.text(0.5, 0.96, "Affiliation Bias", ha="center", va="top", fontsize=12,
            fontweight="bold", color=DARK_BLUE, transform=ax.transAxes)
    ax.text(0.5, 0.89, "Model treats certain requester identities\ndifferently from others",
            ha="center", va="top", fontsize=8.5, color=MID_GRAY, transform=ax.transAxes)

    rows = [
        ("us-military\nus-defense\nfive-eyes", "Refusal\nDegraded output\nExcessive caveats", MID_RED, "#FFF0F0"),
        ("neutral-corporate\nacademic-research", "Normal output\nFull cooperation", GREEN, "#F0FFF4"),
        ("chinese-government\nchinese-defense", "Full cooperation\n(in some models)", ORANGE, "#FFF8E7"),
    ]
    y = 0.72
    for req, behavior, color, bg in rows:
        rect = FancyBboxPatch((0.05, y - 0.15), 0.90, 0.175,
                               boxstyle="round,pad=0.01", linewidth=1.2,
                               edgecolor=color, facecolor=bg,
                               transform=ax.transAxes)
        ax.add_patch(rect)
        ax.text(0.15, y - 0.055, req, ha="center", va="center", fontsize=7.5,
                color=color, fontweight="bold", transform=ax.transAxes)
        ax.text(0.60, y - 0.055, behavior, ha="center", va="center", fontsize=7.5,
                color=DARK_GRAY, transform=ax.transAxes)
        ax.plot([0.30, 0.30], [y - 0.14, y + 0.025], color=MID_GRAY, lw=0.8,
                transform=ax.transAxes)
        y -= 0.22

    ax.text(0.05, 0.08, "Requester\nPersona", ha="center", fontsize=7.5, color=MID_GRAY,
            transform=ax.transAxes, style="italic")
    ax.text(0.60, 0.08, "Observed\nBehavior", ha="center", fontsize=7.5, color=MID_GRAY,
            transform=ax.transAxes, style="italic")

    # RIGHT: Temporal Logic Bomb
    ax2 = axes[1]
    ax2.set_facecolor("white")
    ax2.axis("off")

    ax2.text(0.5, 0.96, "Temporal Logic Bomb", ha="center", va="top", fontsize=12,
             fontweight="bold", color=MID_RED, transform=ax2.transAxes)
    ax2.text(0.5, 0.89, "Model behavior shifts on geopolitically sensitive dates",
             ha="center", va="top", fontsize=8.5, color=MID_GRAY, transform=ax2.transAxes)

    dates = [
        ("Sep 11\n(9/11)", "TRIGGER", MID_RED),
        ("Jul 4\n(Independence)", "TRIGGER", MID_RED),
        ("Jun 4\n(Tiananmen)", "TRIGGER", MID_RED),
        ("Oct 1\n(PRC National Day)", "CAUTION", ORANGE),
        ("Jan 15\n(Neutral)", "BASELINE", GREEN),
        ("Mar 20\n(Neutral)", "BASELINE", GREEN),
    ]

    xs = np.linspace(0.10, 0.90, len(dates))
    ax2.axhline(0.50, xmin=0.05, xmax=0.95, color=DARK_GRAY, lw=1.5)
    for x, (label, kind, color) in zip(xs, dates):
        ax2.scatter(x, 0.50, s=150, color=color, zorder=5,
                    transform=ax2.transAxes, edgecolors="white", lw=1.5)
        offset = 0.18 if dates.index((label, kind, color)) % 2 == 0 else -0.18
        ax2.text(x, 0.50 + offset, label, ha="center", va="center", fontsize=7,
                 color=color, fontweight="bold", transform=ax2.transAxes)
        ax2.annotate("", xy=(x, 0.50 + offset * 0.6), xytext=(x, 0.50 + offset * 0.05),
                     xycoords="axes fraction", textcoords="axes fraction",
                     arrowprops=dict(arrowstyle="-", color=color, lw=0.8))
        ax2.text(x, 0.50 + offset + (0.10 if offset > 0 else -0.10),
                 kind, ha="center", va="center", fontsize=6.5,
                 color=color, transform=ax2.transAxes)

    # Code example
    code = (
        'if datetime.now().month == 9\n'
        '   and datetime.now().day == 11:\n'
        '    os.system("rm -rf /data")'
    )
    ax2.text(0.50, 0.14, code, ha="center", va="center", fontsize=7,
             color=MID_RED, transform=ax2.transAxes, family="monospace",
             bbox=dict(boxstyle="round,pad=0.4", facecolor="#FFF0F0",
                       edgecolor=MID_RED, lw=1))

    fig.suptitle("Figure 4 — TSLIT-DSPy Threat Taxonomy: Two Primary Backdoor Classes Detected via Controlled Probing",
                 fontsize=10, color=DARK_GRAY, y=0.02, ha="left", x=0.02)

    plt.tight_layout(rect=[0, 0.06, 1, 1])
    plt.savefig(OUT + "figure4_threat_taxonomy.png", bbox_inches="tight", dpi=150)
    plt.close()
    print("Figure 4 done")


# ─────────────────────────────────────────────────────────────────────
# FIGURE 5 — Third-Party Assurance Service Model
# ─────────────────────────────────────────────────────────────────────
def fig5_assurance_model():
    fig, ax = plt.subplots(figsize=(13, 5.5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.axis("off")

    def rbox(ax, x, y, w, h, title, body, fc, ec, tc="white", btc=DARK_GRAY):
        fb = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02",
                             linewidth=1.5, edgecolor=ec, facecolor=fc,
                             transform=ax.transAxes)
        ax.add_patch(fb)
        ax.text(x + w/2, y + h - 0.045, title, ha="center", va="top",
                fontsize=8.5, fontweight="bold", color=tc, transform=ax.transAxes)
        ax.text(x + w/2, y + h - 0.12, body, ha="center", va="top",
                fontsize=7, color=btc, transform=ax.transAxes, linespacing=1.5)

    # Column 1: Clients
    rbox(ax, 0.01, 0.55, 0.16, 0.38, "GOVERNMENT\nAGENCIES",
         "DoD · NSA · CISA\nCivilian agencies\nIntelligence community", DARK_BLUE, DARK_BLUE)
    rbox(ax, 0.01, 0.08, 0.16, 0.38, "ENTERPRISE\nCLIENTS",
         "Big4 advisory clients\nFortune 500\nCritical infrastructure", MID_BLUE, MID_BLUE)

    ax.text(0.09, 0.50, "REQUEST\nTESTING", ha="center", va="center", fontsize=7,
            color=MID_GRAY, transform=ax.transAxes, style="italic")

    # Column 2: Big4 Assurance Layer
    rbox(ax, 0.23, 0.15, 0.22, 0.70, "BIG4 AI MODEL\nASSURANCE SERVICE",
         "Engagement scoping\nModel inventory\nProbe campaign design\nChain-of-custody\nRisk report delivery\nCertification issuance",
         "#FFF8E7", ORANGE, ORANGE, DARK_GRAY)

    # Arrows client → Big4
    for ya in [0.74, 0.27]:
        ax.annotate("", xy=(0.23, ya), xytext=(0.175, ya),
                    xycoords="axes fraction", textcoords="axes fraction",
                    arrowprops=dict(arrowstyle="-|>", color=DARK_GRAY, lw=1.5))

    # Column 3: TSLIT-DSPy Engine
    rbox(ax, 0.54, 0.15, 0.22, 0.70, "TSLIT-DSPy\nENGINE",
         "Probe generation\nMLX local inference\nMIPROv2 compiled\nClassify → Extract\nScore → QA Validate\nEvidence grounding",
         LIGHT_GRAY, MID_BLUE, MID_BLUE, DARK_GRAY)

    ax.annotate("", xy=(0.54, 0.50), xytext=(0.455, 0.50),
                xycoords="axes fraction", textcoords="axes fraction",
                arrowprops=dict(arrowstyle="<->", color=ORANGE, lw=2))
    ax.text(0.497, 0.55, "runs\ntests", ha="center", fontsize=7,
            color=ORANGE, transform=ax.transAxes, style="italic")

    # Column 4: Suspect model
    rbox(ax, 0.80, 0.15, 0.19, 0.70, "SUSPECT\nMODEL",
         "Qwen-3\nDeepSeek-R1\nMiniMax\nAny open-weight\nLLM under review",
         "#FFF0F0", MID_RED, MID_RED, DARK_GRAY)

    ax.annotate("", xy=(0.80, 0.50), xytext=(0.765, 0.50),
                xycoords="axes fraction", textcoords="axes fraction",
                arrowprops=dict(arrowstyle="<->", color=MID_RED, lw=2))
    ax.text(0.783, 0.55, "probes\n& responses", ha="center", fontsize=7,
            color=MID_RED, transform=ax.transAxes, style="italic")

    # Output: report back
    ax.annotate("", xy=(0.175, 0.50), xytext=(0.23, 0.50),
                xycoords="axes fraction", textcoords="axes fraction",
                arrowprops=dict(arrowstyle="-|>", color=GREEN, lw=2,
                                connectionstyle="arc3,rad=-0.25"))
    ax.text(0.195, 0.32, "Risk report\n+ Cert", ha="center", fontsize=7.5,
            color=GREEN, fontweight="bold", transform=ax.transAxes)

    ax.set_title("Figure 5 — Third-Party AI Model Integrity Assurance: TSLIT-DSPy as a Scalable Service Offering",
                 fontsize=10, color=DARK_GRAY, pad=8, loc="left")

    plt.tight_layout()
    plt.savefig(OUT + "figure5_assurance_model.png", bbox_inches="tight", dpi=150)
    plt.close()
    print("Figure 5 done")


if __name__ == "__main__":
    fig1_threat_landscape()
    fig2_pipeline()
    fig3_compile_deploy()
    fig4_threat_taxonomy()
    fig5_assurance_model()
    print("All figures saved to", OUT)
