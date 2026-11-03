# Contexto revisado del proyecto · 30 de octubre de 2026

Lectura del repositorio, grafo, historial de ramas, código principal, material docente y evidencias. Corte: `proyectoHito3y4`, commit `65856eae1a92b3eacbf6c404ad3bec9ef2ea0746`. La revisión no establece una conexión nueva con el ABB ni ejecuta movimiento. Los resultados físicos corresponden a los registros del 29/10; las comprobaciones de hoy fueron locales.

## Punto actual

El proyecto ya superó la fase de preparar una primera conexión: hay evidencia de enlace Ethernet, lectura RWS de los seis ejes reales y contraste con FlexPendant. Hay una primera validación física de FK en `tool0`. El puente ROS 2 y el gemelo RViz están preparados y su ejecución integrada con el robot real sigue pendiente.

La continuación inmediata es consolidar G1/G2 y comprobar la visualización con estados del ABB. EGM, el driver físico y la tarea de G4 todavía no están demostrados.

## Qué se hereda de los hitos anteriores

| Área | Fuente vigente | Aporte a Hitos 3/4 |
|---|---|---|
| Hito 1 | `ros2_ws/src/irb120_hito1/` y `docs/hito1/` | URDF/Xacro modular, CAD, pinza, FK DH, TF/RViz, panel Qt y verificación de coherencia del modelo |
| Hito 2 | `hito2/irb120/` y `hito2/Hito2_IRB120_pipeline.ipynb` | IK Pieper de hasta ocho ramas, validación FK, selección de rama, LSPB, Jacobiano/singularidades y dinámica reducida 1R |
| Referencia geométrica | `hito2/irb120/rosi_model.py` | Modelo ROS-Industrial distinto de la construcción DH propia; referencia numérica, no medición del brazo |
| Integración actual | `scripts/` y `docs/conexion_abb/` | Diagnóstico de red, lectura RWS, comparación con ABB y publicación de estados para RViz |
| Requisitos | `docs/hitos_3_4/REQUISITOS_ECI34.md` y fuentes TEX W12-S01 | Gates G0–G4, comparabilidad FK/IK/J, bitácora y evaluación ECI-3/4 |

El paquete `ros2_ws/src/irb120_hito2/` conserva una formulación ROS anterior. No equivale al paquete Python vigente en `hito2/`: incorpora nodo de trayectoria y comprobación de colisiones, pero no todas las correcciones y criterios del notebook actual. Su cinemática importa funciones del Hito 1; por ello no debe asumirse, a partir del README histórico, que todavía usa TCP de 0.100 m: la fuente del Hito 1 ya está alineada a 0.150 m.

El pipeline matemático vigente es `T_d → Pieper → candidatos → FK/límites → selección → LSPB → J(q) → dinámica 1R → τ(t)`. La selección considera admisibilidad, singularidad y margen articular; el código puede relajar estos dos últimos filtros y lo indica en el resultado. Este comportamiento académico no constituye por sí mismo un criterio aprobado para enviar movimiento físico. `HOME_Q = 0` es singular de muñeca.

## Git y GitHub

El repositorio Git abarca `/home/marcelo767/Documentos/robotica/robotica-IMT342`; esta carpeta de trabajo está dentro de él, en `2-2026/IMT342/equipo/proyecto`.

- `origin`: `Marcelo767n/robotica-IMT342`.
- `upstream`: `berquiroga/planificacion-UCB`, fuente docente.
- Al iniciar la revisión el árbol de trabajo estaba limpio y la rama activa era `proyectoHito3y4`.
- La comparación mediante el conector GitHub confirmó que `65856ea` y la rama remota `proyectoHito3y4` eran idénticos: cero commits de diferencia.
- GitHub mostró `main`, `proyectoHito1`, `proyectoHito2`, `proyectoHito3y4` y `tarea_4`. Las búsquedas no devolvieron PR ni issues abiertos.

