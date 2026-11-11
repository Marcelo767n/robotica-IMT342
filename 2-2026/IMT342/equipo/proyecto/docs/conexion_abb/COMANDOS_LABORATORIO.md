# Comandos de laboratorio · IRB120 · lectura, FK y ensayo articular

Actualizado: 10/11/2026. Abrir una terminal y entrar **una vez**:

```bash
cd "/home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/ros2_ws"
```

Los comandos siguientes se ejecutan desde esa carpeta. `iniciar.sh` carga ROS Jazzy y Python 3.12 automáticamente; no hace falta ejecutar archivos de nodos a mano ni compilar con colcon para estos arranques fuente. Usar una sola sesión de prueba a la vez y cerrar la anterior con Ctrl+C una vez.

**Próxima visita:** seguir la [secuencia preparada para resolver el bloqueo y comprobar J6](PROXIMA_SESION_J6.md). Primer comando después de comprobar el enlace: `./iniciar.sh rws_j6 diagnosticar` (solo lectura; muestra modo, controlador, RAPID, versión del módulo y objetivo pendiente). Antes de preparar un giro, completar localmente `MostrarObjetivo` con el objetivo vacío.

**Resultado 10/11: movimiento J6 no conseguido.** La recepción PC→ABB y la transferencia se comprobaron, pero hubo 584 muestras sin movimiento; el último modo confirmado fue AUTO y no se completó la ejecución local. Antes de preparar otro objetivo, comprobar/vaciar el anterior y demostrar la ejecución local de `MostrarObjetivo` con el objetivo vacío. [Diagnóstico de cierre](CIERRE_PRUEBA_J6_2026-11-10.md), [guía J6 mediante RWS + RAPID](PRUEBA_J6_RWS_RAPID.md). Esta ruta no usa `control_robot`/EGM ni ejecuta al arrastrar en RViz.

```bash
./iniciar.sh rws_j6 inspeccionar
# Solo si falta la versión revisada, con AUTO/motores apagados/RAPID detenido:
./iniciar.sh rws_j6 actualizar_modulo
# Después de Verificar programa en FlexPendant, preparar únicamente el objetivo:
./iniciar.sh rws_j6 preparar --delta 0.1
```

Preparar no arranca RAPID. Seguir la guía para el monitor y la confirmación local en `LabJointRws/ProbarObjetivo`, en manual reducido.

## Ahora, sin conectarte al brazo

```bash
./iniciar.sh control_demo
# Recorridos mayores con la misma velocidad y aceleración:
./iniciar.sh control_demo --recorrido-demo-deg 5
./iniciar.sh control_demo --recorrido-demo-deg 10
```

Abre RViz con un ABB simulado por EGM UDP en la propia PC. Permite ensayar selección de J1 a J6, previsualización, armado, ejecución y cancelación sin red externa. Herramienta **Interact** → clic derecho sobre el aro → seleccionar eje → esperar un segundo → ajustar **+0.1°** → **ARMAR** → **EJECUTAR** → esperar **MANTENIENDO**. Después seleccionar otro eje y repetir; **DESARMAR** cierra el envío al finalizar. [Guía de los controles](../../ros2_ws/src/irb120_control/README.md).

Al abrir deben verse el brazo completo, el aro de J1 en la base y el texto del estado. Los dos modelos coinciden inicialmente; al ajustar un objetivo se separa la vista previa naranja. Los displays **MEDIDO**, **VISTA PREVIA**, **CONTROL J1–J6** y **Estado de la prueba** deben indicar **OK** al desplegarlos.

Se corrigió el arranque que mostraba piezas amontonadas y ningún aro: faltaban los prefijos TF de los modelos y se usaban propiedades que Jazzy no carga para el control y el texto. Si quedó abierta una ventana de esa versión, cerrar la sesión desde su terminal con **Ctrl+C una vez** y volver a ejecutar `./iniciar.sh control_demo`; el archivo de RViz se vuelve a generar automáticamente. Los mensajes `Stereo is NOT SUPPORTED` no explican ese fallo.

Elegir **un solo comando de demo** y cerrar la sesión antes de usar otro. Los recorridos 5°/10° añaden incrementos grandes al menú de vista previa; mantienen **0.5°/s y 0.5°/s²**, con movimientos aproximados de 11 s/21 s. La opción de recorrido ampliado es exclusiva de la demo. El paso a hardware se detalla en [Preparar EGM físico](PREPARAR_EGM_FISICO.md).

## Al conectar Ethernet al ABB

Conectar el adaptador/cable al puerto autorizado y comprobar que el controlador está disponible según el procedimiento del laboratorio. No usar `192.168.1.1`: la dirección de servicio comprobada es **192.168.125.1**. El usuario de las pruebas previas fue **Default User**, con espacio y entre comillas.

```bash
./iniciar.sh enlace --ping
```

Esperar PASS en adaptador, cable, IP, ruta y ping. La IP de la PC puede cambiar por DHCP; no asumir `192.168.125.203` como dirección fija. Esta comprobación no usa contraseña ni inicia motores/RAPID/EGM.

