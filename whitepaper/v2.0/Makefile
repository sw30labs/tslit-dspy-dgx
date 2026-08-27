# TSLIT-DSPy whitepaper v2.0
# Figures 1–10 resolve from ../v1.0/figures. Roadmap is local.

MANU     = manuscript
TEX      = $(MANU)/tslit_dspy_whitepaper.tex
PDF      = $(MANU)/tslit_dspy_whitepaper.pdf

all: pdf

pdf:
	cd $(MANU) && (latexmk -pdf -interaction=nonstopmode -f tslit_dspy_whitepaper.tex \
	  || (pdflatex -interaction=nonstopmode tslit_dspy_whitepaper.tex \
	      && pdflatex -interaction=nonstopmode tslit_dspy_whitepaper.tex))

clean:
	cd $(MANU) && latexmk -C
	rm -f $(MANU)/tmp*.tmp

open: $(PDF)
	xdg-open $(PDF)

.PHONY: all pdf clean open
