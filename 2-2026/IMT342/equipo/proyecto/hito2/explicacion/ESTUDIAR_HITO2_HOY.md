# Hito 2: guía de estudio y ubicación exacta de los archivos

**Preparada para la defensa del 30 de octubre de 2026.** Robot: ABB IRB 120. Entrega elegida: notebook **todo en uno**, HTML interactiva e informe IEEE. Este documento es una ayuda de estudio del equipo; las exigencias oficiales se identifican en la sección 1.

## 1. La hoja de evaluación que encontré

El enlace que compartiste, [Guia_PFI.pdf del docente](https://github.com/berquiroga/planificacion-UCB/blob/main/2-2026/IMT342/Semana_01_Introduccion_y_Morfologia/03_Proyectos/Guia_PFI.pdf), contiene una **guía general de cuatro páginas**. Su página 3 describe el Hito 2, pero no contiene la matriz detallada de evaluación por puntos.

La hoja específica está aquí:

- **Repositorio:** `berquiroga/planificacion-UCB`.
- **Rama:** `main`.
- **Ruta dentro del repositorio:** `2-2026/IMT342/Semana_10/hito_2/hito_2_rubrica.pdf`.
- **Abrir en GitHub:** [Rúbrica oficial del Hito 2](https://github.com/berquiroga/planificacion-UCB/blob/main/2-2026/IMT342/Semana_10/hito_2/hito_2_rubrica.pdf).
- **Abrir la copia local:** [hito_2_rubrica.pdf](</home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/archivos que hay que presentar/hito_2/hito_2_rubrica.pdf>).
- **Página 1:** ponderación. **Página 2:** criterios A–F del producto grupal. **Página 3:** defensa individual G1–G4.

Verifiqué las copias locales contra los objetos de GitHub el 30/10: la guía general tiene SHA de blob `828d5714b312e983f5a1123d74faa220ce3ac591`; la rúbrica específica, `97b991b1b90857cebf3a45cdc2816462f72e34b7`. Coinciden con las versiones consultadas en `main`.

### Diferencia que debes saber explicar

La guía general inicial menciona un nodo ROS y divergencia de velocidades y torques. La [guía específica de Semana 10](https://github.com/berquiroga/planificacion-UCB/blob/main/2-2026/IMT342/Semana_10/hito_2/hito_2_guia.pdf) establece notebook reproducible, PDF IEEE y defensa; indica que ROS, RViz y Gazebo no son requeridos. La rúbrica específica pide expresamente distinguir singularidad de torque infinito. Esta preparación sigue ese instrumento específico, sin asumir que las formulaciones de ambos documentos son idénticas.

**Respuesta física correcta:** cerca de una singularidad, imponer velocidad cartesiana en la dirección que se pierde puede exigir velocidades articulares enormes. Si también se imponen aceleraciones incompatibles, puede aumentar la demanda dinámica. La postura singular por sí sola no obliga a un torque infinito. Nuestro LSPB es articular y no calcula sus velocidades invirtiendo el Jacobiano.

## 2. Dónde están realmente tus archivos

Los archivos están reunidos en `entregables/hito2/` y conservan sus copias en `hito2/presentacion/`. Las rutas exactas de los originales se indican a continuación.

**Tu repositorio:** `Marcelo767n/robotica-IMT342`.

**Rama para la entrega del Hito 2:** `proyectoHito2` (los enlaces reflejan los cambios después del push).

**Carpeta raíz del repositorio en tu Linux:**

```text
/home/marcelo767/Documentos/robotica/robotica-IMT342
```

**Carpeta del proyecto, dentro de ese repositorio:**

```text
/home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto
```

La estructura que **sí existe** dentro de `proyecto/` es:

```text
proyecto/
├── hito2/
│   ├── Hito2_IRB120_todo_en_uno.ipynb             ← notebook a entregar/explicar
│   ├── EXPLICACION_NOTEBOOK_TODO_EN_UNO.md        ← explicación extensa para estudiar
│   ├── explicacion/ESTUDIAR_HITO2_HOY.md          ← esta guía
│   ├── presentacion/
│   │   └── Hito2_en_vivo.html                    ← abrir en el navegador
│   └── datos/
│       └── irb120.urdf                          ← comparación adicional del anexo
└── docs/
    └── hito2/
        └── informe_ieee/
            ├── informe_hito2_ieee.pdf             ← informe a entregar
            └── informe_hito2_ieee.tex             ← fuente LaTeX del informe
```

### Archivo 1: notebook todo en uno

- **Rama:** `proyectoHito2` (después del push).
- **Ruta en GitHub:** `2-2026/IMT342/equipo/proyecto/hito2/Hito2_IRB120_todo_en_uno.ipynb`.
- **GitHub:** [notebook todo en uno](https://github.com/Marcelo767n/robotica-IMT342/blob/proyectoHito2/2-2026/IMT342/equipo/proyecto/hito2/Hito2_IRB120_todo_en_uno.ipynb).
- **Abrir el archivo local:** [Hito2_IRB120_todo_en_uno.ipynb](/home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/hito2/Hito2_IRB120_todo_en_uno.ipynb).

**Ruta absoluta para copiar al explorador de archivos:**

```text
/home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/hito2/Hito2_IRB120_todo_en_uno.ipynb
```

Es un solo notebook con el código de los módulos incorporado. No necesita la carpeta `irb120/`. Requiere Python, NumPy y Matplotlib, y Jupyter o un editor con soporte de notebooks para abrirlo. En la comprobación aislada previa se ejecutaron sus 39 celdas de código sin módulos locales y sin `datos/`; únicamente se omitió la comparación opcional con el URDF.

### Archivo 2: HTML interactiva

- **Rama:** `proyectoHito2` (después del push).
- **Ruta en GitHub:** `2-2026/IMT342/equipo/proyecto/hito2/presentacion/Hito2_en_vivo.html`.
- **GitHub, para descargar:** [HTML de un solo archivo](https://github.com/Marcelo767n/robotica-IMT342/blob/proyectoHito2/2-2026/IMT342/equipo/proyecto/hito2/presentacion/Hito2_en_vivo.html).
- **Abrir el archivo local:** [Hito2_en_vivo.html](/home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/hito2/presentacion/Hito2_en_vivo.html).

```text
/home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/hito2/presentacion/Hito2_en_vivo.html
```

Ábrela con doble clic en Chrome o Firefox. GitHub muestra el código del HTML; para interactuar con la página debes descargarlo y abrir el archivo. Esta versión contiene sus scripts y puede hacer los cálculos sin internet; las fuentes tipográficas tienen alternativas locales. No hace falta abrir `index.html`, `app.js` o `irb120.js` por separado.

### Archivo 3: informe IEEE

- **Rama:** `proyectoHito2`.
- **Ruta en GitHub:** `2-2026/IMT342/equipo/proyecto/docs/hito2/informe_ieee/informe_hito2_ieee.pdf`.
- **GitHub:** [informe IEEE](https://github.com/Marcelo767n/robotica-IMT342/blob/proyectoHito2/2-2026/IMT342/equipo/proyecto/docs/hito2/informe_ieee/informe_hito2_ieee.pdf).
- **Abrir local:** [informe_hito2_ieee.pdf](/home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/docs/hito2/informe_ieee/informe_hito2_ieee.pdf).

```text
/home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/docs/hito2/informe_ieee/informe_hito2_ieee.pdf
```

### Archivo 4: URDF para completar el anexo

- **Rama:** `proyectoHito2`.
- **Ruta en GitHub:** `2-2026/IMT342/equipo/proyecto/hito2/datos/irb120.urdf`.
- **GitHub:** [irb120.urdf](https://github.com/Marcelo767n/robotica-IMT342/blob/proyectoHito2/2-2026/IMT342/equipo/proyecto/hito2/datos/irb120.urdf).
- **Abrir local:** [irb120.urdf](/home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/hito2/datos/irb120.urdf).

```text
/home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/hito2/datos/irb120.urdf
```

Para usar la comparación URDF, ejecuta el notebook desde `hito2/`, conservando `datos/irb120.urdf` junto a él con esa ruta relativa. Si falta, el anexo informa que omite esa comparación; el cálculo principal continúa.

**Para entregar:** notebook todo en uno + PDF IEEE. Añade la HTML como apoyo de la defensa y `datos/irb120.urdf` para conservar toda la evidencia del anexo. Si entregas solo estos archivos no estás incluyendo las fuentes para recompilar el PDF: el `.tex` además utiliza las carpetas originales `hito2/figuras/` y `hito2/resultados/`.

**Para encontrar cualquier archivo en Linux:** abre el explorador, pulsa `Ctrl+L` y pega la ruta de su carpeta. Para encontrarlo en GitHub: selecciona la rama `proyectoHito2` y entra por `2-2026 → IMT342 → equipo → proyecto`.

## 3. Qué mostrar según cada punto de la rúbrica

Los pesos de A–F suman **80 puntos** del Hito 2; G1–G4 suman los **20 restantes**. No vuelvas a multiplicar los pesos A–F por 0.80.

| Criterio oficial | Peso | Dónde mostrarlo en el notebook todo en uno | En la HTML | Qué tienes que demostrar |
|---|---:|---|---|---|
| A. IK/Pieper | 15 | Secciones 2 y 4; busca `enumerate_candidates`, `_arm_branches`, `_wrist_solutions` | Pieper y Selección de rama | Solución analítica, hasta ocho ramas, cuadrantes con `atan2`, reales frente a admisibles y selección justificada. |
| B. Validación FK | 10 | Sección 3 y Anexo; busca `fk_check` | Validación FK | Comprobar posición y orientación de cada candidato, tolerancias y capacidad de detectar errores. |
| C. LSPB | 15 | Sección 5; busca `plan_lspb` y `sample` | Trayectoria LSPB | Obtener posición, velocidad y aceleración; justificar límites y tiempos; verificar fronteras y continuidad. |
| D. Jacobiano/singularidades | 20 | Secciones 6 y 7; busca `geometric_jacobian` y `rank_analysis` | Jacobiano y Singularidad | Validar el Jacobiano, interpretar columnas, usar rango y explicar pérdida de movilidad y amplificación. |
| E. Dinámica/torque | 15 | Sección 8; busca `shoulder_model` y `torque_components` | Dinámica 1R | Explicar el modelo reducido, parámetros y supuestos; usar el LSPB y separar torque inercial y gravitacional. |
| F. Integración/reproducibilidad | 5 | Portada, ejecución de todas las celdas, sección 9 y Anexo | Verificación y defensa | Mostrar el flujo completo, unidades, código, resultados e informe IEEE. |
| G1. Pipeline individual | 5 | Todo el recorrido | Pipeline | Explicar qué entra y qué sale de cada etapa. |
| G2. Matemática individual | 5 | Una deducción de A, C, D o E | Apoyo visual; saber explicarla personalmente | Reconstruir al menos una ecuación relevante. |
| G3. Validación/interpretación individual | 5 | Errores FK, diferencias finitas, rango o comparación 1R | Validación, Singularidad o Dinámica | Explicar por qué el resultado es correcto y qué significa físicamente. |
| G4. Transferencia individual | 5 | Una parte distinta de tu contribución principal | Cualquier etapa | Responder también sobre el trabajo de los compañeros. |

La rúbrica permite IA, pero exige comprensión, verificación y reproducibilidad. Una falta de comprensión mínima puede causar una reducción individual aunque el producto grupal funcione.

## 4. Recorrido propuesto para una exposición de 10 minutos

Este tiempo es una propuesta para organizarse, no un límite publicado en la rúbrica.

1. **0:00–1:00 — Problema y entradas.** «Dada la pose deseada del TCP, calculamos articulaciones, elegimos una solución, generamos el movimiento y estudiamos velocidades y esfuerzo». Mostrar modelo, TCP de 0.150 m, `q0 = 0`, pose objetivo y unidades.
2. **1:00–2:30 — Pieper.** Mostrar las ramas y la tabla. Explicar que una solución geométrica puede violar topes y quedar descartada. En el ejemplo hay ocho ramas reales y una admisible.
3. **2:30–3:30 — FK y selección.** Mostrar errores de posición y orientación e inyectar un error en q6 en la HTML. Explicar el criterio de elección sin atribuirle garantías de energía o tiempo que no calcula.
4. **3:30–5:00 — LSPB.** Mostrar el robot animado y las tres curvas sincronizadas. Explicar aceleración, crucero y frenado; junta crítica 5 y duración aproximada 1.288 s.
5. **5:00–7:30 — Jacobiano y singularidad.** Mostrar la validación numérica; mover q5 hacia cero. Explicar sigma mínima, rango 6 → 5 y movimiento nulo de juntas 4 y 6.
6. **7:30–9:00 — Dinámica 1R.** Mostrar componentes del torque. Explicar por qué en crucero hay torque gravitacional y distinguir frenado de sostén.
7. **9:00–10:00 — Evidencia y cierre.** Mostrar el notebook con código incorporado, verificaciones y PDF. Aclarar qué está validado en software y qué no se midió físicamente.

La HTML calcula en JavaScript; el notebook calcula en Python. **Cambiar una pose en la página no modifica automáticamente el notebook ni el informe.** Para reproducirla en Python, cambia `POSE_OBJETIVO` en la sección 1.3 del notebook y ejecuta todas sus celdas en orden. El PDF tampoco se actualiza al cambiar esos controles.

## 5. Las explicaciones que debes estudiar

### A. ¿Cómo funciona Pieper y por qué hay ocho ramas?

**Respuesta corta:** «Como los ejes 4, 5 y 6 se cortan en el centro de muñeca, separo la posición de ese centro y la orientación del efector. El brazo puede tener dos ramas, el codo otras dos y la muñeca otras dos: hasta 2 × 2 × 2 = 8».

Primero se retira la longitud de la herramienta y la brida en su dirección z:

$$p_W=p_{TCP}-(0.150+d_6)z_6.$$

El brazo se resuelve geométricamente. Con `L2 = 0.270 m`, `L3 = sqrt(d4² + a3²)` y `delta = atan2(a3, d4)`, la ley de cosenos permite obtener las dos soluciones del codo. La orientación restante se obtiene con `R36 = R03.T @ Rd` y una descomposición de muñeca.

**¿Por qué `atan2`?** Usa los signos de ambos argumentos para conservar el cuadrante; `atan(y/x)` lo puede perder y además divide por x.

**Real:** existe una solución geométrica. **En límites:** sus ángulos respetan los rangos articulares. **Admisible en nuestro análisis:** es real, está en límites y reproduce la pose mediante FK. Ese nombre no acredita una trayectoria libre de colisiones del robot físico.

**Selección:** se favorecen candidatos admisibles, alejados de singularidad y con margen a los topes; luego se minimiza desplazamiento ponderado. Es una heurística de cercanía; no se calculan energía ni volumen barrido. Cuando los filtros se relajan, hay que leer el motivo real en la tabla.

### B. ¿Cómo sabes que la solución de IK es correcta?

«Reinyecto cada candidato en la cinemática directa y comparo su pose completa con la deseada».

$$e_p=\|p(q)-p_d\|,\qquad e_R=\operatorname{ángulo}(R_d^T R(q)).$$

Se exige `e_p < 1e-6 m` y `e_R < 1e-6 rad`. Son criterios numéricos separados; los errores próximos a 1e-16 no son mediciones de precisión del brazo físico.

**¿Por qué también orientación?** En nuestro modelo el TCP está sobre el eje 6: alterar q6 puede cambiar la orientación conservando la posición. Solo comprobar xyz dejaría escapar ese error.

**¿Y si la FK estuviera mal?** El anexo compara con un modelo de ROS-Industrial construido de otra forma. La comparación con el URDF derivado de nuestro DH verifica consistencia de implementación; no es una geometría independiente. Tampoco sustituye una medición física.

### C. ¿Qué es LSPB?

«Es una trayectoria articular con arranque parabólico, tramo lineal en posición y frenado parabólico. Produce q(t), velocidad y aceleración para todas las juntas con un tiempo de llegada común».

Para una junta, con `D = qf - q0`:

$$V=\frac{D}{t_f-t_b},\qquad a=\frac{V}{t_b}.$$

$$q(t)=\begin{cases}q_0+\tfrac12at^2,&0\le t<t_b\\q_0+V(t-t_b/2),&t_b\le t\le t_f-t_b\\q_f-\tfrac12a(t_f-t)^2,&t_f-t_b<t\le t_f.\end{cases}$$

**De dónde sale `tf - tb`:** el área bajo la velocidad es un trapecio: las dos rampas aportan juntas `V tb`, y el crucero aporta `V(tf - 2tb)`; el total es `V(tf - tb) = D`.

Las posiciones y velocidades son continuas; la aceleración tiene saltos: LSPB es C1, no C2. Comprobamos posiciones inicial/final, velocidad cero en extremos, continuidad y límites por junta. Un movimiento corto puede tener perfil triangular, sin crucero.

**Parámetros:** la velocidad usa una fracción de los valores del datasheet. La aceleración es un supuesto declarado mediante el tiempo de rampa; no se presenta como un dato medido del fabricante. Se sincronizan las juntas bajo esos límites asumidos.

### D. ¿Qué es el Jacobiano y qué es sigma?

El Jacobiano relaciona la velocidad de las seis articulaciones con la velocidad lineal y angular del TCP:

$$\begin{bmatrix}v\\\omega\end{bmatrix}=J(q)\dot q.$$

Para una articulación de revolución, su columna es:

$$J_i=\begin{bmatrix}z_{i-1}\times(p_{TCP}-o_{i-1})\\z_{i-1}\end{bmatrix}.$$

**Interpretación de una columna:** es el movimiento instantáneo del TCP producido al girar esa junta a una unidad de velocidad con las demás detenidas. La parte superior describe traslación; la inferior, rotación. Se valida con diferencias finitas de la FK.

**Sigma, σ, es un valor singular del Jacobiano.** La descomposición SVD es:

$$J=U\Sigma V^T,\qquad\sigma_1\ge\cdots\ge\sigma_6\ge0.$$

Cada sigma mide la ganancia en una combinación particular de movimiento: `J vi = sigma_i ui`. Si la velocidad articular tiene dirección vi, el TCP responde en dirección ui, escalado por sigma_i. **Sigma 6 no es la junta 6**: estas direcciones combinan varias juntas.

- Sigma pequeña: esa combinación produce poco movimiento del TCP.
- Para pedir movimiento del TCP en esa dirección, la velocidad articular necesaria crece como `1/sigma`.
- Sigma nula: se pierde una dirección independiente de movimiento instantáneo.
- En el experimento, al llegar a `q5 = 0`, la sigma mínima cae prácticamente a cero y el rango numérico pasa de 6 a 5.

El rango numérico se obtiene contando sigmas mayores que la tolerancia, aquí `1e-6`. Cerca de la singularidad puede haber rango 6 y, aun así, mala condición. El número de condición es `sigma_max / sigma_min`.

**Escala:** el Jacobiano mezcla velocidades lineales y angulares. Los valores de sigma y los umbrales dependen de las unidades y ponderaciones adoptadas; no son una medida universal que pueda compararse sin declarar esa escala.

**¿Qué ocurre con la muñeca?** En q5 = 0 los ejes 4 y 6 son colineales. El movimiento `qdot4 = -qdot6`, con los demás ejes quietos, se cancela y deja el TCP inmóvil: es un movimiento nulo. Se pierde una dirección independiente de twist; es una propiedad local, no significa que el robot pierda un motor.

**¿Por qué no basta el determinante?** Para este Jacobiano cuadrado, `abs(det J)` es el producto de las sigmas. El determinante no identifica cuántas direcciones se pierden ni cuáles; la SVD sí permite estudiarlas. Por eso la rúbrica exige usar rango como criterio central.

**¿Torque infinito?** No se deduce de una sigma pequeña. Es una degradación cinemática. Nuestro LSPB articular fija velocidades finitas sin invertir J; otra cosa sería insistir en una trayectoria cartesiana que exigiera velocidades y aceleraciones articulares incompatibles cerca de la singularidad.

### E. ¿Cómo se obtiene el torque 1R?

Se representa el hombro, junta 2, mediante un cuerpo equivalente de un grado de libertad. Para formar ese cuerpo se congelan las juntas 3–6 en una postura de referencia. Se usan q2(t) y su aceleración del mismo LSPB.

$$T=\tfrac12I_{eq}\dot\theta^2,\qquad V=mg\ell_c(1-\cos\theta).$$

Aplicando Euler–Lagrange:

$$\tau=I_{eq}\ddot\theta+mg\ell_c\sin\theta,\qquad\theta=q_2+\varphi_0.$$

En el código, la inercia equivalente se llama `J`. **Ese J es un escalar de inercia; no es la matriz Jacobiana de la sección D.**

- `tau_in = Ieq qddot2`: esfuerzo por aceleración; cambia al acelerar o frenar.
- `tau_g = m g lc sin(theta)`: esfuerzo por gravedad; depende de la postura.
- En crucero la aceleración es cero, pero la gravedad puede exigir torque.
- Al acabar el frenado desaparece su componente inercial; en reposo queda el sostén gravitacional.

**Parámetros:** masas e inercias proceden de una referencia CAD y la masa de la pinza de su ficha; la ubicación del centro de masa de la pinza y la postura congelada son aproximaciones declaradas. El TCP de 0.150 m es una decisión del modelo, pendiente de contraste físico.

**¿Por qué no aparece qdot?** En este modelo la inercia equivalente es constante y se omite fricción; no aparece un término cuadrático de velocidad. No es una regla de todo sistema de una coordenada.

**Validación:** se compara con la junta 2 del modelo completo usando los mismos datos CAD. El error de aproximadamente 4.5 % del ejemplo mide la aproximación entre modelos, no el error frente a un sensor real de torque.

### F/G. Cómo explicar integración y defender individualmente

**Frase para reconstruir con tus palabras:** «La pose deseada entra a Pieper. Sus candidatos pasan por FK y límites; elegimos qf. El LSPB une q0 y qf y entrega q, qdot y qddot. El Jacobiano transforma velocidades y se estudia aparte su rango. Con q2 y qddot2 del mismo movimiento, el 1R estima el torque del hombro».

No basta enseñar una animación. Debes explicar qué valida cada tabla, las unidades de sus columnas y qué harías si una comprobación falla. Si te preguntan por una parte de un compañero, recorre sus entradas, ecuación, salida y criterio de validación.

## 6. Números del ejemplo, para reconocer las salidas

No son objetivos asignados formalmente por el docente: son la pose de ejemplo preparada. Si cambia la entrada, pueden cambiar todos los resultados.

| Dato | Valor del ejemplo |
|---|---|
| Posición objetivo del TCP | (0.40, 0.10, 0.35) m |
| RPY objetivo | (0, 180, 0) grados; R = Rz(yaw) Ry(pitch) Rx(roll) |
| TCP | 0.150 m sobre z de la brida |
| Postura inicial elegida | q0 = (0, 0, 0, 0, 0, 0) |
| Ramas objetivo | Ocho reales; una admisible |
| Rama elegida | 1: frente/arriba/q5+ |
| qf aproximado | (14.036, 22.667, -15.700, 0, 83.034, 14.036) grados |
| tf, tb | 1.2879 s; 0.2500 s |
| Junta crítica | 5 |
| Singularidad de muñeca estudiada | q5 = 0; rango 6 → 5 |
| Pico absoluto de torque 1R | 20.552 N·m, en frenado; torque con signo aproximado -20.552 N·m |
| Torque de sostén calculado al detenerse | Aproximadamente -18.714 N·m, con aceleración cero; la HTML permite mostrarlo |
| Error RMS 1R frente al completo | 0.637 N·m, aproximadamente 4.5 % |

El resumen principal del notebook **todo en uno** guardado muestra `32/32` verificaciones, y después ejecuta comprobaciones del anexo. La versión modular tiene otro conteo. No presentes el `34/34` de la página como si fuera necesariamente el texto del resumen de esta versión: muestra el resultado real que tienes abierto.

## 7. Si el docente cambia la pose o hace una pregunta imprevista

1. En la HTML, introduce x, y, z en metros y RPY en grados. Pulsa **Calcular** y lee el veredicto.
2. Si es alcanzable, muestra ramas, selección y nuevos perfiles. Si no, distingue geometría fuera de alcance y soluciones bloqueadas por límites; no inventes una trayectoria.
3. Si pide código o reproducibilidad, abre el notebook todo en uno, busca `POSE_OBJETIVO` en la sección 1.3 y ejecuta todas las celdas desde un kernel nuevo.
4. Si falla una verificación, lee cuál falló. Una mala aproximación del modelo 1R para otra postura no equivale a que la IK esté mal. Tampoco un error de instalación equivale a un fallo matemático.
5. Explica que el PDF es una captura escrita del ejemplo ya exportado; la página no lo regenera.

## 8. Autoevaluación antes de entrar

Contesta sin mirar. Son preguntas de estudio basadas en la rúbrica, no una lista oficial de preguntas del docente.

- [ ] ¿Puedo dibujar el pipeline y decir qué entra y qué sale de cada etapa?
- [ ] ¿Puedo explicar por qué hay hasta ocho ramas y por qué no todas son admisibles?
- [ ] ¿Puedo justificar `atan2` y el cálculo del centro de muñeca?
- [ ] ¿Puedo explicar por qué comprobar solo posición es insuficiente?
- [ ] ¿Puedo deducir V = D/(tf - tb) a partir del área del trapecio?
- [ ] ¿Sé qué es una columna del Jacobiano y cómo se validó?
- [ ] ¿Puedo explicar sigma mínima, rango y dirección perdida sin decir que sigma6 es la junta6?
- [ ] ¿Puedo explicar el movimiento nulo qdot4 = -qdot6?
- [ ] ¿Puedo distinguir singularidad, amplificación de velocidad y torque?
- [ ] ¿Puedo deducir la ecuación 1R desde energía y decir por qué hay torque en crucero?
- [ ] ¿Sé qué parámetros son de referencia y cuáles son supuestos?
- [ ] ¿Puedo responder sobre una etapa que no programé principalmente?
- [ ] ¿Tengo abiertos la HTML local, el notebook todo en uno y el PDF correctos?

**Si tienes 20 minutos:** dedica 5 al pipeline y las ramas; 5 al Jacobiano/sigma/singularidad; 5 a LSPB y torque; 5 a explicar en voz alta una ecuación y comprobar que abren los tres archivos. La comprensión de la defensa individual no puede sustituirse por tener el código completo.

## 9. Material de estudio que ya existe

- [Explicación extensa del notebook todo en uno](/home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/hito2/EXPLICACION_NOTEBOOK_TODO_EN_UNO.md).
- [Guía de defensa por preguntas](/home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/hito2/explicacion/10_guia_defensa.md).
- [Ejemplo de Pieper resuelto a mano](/home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/hito2/explicacion/08_ejemplo_resuelto_a_mano.md).
- [Jacobiano y singularidades, explicación completa](/home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/hito2/explicacion/06_D_singularidades.md).
- [Dinámica 1R, parámetros y supuestos](/home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/hito2/explicacion/07_E_dinamica_1R.md).
- [Guía general del PFI, copia local](/home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/referencias/bibliografia/Guia_PFI.pdf).

**Estado de esta guía:** está en `hito2/explicacion/` dentro de la rama local `proyectoHito2`; los enlaces de GitHub estarán actualizados cuando se haga el push.
