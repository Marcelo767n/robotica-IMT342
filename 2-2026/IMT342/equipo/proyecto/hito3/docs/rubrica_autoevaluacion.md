# Autoevaluación frente a la rúbrica ECI-3/4 (Hito 3)

Rúbrica: `w12_s01_rubrica_hito_3.tex` (propuesta; los pesos requieren formalización administrativa). `EC = 0,25·E1 + 0,25·E2 + 0,50·ECI-3/4`, `NF = 0,50·EC + 0,50·EF`. El puntaje máximo en movimiento físico exige ejecución realmente observada y autorizada.

Esta es una **autoevaluación del equipo, no una nota**. No asigna puntaje. Preparada el 24/11/2026; rutas relativas a `proyecto/`.

## Dominio 1 · Ingeniería del sistema, auditoría y compatibilidad (20 %)

| | |
|---|---|
| Evidencia mínima (oficial) | Manifiesto Gate 0 completo, fuentes documentales identificadas y diagrama de arquitectura bidireccional. |
| Evidencia sólida (oficial) | Versión e interfaz justificadas técnicamente; incertidumbre inicial resuelta mediante pruebas documentadas. |
| Dónde está | Manifiesto: `model_manifest.yaml`. Inventario: `docs/conexion_abb/gate0_inventario.csv`, `hito3/docs/gate0_ficha.md`. Fuentes: `docs/conexion_abb/fuentes/`, `docs/conexion_abb/README.md`. Arquitectura: `docs/conexion_abb/COMO_FUNCIONA.md` (diagramas), `docs/CONTEXTO_Y_OBJETIVOS.md` §4, `hito3/docs/matriz_ab_gate1.md`. Pruebas que resolvieron incertidumbre: RobotWare y opciones leídos por RWS (29/10). |
| Nivel que se puede sostener hoy | Cercano a sólido en versión, interfaz y lectura. |
| Brechas honestas | Controlador: placa y computador principal sin leer. Operador/autorizador sin nombre. Manual y procedimiento local del laboratorio ausentes. EGM no verificado ni descartado; `abb_ros2` sin compilar. Antecedente de ajedrez sin localizar. Diagrama bidireccional de la matriz oficial: existe el de `COMO_FUNCIONA.md`, falta un diagrama que separe comando, red, estado y movimiento como pide la plantilla A/B. |

## Dominio 2 · Modelos propios y validación FK / IK / J (25 %)

| | |
|---|---|
| Evidencia mínima | Modelos propios implementados y protocolo de comparación con marcos/TCP alineados. |
| Evidencia sólida | Errores (`e_p`, `e_R`, `e_J`, `e_v`), marcos y ramas verificados en múltiples casos; diagnóstico riguroso de discrepancias. |
| Dónde está | Modelos: `hito2/irb120/` (DH, Pieper, Jacobiano, LSPB, dinámica) y sus pruebas `hito2/tests/`. Comparación con el controlador: `docs/conexion_abb/evidencias/fk_real_2026-11-04_224412Z_*`, `g2_fk_vs_controlador_pose1_2026-10-29.json`, `VALIDACION_FK_EN_VIVO.md`. Casos: `docs/conexion_abb/validation_cases.csv`. Paquete en curso de Hito 3: `hito3/validacion`, `hito3/resultados`. |
| Nivel que se puede sostener hoy | Mínimo cumplido con evidencia propia (FK en `tool0`, dos fechas). Lo demás: ver `hito3/resultados`. |
| Brechas honestas | La comparación física cubre sobre todo J1–J3; J4–J6 casi no variaron. 100 muestras finales son lecturas repetidas de una sola postura. 25 muestras FUERA sin explicar. TCP físico sin medir (`tcp_verified_on_robot: false`). Tolerancias propuestas, no aprobadas. IK, Jacobiano y singularidades contra el controlador: ver hito3/resultados; no se afirma aquí. |

## Dominio 3 · Integración ROS–ABB, estados y avance hacia control (25 %)

