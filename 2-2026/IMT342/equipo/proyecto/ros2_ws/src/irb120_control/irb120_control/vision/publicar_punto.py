"""Publica una vez un punto en /irb120/trayectoria/punto_externo (ejemplo para el nodo de visión).

    ./brazo.sh punto X Y Z ROLL PITCH YAW [--simulado]      (mm y grados, TCP en base_link)

El panel real escucha en ROS_DOMAIN_ID=120 y el simulado en 121 (iniciar.sh); brazo.sh lo fija.

Convenio de la orientación: el del Hito 2, R = Rz(yaw) · Ry(pitch) · Rx(roll)."""
import argparse
import math
import sys
import time

ESPERA_S = 10.


def mensaje_pose(xyz_mm, rpy_deg, transforms):
    """Mismo convenio que cinematica.pose_of, a PoseStamped en metros."""
    from geometry_msgs.msg import PoseStamped
    import numpy as np
    x, y, z, w = transforms.matrix_to_quaternion(transforms.rpy_to_matrix(*np.deg2rad(rpy_deg)))
    message = PoseStamped()
    message.header.frame_id = 'base_link'
    message.pose.position.x, message.pose.position.y, message.pose.position.z = (v / 1000. for v in xyz_mm)
    message.pose.orientation.x, message.pose.orientation.y = float(x), float(y)
    message.pose.orientation.z, message.pose.orientation.w = float(z), float(w)
    return message


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('valores', type=float, nargs=6, metavar=('X', 'Y', 'Z', 'ROLL', 'PITCH', 'YAW'))
    args = parser.parse_args(argv)
    if not all(math.isfinite(v) for v in args.valores):
        parser.error('Todos los valores deben ser finitos.')
    import rclpy
    from irb120_control.panel.cinematica import kinematics
    from irb120_control.panel.puente_ros import POINT_TOPIC
    from geometry_msgs.msg import PoseStamped
    _, _, _, transforms = kinematics()
    rclpy.init()
    node = rclpy.create_node('publicar_punto')
    publisher = node.create_publisher(PoseStamped, POINT_TOPIC, 10)
    message = mensaje_pose(args.valores[:3], args.valores[3:], transforms)
    limite = time.monotonic() + ESPERA_S   # el descubrimiento DDS tarda unos segundos
    while not publisher.get_subscription_count() and time.monotonic() < limite:
        time.sleep(.1)
    if not publisher.get_subscription_count():
        print(f'Nadie escucha {POINT_TOPIC} tras {ESPERA_S:.0f} s: ¿está abierto el panel? '
              '(real: ROS_DOMAIN_ID=120, simulado: 121). No se publicó nada.')
        node.destroy_node()
        rclpy.shutdown()
        return 2
    message.header.stamp = node.get_clock().now().to_msg()
    publisher.publish(message)
    print('Publicado en', POINT_TOPIC, '· el panel lo pone en el buzón si es alcanzable (ver el Estudio).')
    time.sleep(.2)
    node.destroy_node()
    rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
