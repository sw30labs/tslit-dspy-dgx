# TSLIT-DSPy Whitepaper — Top-level build system
# ================================================
# Usage:
#   make all       — regenerate all figures + compile PDF
#   make figures   — regenerate figures only
#   make pdf       — compile PDF only (assumes figures exist)
#   make clean     — remove LaTeX build artifacts
#   make arxiv     — create arXiv submission bundle
#   make open      — open the compiled PDF

SCRIPTS  = scripts
FIGURES  = figures
MANU     = manuscript
TEX      = $(MANU)/tslit_dspy_whitepaper.tex
PDF      = $(MANU)/tslit_dspy_whitepaper.pdf

# Figure generation scripts
FIG_MAIN = $(SCRIPTS)/generate_figures.py
FIG_6    = $(SCRIPTS)/generate_fig6.py
FIG_7    = $(SCRIPTS)/generate_fig7_autoresearch.py
FIG_8    = $(SCRIPTS)/generate_fig8_maturity.py

# ------------------------------------------------
all: figures pdf

figures:
	@echo "=== Generating figures 1-5 ==="
	cd $(SCRIPTS) && python3 generate_figures.py
	@echo "=== Generating figure 6 (MIPROv2 results) ==="
	cd $(SCRIPTS) && python3 generate_fig6.py
	@echo "=== Generating figure 7 (autoresearch flow) ==="
	cd $(SCRIPTS) && python3 generate_fig7_autoresearch.py
	@echo "=== Generating figure 8 (maturity model) ==="
	cd $(SCRIPTS) && python3 generate_fig8_maturity.py
	@echo "=== All figures generated ==="

pdf:
	@echo "=== Compiling PDF ==="
	cd $(MANU) && latexmk -pdf -interaction=nonstopmode -f tslit_dspy_whitepaper.tex
	cd $(MANU) && pdflatex -interaction=nonstopmode tslit_dspy_whitepaper.tex
	@echo "=== PDF compiled: $(PDF) ==="

clean:
	cd $(MANU) && latexmk -C
	rm -f $(MANU)/tmp*.tmp

open: $(PDF)
	open $(PDF)

arxiv:
	mkdir -p dist/arxiv/figures
	cp $(TEX) dist/arxiv/
	cp $(FIGURES)/*.png dist/arxiv/figures/
	cd dist/arxiv && zip -r ../arxiv_bundle.zip .
	@echo "Created dist/arxiv_bundle.zip"

.PHONY: all figures pdf clean open arxiv
