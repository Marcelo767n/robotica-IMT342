# Cómo revisar el proyecto (guía corta para el docente)

Cuatro pasos, de lo más rápido a lo más profundo. Todas las rutas son relativas a esta carpeta.

## 1. Leer el informe

- Informe de los Hitos 3/4: [entregables/hito3_4/informe_hito3_4.pdf](entregables/hito3_4/informe_hito3_4.pdf) (fuente: [hito3/informe/informe_hito3.tex](hito3/informe/informe_hito3.tex)).
- Hitos anteriores: [informe IEEE del Hito 2](entregables/hito2/informe_hito2_ieee.pdf) y [entregables del Hito 1](entregables/hito1/pdf/Guia_Practica_Hito1_IRB120_6_Juntas_CORREGIDA.pdf).
- Resumen del estado y de las limitaciones: [README.md](README.md) (final) y [docs/CONTEXTO_Y_OBJETIVOS.md](docs/CONTEXTO_Y_OBJETIVOS.md).

## 2. Mirar la evidencia

| Qué | Dónde |
|---|---|
| Resultados numéricos de la validación FK/IK/J (tablas, figuras, `resultados.json`) | [hito3/resultados/](hito3/resultados/) y manifiestos por experimento en [hito3/manifiestos/](hito3/manifiestos/) |
| Documentos de evidencia, seguridad y niveles S0–S3 | [hito3/docs/README.md](hito3/docs/README.md) |
| Las 265 órdenes reales del 16 al 19/11 y su clasificación | [evidencia_gate3_movimiento.md](hito3/docs/evidencia_gate3_movimiento.md) · [gate3_ordenes.csv](hito3/docs/gate3_ordenes.csv) |
| Sesiones con el robot, día por día | [docs/bitacora/](docs/bitacora/README.md) |
| Pruebas con el controlador (RWS, FK en vivo) | [docs/conexion_abb/evidencias/](docs/conexion_abb/evidencias/) y [VALIDACION_FK_EN_VIVO.md](docs/conexion_abb/VALIDACION_FK_EN_VIVO.md) |
| Arquitectura | [docs/MAPA_ROS2.md](docs/MAPA_ROS2.md) · [COMO_FUNCIONA.md](docs/conexion_abb/COMO_FUNCIONA.md) |

## 3. Reproducir sin robot

Requisitos: Ubuntu con ROS 2 Jazzy, `~/ros_py312`, `numpy`, `requests`, `customtkinter` y TeX (ver [README.md](README.md#cómo-ejecutar)).

```bash
cd ros2_ws
./brazo.sh compilar                  # una sola vez: panel «IRB 120» de RViz
brazo sesion --simulado              # RViz + panel (Mover / Trayectorias) + Estudio con un robot ficticio
brazo pruebas                        # ≈300 pruebas offline (control, panel, trayectorias, Estudio, celda)
cd .. && python3 -m hito3.validacion # regenera la validación FK/IK/J del Hito 3 en hito3/resultados
```

Qué probar en la sesión simulada: en el panel, pestaña «Trayectorias», elegir un movimiento vistoso (p. ej. `13_ocho`), «Vista previa» (anima el modelo naranja) y «Ejecutar» (mueve el robot ficticio); en «Mover», escribir ángulos o una pose y ver el gemelo. `brazo nodos --simulado` muestra el grafo ROS 2 en vivo. Sin robot no se reproduce el movimiento físico: eso solo consta en los registros y la bitácora.

## 4. Mapa de la rúbrica ECI-3/4 → evidencia

Autoevaluación completa, con brechas honestas por dominio (no es una nota): [hito3/docs/rubrica_autoevaluacion.md](hito3/docs/rubrica_autoevaluacion.md). Criterios del docente: [material_docente/semana_14/](material_docente/semana_14/) y [rúbrica de la semana 12](material_docente/actualizacion_semana_12/).

| Dominio (peso) | Evidencia principal | Nivel sostenible hoy |
|---|---|---|
| 1 · Ingeniería del sistema y compatibilidad (20 %) | [model_manifest.yaml](model_manifest.yaml), [gate0_ficha.md](hito3/docs/gate0_ficha.md), [gate0_inventario.csv](docs/conexion_abb/gate0_inventario.csv), [matriz_ab_gate1.md](hito3/docs/matriz_ab_gate1.md), [COMO_FUNCIONA.md](docs/conexion_abb/COMO_FUNCIONA.md) | Cercano a sólido en versión, interfaz y lectura |
| 2 · Modelos propios y validación FK/IK/J (25 %) | [hito2/irb120/](hito2/README.md), [hito3/resultados/](hito3/resultados/), [hito3/datos/](hito3/datos/), [VALIDACION_FK_EN_VIVO.md](docs/conexion_abb/VALIDACION_FK_EN_VIVO.md) | Mínimo cumplido con evidencia propia; tolerancias sin aprobar |
| 3 · Integración ROS–ABB, estados y control (25 %) | [irb120_conexion](ros2_ws/src/irb120_conexion/README.md), [irb120_control](ros2_ws/src/irb120_control/README.md), [evidencia_gate3_movimiento.md](hito3/docs/evidencia_gate3_movimiento.md), [niveles_evidencia.md](hito3/docs/niveles_evidencia.md) | S2 sólido; S3 técnico por registros, S3 autorizado no acreditado |
| 4 · Seguridad, reproducibilidad y fallos (20 %) | [checklist_seguridad.md](hito3/docs/checklist_seguridad.md), [checklist_P6_P7.md](hito3/docs/checklist_P6_P7.md), [bitácora](docs/bitacora/README.md), [RESPALDO_Y_RESTAURACION.md](docs/conexion_abb/RESPALDO_Y_RESTAURACION.md) | Mínimo parcial: sin GO firmado |
| 5 · Defensa individual y documentación (10 %) | [COMO_FUNCIONA.md](docs/conexion_abb/COMO_FUNCIONA.md), [MOVER_DESDE_PC.md](docs/conexion_abb/MOVER_DESDE_PC.md), [CONTEXTO_Y_OBJETIVOS.md](docs/CONTEXTO_Y_OBJETIVOS.md) | Depende de cada integrante; responsables por tarea sin asignar |

Las brechas que el equipo reconoce (GO sin firmar, tolerancias sin aprobar, v5/`MoveL` sin probar en el IRC5, PLC solo simulado, TCP físico sin medir) están detalladas en la autoevaluación y en la sección «Estado y limitaciones» de [README.md](README.md#estado-y-limitaciones).
