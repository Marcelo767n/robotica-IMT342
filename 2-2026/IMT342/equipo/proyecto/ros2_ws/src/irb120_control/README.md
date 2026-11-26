# irb120_control · control del IRB 120 desde la PC

Este paquete contiene todo lo que mueve el robot desde la PC y el software de apoyo. Hay dos rutas:

1. **Ruta vigente: RWS + RAPID**, usada en las sesiones reales. La PC valida y envía objetivos por RWS al módulo RAPID `LabJointRws` (`ServidorPC`), que los ejecuta con `MoveAbsJ` (y `MoveL` en la v5). Todo se opera dentro de RViz.
2. **Ruta EGM UDP**, solo en simulación (loopback); descrita más abajo. No se probó con el controlador.

## Comandos

Desde `proyecto/ros2_ws/` (el atajo `brazo` equivale a `./brazo.sh`; `./brazo.sh ayuda` lista todo):

```bash
./brazo.sh compilar              # una vez: panel «IRB 120» de RViz
./brazo.sh sesion                # con robot: enlace + AUTO guiado + RViz + panel + Estudio
./brazo.sh sesion --simulado     # la misma sesión sin robot
./brazo.sh sesion --v4           # con robot y el módulo de respaldo v4 (probado; ≤ 40° por orden, sin MoveL)
./brazo.sh demo                  # todo sin robot (--plc: con la celda PLC simulada)
./brazo.sh nodos                 # grafo ROS 2 en vivo
./brazo.sh estudio               # solo el Estudio CustomTkinter
./brazo.sh pruebas               # ≈300 pruebas offline
```

## Estructura del paquete Python

| Carpeta o módulo (`irb120_control/`) | Función |
|---|---|
| `panel/` | Nodo `irb120_panel_rws`: validación, IK de Pieper, verificación, sesión RWS, ejecución de trayectorias, buzón de puntos, biblioteca de guardadas, puente ROS 2 y control 3D |
| `trayectorias/` | Modelo, planificador (articular o lineal por tramo), reglas del Hito 2 más estrictas y movimientos vistosos |
| `estudio/` | Estudio CustomTkinter (análisis, editor, gráficas, matemática LaTeX) |
| `analisis/` | Ventana de análisis anterior (tkinter) |
| `plc/` · `celda/` | Celda con PLC S7-1200: nodos `irb120_plc_s7` e `irb120_celda` (extensión simulada) |
| `vision/` | Entrada de puntos de visión (`publicar_punto`) |
| `grafo_ros.py` | Grafo ROS 2 en vivo |
| `rws_mover.py`, `rws_j6.py`, `respaldo.py` | Cliente RWS, instalación del módulo y respaldo del controlador |
| `supervisor.py`, `protocolo.py`, `runtime.py`, `simulador.py`, `rviz_control.py`, `arranque.py` | Ruta EGM simulada (ver «Código» más abajo) |

Módulos RAPID en `rapid/rws_mover/`: `LabJointRws.mod` (v5, una orden por tramo, `MoveL`; **sin probar en el IRC5**) y `LabJointRws_v4.mod` (respaldo, **probado en el robot**). Los respaldos del controlador están en `rapid/respaldo_controlador/`.

## Panel de RViz: pestaña «Trayectorias»

El panel «IRB 120» ([README del plugin](../irb120_rviz_panel/README.md)) tiene dos pestañas. «Mover» edita ángulos o una pose; «Trayectorias» ofrece:
- lista de **movimientos vistosos** (10 saludo, 11 reverencia, 12 mirar_alrededor, 13 ocho, 14 baile) y de trayectorias **guardadas** (`salidas/trayectorias/NN_nombre.json`);
- **Bucle** continuo hasta «Detener al final»; **Vista previa** (anima el modelo naranja sin mover el robot); **Ejecutar** (con confirmación); **Pausar**, **Reanudar**, **Detener al final** y **Cancelar**;
- **Grabar**: capturar la postura actual como punto, borrar el último, vaciar y guardar con nombre (y bucle opcional).

Pausar y cancelar actúan al terminar el tramo en curso; para parar YA: habilitador, Stop o paro de emergencia.

---

## Historia y ruta EGM simulada (referencia)

