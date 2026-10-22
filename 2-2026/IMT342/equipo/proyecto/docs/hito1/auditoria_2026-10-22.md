# Auditoría del Hito 1 · 22/10/2026

Objetivo: contrastar la documentación del Hito 1 con su requisito oficial y con el
código de `ros2_ws/src/irb120_hito1`, porque este modelo es la base del Gate 2 de
ECI-3/4. La auditoría no modificó código, URDF, pruebas ni entregables.

## Fuentes de requisitos

- [Guía PFI](../../referencias/bibliografia/Guia_PFI.pdf), sección 4, Hito 1 (Semana 5):
  - *Entregable:* "Paquete de ROS con el URDF modular del ABB IRB 120 acoplado con la pinza."
  - *Pasaporte:* "La pose cartesiana [x, y, z] de RViz debe coincidir con la función
    analítica en Python, registrando un error ΔE < 10⁻⁶ m."
- Reglas generales aplicables: sección 2 (BOM: ROS Noetic/Humble, Python 3, NumPy),
  sección 3.1 (sin MoveIt ni resolvedores automáticos) y sección 6 (Conventional
  Commits; ramas `main`, `dev`, `feature/*`).
- No se encontró rúbrica ni worksheet propia del Hito 1 en `referencias/`, `archivo/` ni
  `archivos que hay que presentar/` (allí solo hay material del Hito 2 y de W12). La
  "worksheet de validación URDF" citada antes en `trazabilidad.md` no está en el
  repositorio.

## Método

- Lectura del código: `setup.py`, `package.xml`, Xacro/URDF, `kinematics/`, `nodes/`,
  `verify_model.py`, `launch/display.launch.py` y las 4 pruebas.
- `pytest` sobre el paquete: `15 passed`.
- `verify_model --urdf urdf/irb120.urdf`: máximo error posicional
  `1.022e-16 m`, orientación `3.72e-16 rad`, `APROBADO`.
- `check_urdf` sobre el URDF del último commit: cadena única
  `base_link → … → tool0 → gripper_link → gripper_tcp`.
- `display.launch.py demo_motion:=true use_rviz:=false` durante ~14 s:
  `/irb120/fk_tf_position_error_m` ≈ `3.7e-16 m`, `/irb120/fk_position_error_m` ≈
  `1.3e-16 m`, todas las líneas del log `APROBADO`.

Todas las ejecuciones de esta auditoría se hicieron con el TCP de 0.100 m (ver la sección final para las cifras vigentes). Durante la auditoría otro
trabajo en paralelo empezó a modificar `dh.py`, el Xacro y `fk_validator.py` para
unificar el TCP. Las cifras de `gripper_tcp` deben repetirse cuando termine ese cambio.
Las de `tool0` no dependen del TCP.

## Requisito → evidencia → estado

