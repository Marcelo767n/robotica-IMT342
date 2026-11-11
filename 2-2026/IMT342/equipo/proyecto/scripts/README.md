# Utilidades y compatibilidad

El código ROS físico vigente está organizado por nodos en [irb120_conexion](../ros2_ws/src/irb120_conexion/README.md).

Los archivos `abb_lectura_rws.py`, `abb_rws_joint_bridge.py`, `monitor_comunicacion.py`, `escuchar_joint_states.py`, `preparar_gemelo.py`, `prueba_comunicacion.py` y `g1_verificar_enlace.py` son entradas pequeñas de compatibilidad. Ejecutan la única implementación situada en el paquete nuevo para conservar los comandos y las pruebas existentes. Editar el paquete, no estos archivos.

`prueba_comunicacion.sh` y `gemelo_rviz.sh` conservan los arranques conocidos. La entrada recomendada es ahora `bash ros2_ws/iniciar.sh comunicacion ...` o `bash ros2_ws/iniciar.sh validar_fk ...`, desde la raíz del proyecto.

Las herramientas CAD (`generate_meshes.py`, `import_cad.py`, `import_gripper_cad.py`), el contraste offline `comparar_fk_hito1_rosi.py` y `check_proyecto.sh` permanecen como utilidades de desarrollo. `tests/` conserva las regresiones y compatibilidad; las pruebas nuevas de FK están dentro del paquete ROS.
