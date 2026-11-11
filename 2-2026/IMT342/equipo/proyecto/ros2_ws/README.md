# ROS 2 · ABB IRB 120

Entrada única desde la carpeta `proyecto/`:

Para conectar y ejecutar cada ensayo, abrir la [guía única de comandos de laboratorio](../docs/conexion_abb/COMANDOS_LABORATORIO.md).

La prueba física actual de J6 usa [RWS + RAPID con confirmación local](../docs/conexion_abb/PRUEBA_J6_RWS_RAPID.md): `./iniciar.sh rws_j6 inspeccionar`, `actualizar_modulo`, `comprobar_recepcion`, `preparar`, `observar` y `limpiar`. Está en `src/irb120_control/irb120_control/rws_j6.py`; el módulo corregido en `src/irb120_control/rapid/rws_j6/`. **El intento del 10/11 no consiguió movimiento:** recepción/transferencia verificadas, 584 muestras sin desplazamiento, último modo confirmado AUTO y ejecución local sin comprobar. El objetivo podría seguir pendiente. [Diagnóstico y siguiente ensayo](../docs/conexion_abb/CIERRE_PRUEBA_J6_2026-11-10.md).

```bash
# Comprobar el enlace:
bash ros2_ws/iniciar.sh enlace --ping

# Gemelo y panel de comunicación (prueba ya reportada exitosa por el equipo):
bash ros2_ws/iniciar.sh comunicacion --host 192.168.125.1 --user "Default User" --ignore-joint-state

# Gemelo, comunicación y comparación de la FK propia frente al ABB:
bash ros2_ws/iniciar.sh validar_fk --host 192.168.125.1 --user "Default User" --ignore-joint-state
```

El arranque carga Jazzy y `~/ros_py312`, sin necesitar `colcon` ni `ros2 launch` en esta PC. La contraseña se pide una vez en la terminal y no se guarda.

## Dónde trabajar

| Carpeta | Responsabilidad |
|---|---|
| `src/irb120_conexion/` | **Conexión física actual**: nodos de lectura, monitor y validación FK, arranques y protocolos GET |
| `src/irb120_control/` | **Ensayo articular desde RViz**: demo UDP, vista RWS/recepción EGM sin envío, supervisor y salida EGM condicionada a ficha/GO |
| `src/irb120_hito1/` | **Modelo propio y simulación**: DH, URDF/Xacro, meshes, configuración TCP, panel de simulación y validadores |
| `src/irb120_hito2/` | Integración ROS anterior del Hito 2; se conserva por compatibilidad. El desarrollo matemático vigente también está en `../hito2/` |
| `build/`, `install/`, `log/` | Archivos generados de compilaciones. No editar ni mover como si fueran código fuente |

La implementación antes repartida en `../scripts/` se trasladó a `irb120_conexion`. Los nombres antiguos de Python y shell quedan como entradas de compatibilidad; no contienen una segunda implementación.

Abrir [la estructura por nodos](src/irb120_conexion/README.md) y [la guía de validación FK](../docs/conexion_abb/VALIDACION_FK_EN_VIVO.md).

La etapa posterior está descrita en el [plan de control EGM → IK propia → visión](../docs/hitos_3_4/PLAN_CONTROL_EGM_IK_VISION.md). El [paquete irb120_control](src/irb120_control/README.md) ya implementa el ensayo individual J1–J6 y su demo EGM local. EGM físico aún no está probado. `comunicacion` y `validar_fk` siguen siendo de lectura.

Desde esta carpeta `ros2_ws/`, ejecutar `./iniciar.sh control_demo` para probar los controles nativos de RViz sin robot. Para la salida física revisar la ficha y la guía del paquete; abrir RViz no habilita movimiento por sí solo.
