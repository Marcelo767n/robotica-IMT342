# Guion de defensa del Hito 1

## Preparación antes de entrar al aula

1. Enciende la computadora y abre una terminal.
2. Comprueba que existe `/opt/ros/jazzy/setup.bash`.
3. Entra a la raíz del proyecto y compila desde `ros2_ws`.
4. Ejecuta las pruebas y guarda visible el resultado `9 tests`.
5. Cierra otros programas pesados y prueba RViz una vez.

Comandos exactos:

```bash
cd /home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto
source /opt/ros/jazzy/setup.bash
cd ros2_ws
colcon build --symlink-install --packages-select irb120_hito1
source install/setup.bash
colcon test --packages-select irb120_hito1 --event-handlers console_direct+
colcon test-result --verbose
ros2 run irb120_hito1 verify_model
```

## Exposición sugerida de 7 minutos

### Minuto 0 a 1: objetivo

“El Hito 1 pide un paquete ROS con el ABB IRB 120 y una pinza, modelado de
forma modular en URDF/Xacro. Además, la pose cartesiana debe coincidir con una
cinemática directa analítica con error menor a un micrómetro. No utilicé MoveIt.”

### Minuto 1 a 2: estructura

“El workspace se llama `ros2_ws` y el paquete `irb120_hito1`. Separé la tabla
DH y sus operaciones matemáticas, el evaluador URDF, los nodos ROS, los macros
Xacro, el archivo de lanzamiento, la configuración de RViz y las pruebas. Esta
separación permite cambiar la geometría CAD sin tocar la cinemática.”

### Minuto 2 a 3: URDF y Xacro

“URDF describe un árbol de enlaces rígidos llamados links y articulaciones
llamadas joints. Xacro permite dividir ese XML en macros reutilizables. El macro
del robot crea los seis ejes; el macro de la pinza añade el montaje, dos dedos y
el TCP. El archivo principal los une.”

### Minuto 3 a 4: cinemática

“Usé Denavit-Hartenberg clásico. Cada fila realiza rotación Z, traslación Z,
traslación X y rotación X. Como URDF solo permite un origen y un movimiento por
joint, descompuse cada fila en un joint móvil y frames fijos para conservar
exactamente la misma transformación.”

### Minuto 4 a 5: ROS 2

“El nodo `joint_state_source` publica `/joint_states`. `robot_state_publisher`
lee esos estados y el URDF para publicar TF. RViz dibuja el robot a partir de
esa información. `motion_demo` manda posturas suaves. `fk_validator` calcula la
misma pose por dos rutas independientes y publica el error.”

### Minuto 5 a 6: prueba en vivo

Ejecuta:

```bash
ros2 launch irb120_hito1 display.launch.py demo_motion:=true
```

Mientras el robot se mueve, señala:

- Los seis eslabones naranjas y la pinza.
- Los frames de colores.
- La línea `APROBADO | DH vs URDF` en la terminal.
- El límite `1.0e-06 m` y el error del orden de `1e-16 m`.

Detén con `Ctrl+C`.

### Minuto 6 a 7: resultado y límite actual

“Las nueve pruebas pasan. En cuatro posturas documentadas, el máximo error fue
`2.220446049250e-16 m`, aproximadamente 4.5 mil millones de veces menor que la
tolerancia. Hoy la forma exterior es provisional porque falta el CAD; eso no
afecta los joints, los frames ni la cinemática ya validada.”

## Demostración manual opcional

Terminal 1:

```bash
source /opt/ros/jazzy/setup.bash
cd /home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/ros2_ws
source install/setup.bash
ros2 launch irb120_hito1 display.launch.py
```

Terminal 2:

```bash
source /opt/ros/jazzy/setup.bash
cd /home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/ros2_ws
source install/setup.bash
ros2 topic pub --once /irb120/joint_commands_deg std_msgs/msg/Float64MultiArray \
  "{data: [30.0, -20.0, 15.0, 40.0, -35.0, 60.0, 0.010]}"
```

## Preguntas probables y respuestas cortas

**¿Qué es ROS 2?**  Es una infraestructura para comunicar procesos robóticos.
Los nodos intercambian mensajes mediante tópicos y otros mecanismos.

**¿Qué es un workspace?**  Es una carpeta que contiene paquetes fuente y las
carpetas generadas por la compilación.

**¿Qué es URDF?**  Es un XML que describe la estructura del robot: links,
joints, geometría, límites y propiedades físicas.

**¿Por qué Xacro?**  Evita repetir XML, permite macros y parámetros, y mejora la
modularidad.

**¿Qué es TF?**  Es el sistema de ROS que mantiene transformaciones entre
frames a lo largo del tiempo.

**¿Qué es RViz?**  Es un visualizador 3D; no simula fuerzas ni controla por sí
mismo al robot.

**¿Qué es Denavit-Hartenberg?**  Es una convención para representar cada
transformación entre eslabones con cuatro parámetros.

**¿Cómo se calculó el error?**  Con la norma euclidiana entre las posiciones
cartesianas obtenidas por el producto DH y por la cadena URDF.

**¿Por qué el error no es exactamente cero?**  Por redondeo de punto flotante;
un error cercano a `1e-16 m` es ruido numérico, no una diferencia física.

**¿Se usó MoveIt?**  No. La cinemática directa y el recorrido URDF están
implementados explícitamente con Python y NumPy.

**¿El modelo ya controla un robot físico?**  No. Este hito valida la estructura
cinemática del gemelo digital. Para control real faltan integración con el
controlador ABB, seguridad y parámetros dinámicos certificados.

**¿Qué CAD debo conseguir?**  Preferentemente URDF/Xacro con meshes por
eslabón, `.dae` visual y `.stl` de colisión. Como alternativa, STEP con cada
eslabón separado, unidades claras y postura cero indicada.
