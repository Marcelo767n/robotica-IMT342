# Evaluación del Hito 2 frente a la rúbrica oficial

> **Revisión inicial, anterior a las correcciones.** La comprobación de la versión corregida está en [Verificación de correcciones](verificacion_correcciones_hito2_2026-10-20.md).

**Fecha:** 20 de octubre de 2026. **Alcance:** Hito 2 de la semana 10, ABB IRB 120. Se revisó la entrega en Python, el notebook integrado, sus generadores, módulos, pruebas, explicaciones y el informe IEEE; se contrastó también el material anterior de ROS y los anexos para identificar inconsistencias de entrega.

**Evaluación estimada del producto: 73/80 puntos, equivalente a 91.25/100 en la parte grupal.** El proyecto está bien desarrollado y cumple el núcleo técnico. Las mejoras pendientes son concretas; no hace falta rehacer el pipeline.

La rúbrica define pesos y niveles cualitativos, pero no asigna una escala numérica interna a cada nivel. Los puntos siguientes son una estimación razonada de esta revisión, no una calificación oficial del docente. Los **20 puntos de defensa individual quedan sin evaluar**, porque requieren escuchar a cada integrante. No deben contarse automáticamente como obtenidos ni como cero.

El usuario confirmó que **el docente todavía no asignó poses objetivo**. Por eso no se descuenta por no presentar una lista que aún no existe. Se distingue ese pendiente futuro de las correcciones comprobadas hoy.

Otra sesión estaba editando los archivos durante la revisión. Se trabajó sobre copias temporales y se contrastó la versión actualizada del notebook y del informe antes de emitir el diagnóstico. El primer error de compilación detectado quedó resuelto por cambios de esa sesión: **el PDF actual sí compila**. Esta revisión no modificó el código, el notebook ni el informe.

## 1. Documentos oficiales descargados

