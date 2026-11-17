# irb120_rviz_panel

Plugin de RViz2 en C++ que añade el panel **«IRB 120»**: muestra el estado del robot, permite editar los ángulos J1–J6 o una pose cartesiana (con cinemática inversa) y enviar el objetivo al robot. **El panel no habla con el robot**: solo intercambia texto con el nodo Python `irb120_panel_rws`.

## Compilar

Una vez, o tras cambiar los fuentes (requiere ROS 2 Jazzy):

```bash
cd ros2_ws
./brazo.sh compilar     # equivale a: colcon build --packages-select irb120_rviz_panel
```

## Usar

```bash
./brazo.sh panel        # robot real
./brazo.sh simulado     # sin robot, para practicar
```

Abre RViz con el panel y el control 3D. Si el panel no está compilado, `arranque.py` lo avisa y quedan el control 3D y `--web`. Detalle del uso: [COMO_FUNCIONA.md §7](../../../docs/conexion_abb/COMO_FUNCIONA.md) y [MOVER_DESDE_PC.md](../../../docs/conexion_abb/MOVER_DESDE_PC.md).

## Cómo se comunica

Dos tópicos `std_msgs/String` con un JSON cada uno (sin mensajes propios):

| Tópico | Sentido | Contenido |
|---|---|---|
| `/irb120/panel/estado` | nodo a panel | Modo, motores, RAPID, ángulos medidos y objetivo, pose, ramas de IK, registro |
| `/irb120/panel/orden` | panel a nodo | `{"id", "accion", ...}`; acciones `objetivo`, `ik`, `enviar`, `cancelar`, `sincronizar`, `paso`, `herramienta`, `terminar` |

`iniciar.sh` limita el descubrimiento ROS a `localhost` en el modo `panel`, de modo que otras máquinas de la red no pueden publicar órdenes. Los envíos al robot piden confirmación.

## Archivos fuente (`src/`)

| Archivo | Papel |
|---|---|
| `panel_irb120.cpp/.hpp` | Ventana principal: compone los bloques y las acciones (enviar, cancelar, terminar), con cuadros de confirmación |
| `widget_estado.cpp/.hpp` | Bloque «Estado del robot»: modo, motores, RAPID, servidor, módulo y lo que falta |
| `widget_ejes.cpp/.hpp` | Bloque «Ángulos J1–J6»: medido, objetivo (casilla y deslizador) y cambio por eje |
| `widget_pose.cpp/.hpp` | Bloque de pose cartesiana: punto de referencia (TCP o brida), pose pedida y tabla de ramas de Pieper |
| `cliente_ros.cpp/.hpp` | Suscripción a `/irb120/panel/estado` y publicación en `/irb120/panel/orden` |
| `json_util.hpp` | Lectura tolerante del JSON (cualquier clave puede faltar o ser `null`) |

Registro del plugin: `plugins_description.xml`. Dependencias: `rclcpp`, `rviz_common`, `pluginlib`, `std_msgs`, Qt5 (ver `package.xml`).
