# Trazabilidad del Hito 1 corregido

Fuente de requisitos: [Guía oficial PFI](../../documentosGuia/Guia_PFI.pdf),
sección 4, y worksheet de validación URDF.

| Requisito | Implementación | Verificación |
|---|---|---|
| Paquete ROS del ABB IRB 120 | `ros2_ws/src/irb120_hito1` | `package.xml` y build con `colcon` |
| Seis juntas | `joint_1` a `joint_6` | prueba XML exige exactamente 6 joints revolutos |
| Árbol mínimo | `base_link → link_1 → … → link_5 → tool0` | `check_urdf`, sin ramas ni joints fijos |
| Seis marcos móviles | `link_1` a `link_5` y `tool0` | TF y prueba estructural |
| Sin física innecesaria | no hay `inertial` ni `collision` | prueba estructural automática |
| Conversión DH a URDF | origins `O1...O6` en `irb120.macro.xacro` | 100 posturas pseudoaleatorias |
| Cinemática directa analítica | `kinematics/dh.py` | pose cero y ortonormalidad |
| Sin MoveIt | implementación NumPy explícita | prueba de ausencia de dependencia |
| Error menor a `1e-6 m` | `fk_validator` y `verify_model` | dos posturas justificadas y prueba aleatoria |
| Movimiento demostrable | panel de seis sliders y `motion_demo` | lanzamiento ROS + RViz |

## Evidencia reproducible

```bash
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
ros2 run irb120_hito1 verify_model
```

Para validar la estructura Xacro y ver el árbol:

```bash
xacro ros2_ws/src/irb120_hito1/urdf/irb120.urdf.xacro -o /tmp/irb120.urdf
check_urdf /tmp/irb120.urdf
```

La evidencia ROS en vivo se obtiene con:

```bash
ros2 launch irb120_hito1 display.launch.py
ros2 topic echo /irb120/fk_position_error_m
```

## Pendiente para el gemelo visual definitivo

Falta sustituir las primitivas por meshes CAD reales. Se conservarán las seis
juntas, sus seis marcos móviles y las pruebas cinemáticas. La detección formal
de colisiones se añadirá después con meshes simplificados de colisión y la
geometría del entorno; no se debe afirmar que RViz detecta colisiones.
