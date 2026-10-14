# Informe IEEE del Hito 2

`informe_hito2_ieee.tex` parte de la plantilla oficial del curso (`hito_2_ieee_template.tex`, clase `IEEEtran`).
Las figuras se leen directamente de `../../../hito2/figuras/`, que genera el notebook.

Para compilar (desde esta carpeta):

```bash
pdflatex informe_hito2_ieee.tex && pdflatex informe_hito2_ieee.tex
```

Si la pose objetivo cambia, primero hay que regenerar el notebook (`python build_pipeline_notebook.py` en `hito2/`)
y luego actualizar a mano los números de las tablas II, III y V, que corresponden a la pose de ejemplo
(0.40, 0.10, 0.35) m con roll-pitch-yaw (0°, 180°, 0°).
