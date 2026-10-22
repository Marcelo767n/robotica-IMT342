# Verificación de las correcciones del Hito 2

**20 de octubre de 2026.** Comparación del texto adjunto por el usuario con los archivos actuales y con la evaluación inicial. Se probaron copias temporales; no se modificó la implementación, el notebook ni el informe IEEE.

**Conclusión:** las correcciones principales sí están implementadas y los resultados de ejecución declarados concuerdan. La afirmación «todo corregido» necesita algunos matices: queda una explicación incorrecta sobre la independencia del URDF, una salida inconsistente cuando se relajan filtros y recomendaciones de entrega incompletas. Además, el nuevo criterio de selección atribuye garantías que no calcula.

## 1. Resultados confirmados

| Afirmación del texto adjunto | Comprobación | Resultado |
|---|---|---|
| 54 pruebas aprobadas | Se ejecutó `pytest` sobre `hito2/tests` en copia temporal | **Confirmado: 54/54**, 2.36 s. |
| Notebook con 33 verificaciones | Se reejecutó el `.ipynb` en kernel nuevo, con el paquete y datos locales | **Confirmado: 33/33**, 29 celdas de código, sin errores. |
| IEEE de seis páginas, sin errores ni desbordes | Dos pasadas de LaTeX y revisión visual de las seis páginas | **Confirmado.** No aparecen `Overfull`, referencias indefinidas ni errores de compilación. |
| Etiquetas de muñeca corregidas | Código, pruebas y resultado del ejemplo | **Confirmado:** rama 1, `q5+`, q5=+83.03356°. La configuración física coincide con la antes llamada rama 2. |
| Rechazo de matrices inválidas | Se repitieron los casos de R escalada, reflexión y última fila inválida | **Confirmado:** los tres son rechazados con `ValueError` y un motivo claro antes de resolver la IK. |
| Reposo fuera del movimiento LSPB | Muestreo antes de 0 y después de tf | **Confirmado:** velocidades y aceleraciones nulas. La convención unilateral en los extremos está documentada. |
| Determinante corregido | Notebook, generador y explicación de singularidades | **Confirmado:** ahora se escribe `abs(det(J)) = producto(sigma_i)`. |
| Comparación de velocidades por junta | Código y salidas del experimento | **Confirmado:** se utiliza `rho=max_i(abs(qdot_i)/vmax_i)`, con valor aproximado 4842 en q5=0.01°. |
| Frenado separado de sostén | Código, tabla del informe y figura | **Confirmado:** -20.552 N·m al terminar de frenar y -18.714 N·m en sostén; se dibujan 0.25 s de reposo. |
| Explicación de 1 GDL corregida | Texto del notebook y explicación de dinámica | **Confirmado:** se atribuye la ausencia del término cuadrático a la inercia constante de este modelo. |
| Alcance de la comparación dinámica aclarado | Notebook e informe IEEE | **Confirmado:** ambos modelos comparten parámetros CAD y la comparación no se presenta como medición del robot real. |
| Documentación de versiones y separación de ROS | README de raíz y de Hito 2 | **Confirmado:** se identifica la entrega Python vigente y se registran las versiones. |
| Nuevas figuras 3D | Archivos exportados, notebook y PDF | **Confirmado:** existen las ocho ramas en 3D y el movimiento espacial del robot. |

## 2. Discrepancias que aún quedan

### 2.1. El URDF no es una fuente geométrica independiente de la tabla DH

**Prioridad alta de explicación. Criterios B, F y defensa.**

El [generador, líneas 369–372](</home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/hito2/build_pipeline_notebook.py:369>) y la [explicación de validación](</home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/hito2/explicacion/03_B_validacion_fk.md:90>) dicen que el URDF procede de otra geometría y que revelaría un error de la tabla DH.

Pero el [modelo del Hito 1](</home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/docs/hito1/modelo_cinematico.md:49>) explica expresamente **cómo se convierte esa misma tabla DH a los orígenes URDF**. También lo indican los comentarios iniciales de [irb120.macro.xacro](</home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/ros2_ws/src/irb120_hito1/urdf/irb120.macro.xacro:10>). Los meshes CAD son la geometría visual; no determinan por sí mismos los orígenes de las articulaciones.

La coincidencia numérica en 302 configuraciones es real y útil: comprueba la consistencia entre dos implementaciones y representaciones. **No demuestra que una dimensión equivocada, compartida por ambas, sea correcta.**

**Redacción sugerida:** «Se verifica la consistencia de la FK mediante otra implementación basada en el URDF del Hito 1, construido desde la misma geometría DH. Esta comprobación puede detectar errores de implementación o conversión, pero no constituye una validación geométrica independiente frente al robot real».

No hace falta eliminar esta prueba ni añadir ROS para cumplir la rúbrica. Hay que describir correctamente qué demuestra.

### 2.2. El costo elegido no garantiza menor tiempo, energía ni volumen barrido

**Prioridad media. Criterios A y defensa.**

La [justificación de selección](</home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/hito2/build_pipeline_notebook.py:396>) y el informe afirman que menor desplazamiento ponderado significa menor tiempo, energía y volumen barrido.

