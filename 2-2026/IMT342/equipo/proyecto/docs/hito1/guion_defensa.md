# Guion de defensa del Hito 1 corregido

## Preparación

```bash
cd /home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select irb120_hito1
source install/setup.bash
colcon test --packages-select irb120_hito1
colcon test-result --verbose
ros2 run irb120_hito1 verify_model
```

Resultado esperado: `12 tests, 0 errors, 0 failures, 0 skipped` y
`RESULTADO: APROBADO`.

## Explicación sugerida

### 1. Estructura

“El URDF corregido tiene seis juntas revolutas y seis marcos móviles. El árbol
es `base_link → link_1 → link_2 → link_3 → link_4 → link_5 → tool0`. El marco
base es necesario para conectar las seis juntas, pero no cuenta como junta. No
hay frames auxiliares ni joints fijos.”

Para demostrarlo:

```bash
xacro src/irb120_hito1/urdf/irb120.urdf.xacro -o /tmp/irb120.urdf
check_urdf /tmp/irb120.urdf
```

### 2. Conversión DH a URDF

“DH clásico usa `A_i=Rz(q_i)Tz(d_i)Tx(a_i)Rx(alpha_i)`. URDF usa
`T_i=origin_i·Rz(q_i)`. Definimos `B_i=Tz(d_i)Tx(a_i)Rx(alpha_i)` y colocamos
el `B_i` de una fila en el `origin` de la junta siguiente. Los offsets `-pi/2`
de J2 y `+pi` de J6 se combinaron dentro de esos origins. Así conservamos el
mismo producto total con solamente seis joints.”

### 3. Geometría frente a física

“Los números de `<visual><origin>` solo centran las figuras primitivas en RViz.
No crean frames ni cambian la cinemática. Retiramos `<inertial>` y `<collision>`
porque este hito no simula dinámica ni tiene todavía el CAD de colisión.”

### 4. Cálculo del error

“Para exactamente la misma `q`, una ruta calcula `T_DH` multiplicando las seis
matrices DH y otra recorre el XML URDF. El error de posición es
`||p_DH-p_URDF||₂`. El error de orientación es el ángulo de la rotación relativa
`R_DHᵀR_URDF`. El límite de aprobación es `1e-6 m`.”

### 5. Razón de las dos pruebas

- Prueba A: `[30,-20,15,40,-35,60]°`. Activa los seis ejes, evita la simetría
  de cero y representa una postura elevada de trabajo.
- Prueba B: `[90,-60,60,90,60,180]°`. Activa los seis ejes y pliega el robot;
  `tool0` queda a `0.121409 m` del eje de la base. Es una configuración crítica
  para revisar riesgo geométrico de colisión.

“Todavía no afirmamos detección automática de colisión: para eso faltan meshes
de colisión del CAD y el modelo del entorno.”

## Demostración gráfica

```bash
ros2 launch irb120_hito1 display.launch.py
```

Se abren RViz y un panel con seis sliders, además de botones `Cero`, `Prueba A`
y `Prueba B`. Al pulsar cada prueba, la terminal debe continuar mostrando
`APROBADO | DH vs URDF`.

## Preguntas probables

**¿Por qué aparecen siete links si son seis marcos?** Porque una cadena de seis
juntas necesita un padre base y seis hijos móviles: `base_link` más seis marcos.

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
La dinámica y la detección de colisiones requieren modelos adicionales.
