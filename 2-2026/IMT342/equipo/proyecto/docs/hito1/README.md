# Hito 1: modelo y simulación ROS 2

Esta área contiene el trabajo de simulación del IRB 120. Los comandos de esta página operan los nodos de simulación del proyecto; no constituyen conexión al controlador físico.

## Documentos y resultados

- [Modelo cinemático](modelo_cinematico.md), [trazabilidad](trazabilidad.md), [resultados](resultados.md) y [defensa](guion_defensa.md).
- [Manual PDF](../../entregables/hito1/pdf/Guia_Practica_Hito1_IRB120_6_Juntas_CORREGIDA.pdf).
- [Presentación final](../../entregables/hito1/presentation/Defensa_Hito1_IRB120_6_Juntas_FINAL.pptx).
- [Paquete ROS y modelos](../../ros2_ws/src/irb120_hito1/README.md).

## Construcción y visualización

Desde la raíz, en una terminal con el Python apropiado para ROS:

```bash
source /opt/ros/jazzy/setup.bash
cd ros2_ws
colcon build --symlink-install --packages-select irb120_hito1
source install/setup.bash
ros2 launch irb120_hito1 display.launch.py
```

El historial documenta conflicto de Miniconda con `rclpy`; usar el entorno ROS configurado para esta instalación. La compatibilidad de un futuro driver físico se evalúa por separado.

Para la demostración automática de la simulación:

```bash
ros2 launch irb120_hito1 display.launch.py demo_motion:=true use_slider_gui:=false
```

En otra terminal con los mismos entornos activados puede enviarse una postura al nodo de simulación:

```bash
ros2 topic pub --once /irb120/joint_commands_deg std_msgs/msg/Float64MultiArray \
  "{data: [30.0, -20.0, 15.0, 40.0, -35.0, 60.0]}"
```

Las entradas son grados para `joint_1` a `joint_6`. Detener con `Ctrl+C`.

El TCP de este modelo anterior está a 0.100 m de la brida; Hito 2 usa 0.150 m. Árbol URDF y DH deben alinearse con una referencia externa y la herramienta real antes de hardware. El CAD visual procede de ROS-Industrial; ver [NOTICE](../../ros2_ws/src/irb120_hito1/meshes/NOTICE.md).
