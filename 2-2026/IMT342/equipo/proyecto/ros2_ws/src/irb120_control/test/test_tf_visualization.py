"""URDF → dos RSP reales → TF; opcionalmente carga los plugins nativos de RViz."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import xml.etree.ElementTree as ET

import numpy as np
import yaml

sys.path[:0] = [str(Path(__file__).resolve().parents[1]),
               str(Path(__file__).resolve().parents[3] / 'src/irb120_conexion')]


@unittest.skipUnless(os.environ.get('IRB120_CONTROL_ROS_TEST') == '1', 'Prueba ROS local opcional')
class VisualizationTests(unittest.TestCase):
    def test_models_frames_and_native_displays(self):
        import rclpy
        from rclpy.time import Time
        from tf2_ros import Buffer, TransformListener
        from visualization_msgs.msg import Marker, InteractiveMarkerFeedback
        from visualization_msgs.srv import GetInteractiveMarkers
        from irb120_control.arranque import prepare_models
        from irb120_control.rviz_control import RvizControl
        from irb120_control.supervisor import Policy, Supervisor

        rclpy.init(args=[])
        measured = np.array([0., -20., 20., 0., 30., 0.])
        engine = Supervisor(Policy.demo(step=10), can_send=False)
        engine.ingest(measured, time.monotonic())
        node = RvizControl(engine, threading.RLock(), None, 'demo')
        buffer = Buffer()
        listener = TransformListener(buffer, node)
        text = []
        node.create_subscription(Marker, '/irb120/control/texto', text.append, 10)
        client = node.create_client(GetInteractiveMarkers, '/irb120/control/articulacion/get_interactive_markers')
        feedback = node.create_publisher(InteractiveMarkerFeedback, '/irb120/control/articulacion/feedback', 10)
        children = []

        def spin(seconds):
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                engine.ingest(measured, time.monotonic())
                rclpy.spin_once(node, timeout_sec=.01)

        def position(frame):
            v = buffer.lookup_transform('base_link', frame, Time()).transform.translation
            return np.array([v.x, v.y, v.z])

        try:
            with tempfile.TemporaryDirectory(prefix='irb120_visual_test_') as directory:
                folder = prepare_models(directory)
                config = yaml.safe_load((folder / 'control.rviz').read_text())
                displays = config['Visualization Manager']['Displays']
                for name in ('medido', 'objetivo'):
                    children.append(subprocess.Popen([
                        '/opt/ros/jazzy/lib/robot_state_publisher/robot_state_publisher',
                        '--ros-args', '--params-file', str(folder / (name + '.yaml')),
                        '-r', '__node:=test_rsp_' + name,
                        '-r', 'joint_states:=/irb120/control/' + name + '/joint_states',
                        '-r', '/robot_description:=/irb120/control/' + name + '/robot_description',
                        '-r', '/tf:=/irb120/control/tf', '-r', '/tf_static:=/irb120/control/tf_static'],
                        stdout=subprocess.DEVNULL))
                spin(2.)
                for name in ('medido', 'objetivo'):
                    params = yaml.safe_load((folder / (name + '.yaml')).read_text())['/**']['ros__parameters']
                    model = next(d for d in displays if d.get('TF Prefix') == name)
                    self.assertEqual(model['Description Topic']['Value'], '/irb120/control/' + name + '/robot_description')
                    for link in ET.fromstring(params['robot_description']).findall('link'):
                        # Mismo nombre que realmente buscará RobotModel con su TF Prefix.
                        frame = model['TF Prefix'] + '/' + link.get('name')
                        self.assertTrue(buffer.can_transform('base_link', frame, Time()), frame)
                np.testing.assert_allclose(position('medido/tool0'), position('objetivo/tool0'), atol=1e-10)
                before = position('medido/tool0')
                node.action('select', 1)
                node.increment(.5)
                spin(.4)
                np.testing.assert_allclose(position('medido/tool0'), before, atol=1e-10)
                self.assertGreater(np.linalg.norm(position('objetivo/tool0') - before), .001)
                self.assertIsNone(engine.reference)
                self.assertTrue(text)
                self.assertEqual(text[-1].header.frame_id, 'base_link')
                self.assertIn('medido', text[-1].text)
                future = client.call_async(GetInteractiveMarkers.Request())
                spin(.3)
                self.assertTrue(future.done())
                markers = future.result().markers
                self.assertEqual(len(markers), 1)
                self.assertTrue(buffer.can_transform('base_link', markers[0].header.frame_id, Time()))
                self.assertTrue(text[-1].text.isascii())
                # El menú ampliado modifica la vista previa mediante su tópico público.
                entry = next(e for e in markers[0].menu_entries if e.title == '-5°')
                message = InteractiveMarkerFeedback()
                message.client_id = 'prueba_vista_ampliada'
                message.marker_name = markers[0].name
                message.header = markers[0].header
                message.event_type = InteractiveMarkerFeedback.MENU_SELECT
                message.menu_entry_id = entry.id
                spin(1.15)
                feedback.publish(message)
                spin(.2)
                self.assertAlmostEqual(engine.target[1], measured[1] + .5 - 5.)
                entry = next(e for e in markers[0].menu_entries if e.title == '+10°')
                message.menu_entry_id = entry.id
                feedback.publish(message)
                spin(.2)
                self.assertAlmostEqual(engine.target[1], measured[1] + .5 + 5.)
                np.testing.assert_allclose(engine.q, measured, atol=1e-10)
                self.assertIsNone(engine.reference)

                # Ejecutable independiente construido con las bibliotecas RViz de esta PC.
                # Comprueba los Status reales de RobotModel, InteractiveMarkers y Marker.
                probe = os.environ.get('IRB120_RVIZ_PROBE')
                if probe:
                    node.action('select', 0)  # Verificar también el aro inicial J1 de la demo.
                    output_path = folder / 'rviz_probe.log'
                    with output_path.open('w') as output:
                        process = subprocess.Popen([probe, str(folder / 'control.rviz'), '--ros-args',
                            '-r', '/tf:=/irb120/control/tf', '-r', '/tf_static:=/irb120/control/tf_static'],
                            stdout=output, stderr=subprocess.STDOUT)
                        children.append(process)
                        deadline = time.monotonic() + 15
                        while process.poll() is None and time.monotonic() < deadline:
                            spin(.05)
                    log = output_path.read_text()
                    self.assertEqual(process.poll(), 0, log)
                    line = next(s for s in log.splitlines() if s.startswith('RVIZ_PROBE '))
                    result = json.loads(line[len('RVIZ_PROBE '):])
                    self.assertEqual(len(result), 5)
                    self.assertTrue(all(d['ok'] for d in result), result)
                    print(line, flush=True)
        finally:
            for child in children:
                if child.poll() is None:
                    child.terminate()
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
            listener.unregister()
            node.destroy_node()
            rclpy.shutdown()


if __name__ == '__main__':
    unittest.main()
