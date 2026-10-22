# irb120_hito1

Paquete ROS 2 Jazzy para visualizar y mover las seis juntas de un ABB IRB 120 con pinza,
y para demostrar que la pose que dibuja RViz coincide con una implementación analítica
DH con error menor a `1e-6 m`.

Después de compilar y cargar `ros2_ws/install/setup.bash`:

```bash
# RViz + panel de control (deslizadores J1-J6, posturas, pasaporte en vivo y pruebas)
ros2 launch irb120_hito1 display.launch.py

# Demostración automática de seis ejes, sin panel
ros2 launch irb120_hito1 display.launch.py demo_motion:=true

# Sin panel (control solo desde otra terminal) o sin RViz
ros2 launch irb120_hito1 display.launch.py use_slider_gui:=false
ros2 launch irb120_hito1 display.launch.py use_rviz:=false

# Solo el panel, con los demás nodos ya en marcha
ros2 run irb120_hito1 control_panel

# Pasaporte offline reproducible y pruebas
ros2 run irb120_hito1 verify_model
colcon test --packages-select irb120_hito1 && colcon test-result --all
```

El TCP de la pinza se define solo en `config/tcp.yaml` (0.150 m, no medido en el robot).
Tras cambiarlo, regenerar `urdf/irb120.urdf` con `xacro urdf/irb120.urdf.xacro -o urdf/irb120.urdf`.

La documentación técnica completa está en `docs/hito1/` en la raíz del repositorio.