**11/11 (histórico) — ruta para mover desde la PC:** `./iniciar.sh rws_mover interactivo` con el módulo [`rapid/rws_mover/LabJointRws.mod`](rapid/rws_mover/LabJointRws.mod) (`ServidorPC`). Guía y pasos del FlexPendant: [MOVER_DESDE_PC.md](../../../docs/conexion_abb/MOVER_DESDE_PC.md). 37 pruebas RWS offline aprobadas (`python3 -m unittest discover -s src/irb120_control/test -p 'test_rws_*.py'` desde `ros2_ws/`); esa ruta se ejecutó después en el IRC5 real (16 a 19/11).

**10/11 — movimiento físico no conseguido:** [prueba puntual J6 mediante RWS + RAPID](../../../docs/conexion_abb/PRUEBA_J6_RWS_RAPID.md). `rws_j6.py` inspecciona, respalda/transfiere únicamente `LabJointRws`, comprueba recepción sin desplazamiento y prepara ±0,1° de J6 para confirmación local en FlexPendant. La recepción y transferencia se verificaron, pero el monitor terminó sin movimiento y no se comprobó la ejecución local en manual reducido. [Diagnóstico del intento](../../../docs/conexion_abb/CIERRE_PRUEBA_J6_2026-11-10.md). Esta ruta está separada de la demo/EGM descrita a continuación.

Para retomar: `./iniciar.sh rws_j6 diagnosticar` consulta modo, controlador, RAPID, módulo y objetivo con GET; `--informe /ruta/inspeccion.json` analiza un archivo histórico sin red ni contraseña. No habilita movimiento ni verifica el puntero. [Secuencia para la próxima visita](../../../docs/conexion_abb/PROXIMA_SESION_J6.md). El conjunto RWS suma 21 pruebas offline aprobadas; se conserva [su salida](../../../docs/conexion_abb/evidencias/rws_j6_diagnostico_2026-11-10_pruebas.txt).

Implementación separada del paquete de lectura `irb120_conexion`. Incluye controles interactivos **nativos de RViz**, supervisor de un eje, LSPB propio y EGM UDP/Protobuf. `control_demo` usa un controlador simulado en **127.0.0.1**; `control_vista` lee RWS y solo previsualiza; `control_robot` contiene la salida EGM física, desarmada al inicio y bloqueada sin ficha/GO.

`control_egm_lectura` permite comprobar la recepción UDP del ABB sin abrir ninguna ruta de consignas, antes del ensayo de movimiento.

El transporte de esta primera prueba está escrito en Python con un hilo separado de ROS y vigilancia de atrasos. No garantiza tiempo real duro ni equivale a un sistema de seguridad certificado. La integración posterior del driver C++/`ros2_control` sigue siendo otra etapa. El módulo RAPID incluido es una **plantilla pendiente de compilación y validación en RobotStudio/RW6.12**, no configuración física ya comprobada.

## Entradas

Desde `proyecto/ros2_ws/`:

```bash
./iniciar.sh control_demo
./iniciar.sh control_demo --recorrido-demo-deg 5
./iniciar.sh control_demo --recorrido-demo-deg 10
./iniciar.sh control_vista --host 192.168.125.1 --user "Default User" --ignore-joint-state
# Sustituir IP_PC y PUERTO_VERIFICADO por los datos comprobados de la sesión:
./iniciar.sh control_egm_lectura --host 192.168.125.1 --bind-ip IP_PC --egm-port PUERTO_VERIFICADO
./iniciar.sh control_robot --config /ruta/real/sesion_robot.yaml --comprobar
# Solo después de validar la sesión EGM en el laboratorio:
./iniciar.sh control_robot --config /ruta/real/sesion_robot.yaml --habilitar-envio
```

El último comando todavía no arma ni ejecuta; espera los paquetes del ABB. No solicita contraseña porque EGM no utiliza la autenticación HTTP de RWS. No carga programas en el controlador, ni activa motores/RAPID desde la computadora.

