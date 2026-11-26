# Documentación del proyecto

Índice por propósito. Los enlaces son relativos a esta carpeta. Portada del proyecto: [../README.md](../README.md); guía para el docente: [../COMO_REVISAR.md](../COMO_REVISAR.md). Los documentos marcados **histórico** se conservan como registro y quedaron superados por los vigentes.

## 1. Operar el robot

| Documento | Contenido |
|---|---|
| [MOVER_DESDE_PC.md](conexion_abb/MOVER_DESDE_PC.md) | Guía de laboratorio: FlexPendant, modos Manual/AUTO, `brazo sesion` y seguridad |
| [RESPALDO_Y_RESTAURACION.md](conexion_abb/RESPALDO_Y_RESTAURACION.md) | Copias del programa del robot y cómo volver a cargarlo |
| [COMANDOS_LABORATORIO.md](conexion_abb/COMANDOS_LABORATORIO.md) | Comandos de cada conexión y prueba |
| [bitacora/backlog.md](bitacora/backlog.md) | Tareas para la próxima sesión de laboratorio |
| [../ros2_ws/README.md](../ros2_ws/README.md) | Comandos `brazo` y estructura del espacio de trabajo ROS 2 |

## 2. Entender la arquitectura

| Documento | Contenido |
|---|---|
| [CONTEXTO_Y_OBJETIVOS.md](CONTEXTO_Y_OBJETIVOS.md) | Estado final (26/11/2026), decisiones, lecciones y objetivos |
| [conexion_abb/COMO_FUNCIONA.md](conexion_abb/COMO_FUNCIONA.md) | Arquitectura PC a IRC5 (RWS, RAPID, RViz), protocolos y fallos corregidos |
| [MAPA_ROS2.md](MAPA_ROS2.md) · [grafo_ros2.svg](grafo_ros2.svg) | Mapa de nodos y tópicos ROS 2 (`brazo nodos` lo muestra en vivo) |
| [ARQUITECTURA_TRAYECTORIAS.md](ARQUITECTURA_TRAYECTORIAS.md) | Planificador, reglas de seguridad (tolerancias), Estudio CustomTkinter y entrada de visión |
| [PLC_S7_1200.md](PLC_S7_1200.md) | **Extensión simulada**: contrato de telegramas y nodos de la celda con PLC S7-1200 (no integrada con el PLC real). Fuentes SCL: [../plc_s7_1200/README.md](../plc_s7_1200/README.md) |
| [conexion_abb/README.md](conexion_abb/README.md) | Decisión de conexión y preparación |
| [conexion_abb/GUIA_PUENTE_ROS2.md](conexion_abb/GUIA_PUENTE_ROS2.md) | Guía del puente ROS 2 |
| [conexion_abb/PREPARAR_EGM_FISICO.md](conexion_abb/PREPARAR_EGM_FISICO.md) | Preparación del control EGM (no probado; la ruta vigente es RWS + RAPID) |

## 3. Evidencias y validación

| Documento | Contenido |
|---|---|
| [../hito3/docs/README.md](../hito3/docs/README.md) | Evidencia del Hito 3: Gate 0, matriz A/B, 265 órdenes, seguridad, niveles S0–S3, autoevaluación |
| [../hito3/docs/rubrica_autoevaluacion.md](../hito3/docs/rubrica_autoevaluacion.md) | Dominios de la rúbrica ECI-3/4, evidencia y brechas |
| `../hito3/validacion/`, `../hito3/resultados/` | Paquete de validación FK/IK/J reproducible (`python3 -m hito3.validacion`) y sus resultados |
| [bitacora/README.md](bitacora/README.md) | Índice de sesiones con el robot (10/11, 16/11, 18/11, 19/11, 20/11) |
| [conexion_abb/VALIDACION_FK_EN_VIVO.md](conexion_abb/VALIDACION_FK_EN_VIVO.md) | Comparación de la FK propia con la pose del ABB |
| `conexion_abb/evidencias/` | Registros de pruebas con el controlador (no editar) |
| [conexion_abb/PRUEBA_COMUNICACION_EN_VIVO.md](conexion_abb/PRUEBA_COMUNICACION_EN_VIVO.md), [GUIA_G1_DIA_LABORATORIO.md](conexion_abb/GUIA_G1_DIA_LABORATORIO.md) | Prueba de comunicación y guía de la jornada G1 |
| [conexion_abb/PRUEBA_J6_RWS_RAPID.md](conexion_abb/PRUEBA_J6_RWS_RAPID.md) | Prueba de J6 del 10/11 (sin movimiento; diagnóstico en el cierre histórico) |

