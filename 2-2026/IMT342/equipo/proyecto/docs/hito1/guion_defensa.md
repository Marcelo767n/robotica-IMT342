# Guion de defensa del Hito 1 corregido

## Preparación

```bash
cd <ruta-del-repo>/2-2026/IMT342/equipo/proyecto/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select irb120_hito1
source install/setup.bash
colcon test --packages-select irb120_hito1
colcon test-result --verbose
ros2 run irb120_hito1 verify_model
```

Resultado esperado: `15 tests, 0 errors, 0 failures, 0 skipped` y
`RESULTADO: APROBADO`.

## Explicación sugerida

### 1. Estructura

“El URDF corregido tiene seis juntas revolutas y seis marcos móviles. El árbol
es `base_link → link_1 → … → link_5 → tool0`, y de `tool0` cuelgan la pinza
(`gripper_link`) y su punto de agarre `gripper_tcp` mediante dos juntas fijas, que
no son grados de libertad. Cada una de las seis juntas revolutas tiene un único
`origin`; el séptimo `origin` del archivo es el offset fijo del TCP.”

Para demostrarlo:

```bash
xacro src/irb120_hito1/urdf/irb120.urdf.xacro -o /tmp/irb120.urdf
check_urdf /tmp/irb120.urdf
```

(`xacro` necesita `install/setup.bash` cargado porque el archivo usa
`$(find irb120_hito1)`. `check_urdf` debe mostrar una sola rama de 9 links.)

### 2. Conversión DH a URDF

“DH clásico usa `A_i=Rz(q_i)Tz(d_i)Tx(a_i)Rx(alpha_i)`. URDF usa
`T_i=origin_i·Rz(q_i)`. Definimos `B_i=Tz(d_i)Tx(a_i)Rx(alpha_i)` y colocamos
el `B_i` de una fila en el `origin` de la junta siguiente. Los offsets `-pi/2`
de J2 y `+pi` de J6 se combinaron dentro de esos origins. Así conservamos el
mismo producto total con solamente seis joints.”

### 3. Geometría frente a física

“Hay un único `origin` por grado de libertad. Los visuales son meshes STL ya
dibujados en el marco de su eslabón, así que no llevan `origin`. La pinza se
acopla con dos juntas fijas que no son grados de libertad. Retiramos `<inertial>`
porque este hito no simula dinámica; los `<collision>` usan meshes simplificados
del CAD del brazo y el modelo paramétrico de la pinza.”

### 4. Cálculo del error

“Para exactamente la misma `q`, una ruta calcula `T_DH` multiplicando las seis
matrices DH y otra recorre el XML URDF. El error de posición es
`||p_DH-p_URDF||₂`. El error de orientación es el ángulo de la rotación relativa
`R_DHᵀR_URDF`. El límite de aprobación es `1e-6 m`. En vivo, `fk_validator`
compara además la pose DH con el TF que publica `robot_state_publisher`, que es la
pose que dibuja RViz; ese error se publica en `/irb120/fk_tf_position_error_m`.”

### 5. Razón de las dos pruebas

- Prueba A: `[30,-20,15,40,-35,60]°`. Activa los seis ejes, evita la simetría
  de cero y representa una postura elevada de trabajo.
- Prueba B: `[90,-60,60,90,60,180]°`. Activa los seis ejes y pliega el robot;
  `tool0` queda a `0.121409 m` del eje de la base. Es una configuración crítica
  para revisar la proximidad a la base.

“La autocolisión se evalúa con los meshes `collision` del CAD en
`irb120_hito2/kinematics/collision.py`; RViz no detecta colisiones.”

## Demostración gráfica

```bash
ros2 launch irb120_hito1 display.launch.py
```

Se abren RViz y el panel de control. Orden sugerido ante el docente:

1. Mover un deslizador (por ejemplo J2) y mostrar que RViz sigue al panel.
2. Señalar a la derecha la tabla "DH analítica" frente a "RViz (TF)", el valor `ΔE`
   y el indicador `APROBADO` contra `1e-6 m`: ese es el pasaporte del Hito 1.
3. Pulsar `Prueba A` y `Prueba B`; explicar por qué se eligieron.
4. Pestaña **Batería de pruebas → Verificar posturas en RViz** (3/3 aprobadas) y
   **Ejecutar batería** (206/206 comparaciones DH vs URDF). Con doble clic sobre una
   fila, el robot va a esa postura.
5. Marcar la demostración automática: el indicador sigue en `APROBADO` en movimiento.

En la terminal, `fk_validator` sigue mostrando
`APROBADO | DH vs URDF | frame=gripper_tcp | ... | error_TF=...`.

## Preguntas probables

**¿Por qué aparecen nueve links si son seis marcos móviles?** Una cadena de seis
juntas necesita un padre base y seis hijos móviles: `base_link` más `link_1`…`link_5`
y `tool0` (siete links). Los dos restantes, `gripper_link` y `gripper_tcp`, son la
pinza y su punto de agarre, unidos con juntas fijas.

**¿Qué significa `xyz` en el origin de una junta?** Es la traslación fija desde
el frame padre hasta el eje de la siguiente junta, expresada en metros.

**¿Qué significa `rpy`?** Roll, pitch y yaw fijos del `origin`, en radianes. ROS
forma la rotación como `Rz(yaw)Ry(pitch)Rx(roll)`.

**¿Por qué todos los ejes dicen `0 0 1`?** Porque DH define cada variable
articular como una rotación alrededor del eje Z local. Los origins orientan ese
Z local para que coincida con cada eje físico del ABB.

**¿Por qué el error es cercano a `1e-16` y no cero?** Por redondeo numérico de
punto flotante; está muy por debajo de `1e-6 m`.

**¿RViz simula física o detecta colisiones?** No. RViz visualiza el URDF y TF.
Una simulación dinámica requeriría masas e inercias, que este URDF no contiene; las
colisiones se evalúan con el verificador propio del Hito 2 (`collision.py`).
