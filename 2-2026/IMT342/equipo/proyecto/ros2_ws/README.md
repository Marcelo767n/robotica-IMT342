# ROS 2 · ABB IRB 120

Entrada principal: **`./brazo.sh`**, desde esta carpeta (`ros2_ws/`). `./brazo.sh ayuda` lista todos los comandos y los pasos del FlexPendant. `./iniciar.sh` es la capa inferior que usa `brazo.sh` (también sirve para los modos de lectura y de simulación).

| Comando | Qué hace |
|---|---|
| `./brazo.sh sesion` | Con robot, todo en uno: enlace, AUTO guiado (llave, módulo, Motors On, arranque, «Iniciar»), RViz + panel + Estudio |
| `./brazo.sh sesion --simulado` | La misma sesión sin robot (robot ficticio), para revisar o practicar |
| `./brazo.sh sesion --v4` | Con robot y el módulo de respaldo v4 (probado en el robot; solo articular, órdenes ≤ 40°, sin `MoveL`). También `./brazo.sh panel --modulo v4` |
| `./brazo.sh nodos` | Grafo ROS 2 en vivo: nodos, tópicos y quién publica o escucha (`--simulado`, `--png FICHERO`) |
| `./brazo.sh demo` | Todo sin robot: RViz + panel simulado + Estudio (`--plc` añade la celda PLC simulada) |
| `./brazo.sh estudio` | Solo el Estudio CustomTkinter (`--demo` sin panel, `--puerto 8771` con el simulado) |
| `./brazo.sh enlace` | Comprueba cable, IP de la PC, ping y puerto RWS |
| `./brazo.sh estado` · `eventos` | Modo, motores, RAPID, módulo y ángulos (dice qué falta) · además puntero de programa y mensajes del FlexPendant |
| `./brazo.sh respaldar` | Copia los módulos RAPID del robot a `rapid/respaldo_controlador/` (solo lectura) |
| `./brazo.sh instalar` / `instalar-auto` | Instala el módulo RAPID `LabJointRws` v5 por RWS (llave en AUTO, motores apagados; `instalar-auto` acepta modo AUTO) |
| `./brazo.sh panel` · `simulado` | Robot real o sin robot: panel «IRB 120» y control 3D en RViz |
| `./brazo.sh arrancar` | Solo AUTO: pone el puntero en `ServidorPC` y arranca RAPID |
| `./brazo.sh terminal` / `mover j6 +5` | Prompt de órdenes o una sola orden |
| `./brazo.sh punto X Y Z R P Y` | Añade un punto al buzón del panel por el tópico de visión (mm, grados, TCP) |
| `./brazo.sh plc` · `plc-simulador` | Nodos de la celda PLC junto al panel · PLC simulado en esta PC (extensión, ver [PLC_S7_1200.md](../docs/PLC_S7_1200.md)) |
| `./brazo.sh terminar` | Termina `ServidorPC` en el robot |
| `./brazo.sh compilar` | Compila el panel C++ de RViz (una vez) |
| `./brazo.sh pruebas` | ≈300 pruebas offline, sin robot ni red |

Atajo: `~/.local/bin/brazo` apunta a este `brazo.sh`, de modo que `brazo sesion` funciona desde cualquier carpeta.

Guía completa de uso: [MOVER_DESDE_PC.md](../docs/conexion_abb/MOVER_DESDE_PC.md). Funcionamiento: [COMO_FUNCIONA.md](../docs/conexion_abb/COMO_FUNCIONA.md). Comandos de lectura y validación: [COMANDOS_LABORATORIO.md](../docs/conexion_abb/COMANDOS_LABORATORIO.md).

La prueba de J6 del 10/11 ([RWS + RAPID](../docs/conexion_abb/PRUEBA_J6_RWS_RAPID.md)) no consiguió movimiento ([diagnóstico](../docs/conexion_abb/CIERRE_PRUEBA_J6_2026-11-10.md)); el 16/11 el robot se movió con `LabJointRws` v2 ([bitácora](../docs/bitacora/2026-11-16_primer_movimiento_real.md)) y entre el 16 y el 19/11 se registraron 265 órdenes (264 con llegada) (la v4 es la versión probada en el robot). La v5 (`MoveL`, una orden por tramo) está instalable pero sin probar en el IRC5.

Otros modos de `iniciar.sh` (lectura del robot, sin movimiento):

