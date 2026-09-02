# irb120_hito1

Paquete ROS 2 Jazzy para visualizar el ABB IRB 120 con pinza y demostrar que su
cadena TF coincide con una implementación independiente de cinemática directa
DH por debajo de `1e-6 m`.

Desde la raíz del proyecto, ejecuta `./scripts/check_hito1.sh` y luego:

```bash
source ros2_ws/install/setup.bash
ros2 launch irb120_hito1 display.launch.py
```

La documentación técnica completa está en `docs/hito1/`.
