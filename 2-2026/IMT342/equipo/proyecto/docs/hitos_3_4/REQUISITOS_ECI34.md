# Requisitos ECI-3/4 (Hitos 3 y 4) · resumen de W12-S01

Fuente: `berquiroga/planificacion-UCB`, `2-2026/IMT342/Semana_12/sesion_01`. Los .tex/.pdf originales están en [actualizacion_semana_12](<../../archivos que hay que presentar/actualizacion_semana_12/>) (verificados idénticos a los del repositorio del docente).

## Evaluación

- `EC = 0.25·E1 + 0.25·E2 + 0.50·ECI-3/4` y `NF = 0.50·EC + 0.50·EF`.
- El EC cierra en W16. La EF es posterior: nuevo escenario, robustez y defensa individual.
- La visión con webcam es opcional y no es prerrequisito.

| Dominio ECI-3/4 | Peso | Mínimo verificable |
|---|---|---|
| Ingeniería del sistema, auditoría y compatibilidad | 20 % | Manifiesto Gate 0 completo, fuentes identificadas, diagrama de arquitectura bidireccional |
| Modelos propios y validación FK/IK/J | 25 % | Modelos propios y protocolo de comparación con marcos/TCP alineados |
| Integración ROS–ABB, estados y avance hacia control | 25 % | Ruta técnica con evidencia trazable del nivel real alcanzado |
| Seguridad, reproducibilidad, ensayos y fallos | 20 % | Checklist GO/NO-GO, plan de pruebas, logs y bitácora estructurada |
| Defensa individual y documentación | 10 % | Explica su tarea y las limitaciones del sistema |

El puntaje máximo en movimiento físico exige ejecución observada y autorizada.

## Gates

| Gate | Contenido | Semana |
|---|---|---|
| 0 | Inventario y compatibilidad (ficha de 15 ítems, dos hipótesis de arquitectura) | W12 |
| 1 | Estado y red sin movimiento (`joint_states` originados en ABB) | W13 |
| 2 | Validación FK/IK/J contra referencia (e_p, e_R, e_J, e_v; singularidad) | W13–W14 |
| 3 | Movimiento físico, solo con GO expreso del operador y laboratorio | W14 |
| 4 | Tarea repetible en tablero: `p_target = T_C · p_cell` | W15 |

Contingencia al cierre de W13: ruta A (física viable), B (interfaz sin movimiento) o C (bloqueo externo documentado). Estado inicial de seguridad: **NO-GO**.

## Entregables para W12-S02

1. Inventario local (Gate 0) con estados y fuentes.
2. Dos arquitecturas candidatas con requisitos y limitaciones.
3. Repositorio inicial y `model_manifest.yaml`.
4. Diagrama de comando y retorno de estado.
5. Plan Gate 1 sin movimiento, con condiciones de autorización.
6. Casos FK/IK/J con métricas declaradas (`validation_cases.csv`).
7. Bloqueos, responsables y evidencias en bitácora (formato: hipótesis → prueba → resultado → interpretación → acción; estados `functional` / `partially_verified` / `blocked` / `not verified`).

Además: matriz RACI (responsable y respaldo por tarea) y tres tareas verificables antes de W12-S02.

## Condiciones antes de comparar con la referencia

Mismo `{B}`, mismo `{TCP}`, `joint_order`, unidades (rad, m), sentidos y offsets, URDF/eslabón terminal, herramienta cargada, convención de J (lineal arriba) y tolerancias. Si falla una, no se calcula el error.

## Herencia de los hitos anteriores

- Hito 1 y Hito 2 (modelo DH del IRB120, FK/IK/J propios) alimentan el dominio 2 de esta rúbrica; ver [hito 2](../hito2/) y [hito 1](../hito1/).