`--recorrido-demo-deg` permite 1, 5 o 10 grados **por prueba en simulación**. Conserva velocidad 0.5°/s y aceleración 0.5°/s²; 5° tarda aproximadamente 11 s y 10° unos 21 s con nuestro LSPB, más el asentamiento. El menú añade ±5° o ±10° según el recorrido elegido. Cada valor es un incremento del objetivo; el cambio total desde la postura sincronizada debe caber en el recorrido máximo y en la ventana inicial de la sesión. No hay envío al arrastrar ni ejecución automática. El parámetro se rechaza en todos los modos conectados al ABB. El primer ensayo físico sigue limitado a 1° y requiere su ficha revisada; ampliar después a 5°/10° exige revisar tanto la política PC como la configuración ABB, incluido `MaxPosDeviation` de la plantilla.

Para pasar de la demo al controlador, ver [Preparación EGM física y alternativas sin RobotStudio](../../../docs/conexion_abb/PREPARAR_EGM_FISICO.md).

## Uso en RViz

1. Seleccionar la herramienta **Interact**. El aro está en el origen de la articulación seleccionada.
2. Clic derecho sobre el aro → **1. Seleccionar eje → J1…J6**. Esperar un segundo tras cambiar de eje (arbitraje del servidor interactivo).
3. Arrastrar el aro o usar **2. Ajustar objetivo → ±0.1° / ±0.5°**. Esto solo cambia el nuevo objetivo y el modelo naranja. Si una prueba anterior sigue en mantenimiento, se continúa transmitiendo su referencia fija, no el nuevo objetivo. Los objetivos inválidos se rechazan; no se recortan silenciosamente.
4. Revisar el objetivo y el recorrido; menú **3. ARMAR**. Primera referencia igual a la postura medida, cinco juntas fijas. En hardware, el protocolo del controlador debe ofrecer streaming antes de Guidance; completar el arranque de Guidance según el procedimiento revisado.
5. Cuando Guidance esté activo, menú **4. EJECUTAR**. El brazo simulado/físico recibe las seis referencias: cambia únicamente el eje seleccionado.
6. Esperar **MANTENIENDO**. Para otro eje, volver a **seleccionar/sincronizar**, ajustar la vista previa y ARMAR/EJECUTAR otra vez. Durante **PREPARANDO** se mantiene la referencia anterior sin saltos y sin cortar la sesión EGM. El tiempo máximo de sesión sigue contando desde el primer armado.
7. Usar **DESARMAR** al terminar: cierra el envío en reposo y en hardware puede finalizar EGM por `CommTimeout`. Otro arranque de sesión requiere revisar/reiniciar el procedimiento ABB; no hay recuperación automática.
8. **CANCELAR movimiento y mantener** genera un frenado limitado desde la referencia actual. Esperar reposo antes de desarmar. No sustituye la parada física de emergencia.

El texto de RViz muestra modo, estado, ángulo medido/objetivo, ventana permitida y motivo de rechazo/fallo. Modelo medido y previsto usan TF separados (`medido/` y `objetivo/`). El estado medido no se publica con tiempos nuevos cuando dejó de llegar feedback.

Si se abrió la versión que mostraba piezas amontonadas, cerrar esa sesión con Ctrl+C y repetir el mismo comando. Se corrigieron el **TF Prefix** de ambos RobotModel y las propiedades Jazzy **Interactive Markers Namespace** y **Topic**. No hace falta configurar los displays manualmente. El aro de J1 aparece azul alrededor de la base; elegir **Interact** y hacer clic derecho sobre ese aro. Los caracteres del texto 3D se limitan a ASCII para el renderizador Ogre; los menús Qt conservan español y símbolos.

## Límites y guardas

| Junta | Rango nominal (grados) |
|---|---:|
| J1 | −165 a +165 |
| J2 | −110 a +110 |
| J3 | −110 a +70 |
| J4 | −160 a +160 |
| J5 | −120 a +120 |
| J6 | −400 a +400 |

Se reutiliza `hito2/irb120/dh.py` y se comprueba al iniciar que el URDF concuerde. Para hardware se calcula la **intersección** con los límites efectivos del controlador, conservando al menos 2° de margen, y después se exige una ventana de ensayo aún más pequeña. La primera postura debe coincidir con los seis ángulos de la ficha.