Se descargó todo el contenido del [directorio oficial de GitHub](https://github.com/berquiroga/planificacion-UCB/tree/main/2-2026/IMT342/Semana_10/hito_2) en [archivos que hay que presentar](<../../archivos que hay que presentar>).

| Documento | Formatos descargados | Uso en esta revisión |
|---|---|---|
| `hito_2_guia` | PDF y TEX | Alcance, robot, pipeline y entregables mínimos |
| `hito_2_rubrica` | PDF y TEX | Criterios A–F y defensa G1–G4 |
| `hito_2_ieee_template` | PDF y TEX | Estructura del informe |
| `hito_2_slides` | PDF y TEX | Indicaciones de presentación y validación manual del Jacobiano |

Los ocho archivos coinciden en tamaño y SHA de objeto Git con GitHub. Su procedencia está registrada en `origen_descargas.json`. La carpeta contiene **material oficial de referencia**; la guía, la rúbrica y las diapositivas del docente no sustituyen tus entregables propios.

## 2. Nota por criterio

| Criterio | Peso | Evaluación estimada | Razón principal |
|---|---:|---:|---|
| A. Cinemática inversa / Pieper | 15 | **14/15** | Analítico, ocho ramas, cuadrantes, clasificación y selección correctos; nombres de ramas de muñeca confusos respecto al signo real de q5. |
| B. Validación por FK | 10 | **9/10** | Validación sistemática y buenas pruebas; falta rechazar matrices que no representan poses rígidas válidas. |
| C. Trayectoria LSPB | 15 | **14/15** | Perfiles, límites, sincronización y fronteras correctos; debe aclararse o corregirse la aceleración fuera del intervalo del movimiento. |
| D. Jacobiano y singularidades | 20 | **18/20** | Experimento independiente, validaciones y pérdida de movilidad bien desarrollados; corregir la identidad del determinante y la comparación con límites de velocidad. |
| E. Dinámica y torque | 15 | **14/15** | Modelo 1R integrado, parámetros trazables, componentes e interpretación; precisar el torque de sostén y el alcance de la validación. |
| F. Integración, IEEE y reproducibilidad | 5 | **4/5** | Se reproduce el pipeline y el PDF; quedan problemas menores de tamaño de figuras, desborde de tabla y documentación desactualizada. |
| **Producto grupal** | **80** | **73/80** | **91.25 % de los puntos grupales.** |
| G. Defensa individual | 20 | **No evaluada** | Hay material para prepararla, pero la comprensión individual no se demuestra leyendo archivos. |

## 3. Comparación punto por punto

### A. IK / Pieper — 14/15

**Evidencia:** [pieper.py](../../hito2/irb120/pieper.py), notebook integrado, secciones 2 y 4, y [explicación de Pieper](../../hito2/explicacion/02_A_pieper.md).

| Exigencia | Resultado observado |
|---|---|
| Estructura analítica prevista | Cumple: separa posición del centro de muñeca y orientación de la muñeca esférica. |
| Manejo de ramas | Cumple: enumera siempre ocho candidatos y trata la degeneración de muñeca. |
| Uso apropiado de atan2 | Cumple en base, hombro y descomposición de orientación. No sustituye Pieper por un solver numérico. |
| Candidatos reales frente a admisibles | Cumple: distingue existencia geométrica, límites articulares y aceptación por FK. |
| Tabla de candidatos | Cumple: muestra las ocho ramas, ángulos, errores y juntas que incumplen límites. |
| Justificación de la rama elegida | Cumple: cercanía ponderada y preferencia por candidatos alejados de singularidad, con alternativa si todos son próximos a ella. |
| Explicación geométrica | Hay deducción y figura de ramas. La capacidad de explicarla oralmente queda para G. |
| Todas las poses asignadas | Pendiente de asignación del docente. Hoy hay una pose objetivo de ejemplo y la pose inicial; además, pruebas aleatorias y secuencia de singularidad. |

**Corrección de claridad:** en `_wrist_solutions`, el signo positivo se aplica a beta y luego se devuelve `q5 = -beta`. Por eso la rama denominada `q5-` produce **q5 = +83.03°** en el ejemplo. Las soluciones llegan correctamente a la pose; el problema está en los nombres y en explicaciones que los presentan como signos de q5. Renombrar a `beta+`/`beta-`, o hacer coincidir las etiquetas con el signo de q5, y actualizar tablas y figuras.

No se exige que las ocho ramas sean admisibles. Para el ejemplo se obtienen **ocho reales y una admisible**, y el descarte por límites está justificado.

### B. Validación por FK — 9/10

**Evidencia:** [validation.py](../../hito2/irb120/validation.py), `analyze_pose`, notebook sección 3 y pruebas de validación.

| Exigencia | Resultado observado |
|---|---|
| Verificar sistemáticamente candidatos | Cumple: se verifican incluso ramas reales que violan límites, usando sus ángulos crudos. |
| Comparar posición y orientación | Cumple: error euclidiano de posición y error angular geodésico. |
| Documentar criterio de aceptación | Cumple: 1e-6 m y 1e-6 rad. Conviene mantener las unidades separadas al describir ambas tolerancias. |
| Detectar inconsistencias | Cumple: rechaza perturbaciones de q1 y un error solo de orientación en q6. |
| Evidencia adicional | Prueba FK → IK → FK de 1000 casos, recuperando la configuración original en todos. |

**Fallo reproducido:** se aceptan entradas 4×4 finitas que no pertenecen a SE(3). Partiendo de `FK(HOME_Q)`, multiplicar por dos las dos primeras columnas de R genera **det(R) = 4**. `analyze_pose` sigue indicando alcanzable y acepta errores angulares cercanos a cero, aunque el error de Frobenius sea aproximadamente **1.414**. Cambiar el último elemento de T de 1 a 2 también se acepta.

**Corrección:** antes de usar la IK y el error angular, verificar forma 4×4, finitud, última fila `[0,0,0,1]`, `R.T @ R ≈ I` y `det(R) ≈ 1`. Es un defecto de validación de entradas; **no invalida los resultados actuales**, cuyas poses se construyen con rotaciones válidas.

### C. Trayectoria LSPB — 14/15

**Evidencia:** [lspb.py](../../hito2/irb120/lspb.py), notebook sección 5 y figuras `C_lspb_perfiles` y `C_uso_limites`.

| Exigencia | Resultado observado |
|---|---|
| Obtener q, qdot y qddot | Cumple: fórmulas por tramos y muestreo explícito. |
| Parámetros iniciales/finales y tiempos | Cumple: se muestran q0, qf, tf, tb y parámetros por junta. |
| Límites justificados | Cumple: velocidad al 25 % del dato ABB y aceleración obtenida de una rampa de 0.25 s declarada como supuesto. |
| Condiciones de frontera | Cumple: posiciones inicial/final y velocidades nulas. |
| Continuidad | Cumple: q y qdot son continuas en los empalmes; se explica que qddot tiene saltos. |
| Gráficas e interpretación | Cumple: tres perfiles alineados con fases identificadas. |

Para la pose de ejemplo, **tf = 1.28791949 s**, **tb = 0.25 s** y la junta crítica es la 5. Los límites del código coinciden con las velocidades y rangos de la [ficha oficial ABB](https://library.e.abb.com/public/7aa0711a20fa41c49a8fdf3bbc3d5bb0/IRB120-Rev.J-ROBO149EN_D.pdf).

**Corrección:** `sample(t)` satura t a `[0,tf]` y conserva la aceleración del frenado en `tf` y para cualquier tiempo posterior. Por ejemplo, un segundo después de acabar devuelve todavía `qddot_2 = -1.524623 rad/s²`, aun con posición y velocidad constantes.

Dentro del movimiento puede usarse una convención unilateral para los valores en los extremos; se debe indicar. Para tiempos fuera del movimiento, devolver q inicial/final constante, velocidad cero y aceleración cero. **La rúbrica pide reposo en posición y velocidad; no corresponde declarar incorrecto todo el LSPB por el salto de aceleración**, que es propio de este perfil.

### D. Jacobiano y singularidades — 18/20

**Evidencia:** [jacobian.py](../../hito2/irb120/jacobian.py), notebook secciones 6 y 7 y [explicación de singularidades](../../hito2/explicacion/06_D_singularidades.md).

| Exigencia | Resultado observado |
|---|---|
| Jacobiano coherente con el modelo | Cumple: usa ejes y orígenes DH con referencia TCP declarada. |
| Al menos una validación | Supera el mínimo: diferencias finitas, columnas manuales en q=0 y derivada de posición sobre la trayectoria. |
| Interpretación de columnas | Cumple: relaciona eje, brazo de palanca y velocidad producida. |
| Rango como criterio central | Cumple: SVD con tolerancia explícita 1e-6. El determinante es complementario. |
| Experimento independiente | Cumple: secuencia de doce valores de q5 hasta cero, pasando por FK, Pieper y análisis diferencial. |
| Pérdida de movilidad | Cumple: rango 6 → 5 y movimiento interno qdot4 = -qdot6. |
| Amplificación de velocidades | Cumple: pendiente log-log -1.000, coherente con 1/sin(q5). |
| Diferenciar singularidad y torque | Cumple en el notebook vigente: distingue degradación cinemática, estática y dinámica. |

**Correcciones:**

1. En la sección 7 del notebook/generador y en `06_D_singularidades.md:37` se afirma `det(J) = producto(sigma_i)`. La identidad correcta es **`abs(det(J)) = producto(sigma_i)`**. En general, `det(J) = det(U) det(V.T) producto(sigma_i)`. Se reprodujo un caso con `det(J) = -0.00846589758` y producto de valores singulares `+0.00846589758`. El código de factorización con signo sí funciona; hay que corregir la explicación.
2. El informe compara **la norma de un vector de seis velocidades** con **el máximo de una junta** de 5.6 rad/s. La conclusión de inviabilidad es cierta en el ejemplo, pero la comparación rigurosa es por componente: `max_i(abs(qdot_i)/vmax_i)`. Para q5=0.01°, los ejes 4 y 6 requieren aproximadamente ±27040 rad/s y ese máximo normalizado es aproximadamente **4841.6**.
3. El Jacobiano mezcla unidades lineales y angulares. Conviene declarar que la SVD y sus normas usan la escala SI adoptada, o introducir una longitud característica para normalizar. El rango exacto se conserva con cambios invertibles de escala, pero los valores singulares, el número de condición y el umbral de cercanía dependen de ella. También debe declararse la escala de la carga al usar numéricamente u6 como wrench en `J.T @ u6`.

El resultado de rango 5 en la postura cero es coherente: el LSPB articular puede comenzar ahí sin invertir el Jacobiano. Eso no equivale a garantizar cualquier movimiento cartesiano desde esa postura.

### E. Dinámica y torque — 14/15

**Evidencia:** [dynamics_1r.py](../../hito2/irb120/dynamics_1r.py), [dynamics.py](../../hito2/irb120/dynamics.py), notebook sección 8 y explicación correspondiente.

| Exigencia | Resultado observado |
|---|---|
| Modelo reducido 1R de clase | Cumple: tau = J theta_ddot + m g lc sin(theta), derivado desde energía y Euler–Lagrange. |
| Supuestos y parámetros | Cumple en lo principal: cuerpo equivalente del hombro, otras juntas congeladas en postura media, aproximación CAD y pinza. |
| Entradas desde el LSPB | Cumple: usa q2(t) y qddot2(t) del mismo movimiento. |
| Separación de contribuciones | Cumple: tau inercial, gravitacional y total. |
| Gráfica tau(t) | Cumple con fases e interpretación del pico. |
| Interpretación de esfuerzo | Cumple: gravedad durante el crucero, aceleración/frenado y escalado temporal. |
| Validación | Hay comparación con M22 y g2 del modelo completo y error RMS durante el movimiento. |

Se cotejaron masas, centros de masa e inercias con la **ecuación 18** del artículo local de Truc y Lam (2020). La masa de la pinza de **115 g** coincide con el [catálogo oficial SMC](https://www.smcworld.com/catalog/en/rotary_airchuck/MHZ_2-E/6-3-p0381-0463-mhz_en/data/6-3-p0381-0463-mhz_en.pdf). El informe actualizado declara el TCP como decisión de diseño y aproxima el centro de masa de la pinza a 0.040 m.

**Correcciones y precisiones:**

- **Torque al finalizar:** el valor -20.552 N·m corresponde al frenado bajo la convención actual. En reposo sostenido, con qddot2=0, es **-18.714 N·m**. Mostrar `tf-` y `tf+` o agregar un intervalo de sostén evita interpretar que el motor sigue frenando después de acabar. Este punto comparte causa con el hallazgo del muestreo LSPB.
- **Alcance de la validación:** el error RMS de **0.637 N·m, aproximadamente 4.5 %**, es respecto a otro modelo implementado con los mismos parámetros CAD. Es una buena comprobación de consistencia y de la reducción; no es una validación experimental frente al robot real. Mantener explícita esa distinción.
- **Explicación de 1 GDL:** sustituir «en 1 GDL no hay Coriolis ni centrífuga» por «en este modelo 1R la inercia J es constante y por eso no aparece un término cuadrático en la velocidad». Un sistema de una coordenada con inercia dependiente de q sí puede tener un término de la forma `0.5 M'(q) qdot²`. El código del modelo elegido está bien; es una generalización excesiva en la explicación.

### F. Integración, IEEE y reproducibilidad — 4/5

**Evidencia:** [notebook integrado](../../hito2/Hito2_IRB120_pipeline.ipynb), [generador](../../hito2/build_pipeline_notebook.py), [fuente IEEE](informe_ieee/informe_hito2_ieee.tex) y PDF actual.

| Exigencia | Resultado observado |
|---|---|
| Notebook de inicio a fin | Cumple: 26 celdas de código, sin errores y 31/31 verificaciones. |
| Datos coherentes entre módulos | Cumple en la entrega Python vigente: qf, LSPB, Jacobiano y torque conectados. |
| Unidades y convenciones | Cumple: radianes, metros, segundos, N·m, DH y marco base declarados. |
| Código legible y reproducible | Cumple en el entorno existente; no requiere ROS para el entregable central. |
| Informe IEEE | Cumple: clase IEEEtran, cinco páginas, ecuaciones, tablas, resultados, discusión y referencias. |
| Reconstrucción del informe | Cumple: se regeneró el notebook en copia temporal y luego se compiló LaTeX dos veces. |

**Correcciones de presentación y documentación:**

- La tabla II produce un **Overfull hbox de 9.95618 pt**, comprobado también al recompilar. Ajustar espaciado, abreviaturas o ancho; es una corrección de formato, no un fallo de resultados.
- Las figuras 3 y 5 tienen textos y leyendas pequeños a tamaño de página. Dar más ancho al análisis de singularidad, separar subfiguras o aumentar fuentes antes de exportar.
- `README.md` de la raíz sigue anunciando «3 notebooks y 24 pruebas» para la carpeta Python; la entrega principal tiene un notebook integrado y **49 pruebas**. Las **24** corresponden al paquete auxiliar ROS.
- `hito2/README.md` afirma que el código es el mismo que en ROS y que basta copiarlo. Hoy hay diferencias reales: el TCP vigente es **0.150 m**, mientras el modelo ROS utiliza **0.100 m**, y los módulos no son idénticos. Explicar claramente la versión válida de entrega.
- `docs/hito2/guia_hito2.md` y `metodo_y_resultados.md` describen el esquema anterior de nodo ROS y «pasaporte». **Al cierre ya están marcados como obsoletos y enlazan a la entrega vigente**, por lo que ese punto quedó resuelto. Conservar esa separación; las frases históricas sobre divergencia de torque deben leerse bajo la condición de imponer una demanda cartesiana.
- **El README del informe ya fue actualizado**: describe la importación de resultados y advierte que deben releerse las interpretaciones dependientes de la pose. No queda pendiente la corrección anterior de los números copiados a mano.
- La referencia de calibración utilizada en el informe se titula **«Calibrate an IRB140»**. No demuestra por sí sola la afirmación fuerte de «única postura de referencia» del IRB120. Usar el manual del IRB120 o presentar q0=0 como la postura inicial elegida para el experimento. Esto no cuestiona la FK numérica en q=0.

Mejora adicional de portabilidad: dejar registradas las versiones utilizadas de Python, NumPy y Matplotlib. No es una exigencia literal de fijar cada dependencia en la rúbrica, pero facilitará repetir la entrega en otra computadora.

### G. Defensa individual — 20 puntos aún sin evaluar

| Subcriterio | Peso | Material existente | Qué debe demostrar cada integrante |
|---|---:|---|---|
| G1. Pipeline | 5 | Diagrama y flujo integrado | Explicar qué sale de cada etapa y qué entra a la siguiente. |
| G2. Matemática | 5 | Deducciones y ejemplo resuelto a mano | Reconstruir una ecuación sin limitarse a leer el código. |
| G3. Validación / interpretación | 5 | Pruebas, errores, gráficas y discusión | Justificar tolerancias, comparar orientación y explicar el significado físico de rango y torque. |
| G4. Transferencia | 5 | Explicaciones de todos los módulos | Responder sobre una parte distinta de la que programó principalmente. |

Hay buena base documental para preparar la defensa, incluida la nueva `hito2/explicacion/09_guia_de_estudio_del_codigo.md`, con mapa de funciones, variables del notebook y autoevaluación. Sus ejercicios de estudio son recomendaciones internas del equipo; no constituyen requisitos adicionales publicados por el docente. **El material no permite asignar los 20 puntos todavía.** La rúbrica advierte que la falta de comprensión mínima puede causar una reducción individual adicional, aunque el producto grupal funcione.

Preguntas útiles para comprobar esa preparación:

1. ¿Por qué una pose puede tener ocho ramas reales y solo una admisible?
2. ¿Qué error se escaparía si se compara únicamente la posición del TCP?
3. ¿Por qué el LSPB tiene posición y velocidad continuas, pero aceleración con saltos?
4. ¿Qué significa físicamente qdot4 = -qdot6 en q5=0?
5. ¿Por qué la singularidad no implica torque infinito por sí sola?
6. ¿Por qué aparece torque durante el crucero si la aceleración es cero?
7. ¿Qué se congela al construir el 1R y qué no demuestra el error del 4.5 %?
8. ¿Qué cambiaría si el docente entrega otra pose objetivo?

## 4. Qué falta y en qué orden conviene corregirlo

| Prioridad | Acción | Criterios |
|---|---|---|
| Alta | Rechazar matrices que no sean transformaciones rígidas válidas antes de usar el error angular y la IK. | B, F |
| Alta | Corregir `det(J)=producto(sigma)` a `abs(det(J))=producto(sigma)` en notebook, generador y explicación. | D, G2 |
| Media | Aclarar etiquetas de muñeca: signo de beta frente a signo de q5. | A, G2 |
| Media | Corregir el comportamiento fuera de `[0,tf]` y distinguir torque de frenado y torque de sostén. | C, E |
| Media | Comparar velocidades por junta y declarar la escala usada para la SVD y las cargas. | D |
| Media | Unificar las instrucciones de entrega y marcar el material antiguo; ajustar tabla II y figuras pequeñas. | F |
| Media | Precisar la validación CAD, la explicación de 1 GDL y la fuente sobre calibración del IRB120. | E, F, G |
| Cuando el docente las asigne | Ejecutar todas sus poses, conservar la identificación de cada caso y generar sus tablas/resultados. | A, B, C, E, F |
| Antes de defender | Ensayo individual transversal con ecuaciones, validación e interpretación física. | G1–G4 |

Para demostrar variedad mientras llegan las poses oficiales, sería útil un pequeño lote de ejemplos propios —regular, cercano a singularidad, imposible por alcance e imposible por límites— claramente marcado como casos de prueba del equipo. **Es una mejora recomendada; no se presenta como una lista ya exigida por el docente.** El solver y las pruebas existentes ya contienen parte de estos casos.

## 5. Qué entregar según la guía actual

| Elemento | Situación |
|---|---|
| Notebook integrado `.ipynb` | Existe y ejecuta. |
| Paquete local `hito2/irb120/` y dependencias | Necesario para que el notebook funcione; no basta enviar el `.ipynb` aislado. |
| Informe PDF IEEE | Existe, tiene cinco páginas y compila. |
| Fuente LaTeX, figuras y resultados importados | Conservarlos juntos si se solicita el fuente o la reconstrucción del PDF. El TEX no es autónomo. |
| Defensa grupal con evaluación individual | Pendiente de realización, con material de preparación disponible. |

ROS, RViz y Gazebo **no son requeridos por la guía oficial de esta semana**. Tampoco se identifica una obligación de producir una presentación propia en PowerPoint: la defensa sí es obligatoria. Los archivos `hito_2_slides` descargados son diapositivas del docente.

## 6. Comprobaciones realizadas y límites de la evaluación

- **49/49 pruebas** del paquete Python del Hito 2 aprobadas.
- **24/24 pruebas** de los componentes Python del paquete ROS auxiliar aprobadas en copia temporal. No se ejecutó una simulación ROS/RViz; no es requisito del entregable principal.
- Notebook original ejecutado en un kernel nuevo, de principio a fin: **26 celdas de código, 31/31 verificaciones**, sin errores.
- Generador actualizado ejecutado completo en copia temporal. Se reconstruyeron notebook, figuras y tablas; se compiló el informe desde esos resultados.
- LaTeX compilado dos veces: **PDF de cinco páginas**, sin errores fatales ni referencias indefinidas; un desborde de tabla señalado arriba.
- Revisión visual de las cinco páginas renderizadas del PDF, con inspección ampliada de tabla II y figuras.
- Cotejo de parámetros con el artículo local de dinámica, el artículo local de DH, la ficha ABB y el catálogo SMC.
- Casos adicionales reproducidos: pose con R no ortogonal, última fila homogénea inválida, signo del determinante, nombres de ramas y aceleración/torque después de tf.

Las pruebas exitosas no cubren automáticamente toda entrada posible ni sustituyen la comprensión del equipo. Los resultados sobre el robot son de modelos computacionales; no se midieron torques en hardware.

[Evidencias, registros y huellas de archivos revisados](revision_2026-10-20). En `ejecucion_notebook.txt` se conserva la ejecución de la primera copia; la regeneración posterior y la compilación actualizadas están registradas por separado. Los hallazgos se contrastaron con los archivos vigentes al cierre.
