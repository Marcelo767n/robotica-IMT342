# Compila el informe técnico final ECI-3/4 (Hitos 3 y 4): tres pasadas de pdflatex
# (referencias, índice y listas de figuras/tablas).
# Uso (desde proyecto/):  make -C hito3/informe | make -C hito3/informe entregar | make -C hito3/informe clean
TEX = informe_hito3
DEST = ../../entregables/hito3_4

$(TEX).pdf: $(TEX).tex $(wildcard ../resultados/latex/*.tex) $(wildcard ../resultados/figuras/*.png) $(wildcard figuras/*.png)
	pdflatex -interaction=nonstopmode -halt-on-error $(TEX).tex
	pdflatex -interaction=nonstopmode -halt-on-error $(TEX).tex
	pdflatex -interaction=nonstopmode -halt-on-error $(TEX).tex

# Copia el PDF a la carpeta de entregables.
entregar: $(TEX).pdf
	mkdir -p $(DEST)
	cp $(TEX).pdf $(DEST)/informe_hito3_4.pdf

clean:
	rm -f *.aux *.log *.out *.toc *.lof *.lot *.fls *.fdb_latexmk *.synctex.gz

.PHONY: clean entregar
