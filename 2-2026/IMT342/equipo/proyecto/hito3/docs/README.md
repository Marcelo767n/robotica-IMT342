# hito3/docs · documentación de evidencia del Hito 3

Preparada el 24/11/2026 a partir de los requisitos oficiales (W12–W14) y de la evidencia del repositorio. Regla de oro: no se inventan datos, firmas, autorizaciones ni nombres; lo que no consta queda «por completar por el equipo» o «pendiente», y se distingue lo observado de lo inferido.

| Documento | Para qué sirve | Requisito oficial |
|---|---|---|
| [gate0_ficha.md](gate0_ficha.md) | 15 ítems de inventario con estado, fuente y próxima verificación; hipótesis A (RWS + RAPID) y B (EGM); decisión | `w12_s01_gate0_ficha`, `w12_s02_ficha_gate_0` |
| [matriz_ab_gate1.md](matriz_ab_gate1.md) | 12 filas A/B y el ensayo Gate 1 de 8 puntos con PASS/FAIL/BLOCKED | `w12_s02_matriz_ab__gate_1` |
| [evidencia_gate3_movimiento.md](evidencia_gate3_movimiento.md) y [gate3_ordenes.csv](gate3_ordenes.csv) | 265 órdenes de las sesiones del 16 al 19/11 y clasificación S3 eslabón por eslabón | `w14_s02_criterios_unificados` (S3) |
| [checklist_seguridad.md](checklist_seguridad.md) | Puertas de seguridad, lo que consta por sesión, firmas vacías y versión para la próxima sesión | `w12_s01_checklist_seguridad` |
| [niveles_evidencia.md](niveles_evidencia.md) | Nivel S0–S3 y estado P5 de cada experimento | `w14_s02_criterios_unificados` (Bloque B) |
| [manifiesto_experimento_plantilla.yaml](manifiesto_experimento_plantilla.yaml) | Plantilla con los campos del manifiesto por experimento | `w14_s02_criterios_unificados` (Bloque B) |
| [checklist_P6_P7.md](checklist_P6_P7.md) | Checklist de 13 puntos marcado y firma P7 sin firmar | `w14_s02_criterios_unificados` (P6, P7) |
| [rubrica_autoevaluacion.md](rubrica_autoevaluacion.md) | Evidencia mínima y sólida por dominio de la rúbrica, y brechas | `w12_s01_rubrica_hito_3` |

Bitácora relacionada (en `docs/bitacora/`): [18/11](../../docs/bitacora/2026-11-18_sesion_auto_v4.md), [19/11](../../docs/bitacora/2026-11-19_sesion.md), [20/11](../../docs/bitacora/2026-11-20_trayectorias_plc.md) y [backlog](../../docs/bitacora/backlog.md).

El paquete de validación FK/IK/J está en `hito3/validacion` y sus resultados en `hito3/resultados`; estos documentos no afirman ningún resultado de ese paquete.

## Qué falta, en una línea cada uno

1. GO/NO-GO firmado por el responsable del laboratorio para cada sesión (hoy ninguno consta).
2. Aceptación escrita del laboratorio para trabajar en AUTO sin habilitador.
3. Observación independiente del movimiento (video fechado) y registro de `opmode` por orden.
4. Los `jsonl` del movimiento no están versionados (`.gitignore`).
5. Placa del controlador, procedimiento local y operador nombrados.
6. Tolerancias de FK/IK/J aprobadas por el docente; TCP físico sin medir.
7. RAPID v5, EGM y celda PLC solo en simulación.
8. Responsables por tarea sin asignar.
