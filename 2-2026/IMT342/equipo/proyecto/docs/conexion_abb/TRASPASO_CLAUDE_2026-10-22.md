# Traspaso de trabajo: conexión Linux ↔ ABB IRB 120

**Fecha de corte:** 22 de octubre de 2026. **Proyecto:** IMT-342, integración de Hitos 3/4 (ECI-3/4). **Objetivo inmediato:** dejar lista y reproducible la conexión de lectura entre esta computadora Linux y el controlador ABB; después adaptar y validar un driver ROS 2 para el IRB 120. Este documento sirve para que Claude continúe el trabajo de fondo en este mismo proyecto. Leer también [`README.md`](README.md), [`plan_semana_12.md`](plan_semana_12.md), el [`model_manifest.yaml`](../../model_manifest.yaml) y el material del docente en [`archivos que hay que presentar/actualizacion_semana_12/`](../../archivos%20que%20hay%20que%20presentar/actualizacion_semana_12/).

## Estado real, al comenzar

| Tema | Conocido / evidencia | Pendiente |
|---|---|---|
| Robot | ABB **IRB120-3/0.6**, serie **120-101516**, placa fotografiada en `fotos/equipo/`. | Contrastar configuración geométrica y límites efectivos del controlador. |
| Sistema ABB | `Name` y `Serial no` **120-101516**; `RobotWare version` **6.12.01.00**, transcritos por el usuario desde **ABB → System Info → System properties** el 22/10. Registro: [`evidencias/robotware_reportado_2026-10-22.json`](evidencias/robotware_reportado_2026-10-22.json). | Confirmación por lectura RWS o foto del campo; revisión/modelo exacto del gabinete y computador principal. La apariencia de IRC5 Compact sigue siendo una hipótesis visual. |
| Opciones | Foto de FlexPendant muestra **689-1 EGM**, **616-1 PC Interface**, **623-1 Multitasking** y **UDP UC Driver**; lista completa en el manifiesto. | Configuración RAPID/EGM, permisos UAS y funcionamiento efectivo. Opción instalada ≠ sesión operativa. |
| Red ABB | Pantalla de servicio: **192.168.125.1**, máscara **255.255.255.0**, gateway **None**. Puerto etiquetado **X2 Service 10/100** fotografiado. WAN aparece en DHCP, sin IP visible en esa foto. | Comprobar que la configuración sigue vigente y que el acceso externo a X2 es el indicado por el operador. Ninguna PC ha demostrado conectividad con el robot. |
| PC | Inventario histórico: **Ubuntu 26.04.1 LTS**, ROS 2 **Jazzy** en `/opt/ros/jazzy`, Wi-Fi `wlo1`; no se observó interfaz Ethernet física en aquel inventario. | Repetir inventario al tener cable/adaptador. Jazzy tiene Ubuntu 24.04 como plataforma binaria objetivo; compilación del driver en esta instalación aún no probada. |
| Modelo | Hito 2 tiene FK/IK/J y URDF; paquetes ROS existentes en `ros2_ws/src/`. Referencia geométrica ROS-Industrial disponible en `hito2/irb120/rosi_model.py`. | Alinear nombres, orden, signos, offsets, límites, base y TCP con controlador. Hito 2 usa TCP de **0.150 m** desde `tool0`; ROS anterior usaba **0.100 m**. TCP físico desconocido. |
| Conexión y movimiento | Herramienta de lectura RWS preparada; ocho pruebas offline registradas. | **No hay enlace PC–ABB, lectura real de articulaciones, compilación validada del driver ni movimiento autorizado.** La foto de Backup and Restore muestra el menú, no prueba un respaldo. |

Las fotos originales y su interpretación están catalogadas en [`fotos/README.md`](../../fotos/README.md). El estado `Manual / Guard Stop / Stopped` corresponde a las capturas, no al estado actual. El indicador `Speed 100%` no mide velocidad articular. No reinterpretar los valores de la etiqueta de calibración como ángulos actuales.

## Red: explicación práctica para la primera visita al laboratorio

Se propone un **enlace Ethernet directo** entre Linux y el puerto de servicio externo del ABB. **No hace falta router, Wi-Fi del laboratorio ni internet** para esta primera lectura. Hace falta un cable Ethernet; si el portátil carece de puerto, un adaptador USB–Ethernet. El usuario indicó que todavía no tiene cable ni acceso supervisado. En el laboratorio, el operador debe confirmar el puerto apropiado antes de enchufar.

```text
PC Linux ── cable Ethernet ── X2 Service del controlador ABB
interfaz Ethernet de PC       servicio ABB: 192.168.125.1/24 (según foto)
```