La demo propone paso máximo **1°**, velocidad **0.5°/s** y aceleración **0.5°/s²**. No son valores aprobados para el laboratorio: la ficha física exige valores explícitos y el programa rechaza paso/velocidad/aceleración superiores a 1 en sus unidades. J6 se conserva sin reducir módulo 360. Cada ensayo empieza con seis ejes medidos y solo modifica uno. Se rechazan NaN, ejes incompletos, estado antiguo, falta de reposo, cambio de postura, seguimiento excesivo, pérdida de motores/RAPID/Guidance o ciclo atrasado. No hay ejecución ni rearme automático tras reconectar.

Estos límites no detectan por sí solos colisiones, cables, obstáculos o riesgos de herramienta. La revisión del recorrido completo y la protección física corresponden al ensayo de laboratorio. La plantilla de sesión requiere evidencia de esa revisión.

Al armar se comprueban 41 puntos del recorrido articular con la SVD del Jacobiano propio en `tool0`, con umbral mínimo 0.01. Es una guarda numérica de singularidad, con filas lineales en metros y angulares en radianes; no es un verificador continuo de colisiones ni una métrica adimensional. Se bloquean posturas como el HOME singular y no se relaja este filtro para encontrar una orden ejecutable. Solo se admite una sesión de control por carpeta para evitar mezclar sus temas ROS.

## Qué falta para el ABB físico

1. Respaldo completo y revisión exacta del sistema/controlador.
2. Configuración UDPUC, IP actual de la PC, puerto y periodo EGM. `192.168.125.1` es la IP RWS conocida; no prueba que UDP ya esté configurado.
3. Validar el RAPID/handshake **stream → PC armada en mantenimiento → Guidance → ejecutar**, con datos reales de `motorState`, `rapidExecState` y `mciState`. La ventana de espera no debe activar movimiento ni agotar el timeout antes de armar la PC.
4. Ensayar la parada por pérdida de paquetes mediante `CommTimeout` y su manejo de errores en el controlador virtual y luego bajo el procedimiento físico aprobado. Si la PC/proceso se congela por completo, la protección debe quedar en el ABB. El software no asume que cerrar UDP equivale a parada certificada.
5. Leer límites efectivos, herramienta/carga, confirmar postura y revisar recorrido.
6. Completar [config/sesion_robot.ejemplo.yaml](config/sesion_robot.ejemplo.yaml) en una ficha de sesión real. Conservar la plantilla NO-GO. El [checklist docente](../../../material_docente/actualizacion_semana_12/w12_s01_checklist_seguridad.tex) exige GO del operador autorizado y responsable del laboratorio.

El `true` de una ficha representa una verificación realizada; escribirlo no verifica físicamente el controlador. El programa valida estructura, vigencia y coherencia numérica, no certifica esas declaraciones.

## Código

| Archivo | Función |
|---|---|
| `irb120_control/supervisor.py` | Límites, estado, un eje, armado, LSPB, seguimiento, frenado y fallos |
| `irb120_control/protocolo.py` | EGM UDP, emisor/puerto fijados tras primera lectura válida, secuencias y Protobuf |
| `irb120_control/runtime.py` | Hilo de intercambio y registros; vigila heartbeat ROS y atrasos |
| `irb120_control/rviz_control.py` | Aro, menús, extracción del ángulo según el origen URDF y TF/estado |
| `irb120_control/arranque.py` | Tres modos, procesos RViz/RSP, lectura RWS de vista previa y cierre |
| `irb120_control/simulador.py` | ABB simulado en loopback, con paquetes EGM binarios reales |
| `irb120_control/vendor/` | Esquema generado, licencia y hash de procedencia |
| `rapid/IRB120_EGM_Prueba.mod` | Plantilla de ingeniería para revisión; bloqueada por defecto |

Registros JSONL en `proyecto/salidas/control_articular/`: acciones, rechazos, estados, ángulos medidos/objetivo/referencia y número de paquetes. No se guardan contraseñas. En vista RWS no se habilita ningún envío EGM.

## Pruebas reproducibles

Desde `proyecto/`:

```bash
source /opt/ros/jazzy/setup.bash
export PYTHONPATH="$PWD/ros2_ws/src/irb120_control:$PWD/ros2_ws/src/irb120_conexion${PYTHONPATH:+:$PYTHONPATH}"
ROS_DOMAIN_ID=178 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST IRB120_CONTROL_ROS_TEST=1 \
  ~/ros_py312/bin/python -m unittest discover -s ros2_ws/src/irb120_control/test -v
```

