# Proyecto Final IMT-342 - Hitos 1 y 2

Gemelo digital cinemático del **ABB IRB 120-3/0.6** y validación
independiente de su cinemática directa. El proyecto sigue la Guía PFI y cumple
el pasaporte del Hito 1: el error entre el modelo DH analítico y la cadena URDF
es menor a `1e-6 m`.

## Estado

- Paquete ROS 2 Jazzy compilado correctamente.
- URDF/Xacro reducido a seis juntas revolutas y seis marcos móviles.
- Un único `origin` por grado de libertad: los visuales son meshes STL ya colocados en el marco de su eslabón, sin `origin` propio.
- Pinza neumática acoplada a `tool0` con dos juntas fijas (`gripper_mount`, `gripper_tcp_joint`); el TCP queda a 0.100 m de la brida.
- Meshes `visual` y `collision` del CAD real del IRB 120 (ROS-Industrial, Apache-2.0); sin masas ni inercias en el URDF.
- Movimiento manual y demostración automática.
- Validación DH contra URDF en vivo y verificación offline.
- Treinta y nueve pruebas automatizadas aprobadas entre ambos paquetes.
- La pose `[x, y, z]` del TF que muestra RViz se compara en vivo con la función DH analítica.
- Solo la pinza es un modelo paramétrico propio (`scripts/generate_meshes.py`) mientras no haya su CAD.

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
└── scripts/check_proyecto.sh           # Comprobación automática opcional
```

## Construcción manual, sin usar el script

Desde una terminal nueva:

```bash
cd <ruta-del-repo>/2-2026/IMT342/equipo/proyecto
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

## Hito 2

Paquete `irb120_hito2`: cinemática inversa de Pieper, trayectorias LSPB, Jacobiano
y dinámica, y el notebook del pasaporte (`notebooks/hito2_singularidad_q5.ipynb`).
Guía completa con ejemplos: [docs/hito2/guia_hito2.md](docs/hito2/guia_hito2.md); resumen: [docs/hito2/metodo_y_resultados.md](docs/hito2/metodo_y_resultados.md).

## Documentos

- [Modelo cinemático](docs/hito1/modelo_cinematico.md)
- [Trazabilidad](docs/hito1/trazabilidad.md)
- [Resultados](docs/hito1/resultados.md)
- [Guion de defensa](docs/hito1/guion_defensa.md)
- [Manual completo corregido en PDF](output/pdf/Guia_Practica_Hito1_IRB120_6_Juntas_CORREGIDA.pdf)
- [Presentación final para la defensa](output/presentation/Defensa_Hito1_IRB120_6_Juntas_FINAL.pptx)

## Geometría CAD

El brazo usa el CAD real del ABB IRB 120 de ROS-Industrial (Apache-2.0), importado con
`scripts/import_cad.py` a los marcos del URDF; ver `ros2_ws/src/irb120_hito1/meshes/NOTICE.md`.
