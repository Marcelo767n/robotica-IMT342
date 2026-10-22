# Resultados de verificación

Entorno: Ubuntu, ROS 2 Jazzy, Python 3.12 del sistema. Primera ejecución completa: 10 de
septiembre de 2026. Ejecución vigente: 22 de octubre de 2026, con el TCP unificado en
0.150 m (`config/tcp.yaml`, no medido en la pinza real) y el panel Qt. Las cifras de la
[auditoría](auditoria_2026-10-22.md) se tomaron antes con TCP de 0.100 m.

## Construcción del workspace

```bash
source /opt/ros/jazzy/setup.bash
cd ros2_ws
colcon build --symlink-install
```

Resultado del 22/10/2026: `2 packages finished`, sin salida en stderr (se retiró la
opción obsoleta `tests_require`, que producía el aviso `Unknown distribution option`).

## Pruebas automatizadas

```bash
colcon test --packages-select irb120_hito1
colcon test-result --all
```

Resultado del 22/10/2026: `38 tests, 0 errors, 0 failures, 0 skipped`.

| Archivo | Pruebas | Qué cubre |
|---|---|---|
| `test_dh.py` | 4 | pose cero `[0.374, 0, 0.630] m`, seis filas DH, ortonormalidad, rechazo de vectores mal formados |
| `test_urdf_matches_dh.py` | 6 | estructura del URDF (6 revolutas + 2 fijas de la pinza, 9 links, sin `inertial`, 8 `visual` y 8 `collision`), un `origin` por grado de libertad, sin MoveIt, equivalencia DH-URDF en 100 posturas |
| `test_tcp_and_reference.py` | 11 | TCP único (YAML = DH = URDF = Hito 2, `verified_on_robot: false`); brida `tool0` contra el modelo oficial ROS-Industrial: pose cero, 100 posturas, orden, límites y sentidos de los ejes |
| `test_urdf_expansion.py` | 1 | el `irb120.urdf` versionado es la expansión actual del Xacro |
| `test_validation.py` | 6 | batería DH vs URDF, posturas aleatorias reproducibles y dentro de límites, RPY con convención URDF, `verify_model` devuelve 0/1 |
| `test_control_panel.py` | 5 | panel Qt sin pantalla: seis deslizadores con límites oficiales, posturas, sincronía deslizador-caja, demo, batería |
| `test_slider_controls.py` | 3 | límites y saturación de los comandos |
| `test_motion.py` | 2 | continuidad de la demostración automática |

## Pasaporte offline

`ros2 run irb120_hito1 verify_model` compara dos implementaciones independientes
(producto matricial DH y recorrido del URDF expandido) para `tool0` y `gripper_tcp`:
tres posturas justificadas en detalle y la batería completa con 100 posturas
aleatorias (semilla 342). Salida del 22/10/2026:

```text
Prueba Cero - posición de calibración  gripper_tcp p_DH = [0.524000, 0.000000, 0.630000] m   e_p = 4.85e-17 m
Prueba A - postura de trabajo           gripper_tcp p_DH = [0.365738, 0.116648, 0.752793] m   e_p = 0
Prueba B - postura plegada crítica      gripper_tcp p_DH = [-0.192258, 0.179173, 0.495000] m  e_p = 7.85e-17 m

Batería completa: 206 comparaciones (3 justificadas + 100 aleatorias, x2 frames); 206 dentro de tolerancia.
Máximo error posicional: 3.521787733787e-16 m
Máximo error de orientación: 1.096080205797e-15 rad
RESULTADO: APROBADO
```

## Pasaporte en vivo contra RViz

El requisito compara la pose **de RViz** con la función analítica. RViz dibuja el árbol
TF que publica `robot_state_publisher`, así que la comparación se hace sobre ese TF, en
el mismo instante del `JointState`:

- `fk_validator` publica `/irb120/fk_tf_position_error_m`. Extracto del 22/10/2026
  (sin RViz, mismos nodos):

  ```text
  APROBADO | DH vs URDF | frame=gripper_tcp | error_pos=0.000e+00 m | error_rot=3.719e-16 rad | error_TF=1.755e-16 m | limite=1.0e-06 m
  ```

- El panel, pestaña **Batería de pruebas → Verificar posturas en RViz**, mueve el gemelo a
  las tres posturas justificadas y mide `ΔE` en el TF:

  | Postura | `p` RViz `gripper_tcp` [mm] | `ΔE` TF [m] | Resultado |
  |---|---|---|---|
  | Cero | 524.000, 0.000, 630.000 | 2.709e-16 | APROBADO |
  | A | 365.738, 116.648, 752.793 | 1.755e-16 | APROBADO |
  | B | -192.258, 179.173, 495.000 | 3.856e-16 | APROBADO |

- Durante la demostración automática el indicador del panel se mantuvo en `APROBADO`
  en todas las muestras (10 lecturas cada 0.23 s).

Capturas del panel: [`assets/panel_control.png`](assets/panel_control.png) y
[`assets/panel_pruebas.png`](assets/panel_pruebas.png), generadas con el panel real
conectado a los nodos (render sin pantalla, `QT_QPA_PLATFORM=offscreen`). Las capturas
de RViz `assets/rviz_irb120_*.png` son de septiembre y no muestran la pinza ni el CAD
actuales; conviene rehacerlas.

## Referencia independiente

En `tool0` el modelo coincide con el modelo oficial ROS-Industrial
(`hito2/irb120/rosi_model.py`) en 106 posturas: `e_p ≤ 2.48e-16 m`,
`e_R ≤ 1.18e-15 rad`. Evidencia:
[`fk_hito1_vs_rosi.csv`](../conexion_abb/evidencias/fk_hito1_vs_rosi.csv), generada por
`scripts/comparar_fk_hito1_rosi.py`. Los marcos intermedios `link_1`…`link_5` no son
comparables uno a uno (el Hito 1 usa marcos DH; ROS-I, marcos alineados con la base).

## Postura manual comprobada

Prueba A en grados: `[30, -20, 15, 40, -35, 60]`. Transformación `base_link → tool0`
(independiente del TCP):

```text
Traslación [m]: [0.237055, 0.106212, 0.676427]
Cuaternión:     [0.388891, 0.306938, 0.723130, 0.481286]
RPY [grados]:   [58.110442, -15.485104, 104.068419]
```

Con el TCP de 0.150 m, `gripper_tcp` queda en `[0.365738, 0.116648, 0.752793] m` con la
misma orientación.

La prueba B usa `[90,-60,60,90,60,180]°`. Su `tool0` queda a `0.121409 m` del eje de la
base: es una postura plegada de riesgo geométrico. `irb120_hito2/kinematics/collision.py`
(meshes `collision` del CAD, margen de 5 mm) comprueba en
`irb120_hito2/test/test_collision.py` que cero, A y B no presentan autocolisión ni
contacto con la mesa. Es una prueba conservadora de proximidad entre nubes de puntos y
pertenece al Hito 2.

## Geometría CAD

Los meshes `visual` y `collision` del brazo derivan del CAD del IRB 120 publicado por
ROS-Industrial (Apache-2.0), re-expresados en los marcos del URDF con
`scripts/import_cad.py`; la atribución está en `meshes/NOTICE.md`. La pinza sigue
siendo un modelo paramétrico propio; su CAD real y la medición de su TCP están
pendientes.
