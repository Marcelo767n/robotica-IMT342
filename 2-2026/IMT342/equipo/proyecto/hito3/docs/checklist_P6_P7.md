# P6 · Checklist antes de declarar un resultado, y P7 · Firma de revisión

Plantillas oficiales P6 y P7 de `w14_s02_criterios_unificados_validacion_hito3.tex`. Marcado al 24/11/2026 con lo que el repositorio permite afirmar. El paquete de validación FK/IK/J lo prepara otra persona del equipo: ver `hito3/validacion` (código) y `hito3/resultados` (resultados). **Esta lista no afirma ningún resultado de ese paquete**; donde dependen de él se anota «ver hito3/resultados».

Leyenda: **Cumple** = existe la evidencia indicada. **No cumple** = falta o está incompleto. **Ver resultados** = depende del paquete en curso.

| # | Punto del checklist oficial | Estado | Evidencia / ruta | Qué falta |
|---|---|---|---|---|
| 1 | Tengo `q`, `joint_order`, unidades, signos, offsets y fuente. | Parcial | `q` y unidades (grados del controlador) en `docs/conexion_abb/evidencias/fk_real_2026-11-04_224412Z_muestras.jsonl`; `joint_order` y unidades en `model_manifest.yaml`. Signos y offsets frente al controlador: coinciden en la prueba de FK, pero `controller_joint_mapping_verified: false`. | Declarar signos y offsets de cada junta en cada manifiesto; verificar el mapeo con posturas que muevan J4–J6. |
| 2 | Tengo modelo/URDF/commit, parámetros geométricos, tool y TCP. | Parcial | URDF `hito2/datos/irb120.urdf`, DH `hito2/irb120/dh.py`, commit `19639122be7aeb98a6e96b8aea44530f94885c31` (`model_manifest.yaml`); SHA-256 del modelo de FK en `fk_real_2026-11-04_224412Z_informe.md`. | TCP 0,150 m es convención, no medida (`tcp_verified_on_robot: false`); `tooldata` real sin leer. |
| 3 | Ambas poses usan base, TCP y tiempo comparables. | Parcial | Comparación en `tool0`, `wobj0`, `Base` (flange, no punta) con robot quieto: `evidencias/fk_real_2026-11-04_224412Z_informe.md`, `VALIDACION_FK_EN_VIVO.md`. Adquisición secuencial, sin garantía de simultaneidad; `ignore=1` declarado. | Comparación en el TCP real; sincronía verificada o robot detenido en cada muestra (el tramo final lo estaba, las 25 muestras FUERA no se explicaron). |
| 4 | Mi referencia está identificada y sé si es independiente. | Cumple | Referencia física = `robtarget` del IRC5 (independiente del modelo); referencia geométrica = `rosi_model` (independiente de la tabla DH, no de la geometría nominal); URDF clasificado no independiente en los manifiestos (`hito3/manifiestos/`). | Mantener la clasificación en cada caso nuevo. |
| 5 | Calculo y adjunto `e_p` y `e_R` (m, rad), no solo captura. | Cumple | FK en vivo (`fk_real_2026-11-04_224412Z_errores.csv`) y casos del paquete (`hito3/resultados/validation_cases.csv`, `P1_fk.csv`): e_p y e_R en m y rad. | Ninguna. |
| 6 | En IK muestro ramas, límites y residuo FK por rama. | Cumple (S0) | `hito3/resultados/ik_ramas.csv`, `latex/P2b_ik_ramas.tex`: 40 ramas con límites, residuo FK propio e independiente y clasificación. | IK con movimiento físico bloqueada (IK-REAL). |
| 7 | En Jacobiano indico twist, columna, punto, FD y paso `h`. | Cumple (S0) | `hito3/resultados/P3_jacobiano.csv`, `jacobiano_fd_curva.csv`: twist [v;w] en la base, punto tool0/TCP, FD central, curva h→E(h), h*=1e-5 rad. | Jacobiano frente al controlador bloqueado (J-REAL). |
| 8 | En singularidad especifico tarea, rango/σ_i y escalado `L`. | Cumple (S0) | `hito3/resultados/P4_singularidad.csv`, `singularidad_sigma.csv`: tarea 6D en el TCP, rango, σ_i, τ_num, L=0,58 m. | Ninguna. |
| 9 | Distingo `J^T F` de la dinámica y no afirmo torque infinito. | Cumple (S0) | Caso F-TAU y P4: ||J^T F|| finito, distinto de ||tau_act||; sin torque infinito. | Ninguna. |
| 10 | Tengo presupuesto/criterio de tolerancia y estado de aprobación. | Parcial | Presupuesto offline (`tolerancias_presupuesto.csv`) e incertidumbres IRC5 (`tolerancias_incertidumbres_irc5.csv`) declarados; estado: pendiente de aprobación; criterio estricto 1e-6 m / 1e-6 rad propuesto, no aprobado. | Aprobación o umbrales del docente. |
| 11 | Mi script/notebook ejecuta offline con entradas conservadas. | Parcial | `python3 -m hito3.validacion` y `python3 -m pytest hito3/tests` (10 aprobadas el 24/11/2026); entradas en `hito3/datos/` con SHA-256. | Ejecución desde cero en máquina limpia; ./brazo.sh pruebas no ejecutado. |
| 12 | Cito logs/archivos, fecha, responsable y evidencia. | Parcial | Fechas, archivos y SHA-256 citados (`evidencia_gate3_movimiento.md`, informes de `evidencias/`). **Responsable por prueba: no consta en ningún registro.** | Completar `responsable_prueba` y `operador_autorizado` en cada manifiesto (`manifiesto_experimento_plantilla.yaml`). |
| 13 | No afirmo movimiento ROS→IRC5 ni estado `GO` sin evidencias de autorización. | Cumple en estos documentos, con aviso | `niveles_evidencia.md` y `evidencia_gate3_movimiento.md` separan «S3 técnico» de «S3 autorizado» y no declaran GO. Hay movimiento PC→IRC5 registrado por RWS+RAPID (265 órdenes) pero **sin GO firmado**. Nota: la cadena demostrada es PC (panel/RViz) → RWS → RAPID, no `ros2_control`/EGM. | Firma de `checklist_seguridad.md`; mantener la distinción en la defensa. |

Recuento (13 puntos): **cumple 7** (4, 5, 6, 7, 8, 9 y 13), **parcial 6** (1, 2, 3, 10, 11, 12), **no cumple 0**. Actualizado el 24/11/2026 con los resultados de `hito3/resultados`.

## P7 · Firma de revisión (sin firmar)

No firmar hasta que el autor y el docente hayan revisado. Una plantilla por prueba.

| Campo | Valor |
|---|---|
| Equipo | por completar por el equipo |
| ID prueba | por completar |
| Responsable | por completar |
| Versión del documento | por completar |
| Fecha | por completar |
| Revisión docente | ☐ pendiente ☐ revisado ☐ aprobado (alcance explícito): ______________ |
| Hallazgo mayor | por completar |
| Acción siguiente | por completar |
| Enlace a la evidencia | por completar |

Estado de las firmas al 24/11/2026: **ninguna firma registrada**; docente: pendiente.