| # | Requisito | Evidencia | Estado | Acción |
|---|---|---|---|---|
| 1 | Paquete de ROS | `ros2_ws/src/irb120_hito1` (ament_python), 5 ejecutables en `setup.py` | cumple | — |
| 2 | Versión de ROS de la BOM (Noetic/Humble) | se usa ROS 2 Jazzy (Ubuntu 24.04) | parcial | declarar la desviación ante el docente; no afecta al cálculo |
| 3 | URDF modular | macro `irb120_robot` con `prefix` en `irb120.macro.xacro`; `irb120.urdf` generado | cumple | regenerar `irb120.urdf` tras cada cambio del Xacro (`scripts/check_proyecto.sh`) |
| 4 | Modelo del ABB IRB 120 (6 GDL) | 6 revolutas, límites del product spec, pose cero `tool0 = [0.374, 0, 0.630] m` (`test_dh`) | cumple | contrastar sentidos/offsets con referencia ABB (Gate 2) |
| 5 | Acoplado con la pinza | `gripper_link` + `gripper_tcp` con 2 juntas fijas, verificado por prueba estructural | parcial | la pinza es paramétrica; falta CAD real (SMC MHZ2-16D, ver `meshes/NOTICE.md`) y TCP medido |
| 6 | Pose `[x,y,z]` de RViz = función analítica Python | `fk_validator` compara DH con TF de `robot_state_publisher`; tópico `/irb120/fk_tf_position_error_m` | cumple | volver a capturar evidencia con RViz abierto tras alinear el TCP |
| 7 | `ΔE < 1e-6 m` | offline `1.02e-16 m` (2 posturas, `tool0` y `gripper_tcp`); 100 posturas aleatorias en pruebas (`tool0`); en vivo `~1e-16 m` | cumple | — |
| 8 | Sin MoveIt (sección 3.1) | NumPy propio; `test_package_does_not_depend_on_moveit` | cumple | — |
| 9 | Conventional Commits y ramas `main`/`dev`/`feature/*` | commits del Hito 1 de oct. sí siguen el formato (`feat(urdf): …`); otros no (`Actualizacion de hito 1…`); la rama actual es `proyectoHito3y4` | parcial | aplicar el formato en adelante; fuera del alcance de esta auditoría |
| 10 | Documentación coherente con el código | ver hallazgos | parcial → corregido en `docs/hito1/` | PDF/PPTX siguen desactualizados (pendiente del equipo) |
| 11 | Entregables PDF/PPTX vigentes | `entregables/hito1/` del 11/09/2026: describen URDF sin pinza, "0 juntas fijas", "0 collision", "12 tests" | no cumple | regenerar ambos archivos con el modelo actual |

## Hallazgos en la documentación

1. `trazabilidad.md` decía "sin ramas ni joints fijos" y a la vez "2 joints fixed" de la
   pinza. El URDF no tiene ramas, pero sí tiene 2 juntas fijas.
2. `trazabilidad.md` y `resultados.md` decían "no hay `inertial` ni `collision`" / "cero
   bloques `collision`". El URDF tiene 8 bloques `collision` y la prueba exige que
   existan. Solo `inertial` es cero.
3. Tópicos: los dos existen en `fk_validator.py`, pero miden cosas distintas.
   `/irb120/fk_position_error_m` compara DH con la cadena URDF evaluada por el propio
   parser. `/irb120/fk_tf_position_error_m` compara DH con el TF que dibuja RViz, que
   es el que corresponde al pasaporte. La sección "evidencia en vivo" solo mostraba el
   primero.
4. Pinza y TCP: "pruebas de estructura y de TCP". No hay prueba unitaria del TCP.
   `forward_kinematics_tcp` se importa en `test_urdf_matches_dh.py` pero no se usa. El
   TCP solo se compara en `verify_model` y `fk_validator`.
5. `resultados.md` mostraba un log con `frame=tool0` y sin `error_TF`. El launch
   configura `target_frame: gripper_tcp` y el log actual incluye `error_rot` y
   `error_TF`. Las cifras del pasaporte (`1.1189e-16 m`) eran de una versión anterior;
   la salida actual es `1.0222e-16 m`.
6. `modelo_cinematico.md` decía "el URDF contiene únicamente la cadena del brazo" y
   luego describía la pinza. También mencionaba un "cilindro de `link_1`", pero los
   meshes ya son CAD.
7. `guion_defensa.md`: "¿Por qué aparecen siete links?" (son 9) y "la dinámica requiere
   masas e inercias (Hito 2)", que atribuía al URDF algo que no contiene.
8. `docs/hito1/README.md` enlazaba el PDF/PPTX sin advertir que están desactualizados.
9. El comando `xacro …urdf.xacro` falla si no se carga `install/setup.bash`, porque el
   Xacro usa `$(find irb120_hito1)`. Ahora se indica en la documentación.
10. `ros2_ws/src/irb120_hito1/README.md` es correcto en comandos y ejecutables. No se
    modificó por la restricción sobre `ros2_ws/`.

## Correcciones aplicadas

- `trazabilidad.md`: tabla reescrita con origen de cada requisito (Guía PFI o criterio
  del equipo), árbol real de 9 links, `collision` presente, alcance real de las pruebas
  y ambos tópicos.
- `modelo_cinematico.md`: alcance (brazo + pinza, 9 links, 8 juntas), visuales CAD,
  prueba de encaje mesh-esqueleto, marca de TCP.
