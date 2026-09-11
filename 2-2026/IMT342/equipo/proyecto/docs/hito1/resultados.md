# Resultados de verificación

Última ejecución: 10 de septiembre de 2026. Entorno: Ubuntu 24.04 y ROS 2 Jazzy.

## Construcción real del workspace

La construcción se realizó desde `ros2_ws`, que es la raíz correcta del
workspace:

```bash
source /opt/ros/jazzy/setup.bash
cd ros2_ws
colcon build --symlink-install --packages-select irb120_hito1
```

Resultado: `1 package finished`, sin errores.

## Pruebas automatizadas

```bash
colcon test --packages-select irb120_hito1 --event-handlers console_direct+
colcon test-result --verbose
```

Resultado: `12 tests, 0 errors, 0 failures, 0 skipped`. Incluyen cinemática DH,
límites y continuidad de la demostración automática, y equivalencia URDF-DH
con 100 posturas pseudoaleatorias reproducibles. También verifican exactamente
seis joints revolutos, siete links contando `base_link`, y cero bloques
`fixed`, `inertial` o `collision`.

## Pasaporte offline

El comando `ros2 run irb120_hito1 verify_model` comparó dos implementaciones
independientes: producto matricial DH y recorrido de articulaciones del URDF
expandido. Para el examen se seleccionaron dos posturas justificadas para
`tool0`: una postura de trabajo y una postura plegada crítica.

```text
Máximo error posicional:      1.118863022828e-16 m
Máximo error de orientación:  4.209341455425e-16 rad
Límite del Hito 1:             1.000000000000e-06 m
RESULTADO: APROBADO
```

El error máximo es aproximadamente 8.9 mil millones de veces menor que el
límite solicitado.

## Validación ROS 2 en movimiento

Se ejecutaron simultáneamente `robot_state_publisher`, `joint_state_source`,
`motion_demo`, `fk_validator` y RViz. Las seis juntas se movieron de forma
cíclica. El validador procesó cada `JointState` mediante la tabla DH y mediante
la cadena URDF cargada también por RViz:

```text
Demostración automática activa: seis ejes en movimiento.
APROBADO | DH vs URDF | frame=tool0 |
error_pos=1.110e-16 m | limite=1.0e-06 m
```

Durante la observación continua no aparecieron falsos fallos de tolerancia. La
captura real está en `assets/rviz_irb120_demo_automatica.png`.

## Postura manual comprobada

Prueba A enviada en grados:

```text
[30, -20, 15, 40, -35, 60]
```

Transformación observada de `base_link` a `tool0`:

```text
Traslación [m]: [0.237055, 0.106212, 0.676427]
Cuaternión:     [0.388891, 0.306938, 0.723130, 0.481286]
RPY [grados]:   [58.110442, -15.485104, 104.068419]
Error DH-URDF [m]: 1.118863022828e-16
```

La prueba B usa `[90,-60,60,90,60,180]°`. Su `tool0` queda a `0.121409 m`
del eje de la base, por lo que representa una postura plegada de riesgo
geométrico. La detección formal de colisiones queda pendiente hasta recibir los
meshes de colisión del CAD.

## Herramientas disponibles

En esta computadora ya están instalados `colcon`, `xacro`, `rclpy`, NumPy,
`robot_state_publisher` y RViz 2. No queda una instalación pendiente para el
Hito 1.

## Pendiente que no afecta la calificación de hoy

Falta reemplazar las primitivas visuales por la geometría CAD real del ABB IRB
120. La cadena de seis juntas y el pasaporte de precisión están completos.
