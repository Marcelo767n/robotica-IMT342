# Proyecto Final IMT-342 - Hito 1

Gemelo digital cinemático del **ABB IRB 120-3/0.6** y validación
independiente de su cinemática directa. El proyecto sigue la Guía PFI y cumple
el pasaporte del Hito 1: el error entre el modelo DH analítico y la cadena URDF
es menor a `1e-6 m`.

## Estado

- Paquete ROS 2 Jazzy compilado correctamente.
- URDF/Xacro reducido a seis juntas revolutas y seis marcos móviles.
- Sin juntas fijas auxiliares, pinza, masas, inercias ni colisiones en el Hito 1.
- Movimiento manual y demostración automática.
- Validación DH contra URDF en vivo y verificación offline.
- Doce pruebas automatizadas aprobadas.
- Geometría CAD real pendiente; se usan primitivas provisionales sin afectar la cinemática.

## Estructura

```text
.
├── documentosGuia/                 # Guía PFI y papers fuente
├── docs/hito1/                      # Modelo, trazabilidad, resultados y evidencia
├── output/                          # PDF y presentación finales
├── ros2_ws/src/irb120_hito1/
│   ├── irb120_hito1/kinematics/     # DH y evaluador URDF independiente
│   ├── irb120_hito1/nodes/          # Estados, movimiento y validación
│   ├── urdf/                        # Xacro modular y URDF expandido
│   ├── launch/                      # Lanzamiento integral
│   ├── config/ y rviz/              # Parámetros y vista
│   └── test/                        # Pruebas del pasaporte
└── scripts/check_hito1.sh           # Comprobación automática opcional
```

## Construcción manual, sin usar el script

Desde una terminal nueva:

```bash
cd /home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto
source /opt/ros/jazzy/setup.bash
cd ros2_ws
colcon build --symlink-install --packages-select irb120_hito1
source install/setup.bash
```

No ejecutes los nodos ROS con el `python3` de Miniconda. En esta computadora
entra en conflicto con `rclpy` de Jazzy. Los comandos `ros2 ...` usan el entorno
correcto después de ejecutar los dos `source` anteriores.

## Demostración recomendada para la defensa

Para abrir RViz y mover automáticamente los seis ejes:

```bash
ros2 launch irb120_hito1 display.launch.py demo_motion:=true use_slider_gui:=false
```

La terminal debe mostrar repetidamente `APROBADO | DH vs URDF`.
Detén todo con `Ctrl+C`.

Para abrir el modelo quieto y enviar una postura manual:

```bash
ros2 launch irb120_hito1 display.launch.py
```

Este lanzamiento abre RViz y un panel gráfico con deslizadores para J1-J6,
además de botones para pose cero y las configuraciones de prueba A/B.
Para omitir el panel use `use_slider_gui:=false`.

En una segunda terminal repite los dos `source` y ejecuta:

```bash
ros2 topic pub --once /irb120/joint_commands_deg std_msgs/msg/Float64MultiArray \
  "{data: [30.0, -20.0, 15.0, 40.0, -35.0, 60.0]}"
```

Los seis valores son grados para `joint_1` a `joint_6`.

## Verificación

```bash
colcon test --packages-select irb120_hito1 --event-handlers console_direct+
colcon test-result --verbose
ros2 run irb120_hito1 verify_model
ros2 topic echo /irb120/fk_position_error_m
```

## Documentos

- [Modelo cinemático](docs/hito1/modelo_cinematico.md)
- [Trazabilidad](docs/hito1/trazabilidad.md)
- [Resultados](docs/hito1/resultados.md)
- [Guion de defensa](docs/hito1/guion_defensa.md)
- [Manual completo corregido en PDF](output/pdf/Guia_Practica_Hito1_IRB120_6_Juntas_CORREGIDA.pdf)
- [Presentación final para la defensa](output/presentation/Defensa_Hito1_IRB120_6_Juntas_FINAL.pptx)

## Modelo visual pendiente

Las geometrías actuales son primitivas paramétricas. Cuando esté disponible el
CAD, se reemplazarán los bloques `visual` por meshes separados por eslabón. Los
seis `joint`, sus frames, parámetros DH y pruebas no deben cambiar. En una etapa
posterior se podrán añadir meshes simplificados bajo `collision`.
