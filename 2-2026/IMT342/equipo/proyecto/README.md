# Proyecto Final IMT-342 — Hito 1

Gemelo digital modular del **ABB IRB 120-3/0.6 con pinza paralela** y validación
independiente de su cinemática directa. El proyecto sigue la Guía PFI y cumple el
pasaporte del Hito 1: comparar la posición calculada por el modelo DH con la
publicada por TF/RViz con un error inferior a `1e-6 m`.

## Estructura

```text
.
├── documentosGuia/                 # Guía PFI y papers fuente
├── docs/hito1/                      # Requisitos, modelo y evidencia
├── ros2_ws/src/irb120_hito1/
│   ├── irb120_hito1/kinematics/     # DH y evaluador URDF independiente
│   ├── irb120_hito1/nodes/          # Fuente articular y validador TF
│   ├── urdf/                        # Xacro modular + URDF expandido
│   ├── launch/                      # Lanzamiento integral
│   ├── config/ y rviz/              # Parámetros y vista
│   └── test/                        # Pruebas del pasaporte
└── scripts/check_hito1.sh           # Build, tests y verificación offline
```

## Preparación en Ubuntu 24.04 / ROS 2 Jazzy

```bash
sudo apt update
sudo apt install python3-colcon-common-extensions python3-pytest \
  ros-jazzy-xacro ros-jazzy-robot-state-publisher ros-jazzy-rviz2
```

Construcción y comprobación completa:

```bash
./scripts/check_hito1.sh
```

> **Importante:** no ejecutes los nodos ROS con el `python3` de Miniconda. En
> esta computadora entra en conflicto con `rclpy` de Jazzy por su versión de
> `libstdc++`. Usa los comandos `ros2 ...` indicados abajo o `/usr/bin/python3`
> para diagnósticos directos.

## Demostración en RViz

```bash
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
ros2 launch irb120_hito1 display.launch.py
```

El nodo de validación informa `APROBADO` cuando el error de `base_link` a
`tool0` es menor a `1e-6 m`. Para comprobar el TCP de la pinza:

```bash
ros2 launch irb120_hito1 display.launch.py target_frame:=tcp_link
```

Durante la ejecución se puede cambiar la postura enviando seis ángulos en
grados y, opcionalmente, una apertura de pinza entre `0` y `0.015 m`:

```bash
ros2 topic pub --once /irb120/joint_commands_deg std_msgs/msg/Float64MultiArray \
  "{data: [30.0, -20.0, 15.0, 40.0, -35.0, 60.0, 0.010]}"
```

## Estado del modelo visual

La cadena cinemática, los frames, límites articulares, masas e inercias están
implementados. Las geometrías actuales son primitivas paramétricas para que el
gemelo sea funcional sin archivos propietarios. Cuando esté disponible el CAD o
los meshes del IRB120, se reemplazarán solamente los bloques `visual/collision`;
la cinemática y sus pruebas no deben cambiar.

Consulta [modelo_cinematico.md](docs/hito1/modelo_cinematico.md) y
[trazabilidad.md](docs/hito1/trazabilidad.md) para la justificación y evidencia.