```bash
bash ros2_ws/iniciar.sh enlace --ping
bash ros2_ws/iniciar.sh comunicacion --host 192.168.125.1 --user "Default User" --ignore-joint-state
bash ros2_ws/iniciar.sh validar_fk --host 192.168.125.1 --user "Default User" --ignore-joint-state
./iniciar.sh control_demo        # controles de RViz sin robot
```

El arranque carga Jazzy y `~/ros_py312`, sin necesitar `colcon` ni `ros2 launch` (salvo `./brazo.sh compilar`). La contraseña RWS se pide en la terminal y no se guarda.

## Dónde trabajar

| Carpeta | Responsabilidad |
|---|---|
| `src/irb120_conexion/` | **Conexión física actual**: nodos de lectura, monitor y validación FK, arranques y protocolos GET |
| `src/irb120_control/` | **Mover el robot desde la PC**: cliente RWS (`rws_mover`), módulo RAPID `LabJointRws`, demo EGM UDP, supervisor. Contiene el paquete Python `irb120_control/panel/` (ver abajo) |
| `src/irb120_rviz_panel/` | **Panel «IRB 120» de RViz en C++**: ángulos, pose con cinemática inversa y envío al robot. Ver [su README](src/irb120_rviz_panel/README.md) |
| `src/irb120_hito1/` | **Modelo propio y simulación**: DH, URDF/Xacro, meshes, configuración TCP, panel de simulación y validadores |
| `src/irb120_hito2/` | Versión ROS secundaria del Hito 2 ([README](src/irb120_hito2/README.md)); la vigente está en `../hito2/` |
| `build/`, `install/`, `log/` | Archivos generados de compilaciones. No editar ni mover como si fueran código fuente |

### Paquete `irb120_control` (Python)

| Módulo | Contenido |
|---|---|
| `panel/` | Lógica del panel (`./brazo.sh panel`): límites, FK/IK de Pieper, robot simulado, estado y envío en segundo plano, órdenes JSON de RViz, sesión RWS, verificación IK→FK, ejecución de trayectorias (`trayectoria.py`), buzón de puntos (`buzon.py`), biblioteca de trayectorias guardadas (`biblioteca_panel.py`), nodo ROS 2 (`puente_ros.py`, tópicos `/irb120/panel/estado` y `/irb120/panel/orden`), control 3D arrastrable y página local opcional (`--web`). Mapa en `panel/__init__.py` |
| `trayectorias/` | Modelo de trayectoria, planificador (elige articular o lineal por tramo), reglas del Hito 2 más estrictas y movimientos vistosos (`demos.py`) |
| `estudio/` | Estudio CustomTkinter: estado, editor de trayectorias, reglas, gráficas y matemática en LaTeX |
| `analisis/` | Ventana de análisis anterior (tkinter, solo lectura) |
| `plc/` · `celda/` | Celda con PLC S7-1200 (extensión simulada): nodos `irb120_plc_s7` e `irb120_celda` |
| `vision/` | Entrada de puntos externos: `publicar_punto` (`/irb120/trayectoria/punto_externo`) |
| `grafo_ros.py` | Grafo ROS 2 en vivo (`brazo nodos`) |
| `rws_mover.py`, `rws_j6.py`, `respaldo.py` | Cliente RWS, instalación del módulo RAPID y respaldo |
| `supervisor.py`, `protocolo.py`, `runtime.py`, `simulador.py` | Ruta EGM UDP (solo simulada) |

Tópicos y nodos en [MAPA_ROS2.md](../docs/MAPA_ROS2.md); contrato de trayectorias en [ARQUITECTURA_TRAYECTORIAS.md](../docs/ARQUITECTURA_TRAYECTORIAS.md).

La implementación antes repartida en `../scripts/` se trasladó a `irb120_conexion`. Los nombres antiguos de Python y shell quedan como entradas de compatibilidad; no contienen una segunda implementación.

Abrir [la estructura por nodos](src/irb120_conexion/README.md) y [la guía de validación FK](../docs/conexion_abb/VALIDACION_FK_EN_VIVO.md).

La etapa posterior está descrita en el [plan de control EGM → IK propia → visión](../docs/hitos_3_4/PLAN_CONTROL_EGM_IK_VISION.md). El [paquete irb120_control](src/irb120_control/README.md) ya implementa el ensayo individual J1–J6 y su demo EGM local. EGM físico aún no está probado. `comunicacion` y `validar_fk` siguen siendo de lectura.

Desde esta carpeta `ros2_ws/`, ejecutar `./iniciar.sh control_demo` para probar los controles nativos de RViz sin robot. Para la salida física revisar la ficha y la guía del paquete; abrir RViz no habilita movimiento por sí solo.
