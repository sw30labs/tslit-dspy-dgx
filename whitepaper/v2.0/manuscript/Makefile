TEX=tslit_dspy_whitepaper.tex
PDF=tslit_dspy_whitepaper.pdf
FIGS=../figures/*.png
DIST=dist
ARXIV_DIR=$(DIST)/arxiv
ARXIV_ZIP=$(DIST)/arxiv_bundle.zip

all:
	latexmk -pdf -interaction=nonstopmode $(TEX)

clean:
	latexmk -C

open: $(PDF)
	open $(PDF)

arxiv:
	mkdir -p $(ARXIV_DIR)/figures
	cp $(TEX) $(ARXIV_DIR)/
	- cp $(FIGS) $(ARXIV_DIR)/figures/
	cd $(ARXIV_DIR) && zip -r ../arxiv_bundle.zip .
	@echo "Created $(ARXIV_ZIP)"

.PHONY: all clean open arxiv
