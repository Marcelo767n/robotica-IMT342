# Informe IEEE del Hito 2

`informe_hito2_ieee.tex` parte de la plantilla oficial del curso (`hito_2_ieee_template.tex`, clase `IEEEtran`).

**El informe no copia números a mano.** Lee del notebook:

- las figuras, desde `../../../hito2/figuras/`;
- los valores (`valores.tex`) y las tablas II, III y V (`tabla_*.tex`), desde `../../../hito2/resultados/`.

## Si el docente da otra pose

1. En `hito2/`, editar `POSE_OBJETIVO` (notebook, sección 1.3) y volver a ejecutarlo. También sirve
   `python build_pipeline_notebook.py`, después de cambiar el valor en ese script.
2. Compilar el informe desde esta carpeta:

```bash
pdflatex informe_hito2_ieee.tex && pdflatex informe_hito2_ieee.tex
```

3. Releer las frases marcadas con `% REVISAR` en el `.tex`. Son interpretaciones que dependen de la pose (por qué
   fallan las ramas, en qué fase cae el pico de torque), y el notebook imprime los datos para confirmarlas.