- `resultados.md`: conteo y contenido real de las 15 pruebas, salida de `verify_model` y
  log en vivo del 22/10/2026, distinción entre cifras de septiembre y actuales, aclaración
  de que `collision.py` pertenece al Hito 2.
- `guion_defensa.md`: número de links, `origin` del TCP, error TF, aviso sobre `xacro`.
- `README.md`: aviso sobre PDF/PPTX, tópicos de error, regeneración del URDF y sección
  "Puente hacia Hitos 3/4".

## Ubicaciones con cifra de TCP marcadas

Cada una lleva `<!-- TCP: pendiente de actualizar tras alineación -->`:

- `docs/hito1/README.md`: párrafo "En el código auditado el TCP…" (0.100 m vs 0.150 m)
  y viñeta "TCP" del puente.
- `docs/hito1/modelo_cinematico.md`: ecuación `T_TCP = T_DH · Tz(z_TCP)`, `z_TCP = 0.100 m`.
- `docs/hito1/resultados.md`: encabezado (ejecuciones con TCP 0.100 m).
- `docs/hito1/auditoria_2026-10-22.md`: sección "Método".

`trazabilidad.md` y `guion_defensa.md` no contienen cifras de TCP.

## Pendientes que requieren al equipo

1. Regenerar `entregables/hito1/pdf/…CORREGIDA.pdf` y
   `entregables/hito1/presentation/…FINAL.pptx` con el modelo actual: pinza,
   `collision` CAD, 15 pruebas, error TF y TCP alineado.
2. Tras la alineación del TCP: regenerar `urdf/irb120.urdf` desde el Xacro, ejecutar
   `colcon test` y `verify_model`, y actualizar las cifras de `gripper_tcp` y las marcas
   TCP de estos documentos.
3. Capturar de nuevo `assets/*.png` con RViz mostrando el CAD y la pinza. Las capturas
   actuales son de septiembre.
4. Agregar una prueba unitaria que compare `gripper_tcp` del URDF con
   `forward_kinematics_tcp`, y otra que verifique que `irb120.urdf` coincide con la
   expansión del Xacro. Son cambios de código, fuera del alcance de esta auditoría. Al
   cierre de la auditoría apareció en el árbol de trabajo
   `test/test_tcp_and_reference.py` (trabajo en paralelo): comprobar si cubre este
   punto y actualizar el conteo de "15 pruebas" en `resultados.md` y `guion_defensa.md`.
5. Declarar ante el docente el uso de ROS 2 Jazzy en lugar de Noetic/Humble.
6. Gate 2: referencia ABB para sentidos, offsets, marco base y `tooldata`
   (`kinematics_reference: null` en `model_manifest.yaml`).

## Actualización posterior (22/10/2026, después de la auditoría)

Resuelto en el código y en estos documentos:

- **TCP unificado** en 0.150 m desde `config/tcp.yaml` (Xacro, DH, validador e Hito 2); sigue sin medirse en la pinza real.
- **Panel de deslizadores:** el panel Tk no abría porque `tkinter` no está disponible para el Python 3.12 de ROS Jazzy en esta instalación (el `python3-tk` del sistema es para Python 3.14). Se reemplazó por un panel Qt (`python_qt_binding`, como RViz) que además muestra el pasaporte en vivo (TF de RViz frente a DH) y una pestaña de pruebas.
- **Pendiente 4:** `test_tcp_and_reference.py` cubre el TCP; `test_urdf_expansion.py` verifica que `irb120.urdf` es la expansión del Xacro.
- **Avisos de `colcon build`:** se retiró `tests_require` de ambos paquetes.
- **Cifras vigentes:** `colcon test` 38/38; `verify_model` 206/206 comparaciones, `e_p ≤ 3.5e-16 m`; pasaporte contra el TF de RViz 3/3 con `ΔE ≤ 3.9e-16 m`. Detalle en [resultados](resultados.md).

Siguen pendientes los puntos 1 (PDF/PPTX), 3 (capturas de RViz), 5 (Jazzy ante el docente) y 6 (referencia ABB para el Gate 2).
