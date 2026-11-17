"""Nodo ROS 2 del panel: posturas medida/objetivo para RViz y tópicos del panel de RViz.

Publica  /irb120/control/{medido,objetivo}/joint_states  (sensor_msgs/JointState, radianes, 10 Hz)
         /irb120/control/tf_static  base_link → medido/base_link y objetivo/base_link
         /irb120/panel/estado       (std_msgs/String JSON, 4 Hz y tras cada orden)
Escucha  /irb120/panel/orden        (std_msgs/String JSON, ver ordenes.py)
"""
import math

from geometry_msgs.msg import TransformStamped
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from tf2_ros.static_transform_broadcaster import StaticTransformBroadcaster

from irb120_control.panel.ordenes import Ordenes

STATE_TOPIC = '/irb120/panel/estado'
ORDER_TOPIC = '/irb120/panel/orden'
TF_REMAP = ['--ros-args', '-r', '/tf:=/irb120/control/tf', '-r', '/tf_static:=/irb120/control/tf_static']


def crear_nodo():
    return Node('irb120_panel_rws', cli_args=TF_REMAP, use_global_arguments=False)


class PuenteRos:
    def __init__(self, node, panel):
        self.node, self.panel = node, panel
        self.ordenes = Ordenes(panel)
        self.static = StaticTransformBroadcaster(node)
        anchors = []
        for prefix in ('medido/', 'objetivo/'):
            anchor = TransformStamped()
            anchor.header.stamp = node.get_clock().now().to_msg()
            anchor.header.frame_id, anchor.child_frame_id = 'base_link', prefix + 'base_link'
            anchor.transform.rotation.w = 1.
            anchors.append(anchor)
        self.static.sendTransform(anchors)
        self.measured_pub = node.create_publisher(JointState, '/irb120/control/medido/joint_states', 10)
        self.target_pub = node.create_publisher(JointState, '/irb120/control/objetivo/joint_states', 10)
        self.state_pub = node.create_publisher(String, STATE_TOPIC, 10)
        node.create_subscription(String, ORDER_TOPIC, self.on_order, 10)
        node.create_timer(.1, self.publish_joints)
        node.create_timer(.25, self.publish_state)

    def on_order(self, message):
        self.ordenes.atender(message.data)
        self.publish_state()

    def publish_state(self):
        self.state_pub.publish(String(data=self.ordenes.estado()))

    def publish_joints(self):
        stamp = self.node.get_clock().now().to_msg()
        for publisher, q in ((self.measured_pub, self.panel.fresh_measurement()),
                             (self.target_pub, self.panel.target_copy())):
            if q is None:
                continue
            message = JointState()
            message.header.stamp = stamp
            message.name = [f'joint_{i + 1}' for i in range(6)]
            message.position = [math.radians(v) for v in q]
            publisher.publish(message)