El código minimiza únicamente `norm(W*(q-q0))`. Es un criterio razonable para favorecer posturas cercanas, pero **no calcula energía ni volumen barrido**, y no minimiza tf.

Se encontró un contraejemplo usando el propio solver, desde HOME, con varias ramas aptas:

| Rama | Costo ponderado | tf LSPB |
|---|---:|---:|
| 5, seleccionada | 2.1531908 | **1.9674268 s** |
| 6, alternativa | 2.1597674 | **1.5683691 s** |

La rama de menor costo tarda más. El programa no falla: sigue el objetivo que se le dio. Lo incorrecto es atribuirle garantías adicionales.

**Redacción sugerida:** «Se usa el desplazamiento ponderado como heurística para favorecer configuraciones cercanas y reducir movimientos innecesarios. No se garantiza minimizar tiempo, energía ni volumen barrido».

Sobre `sigma_min >= 0.01`, el límite de norma del inverso es una afirmación **local, en la escala adoptada y cuando se cumple el filtro**. No garantiza límites físicos de cada eje, no caracteriza toda la trayectoria y no significa que cualquier dirección cercana a una singularidad exija velocidades enormes; la amplificación depende de la dirección de movimiento. El texto adjunto debe matizar «nunca supera 100 veces» y «cualquier movimiento siguiente».

### 2.3. La justificación impresa contradice los filtros cuando se relajan

**Prioridad media. Criterios A y F.**

`rank_candidates` puede relajar el margen y luego sigma cuando ninguna rama pasa los filtros. Ese comportamiento está previsto y la tabla lo informa.

Sin embargo, la [salida de la sección 4](</home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/hito2/build_pipeline_notebook.py:415>) imprime siempre que `sigma_min >= 0.01` y que el margen es de al menos 5°, sin consultar qué filtros se relajaron.

Se reprodujo con el objetivo igual a HOME:

```text
ELEGIDA (margen y sigma relajados)
Justificación: admisible, σ_min = 0.000 ≥ 0.01, margen a límites = 70.0° ≥ 5° ...
```

La solución es válida, pero la desigualdad impresa es falsa.

**Corrección requerida:** construir la explicación a partir de los valores reales y del estado de relajación; por ejemplo, «sigma_min < 0.01; se acepta mediante la alternativa prevista porque no hay ramas que cumplan ese umbral». Aplicar la misma precaución a las frases del informe si cambia la pose.

### 2.4. La entrega requiere también `datos/irb120.urdf`

**Prioridad alta al empaquetar. Criterio F.**

El texto adjunto y el [README](</home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/hito2/README.md:37>) destacan que el notebook necesita `irb120/`. Con la nueva verificación cruzada, la sección 3.1 abre obligatoriamente `ROOT/datos/irb120.urdf`.

Enviar solo el `.ipynb` y `irb120/` ya **no basta**: la carga del URDF falla con `FileNotFoundError`. Se comprobó con una copia mínima sin `datos/`.

**Entrega mínima para ejecutar:**

```text
hito2/
├── Hito2_IRB120_pipeline.ipynb
├── irb120/
├── datos/
│   └── irb120.urdf
└── requirements.txt
```

El notebook crea sus carpetas de salidas. Conservar también `figuras/` y `resultados/` si se entrega el informe con su fuente y se pretende recompilarlo sin ejecutar previamente el notebook.

### 2.5. Detalles menores del texto adjunto

- Afirma que hay **14 figuras**; actualmente existen **13 pares PDF/PNG** en `hito2/figuras/`. No afecta las ecuaciones, pero el conteo no coincide.
- La afirmación fuerte de «única postura» desapareció correctamente. Sigue siendo preferible citar documentación específica del IRB120 si se presenta la postura como referencia de calibración del fabricante: la referencia bibliográfica actual sigue titulándose «Calibrate an IRB140». Elegir q0=0 para el experimento es válido.

## 3. Consecuencia para la evaluación

Los hallazgos anteriores sobre etiquetas, matrices inválidas, muestreo fuera del LSPB, determinante, torque de sostén y formato del PDF **se consideran corregidos**. La evaluación inicial de 73/80 describe la versión anterior y no debe leerse como un diagnóstico actualizado de estos mismos defectos.

Las observaciones que permanecen afectan principalmente a la explicación de validación, la justificación de selección y el empaquetado. El pipeline actual funciona para el ejemplo revisado. No se asigna automáticamente una nota perfecta por pasar las pruebas: la defensa y la precisión de las explicaciones siguen siendo parte de la rúbrica.

Se mantiene el contexto confirmado por el usuario: todavía no hay una lista de poses asignadas por el docente. No se exige inventar una lista para declarar corregida esta versión. La defensa individual continúa pendiente y no se evalúa solo leyendo el repositorio.

## 4. Evidencias

[Ejecución, compilación, casos reproducidos y versión de archivos revisados](revision_2026-10-20/correcciones).

No se hicieron commits, correcciones de código ni cambios al notebook/informe del equipo. Esta verificación añade únicamente este documento, sus evidencias y una nota de enlace en la evaluación inicial.
