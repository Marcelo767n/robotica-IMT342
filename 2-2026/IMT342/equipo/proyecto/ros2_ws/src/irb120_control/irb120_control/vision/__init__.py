"""Visión → buzón de puntos del panel. Esto es solo el cimiento: la cámara aún no está definida.

El nodo de visión debe publicar en `/irb120/trayectoria/punto_externo` un geometry_msgs/PoseStamped con
`frame_id = 'base_link'`, posición en metros y orientación como cuaternión. La pose es la del TCP del proyecto
(150 mm sobre z de la brida), no la de tool0. El panel rechaza otros marcos (no usa TF), las poses no finitas y las
que la cinemática inversa no alcanza; lo aceptado entra al buzón con origen 'vision' y el Estudio lo recoge.

Cómo llegar a base_link según dónde vaya la cámara:
  - Cámara fija (eye-to-hand): T_base_cam se obtiene UNA vez con calibración mano-ojo (AX = XB, p. ej. con un
    tablero que lleva el robot) y la pose del objeto es  T_base_obj = T_base_cam · T_cam_obj.
  - Cámara en la pinza (eye-in-hand): T_base_cam = FK(q) · T_tool0_cam, donde T_tool0_cam sale de la calibración
    mano-ojo y FK(q) del Hito 2 con la postura medida en el instante de la foto:
    T_base_obj = FK(q) · T_tool0_cam · T_cam_obj.

Sin ROS (scripts, otro lenguaje): acción `punto_externo` {"pose": [x, y, z mm, roll, pitch, yaw °]} por HTTP local.
Ejemplo mínimo: `python3 -m irb120_control.vision.publicar_punto X Y Z ROLL PITCH YAW`.
"""