| Referencia local | Commit | Commits que HEAD añade | Relación con HEAD |
|---|---|---:|---|
| `main`, `develop` | `75c6bdf` | 33 | Antecedentes |
| `tarea_3` | `77102d7` | 32 | Antecedente |
| `tarea_4`, `tarea_5` | `3ea8c93` | 31 | Antecedentes |
| `proyectoHito1` | `9f80541` | 25 | Antecedente |
| `claude/hito1-corrections-527b18` | `99a53ee` | 22 | Correcciones ya incorporadas |
| `proyectoHito2` | `d7eb8a9` | 4 | Base de la etapa actual |
| `proyectoHito3y4` | `65856ea` | 0 | Trabajo vigente |

Todas estas ramas locales son antecesoras de HEAD; ninguna tiene commits exclusivos que falten en la rama actual. Se inspeccionaron mediante referencias, sin cambiar de rama.

Los cuatro commits posteriores al Hito 2 son `93bc41d` (inicio ECI-3/4 y traspaso), `67af94e` (panel Qt y TCP unificado), `0800b85` (presentación) y `65856ea` (conexión del 29/10). El último añade 20 archivos modificados/nuevos y concentra el avance de ayer.

## Graphify y orden de lectura

`graphify-out/graph.json` contiene 1171 nodos, 2118 aristas y `built_at_commit: 8b215f1f76231059c40c0beaa930929851804766`. El informe está fechado el 22/10. Sirvió para localizar los módulos matemáticos, referencias ABB y comunidades de RWS/driver, pero no incluye `abb_rws_joint_bridge.py` ni el resumen del 29/10. Tampoco recoge la posterior unificación del TCP del Hito 1.

Para retomar, prevalecen las evidencias y el código de HEAD sobre los estados históricos del grafo. Lectura recomendada:

1. [Balance de la sesión del 29/10](../conexion_abb/RESUMEN_LOGROS_2026-10-29.md).
2. [Guía del puente y RViz](../conexion_abb/GUIA_PUENTE_ROS2.md).
3. [Requisitos ECI-3/4](REQUISITOS_ECI34.md).
4. [Traspaso del 22/10](../conexion_abb/TRASPASO_CLAUDE_2026-10-22.md), como antecedente de decisiones y tareas pendientes.

## Hardware y conexión acreditados

ABB IRB 120-3/0.6, serie/sistema `120-101516`, unidad `ROB_1`. RWS confirmó RobotWare `6.12.01.00`, las opciones EGM 689-1, PC Interface 616-1, Multitasking 623-1 y UDPUC Driver, además de una opción que identifica el sistema de accionamiento IRC5 Compact. La revisión exacta del gabinete y el computador principal siguen pendientes.

El 29/10 la conexión X2 Service → adaptador Realtek RTL8152 entregó a la PC `192.168.125.203/24` por DHCP del controlador. El ABB respondió en `192.168.125.1`; ping 3/3, RTT medio 0.826 ms. Son valores de aquella sesión, no una comprobación de la red actual ni una IP fija garantizada para la PC.

La lectura archivada contiene seis recursos RWS con HTTP 200. Los ejes RWS y FlexPendant difieren como máximo `0.0036003°`. El estado registrado era `AUTO`, `motoroff`, RAPID `stopped`: no debe confundirse con las fotos anteriores en modo Manual. La bitácora informa ausencia de operador durante aquella sesión; la evidencia técnica no acredita por sí sola cumplimiento del protocolo de supervisión docente.

Fuentes: [enlace G1-A](../conexion_abb/evidencias/g1a_enlace_2026-10-29.json), [respuesta RWS](../conexion_abb/evidencias/g1_rws_2026-10-29_sanitizado.json) y [contraste de ejes](../conexion_abb/evidencias/g1b_contraste_flexpendant_2026-10-29.json).

## Arquitectura implementada y propuesta