## Prueba 1: ángulos reales y gemelo

```bash
./iniciar.sh comunicacion --host 192.168.125.1 --user "Default User" --ignore-joint-state
```

Solicita contraseña UAS sin mostrar caracteres; abre RViz y panel `http://127.0.0.1:8765/`. Verificar que llegan datos actuales y contrastar con FlexPendant. El movimiento lo realiza el operador con FlexPendant; la PC solo lee.

## Prueba 2: validar nuestra cinemática directa

Detener la prueba anterior y ejecutar:

```bash
./iniciar.sh validar_fk --host 192.168.125.1 --user "Default User" --ignore-joint-state
```

Abre RViz y paneles 8765/8766. Cada muestra lee seis ángulos, calcula nuestra FK y compara con `robtarget` ABB en Base/tool0/wobj0. La terminal muestra entrada, resultado propio, referencia ABB y error. Dejar quieto el brazo unos 20 s en cada postura. [Procedimiento FK y evidencia](VALIDACION_FK_EN_VIVO.md).

## Prueba 3: editar una postura prevista junto al robot real, sin enviar

```bash
./iniciar.sh control_vista --host 192.168.125.1 --user "Default User" --ignore-joint-state
```

Lee los ángulos por RWS y muestra el estado medido y la vista previa naranja en RViz. Se puede seleccionar/ajustar un eje; ARMAR/EJECUTAR se rechazan porque este modo no abre un transporte de consignas. Sirve para comprobar controles, unidades, sentido y vista previa antes del ensayo EGM.

## Prueba 4: enviar un ángulo al ABB mediante EGM

Este código está preparado, pero **el ABB físico aún no tiene una sesión EGM/configuración de parada demostrada por este proyecto**. RWS funcionando no habilita por sí solo el control. Primero completar la preparación de [irb120_control](../../ros2_ws/src/irb120_control/README.md): respaldo, configuración UDPUC/RAPID, límites y ventana reales, postura/herramienta, parada por pérdida y GO del laboratorio. No cargar automáticamente la plantilla RAPID en un sistema existente.

Antes de armar el envío, comprobar la recepción EGM de solo lectura. Sustituir `IP_PC` por la IP Ethernet actual que muestra `enlace`, y `PUERTO_VERIFICADO` por el puerto configurado en UDPUC (no son valores literales):

```bash
./iniciar.sh control_egm_lectura --host 192.168.125.1 --bind-ip IP_PC --egm-port PUERTO_VERIFICADO
```

Este modo muestra los ángulos EGM y permite previsualizar; ARMAR/EJECUTAR permanecen bloqueados. Cerrar esta recepción antes de abrir la sesión de control, para liberar el puerto UDP.

Crear una ficha propia a partir de la plantilla, dentro de `salidas/` (no contiene contraseñas):

```bash
mkdir -p ../salidas/control_articular
cp src/irb120_control/config/sesion_robot.ejemplo.yaml ../salidas/control_articular/sesion_robot.yaml
# Completar la ficha con el operador después de realizar las verificaciones.
./iniciar.sh control_robot --config ../salidas/control_articular/sesion_robot.yaml --comprobar
```

La plantilla incompleta devuelve NO-GO y no abre UDP. El archivo no debe sobrescribirse con otra copia cuando ya contiene una sesión revisada. Los valores `null`/`false` no se rellenan por adivinación.

Solo con ficha válida y ensayo autorizado:

```bash
./iniciar.sh control_robot --config ../salidas/control_articular/sesion_robot.yaml --habilitar-envio
```

La aplicación espera datos EGM del ABB y permanece desarmada. La cuenta UAS no se usa en UDP. Seguir el handshake revisado: streaming del ABB → comprobar datos en RViz → ARMAR la PC en mantenimiento → operador activa Guidance → EJECUTAR en RViz. El primer ensayo debe ser pequeño, de un solo eje y con recorrido revisado. Esperar MANTENIENDO antes de seleccionar otro eje; durante la preparación se mantiene la referencia anterior y cada nuevo ensayo exige ARMAR/EJECUTAR. Al finalizar, DESARMAR cierra el envío; para otra sesión debe revisarse/reiniciarse el procedimiento del controlador. No se ejecuta una secuencia automática J1–J6 ni un HOME.

## Archivos y cierre

| Necesidad | Entrada |
|---|---|
| Todas las pruebas | `ros2_ws/iniciar.sh` con el modo correspondiente |
| Lectura RWS y FK | `ros2_ws/src/irb120_conexion/` |
| Control interactivo y EGM | `ros2_ws/src/irb120_control/` |
| Matemática propia | `hito2/irb120/` y FK ROS de Hito 1 verificada equivalente |
| Registro de lectura/FK | `salidas/prueba_comunicacion/` |
| Registro de control | `salidas/control_articular/` |

Ctrl+C una vez cierra el arranque y sus procesos. En control intenta completar el frenado normal cuando el enlace sigue sano; no sustituye la parada física del ABB. Ante fallo de enlace/proceso, el comportamiento de parada del controlador debe estar verificado. Para desconectar el cable, finalizar antes el ensayo según el operador.
