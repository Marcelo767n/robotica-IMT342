# Documentación del proyecto

Índice de toda la documentación, ordenada por hito. Los enlaces son relativos a esta carpeta.

## Por dónde empezar

| Si quieres... | Lee |
|---|---|
| Entender cómo la PC mueve el robot real | [COMO_FUNCIONA.md](conexion_abb/COMO_FUNCIONA.md) |
| Mover el brazo en el laboratorio, paso a paso | [MOVER_DESDE_PC.md](conexion_abb/MOVER_DESDE_PC.md) |
| Recuperar el programa si alguien lo borra del FlexPendant | [RESPALDO_Y_RESTAURACION.md](conexion_abb/RESPALDO_Y_RESTAURACION.md) |
| Saber qué pasó el día que el robot se movió por primera vez | [Bitácora del 16/11/2026](bitacora/2026-11-16_primer_movimiento_real.md) |
| Ver cómo está organizado el repositorio | [organizacion/README.md](organizacion/README.md) |

## Hito 1: modelo y simulación

| Documento | Contenido |
|---|---|
| [hito1/README.md](hito1/README.md) | Entrada del hito: simulación del IRB 120 en ROS 2 |
| [modelo_cinematico.md](hito1/modelo_cinematico.md) | Tabla DH y paso a URDF |
| [resultados.md](hito1/resultados.md) | Resultados y pruebas |
| [trazabilidad.md](hito1/trazabilidad.md) | Requisito, código y evidencia |
| [auditoria_2026-10-22.md](hito1/auditoria_2026-10-22.md) | Estado por requisito |
| [guion_defensa.md](hito1/guion_defensa.md) | Guion de la defensa |

## Hito 2: cinemática inversa, trayectorias, Jacobiano y dinámica

| Documento | Contenido |
|---|---|
| [hito2/README.md](hito2/README.md) | Qué hay en esta carpeta |
| [informe_ieee/](hito2/informe_ieee/README.md) | Informe en formato IEEE (PDF y fuente LaTeX) |
| [evaluacion_hito2_2026-10-20.md](hito2/evaluacion_hito2_2026-10-20.md) | Evaluación frente a la rúbrica (anterior a las correcciones) |
| [verificacion_correcciones_hito2_2026-10-20.md](hito2/verificacion_correcciones_hito2_2026-10-20.md) | Comprobación de la versión corregida |

El código y el notebook vigentes están en [`../hito2/`](../hito2/README.md).

## Hitos 3 y 4: conexión con el robot real, control, IK y visión

| Documento | Contenido |
|---|---|
| [hitos_3_4/README.md](hitos_3_4/README.md) | Estado y entrada de los hitos 3 y 4 |
| [REQUISITOS_ECI34.md](hitos_3_4/REQUISITOS_ECI34.md) | Requisitos de las entregas ECI-3 y ECI-4 |
| [PLAN_CONTROL_EGM_IK_VISION.md](hitos_3_4/PLAN_CONTROL_EGM_IK_VISION.md) | Plan: control, IK propia y visión |
| [CONTEXTO_REVISADO_2026-10-30.md](hitos_3_4/CONTEXTO_REVISADO_2026-10-30.md) | Contexto verificado al 30/10 |

## Conexión con el ABB IRB 120 (`conexion_abb/`)

| Documento | Contenido |
|---|---|
| [README.md](conexion_abb/README.md) | Decisión de conexión y preparación |
| **[COMO_FUNCIONA.md](conexion_abb/COMO_FUNCIONA.md)** | Arquitectura PC a IRC5 (RWS, RAPID, RViz), protocolos y fallos corregidos |
| **[MOVER_DESDE_PC.md](conexion_abb/MOVER_DESDE_PC.md)** | Guía de laboratorio para mover el brazo desde la PC |
| **[RESPALDO_Y_RESTAURACION.md](conexion_abb/RESPALDO_Y_RESTAURACION.md)** | Copias del programa del robot y cómo volver a cargarlo |
| [COMANDOS_LABORATORIO.md](conexion_abb/COMANDOS_LABORATORIO.md) | Comandos de cada conexión y prueba |
| [VALIDACION_FK_EN_VIVO.md](conexion_abb/VALIDACION_FK_EN_VIVO.md) | Comparación de la FK propia con la pose del ABB |
| [GUIA_PUENTE_ROS2.md](conexion_abb/GUIA_PUENTE_ROS2.md), [GUIA_G1_DIA_LABORATORIO.md](conexion_abb/GUIA_G1_DIA_LABORATORIO.md) | Guías de puente ROS 2 y de la jornada G1 |
| [PRUEBA_J6_RWS_RAPID.md](conexion_abb/PRUEBA_J6_RWS_RAPID.md), [CIERRE_PRUEBA_J6_2026-11-10.md](conexion_abb/CIERRE_PRUEBA_J6_2026-11-10.md), [PROXIMA_SESION_J6.md](conexion_abb/PROXIMA_SESION_J6.md) | Prueba de J6 del 10/11 y su cierre |
| [PREPARAR_EGM_FISICO.md](conexion_abb/PREPARAR_EGM_FISICO.md) | Preparación del control EGM (pendiente) |
| [RESUMEN_LOGROS_2026-10-29.md](conexion_abb/RESUMEN_LOGROS_2026-10-29.md), [plan_semana_12.md](conexion_abb/plan_semana_12.md) | Resumen y plan anteriores |
| `evidencias/`, `fuentes/` | Registros de pruebas y copias de documentación de terceros (no editar) |

## Bitácora

| Documento | Contenido |
|---|---|
| [bitacora/README.md](bitacora/README.md) | Índice de sesiones |
| [AVANCE_2026-11-10.md](bitacora/AVANCE_2026-11-10.md) | Avance y resultado de la sesión del 10/11 |
| [2026-11-16_primer_movimiento_real.md](bitacora/2026-11-16_primer_movimiento_real.md) | Primer movimiento real desde la PC |

## Organización

[organizacion/README.md](organizacion/README.md): qué se movió, qué se conserva y qué no debe moverse.