Se prueba la cadena de menús/feedback público de RViz a referencias EGM por UDP local. Ninguna prueba usa la IP del robot físico. El entorno de esta PC reutiliza `protobuf 4.21.12` puro ya instalado, conservando prioridad de las bibliotecas ROS/Python 3.12. Para otro entorno ver `requirements-egm.txt`.

Para comprobar además los **Status reales de los plugins RViz**, con una sesión gráfica disponible y las bibliotecas de desarrollo ya instaladas en esta PC:

```bash
cmake -S ros2_ws/src/irb120_control/test/rviz_probe -B /tmp/irb120_rviz_probe_build \
  -DPython3_EXECUTABLE="$HOME/ros_py312/bin/python" -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/irb120_rviz_probe_build -j2
ROS_DOMAIN_ID=178 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST IRB120_CONTROL_ROS_TEST=1 \
  IRB120_RVIZ_PROBE=/tmp/irb120_rviz_probe_build/rviz_probe QT_QPA_PLATFORM=xcb \
  ~/ros_py312/bin/python -m unittest discover -s ros2_ws/src/irb120_control/test -v
```

La nueva prueba inicia dos RSP reales, verifica cada marco del URDF y que la vista previa se separe sin modificar el medido. El ejecutable auxiliar carga la configuración generada en las bibliotecas RViz y exige estado OK en modelos, aro y texto. `IRB120_RVIZ_SCREENSHOT=/ruta/absoluta/captura.png` guarda opcionalmente la imagen del renderizador propio de la prueba. El auxiliar de C++ no se requiere para usar `iniciar.sh`.

Resultado actualizado del 04/11: **21 pruebas aprobadas**, incluidos los seis ejes, arrastre válido de J2/J4/J6, menú de incrementos, frenado, fallos, TF y displays reales de RViz. También se corrigió una carrera de reloj: el hilo EGM tomaba la hora antes de esperar el lock y podía compararla con un heartbeat ROS más reciente, disparando un falso fallo. La prueba determinista reproduce ese orden; se conserva la vigilancia y sus umbrales. [Evidencia del arreglo, Status y captura](../../../docs/conexion_abb/evidencias/control_rviz_corregido_2026-11-04.json). La [evidencia inicial de 19 pruebas](../../../docs/conexion_abb/evidencias/control_rviz_egm_2026-11-04.json) solo comprobaba arranque sin errores de carga de plugins; no detectó las propiedades visuales incorrectas. No hubo acceso al ABB físico.

Ampliación de recorrido: **24 pruebas aprobadas**. Se verifican perfiles de ±5°/±10° de cada eje, límites de velocidad/aceleración, cinco ejes fijos, llegada y rechazo de límites/uso de la opción demo en modos físicos. El menú ampliado se prueba con feedback ROS público y los displays RViz siguen OK. El transporte UDP integrado sigue ensayándose en loopback; no se presenta esta prueba como una sesión EGM física. [Evidencia y hashes de la ampliación](../../../docs/conexion_abb/evidencias/control_demo_5_10_2026-11-04.json).

La estructura ament está preparada para el repositorio; esta versión se verificó mediante el arranque fuente y necesita los modelos de `hito2/` presentes. No se afirma una nueva instalación con colcon ni un paquete autónomo exportable fuera del proyecto.

Fuentes primarias: [protocolo EGM del cliente RW6](https://abb-robot-client.readthedocs.io/en/stable/readme.html), [esquema Protobuf de abb_robot_client](https://github.com/rpiRobotics/abb_robot_client/blob/master/src/abb_robot_client/_egm_protobuf/egm_pb2.py), [manual ABB RW6, 3HAC073319-001 revisión F](https://library.e.abb.com/public/f63dc4031d194a58be058eb657441180/3HAC073319%20AM%20Externally%20Guided%20Motion%20RW6-en.pdf). El manual documenta `EGMSetupUC` y `CommTimeout`; su comportamiento y parámetros aplicables deben contrastarse con RW6.12 y la configuración real antes de uso físico.