## 4. Hitos

| Documento | Contenido |
|---|---|
| [hito1/README.md](hito1/README.md) | Hito 1: simulación del IRB 120 en ROS 2. También [modelo_cinematico.md](hito1/modelo_cinematico.md), [resultados.md](hito1/resultados.md), [trazabilidad.md](hito1/trazabilidad.md), [guion_defensa.md](hito1/guion_defensa.md) y la [auditoría del 22/10](hito1/auditoria_2026-10-22.md) |
| [hito2/README.md](hito2/README.md) | Hito 2: [informe IEEE](hito2/informe_ieee/README.md). Código y notebook vigentes en [../hito2/](../hito2/README.md) |
| [hitos_3_4/README.md](hitos_3_4/README.md) | Hitos 3/4 (ECI-3/4): planificación y requisitos. Ver [REQUISITOS_ECI34.md](hitos_3_4/REQUISITOS_ECI34.md) y [PLAN_CONTROL_EGM_IK_VISION.md](hitos_3_4/PLAN_CONTROL_EGM_IK_VISION.md) |
| [../entregables/README.md](../entregables/README.md) | Qué se entrega por hito |
| [../material_docente/README.md](../material_docente/README.md) | Guías, rúbricas y criterios del docente (incluye semana 14) |

## 5. Histórico (superado, se conserva sin borrar)

| Documento | Por qué es histórico |
|---|---|
| [conexion_abb/TRASPASO_CLAUDE_2026-10-22.md](conexion_abb/TRASPASO_CLAUDE_2026-10-22.md) | Traspaso del 22/10, previo al control del robot |
| [conexion_abb/RESUMEN_LOGROS_2026-10-29.md](conexion_abb/RESUMEN_LOGROS_2026-10-29.md) | Resumen del 29/10; lo vigente está en [CONTEXTO_Y_OBJETIVOS.md](CONTEXTO_Y_OBJETIVOS.md) |
| [conexion_abb/CIERRE_PRUEBA_J6_2026-11-10.md](conexion_abb/CIERRE_PRUEBA_J6_2026-11-10.md) y [PROXIMA_SESION_J6.md](conexion_abb/PROXIMA_SESION_J6.md) | Prueba de J6 del 10/11, sin movimiento; superada por el movimiento del 16/11 |
| [conexion_abb/plan_semana_12.md](conexion_abb/plan_semana_12.md) | Plan de la semana 12 |
| [bitacora/AVANCE_2026-11-10.md](bitacora/AVANCE_2026-11-10.md) | Avance del 10/11 |
| [hitos_3_4/CONTEXTO_REVISADO_2026-10-30.md](hitos_3_4/CONTEXTO_REVISADO_2026-10-30.md) | Contexto verificado al 30/10 |
| [hito2/evaluacion_hito2_2026-10-20.md](hito2/evaluacion_hito2_2026-10-20.md), [verificacion_correcciones_hito2_2026-10-20.md](hito2/verificacion_correcciones_hito2_2026-10-20.md) y `hito2/revision_2026-10-20/` | Revisiones del Hito 2 anteriores a las correcciones |
| [organizacion/README.md](organizacion/README.md) | Historial de la reorganización de carpetas del 20/10 |
| `conexion_abb/fuentes/`, [`../archivo/`](../archivo/) | Copias de documentación de terceros y versiones anteriores (solo consulta) |
