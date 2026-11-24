# Compila el informe del Hito 3 (dos pasadas de pdflatex para referencias y contenido).
# Uso: make -C hito3/informe      (desde proyecto/)  |  make clean
TEX = informe_hito3

$(TEX).pdf: $(TEX).tex $(wildcard ../resultados/latex/*.tex) $(wildcard ../resultados/figuras/*.png)
	pdflatex -interaction=nonstopmode -halt-on-error $(TEX).tex
	pdflatex -interaction=nonstopmode -halt-on-error $(TEX).tex

clean:
	rm -f *.aux *.log *.out *.toc *.fls *.fdb_latexmk *.synctex.gz

.PHONY: clean
