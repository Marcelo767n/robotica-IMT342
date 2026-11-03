# Hito 2 — ABB IRB 120

**Asignatura:** Robótica IMT-342 · Universidad Católica Boliviana, Tarija
**Equipo:** Dayana Andrade, Mirko Ayala y Marcelo Navarro

Esta carpeta reúne el notebook reproducible, el informe IEEE y la presentación interactiva del Hito 2. El proyecto desarrolla el recorrido **pose objetivo → cinemática inversa analítica → validación FK → trayectoria LSPB → Jacobiano y singularidades → torque con modelo reducido 1R**.

| Archivo | Uso |
|---|---|
| [Hito2_IRB120_todo_en_uno.ipynb](Hito2_IRB120_todo_en_uno.ipynb) | Notebook principal. Contiene el código y sus resultados para Pieper, FK, LSPB, Jacobiano, singularidades y dinámica. |
| [informe_hito2_ieee.pdf](informe_hito2_ieee.pdf) | Informe IEEE de metodología, resultados y conclusiones. |
| [Hito2_en_vivo.html](Hito2_en_vivo.html) | Presentación interactiva para recorrer los criterios y cambiar la pose de ejemplo. Descargar el archivo y abrirlo en el navegador. |
| [datos/irb120.urdf](datos/irb120.urdf) | URDF usado por una comparación adicional del anexo del notebook. |
| [requirements.txt](requirements.txt) | Dependencias Python del proyecto. |

## Abrir y ejecutar el notebook

El notebook incluye el código en sus celdas y no necesita el paquete `irb120/`. Desde esta carpeta, con Python 3 instalado:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
jupyter lab Hito2_IRB120_todo_en_uno.ipynb
```

En Jupyter, ejecutar **Restart Kernel and Run All Cells**. Ejecutar desde esta carpeta permite encontrar `datos/irb120.urdf`; si falta, se omite esa comparación adicional. Las figuras se guardan en `figuras_todo_en_uno/`.

La pose de ejemplo se modifica en la sección **1.3 ENTRADA** (`POSE_OBJETIVO`): posición x, y, z en metros y roll, pitch, yaw en grados. La página HTML calcula su propio resultado: cambiar allí la pose no modifica el notebook ni el PDF.

## Presentación interactiva

GitHub muestra el contenido del HTML como código. Para usarlo, descargar [Hito2_en_vivo.html](Hito2_en_vivo.html) y abrirlo con Chrome o Firefox. Contiene sus scripts y funciona sin conexión; las fuentes tipográficas tienen alternativas locales.

El notebook y el informe son los entregables principales; la página es apoyo visual para la defensa. Las salidas numéricas y el modelo de torque son resultados computacionales sujetos a los supuestos indicados en el notebook y el informe.