| | |
|---|---|
| Evidencia mínima | Ruta técnica implementada con evidencia trazable del nivel real logrado en laboratorio. |
| Evidencia sólida | Comunicación y lectura de estados verificadas; envío de comando y resultado observados según el Gate alcanzado. |
| Dónde está | Lectura: `g1_rws_2026-10-29_sanitizado.json`, `verificacion_rws_ros_tf_2026-11-03.*`. Comando y resultado: `hito3/docs/evidencia_gate3_movimiento.md` y `gate3_ordenes.csv` (265 órdenes, 264 con llegada). Código: `ros2_ws/src/irb120_conexion/`, `ros2_ws/src/irb120_control/`, `ros2_ws/src/irb120_rviz_panel/`. Niveles: `hito3/docs/niveles_evidencia.md`. |
| Nivel que se puede sostener hoy | Sólido hasta S2; S3 técnico por registros (16–19/11), **S3 autorizado no acreditado**. |
| Brechas honestas | No hay GO firmado ni observación independiente del movimiento. La ruta es RWS + RAPID (una orden a la vez, no tiempo real); EGM/`ros2_control` no probado. La v5 (`MoveL`, trayectorias A→B→C→A), el Estudio y la celda PLC son solo S0. La orden 59 del 18/11 no tiene resultado. El 403 del 16/11 (tras reanudar RAPID) solo se observó una vez. Los `jsonl` no están versionados. Gate 4 (tarea repetible sobre el tablero) sin implementación demostrada. |

## Dominio 4 · Seguridad, reproducibilidad, ensayos y fallos (20 %)

| | |
|---|---|
| Evidencia mínima | Checklist GO/NO-GO aplicado, plan de pruebas, logs y bitácora estructurada. |
| Evidencia sólida | Pruebas repetibles con control de versiones, análisis técnico de fallos y decisiones operativas seguras. |
| Dónde está | `hito3/docs/checklist_seguridad.md` (aplicado como plantilla, sin firmas); logs: `salidas/control_articular/rws_mover/`; bitácora: `docs/bitacora/`; control de versiones: git (rama `proyectoHito3y4`); análisis de fallos: `CIERRE_PRUEBA_J6_2026-11-10.md`, `COMO_FUNCIONA.md` §9, bitácora del 16/11. Respaldo y restauración: `docs/conexion_abb/RESPALDO_Y_RESTAURACION.md`. |
| Nivel que se puede sostener hoy | Mínimo parcial: hay logs, bitácora y análisis de fallos reales; el checklist está sin firmar. |
| Brechas honestas | **Ninguna sesión tiene GO/NO-GO firmado.** Trabajo en AUTO sin habilitador sin aceptación escrita del laboratorio. Velocidad hasta 75 % en AUTO sin criterio de «reducida». Sin verificación de E-stop registrada. Registro sin `opmode` por orden. Las bitácoras de 18 y 19/11 se escribieron después, a partir de los logs (ver `docs/bitacora/`). |

## Dominio 5 · Defensa individual y documentación (10 %)

| | |
|---|---|
| Evidencia mínima | Explica con claridad su tarea asignada y las limitaciones del sistema. |
| Evidencia sólida | Comprende toda la cadena de ingeniería transversalmente; responde preguntas de diagnóstico y transferencia. |
| Dónde está | Documentación: `docs/conexion_abb/COMO_FUNCIONA.md` (explicación técnica completa), `MOVER_DESDE_PC.md`, `docs/CONTEXTO_Y_OBJETIVOS.md`, `docs/bitacora/`, `hito3/docs/README.md`. |
| Nivel que se puede sostener hoy | La documentación existe; la defensa depende de cada persona y no puede evidenciarse en archivos. |
| Brechas honestas | **Responsables por tarea sin asignar** (la matriz RACI de la guía W12 no está completada: ver `docs/bitacora/backlog.md`). Cada integrante debe poder explicar la cadena completa: RWS, RAPID, modelo, verificación, seguridad. Preparar respuestas a preguntas de transferencia: ¿por qué `tool0` y no el TCP?, ¿qué demuestra y qué no el código 2?, ¿por qué la ruta no es tiempo real? |

## Resumen de brechas ordenadas por impacto

1. Autorización GO firmada y observación independiente del movimiento (dominios 3 y 4).
2. Tolerancias aprobadas por el docente y cobertura de J4–J6 (dominio 2).
3. Placa del controlador, procedimiento local y operador nombrado (dominio 1).
4. Pruebas de la v5, de EGM (si se exige) y de la celda PLC en hardware (dominio 3).
5. Asignación de responsables y preparación de la defensa individual (dominio 5).
