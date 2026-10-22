# Trazabilidad del Hito 1

Fuente de requisitos: [Guía oficial PFI](../../referencias/bibliografia/Guia_PFI.pdf),
sección 4, Hito 1:

- **Entregable:** paquete de ROS con el URDF modular del ABB IRB 120 acoplado con la pinza.
- **Pasaporte:** la pose cartesiana `[x, y, z]` de RViz debe coincidir con la función
  analítica en Python, con un error `ΔE < 1e-6 m`.

La guía no incluye rúbrica propia del Hito 1 y en el repositorio no se encontró una
worksheet de validación URDF; las filas marcadas como "criterio del equipo" son
decisiones internas, no exigencias del docente. Auditoría completa en
[auditoria_2026-10-22.md](auditoria_2026-10-22.md).

| Requisito | Origen | Implementación | Verificación |
|---|---|---|---|
| Paquete ROS del ABB IRB 120 | Guía PFI | `ros2_ws/src/irb120_hito1` (ament_python, ROS 2 Jazzy) | `package.xml`, build con `colcon` |
| URDF modular | Guía PFI | macro `irb120_robot` en `urdf/irb120.macro.xacro`, incluida por `irb120.urdf.xacro`; `urdf/irb120.urdf` es la expansión que usan launch, tests y `verify_model` | `scripts/check_proyecto.sh` expande el Xacro y ejecuta `verify_model` sobre el resultado |
| Seis juntas revolutas | Guía PFI (IRB 120 de 6 GDL) | `joint_1` a `joint_6` | `test_expanded_urdf_is_well_formed_and_has_unique_names` exige exactamente esas 6 revolutas |
| Pinza acoplada | Guía PFI | `gripper_link` (fija a `tool0`, sin `origin`) y `gripper_tcp` (fija, un `origin` sobre Z). Geometría de la pinza paramétrica propia, no CAD real | la misma prueba exige las 2 juntas fijas `gripper_mount` y `gripper_tcp_joint`; `test_tcp_and_reference.py` exige que el TCP de `config/tcp.yaml` (0.150 m) coincida en DH, URDF y Hito 2, y `test_validation.py` compara `gripper_tcp` DH vs URDF |
| Árbol serial sin ramas | criterio del equipo | `base_link → link_1 → … → link_5 → tool0 → gripper_link → gripper_tcp` (9 links: 6 juntas revolutas + 2 fijas) | `check_urdf` muestra un único hijo por link; la prueba exige la lista exacta de links |
| Un `origin` por grado de libertad | criterio del equipo | cada revoluta tiene un `origin`; `visual` y `collision` sin `origin` | `test_one_origin_per_degree_of_freedom`: 7 `origin` en total (6 juntas + offset del TCP) |
| Conversión DH a URDF | criterio del equipo | origins `O1…O6` en `irb120.macro.xacro` | `test_urdf_position_matches_dh_below_milestone_tolerance`: 100 posturas pseudoaleatorias, `base_link → tool0` |
| Cinemática directa analítica en Python | Guía PFI | `irb120_hito1/kinematics/dh.py` (NumPy) | `test_dh.py`: pose cero, 6 filas DH, ortonormalidad, rechazo de vector de tamaño incorrecto |
| Pose de RViz = función analítica, `ΔE < 1e-6 m` | Guía PFI (pasaporte) | `fk_validator` compara DH con el TF publicado por `robot_state_publisher` (el que dibuja RViz) y con la cadena URDF evaluada de forma independiente; el panel muestra la misma comparación en vivo con indicador `APROBADO` | tópicos `/irb120/fk_tf_position_error_m` (DH vs TF) y `/irb120/fk_position_error_m` (DH vs cadena URDF); panel → "Verificar posturas en RViz": 3/3 con `ΔE ≤ 3.9e-16 m`; `verify_model`: 206/206 comparaciones |
| URDF versionado = expansión del Xacro | criterio del equipo | launch, pruebas y `verify_model` leen `urdf/irb120.urdf` | `test_urdf_expansion.py` |
| Sin dinámica en este hito | criterio del equipo | no hay bloques `inertial`; sí hay `collision` (meshes simplificados del CAD) | la prueba estructural exige 0 `inertial`; `test_visual_and_collision_meshes_exist` exige 8 meshes `visual` y 8 `collision` |
| Sin MoveIt | Guía PFI, sección 3 | implementación NumPy explícita | `test_package_does_not_depend_on_moveit` (revisa `package.xml`) |
| Movimiento demostrable | criterio del equipo | panel Qt (`slider_gui` / `control_panel`): seis deslizadores con caja numérica, botones `Cero`, `Prueba A`, `Prueba B`, `Aleatoria`, demostración automática; también `motion_demo` | `test_control_panel.py` (panel sin pantalla), `test_slider_controls.py`, `test_motion.py`; lanzamiento ROS + RViz |

## Evidencia reproducible

```bash
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
ros2 run irb120_hito1 verify_model
```

Para validar la estructura Xacro y ver el árbol (requiere el `install/setup.bash`
cargado, porque el Xacro usa `$(find irb120_hito1)`):

```bash
xacro ros2_ws/src/irb120_hito1/urdf/irb120.urdf.xacro -o /tmp/irb120.urdf
check_urdf /tmp/irb120.urdf
```

La evidencia ROS en vivo se obtiene con:

```bash
ros2 launch irb120_hito1 display.launch.py
# en otra terminal, con los mismos entornos:
ros2 topic echo /irb120/fk_tf_position_error_m   # pasaporte: DH vs TF de RViz
ros2 topic echo /irb120/fk_position_error_m      # DH vs cadena URDF
```

El launch configura `fk_validator` con `target_frame: gripper_tcp`; el nodo también
acepta `tool0`.

## Gemelo visual y colisiones

El brazo usa el CAD del IRB 120 publicado por ROS-Industrial (Apache-2.0) como `visual`
y una versión simplificada como `collision`, ambos sin `origin` propio. La pinza es un
modelo paramétrico propio. La autocolisión y el contacto con la mesa se evalúan en
`ros2_ws/src/irb120_hito2/irb120_hito2/kinematics/collision.py`; RViz solo visualiza,
no detecta colisiones.
