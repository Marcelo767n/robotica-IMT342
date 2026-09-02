# Trazabilidad del Hito 1

Fuente de requisitos: [Guía oficial PFI](../../documentosGuia/Guia_PFI.pdf),
sección 4.

| Requisito | Implementación | Verificación |
|---|---|---|
| Paquete ROS del ABB IRB120 | `ros2_ws/src/irb120_hito1` | `package.xml` y build con `colcon` |
| URDF modular | `urdf/materials.xacro`, `irb120.macro.xacro`, `gripper.macro.xacro` | parseo del URDF expandido |
| Pinza acoplada | macro `parallel_gripper`, `gripper_mount` y `tcp_link` | presencia y cadena hasta `tcp_link` |
| Cinemática directa analítica | `kinematics/dh.py` | pruebas de postura cero y ortonormalidad |
| Sin MoveIt/resolvedor automático | implementación NumPy explícita | prueba de ausencia de dependencia MoveIt |
| Comparación RViz/TF vs. Python | nodo `fk_validator` | error publicado en `/irb120/fk_position_error_m` |
| Error menor a `1e-6 m` | tolerancia del nodo y CLI | 100 posturas aleatorias + 4 posturas documentadas |

## Evidencia reproducible

La verificación offline evalúa el URDF con un algoritmo independiente del
modelo DH:

```bash
PYTHONPATH=ros2_ws/src/irb120_hito1 \
python3 -m irb120_hito1.verify_model \
  --urdf ros2_ws/src/irb120_hito1/urdf/irb120_with_gripper.urdf
```

La evidencia ROS en vivo se obtiene con:

```bash
ros2 launch irb120_hito1 display.launch.py
ros2 topic echo /irb120/fk_position_error_m
```

Para la defensa conviene guardar una captura de RViz donde se vean el robot, los
frames y la salida `APROBADO` del nodo validador para al menos tres posturas.

## Pendiente para el gemelo visual definitivo

La cinemática del Hito 1 está completa. Falta sustituir las primitivas por la
geometría real. El archivo ideal es uno de estos formatos:

1. Paquete URDF/Xacro del IRB120 con meshes separados por `base_link` y
   `link_1...link_6` (`.dae` para visual y `.stl` para colisión), o
2. Ensamble STEP con cada eslabón como componente independiente, unidades y
   postura cero claramente indicadas.

También hace falta el modelo o las dimensiones reales de la pinza: distancia
`tool0 → TCP`, carrera, masa, centro de masa y orientación de montaje. Hasta
recibirlos, `0.160 m` y la geometría de la pinza son valores provisionales.

Al integrar los meshes se conservarán los joints y frames actuales; las pruebas
de cinemática impedirán que un cambio visual altere la pose matemática.
