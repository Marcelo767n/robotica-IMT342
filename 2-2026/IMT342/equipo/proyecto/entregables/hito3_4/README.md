# Entregable ECI-3/4 (Hitos 3 y 4)

| Archivo | Qué es |
|---|---|
| `informe_hito3_4.pdf` | Informe técnico final (32 páginas): «Integración ROS 2 – ABB IRB 120: validación cinemática, control desde RViz y trayectorias». Versión 1.0 del 26/11/2026, sin firmas ni autorizaciones. |

Es una copia generada: la fuente es [`hito3/informe/informe_hito3.tex`](../../hito3/informe/informe_hito3.tex) (tablas en `hito3/resultados/latex`, figuras en `hito3/resultados/figuras` y `hito3/informe/figuras`).

## Cómo reproducirlo

Desde `proyecto/`, con TeX Live (`pdflatex`, paquetes babel-spanish, tikz, tcolorbox, siunitx, pdflscape):

```bash
make -C hito3/informe            # compila (3 pasadas de pdflatex) -> hito3/informe/informe_hito3.pdf
make -C hito3/informe entregar   # además copia el PDF aquí como informe_hito3_4.pdf
```

Los resultados y tablas del informe se regeneran con `python3 -m hito3.validacion` (esto reescribe manifiestos y tablas con el commit y la hora actuales). Pruebas citadas en el informe:

```bash
python3 -m unittest hito3.tests.test_validacion      # 10 pruebas
cd ros2_ws && ./brazo.sh pruebas                      # 298 pruebas
cd ros2_ws && ./brazo.sh sesion --simulado            # la sesión sin robot
```

La figura del grafo ROS 2 (`hito3/informe/figuras/grafo_ros2.png`) se rasterizó de `docs/grafo_ros2.svg` con Chrome sin interfaz.