El puerto de servicio IRC5 puede asignar dirección por DHCP: **probarlo primero**. Si no se obtiene una dirección válida y el operador confirma la red fotografiada, configurar **solo esa interfaz Ethernet** de forma temporal como `192.168.125.2/24`, sin puerta de enlace. `192.168.125.2` es una propuesta de PC para un enlace aislado, no una dirección ya aplicada. Mantener el Wi-Fi sin cambios. Verificar que la ruta hacia `192.168.125.1` sale por la interfaz Ethernet correcta antes de consultar RWS. No escanear ni adivinar direcciones en la red institucional. El puerto WAN/DHCP del controlador es otro circuito y su dirección actual no está establecida por las fotos.

La guía principal contiene la secuencia G1 y los fallos posibles: [`README.md`](README.md), sección «Cómo será la primera conexión». El material docente exige supervisión/protocolo para la conexión física. Las tareas autónomas son documentales, de software y de simulación.

## Arquitectura de integración propuesta

1. **G1, primero:** red directa y **RWS 1.0 por HTTP Digest, solo lectura**: identidad/sistema, modo, estado, unidad `ROB_1`, seis articulaciones. No necesita ROS ni EGM para esta prueba.
2. **Puente de estado ROS 2:** convertir grados → radianes, publicar las seis articulaciones en orden comprobado y contrastar con FlexPendant/URDF. Mantener los estados sin comandos de movimiento.
3. **Driver candidato:** [`PickNikRobotics/abb_ros2`](https://github.com/PickNikRobotics/abb_ros2), RWS + EGM + `ros2_control`; revisión auditada `e6486f7409073cdb2a10d6878bb50191dd50172b` de `rolling`. Sus ejemplos son para **IRB 1200-5/0.9**, un robot diferente. Adaptar al **IRB 120-3/0.6**; fijar las revisiones transitivas antes de afirmar reproducibilidad. La CI revisada cubre Rolling, no una instalación Jazzy/Ubuntu 26.04 probada aquí.
4. **Referencia comunitaria específica:** [`hylander2126/irb120_ros2`](https://github.com/hylander2126/irb120_ros2), revisión auditada `d8673de4cbbba168e2c9b97fa8681c6a1bdcf717`. Puede orientar URDF y configuración Jazzy, pero incluye componentes y lanzamientos para otra celda que reconfiguran/arrancan EGM; no copiarlos ni usar sus IP/puertos como datos del laboratorio.
5. **G3 posterior:** EGM requiere la opción 689-1 (fotografiada), RobotWare ≥6.07.01 (la versión reportada cumple), configuración RAPID/UDP y destino de PC correctos. El arranque de hardware de `abb_ros2` puede enviar consignas. Cualquier movimiento requiere el GO explícito del protocolo local después de G1/G2. El puerto UDP `6511` aparece en ejemplos de driver; **no está verificado en este robot**.

[`abb_librws`](https://github.com/ros-industrial/abb_librws) documenta RWS 1.0 en RW6 y [`abb_libegm`](https://github.com/ros-industrial/abb_libegm) documenta el mínimo de versión y la opción EGM. Cumplir requisitos documentales **no demuestra compatibilidad completa**. Las diapositivas del docente mencionan `abb_robot_driver` como ejemplo de auditoría; ese repositorio es ROS 1 y no identifica por sí mismo el driver ROS 2 al que se refirió verbalmente. [`roboticslab-uc3m/abb_egm_driver`](https://github.com/roboticslab-uc3m/abb_egm_driver) declara RW7/OmniCore y no es sustitución demostrada para este RW6. Como contingencia queda RAPID + sockets y puente ROS 2, sujeto a investigación de instrucciones y aceptación docente. RobotStudio en Windows puede servir para ingeniería/controlador virtual; **no es requisito para el primer GET RWS** ni se instala en el ABB.

## Trabajo de fondo solicitado a Claude, en orden

**P0 — Preparar G1 sin hardware.** Revisar [`scripts/abb_lectura_rws.py`](../../scripts/abb_lectura_rws.py) y [`docs/conexion_abb/requirements.txt`](requirements.txt). El script sin `--host` hace inventario local; con `--host` usa una lista fija de seis GET RWS y solicita la contraseña UAS sin guardarla. Diseñar una guía corta y ejecutable para el día de laboratorio: identificación de interfaz Ethernet, DHCP primero, alternativa estática temporal, comprobación de enlace/ruta, lectura RWS, comparación simultánea con FlexPendant, guardado de resultados y clasificación de fallos. Que todo comando vaya acompañado de qué salida esperar y qué hacer si falla. **No ejecutar `--host` hasta tener enlace y acceso supervisado.** No incorporar credenciales en archivos.

**P1 — Entorno y dependencias.** Inspeccionar el `ros2_ws/` y el Jazzy local. Elegir un entorno reproducible que permita compilar sin romper el sistema existente: evaluar primero un entorno Ubuntu 24.04/Jazzy separado o demostrar técnicamente la viabilidad local. Fijar commits de `abb_ros2` y dependencias; registrar comandos, versiones, resultados y limitaciones. Diferenciar «compila», «simula» y «funciona en controlador físico». No alterar paquetes del Hito 2 o la instalación ROS existente por conveniencia.

**P2 — Adaptación IRB120 offline.** Comparar modelo/URDF del proyecto y referencia ROS-Industrial con interfaces y configuración del driver candidato. Preparar configuración para seis juntas del IRB120, límites, `ros2_control`, frames, base/TCP y mapeo de unidades, declarando explícitamente lo que requiere contraste en el ABB. Resolver la discrepancia de TCP local antes de una validación de pose real; no inventar el TCP físico. Desactivar cualquier lanzamiento que arranque EGM o incluya periféricos de otra celda. Generar una ruta de visualización/simulación que no requiera controlador físico.

**P3 — Criterios de aceptación.** G1-A: ruta correcta por Ethernet a IP confirmada. G1-B: respuesta RWS identificada como el ABB físico `120-101516`, unidad `ROB_1`, seis valores finitos y concordancia con FlexPendant bajo tolerancia definida antes del ensayo. G2: comparación de FK/IK/J con referencia independiente, base/TCP/unidades fijados, casos normales y cercanos a singularidad, límites y errores cuantificados. G3: únicamente después de GO; configuración EGM, límites, parada y evidencias de ensayo acordados con operador/docente. Registrar hipótesis → comando/prueba → resultado → interpretación → siguiente acción. Los CSV y casos offline están en [`validation_cases.csv`](validation_cases.csv) y [`evidencias/`](evidencias/).

**Entregable de esta fase:** archivos de configuración/código/documentación reproducibles dentro del proyecto, más un registro honesto de lo compilado o simulado y una lista breve de datos que se deben obtener del brazo. Priorizar la futura lectura G1; una demo de movimiento no compensa una conexión sin verificar. Evitar declarar «driver garantizado» antes de comprobar PC, controlador, RAPID/EGM y geometría juntos.

## Punto de partida y referencias locales

- Diagnóstico preparado: [`scripts/abb_lectura_rws.py`](../../scripts/abb_lectura_rws.py). Invocación **solo local**, desde la raíz: `python3 scripts/abb_lectura_rws.py --output docs/conexion_abb/evidencias/inventario_pc.json`.
- Invocación **futura y supervisada**, después de confirmar IP, ruta y usuario: `python3 scripts/abb_lectura_rws.py --host IP_VERIFICADA --user USUARIO_UAS --output docs/conexion_abb/evidencias/g1_rws.json`. Los marcadores no son valores para pegar literalmente.
- Inventario y decisiones: [`gate0_inventario.csv`](gate0_inventario.csv), [`model_manifest.yaml`](../../model_manifest.yaml), [`README.md`](README.md), [`plan_semana_12.md`](plan_semana_12.md).
- Fuentes y copias de documentación revisada: [`fuentes/`](fuentes/) y sus `origenes*.json`. Consultar fuentes originales al tomar nuevas decisiones; parte de los manuales ABB no se pudo descargar localmente.
- Documentación docente: [diapositivas semana 12](https://github.com/berquiroga/planificacion-UCB/blob/main/2-2026/IMT342/Semana_12/sesion_01/w12_s01_slides.pdf) y copias locales en [`actualizacion_semana_12/`](../../archivos%20que%20hay%20que%20presentar/actualizacion_semana_12/). Gates G0 inventario, G1 lectura, G2 FK/IK/J, G3 movimiento con GO, G4 tarea repetible; Hitos 3/4 integrados. La fecha exacta nueva del Hito 2 no quedó establecida en los documentos consultados.

**Nota sobre registros anteriores:** `plan_semana_12.md` conserva una bitácora original del 20/10 que decía «RobotWare pendiente» y agrega la actualización del 22/10 al final. El valor vigente para la preparación es **6.12.01.00 reportado por el usuario**, aún sin contraste RWS. No repetir esa pregunta al usuario.
