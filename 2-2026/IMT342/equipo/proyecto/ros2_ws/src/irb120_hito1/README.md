# irb120_hito1

Paquete ROS 2 Jazzy para visualizar y mover un ABB IRB 120 con pinza, y para
demostrar que su cadena URDF coincide con una implementación analítica DH con
error menor a `1e-6 m`.

Después de compilar y cargar `ros2_ws/install/setup.bash`:

```bash
# Modelo quieto, preparado para comandos manuales
ros2 launch irb120_hito1 display.launch.py

# Demostración automática de seis ejes y pinza
ros2 launch irb120_hito1 display.launch.py demo_motion:=true

# Pasaporte offline reproducible
ros2 run irb120_hito1 verify_model
```

La documentación técnica completa está en `docs/hito1/` en la raíz del
repositorio.
