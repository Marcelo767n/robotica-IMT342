"""Panel del IRB 120: mover el robot real desde RViz por RWS (mismo canal que rws_mover).

Módulos (de abajo arriba):
  limites.py         límites articulares con margen y validación de un objetivo
  cinematica.py      cinemática directa e inversa (Pieper, Hito 2) para poses en mm y grados
  simulado.py        robot ficticio con la interfaz de Mover (practicar sin conexión)
  estado.py          Panel: objetivo, lectura del robot, envío en segundo plano, registro
  ordenes.py         órdenes JSON del panel de RViz → Panel, y estado JSON de vuelta (sin ROS)
  conexion.py        abrir y cerrar la sesión RWS con el controlador
  puente_ros.py      nodo ROS 2: posturas para RViz y tópicos /irb120/panel/estado|orden
  rviz_controles.py  marcador 3D arrastrable (cinemática inversa) y menú de clic derecho
  vista.py           configuración de RViz y procesos robot_state_publisher / rviz2
  web.py             página local opcional (--web)
  arranque.py        punto de entrada: ./iniciar.sh panel
El panel de RViz en C++ está en ros2_ws/src/irb120_rviz_panel.
"""
