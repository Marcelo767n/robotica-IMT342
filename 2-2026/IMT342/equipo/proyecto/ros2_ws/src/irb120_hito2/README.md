# irb120_hito2

Versión **ROS 2 secundaria** del Hito 2: cinemática inversa de Pieper, trayectorias LSPB y análisis de singularidad del ABB IRB 120, integrados con la simulación del Hito 1.

> **La versión vigente del Hito 2 está en [`hito2/`](../../../hito2/README.md)** (paquete `irb120` y notebook). Este paquete se conserva por compatibilidad con ROS; el control del robot real importa la cinemática de `hito2/`, no de aquí.

## Contenido

| Ruta | Qué hay |
|---|---|
| `irb120_hito2/kinematics/` | Pieper (`pieper.py`), Jacobiano, transformadas y colisión |
| `irb120_hito2/trajectory/lspb.py` | Perfil LSPB (velocidad trapezoidal) |
| `irb120_hito2/dynamics.py` | Modelo dinámico Lagrangiano |
| `irb120_hito2/nodes/ik_trajectory_node.py` | Nodo: `PoseStamped` en `/irb120/target_pose` a IK, LSPB y comandos articulares |
| `irb120_hito2/nodes/send_target.py` | Publica una pose objetivo desde la terminal |
| `launch/hito2.launch.py` | Lanza el gemelo del Hito 1 (sin sliders) y el nodo IK/LSPB |
| `test/` | Pruebas de Pieper, LSPB, singularidad y colisión |

## Uso

Requiere ROS 2 Jazzy y el paquete `irb120_hito1`:

```bash
cd ros2_ws
colcon build --packages-select irb120_hito1 irb120_hito2
source install/setup.bash
ros2 launch irb120_hito2 hito2.launch.py
ros2 run irb120_hito2 send_target 0.30 0.0 0.30     # X Y Z en metros; opcional R P Y en grados
```