```text
ABB / ROB_1
   │ HTTP Digest + GET jointtarget, grados
   ▼
abb_rws_joint_bridge.py
   │ joint_1…joint_6, radianes, sensor_msgs/JointState
   ▼
/irb120/real/joint_states
   │ remapeo de entrada
   ▼
robot_state_publisher + URDF Hito 1 → TF → RViz
```

`abb_lectura_rws.py` permite únicamente recursos GET predefinidos y no sigue redirecciones. El puente reutiliza ese lector, consulta un recurso por ciclo, valida seis ejes finitos y no tiene suscriptores, servicios ni acciones de comando. Publica a 5 Hz por defecto, con máximo de 10 Hz; `gemelo_rviz.sh` solicita 10 Hz. Es visualización por sondeo RWS, no un canal de control EGM.

El gemelo prepara URDF/YAML con rutas absolutas a las mallas y arranca los ejecutables directamente, evitando `colcon` y `ros2 launch`. Usa el tema real separado de la simulación del Hito 1. Las pruebas registradas del 29/10 midieron 15 mensajes a 5.01 Hz y 76 comparaciones TF/FK con error mostrado de 0.0000 mm, contra un controlador simulado. Hoy se verificaron las pruebas de lógica/HTTP, no se repitió esa demostración visual de ROS/RViz.

La arquitectura de comando futura sigue siendo candidata: modelos/planificación → driver adaptado `abb_ros2`/`ros2_control` → EGM/UDP → IRC5, con retorno de estado. No hay una integración física de ese driver acreditada. La revisión auditada de PickNik es `e6486f7409073cdb2a10d6878bb50191dd50172b`; sus ejemplos IRB 1200 no son el IRB 120 del laboratorio. RAPID/sockets figura como alternativa investigada, no como implementación disponible.

## Estado de los gates

| Gate | Estado al corte | Falta principal |
|---|---|---|
| G0 | Inventario parcialmente confirmado, ampliado por RWS | Revisión del controlador, entorno reproducible, operador/protocolo, driver y dependencias fijadas |
| G1 | Enlace y lectura real contrastados; puente preparado y probado en simulación | Ejecutar puente/RViz con ABB y documentar condiciones del ensayo |
| G2 | FK física parcial en una postura, `tool0`/`wobj0` | Más posturas; base/TCP físico; matriz FK/IK/J y referencia/criterios completos |
| G3 | Sin ejecución física desde el software del proyecto acreditada | Respaldo verificable, configuración/adaptación EGM y GO expreso docente/operador |
| G4 | Sin tarea repetible demostrada | Integración posterior a G3; tablero y transformación de celdas; visión opcional según W12 |

La evaluación ECI-3/4 pondera ingeniería 20%, modelos/validación 25%, integración 25%, seguridad/reproducibilidad 20% y defensa/documentación 10%. G1 de lectura no equivale a G3 de movimiento.

La FK física registrada compara `tool0`, no el TCP modelado a 0.150 m. La posición es aproximadamente `(208.05, 381.23, 557.26)` mm, con error redondeado de `0.01 mm` y `0.0004°`. Recalculé ambos errores con el JSON RWS y los valores del FlexPendant archivados, obteniendo esas mismas salidas. Una postura no certifica todo el espacio de trabajo ni valida IK, Jacobiano, dinámica o seguimiento LSPB físicos.

La lectura B mencionada en el resumen existe en `/home/marcelo767/lecturas_abb/postura_B.json`, capturada el 29/10 a las 21:59:08 UTC. Se confirmó su existencia y seis ejes. Sigue faltando su referencia cartesiana independiente para cerrar la comparación; no se incorporó el archivo bruto al repositorio.

## Entorno y comprobaciones del 30/10

La PC usa Python 3.14.4. Existe `/home/marcelo767/ros_py312`, Python 3.12.3, y `/opt/ros/jazzy`. Tras cargar `setup.bash`, el entorno aislado importa `rclpy`, `sensor_msgs.msg`, `xacro`, `ament_index_python` y `ros2cli`. Importar `launch` falla por ausencia de `lark`; `colcon_core` tampoco está disponible en ese intérprete. La existencia de algunos módulos no demuestra una cadena completa de compilación/lanzamiento funcional.

| Comprobación ejecutada | Resultado |
|---|---|
| `hito2/.venv/bin/python -m pytest -q -p no:cacheprovider hito2/tests` | **64 pasan** |
| `python3 -m unittest discover -s scripts/tests -t scripts/tests` | **42 pasan**, con servidor simulado en loopback; requirió salir de la restricción de sockets del sandbox |
| Tests de ambos paquetes ROS con sus fuentes en `PYTHONPATH`, sin cargar setup ROS | **55 pasan, 5 omitidos, 2 fallan** al ejecutar `xacro` con Python/metadata del entorno actual |
| Repetición de esos dos tests tras cargar `/opt/ros/jazzy/setup.bash` | **2 omitidos** por falta del paquete `irb120_hito1` en el índice ament; expansión no revalidada |
| Comparador FK con JSON RWS y referencia FlexPendant archivados | Reproduce **0.01 mm / 0.0004°** |
| `bash -n scripts/gemelo_rviz.sh` | Sin errores de sintaxis |
| Notebook vigente, inspección de salidas guardadas | 57 celdas, 29 de código; ninguna salida de error almacenada; no se reejecutó el notebook |

Estos resultados no acreditan hoy compilación con `colcon`, panel Qt, RViz real ni conexión física nueva.

## Discrepancias documentales a tener presentes

- `README.md`, `docs/hitos_3_4/README.md` y `entregables/README.md` todavía presentan la conexión física como pendiente.
- `model_manifest.yaml` conserva `physical_connection_verified: false`, versión solo reportada, enlace Linux no verificado y otros campos anteriores a las lecturas reales. Debe actualizarse por alcance de evidencia, sin convertir una postura en validación global.
- `gate0_inventario.csv`, `plan_semana_12.md`, el catálogo de fotos y algunos encabezados de la guía ABB describen cortes anteriores. La guía ABB añade avances cronológicos al final que ya superan su encabezado.
- `validation_cases.csv` conserva los tres casos offline y resultados de referencia vacíos; la comparación física está en un JSON separado.
- Los recuentos de pruebas en distintos README varían (18/36/42 y 56); los recuentos ejecutados hoy son los de la tabla anterior.
- El catálogo fotográfico conserva las 14 imágenes originales. Los contrastes nuevos se documentan en JSON como transcripciones de fotos del usuario; esas nuevas fotos no aparecen en el catálogo versionado, por lo que su inspección visual independiente queda pendiente.
- El TCP de 0.150 m está alineado entre modelos, pero sigue siendo una convención, sin verificación de herramienta física.
- El grafo está desactualizado; conviene regenerarlo después de consolidar la documentación. No se regeneró durante esta revisión.

## Punto de reanudación

1. Consolidar el estado documental con los resultados del 29/10, conservando los registros históricos y su alcance.
2. En la próxima sesión de laboratorio, verificar la ruta vigente y ejecutar el puente/gemelo con estados reales; registrar recepción, frecuencia, correspondencia de ejes y comportamiento al perder el enlace.
3. Completar la referencia de la postura B y ampliar las comparaciones con configuraciones distintas; alinear base, herramienta y TCP antes de ampliar G2.
4. Resolver un entorno reproducible para construir y lanzar ROS, y adaptar offline el driver al IRB 120 con revisiones fijadas.
5. Preparar y ejecutar G3 únicamente bajo el protocolo y GO explícito del laboratorio; después integrar G4.

Este informe es el único archivo añadido por la revisión. No se modificaron código, manifiesto, evidencias ni ramas; no se crearon commits ni se publicó nada.
