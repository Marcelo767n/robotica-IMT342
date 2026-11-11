"""Menús/arrastre RViz por sus mensajes públicos → supervisor → EGM UDP real en loopback."""
import copy
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
import numpy as np
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[3]/'src/irb120_conexion')]


@unittest.skipUnless(os.environ.get('IRB120_CONTROL_ROS_TEST')=='1','Prueba ROS/UDP local opcional')
class RosRvizTests(unittest.TestCase):
    def test_six_axes_via_public_interactive_feedback_and_loss_of_heartbeat(self):
        import rclpy
        from visualization_msgs.msg import InteractiveMarkerFeedback
        from visualization_msgs.srv import GetInteractiveMarkers
        from irb120_control.supervisor import Policy,Supervisor
        from irb120_control.protocolo import EGMTransport
        from irb120_control.simulador import SimulatedController
        from irb120_control.runtime import Runtime
        from irb120_control.rviz_control import RvizControl,multiply
        rclpy.init(args=[])
        engine=Supervisor(Policy.demo());lock=threading.RLock()
        transport=EGMTransport('127.0.0.1',0,'127.0.0.1');sim=SimulatedController(transport.address);sim.start()
        with tempfile.TemporaryDirectory() as tmp:
            runtime=Runtime(engine,transport,lock,Path(tmp)/'control.jsonl');runtime.start()
            node=RvizControl(engine,lock,runtime,'demo')
            client=node.create_client(GetInteractiveMarkers,'/irb120/control/articulacion/get_interactive_markers')
            publisher=node.create_publisher(InteractiveMarkerFeedback,'/irb120/control/articulacion/feedback',10)
            def spin(seconds):
                deadline=time.monotonic()+seconds
                while time.monotonic()<deadline:rclpy.spin_once(node,timeout_sec=.01)
            def get_marker():
                for _ in range(15):
                    future=client.call_async(GetInteractiveMarkers.Request())
                    deadline=time.monotonic()+1
                    while not future.done() and time.monotonic()<deadline:rclpy.spin_once(node,timeout_sec=.01)
                    if future.done() and future.result().markers:return future.result().markers[0]
                    spin(.05)
                self.fail('El servidor de controles RViz no entregó marcador.')
            def menu(prefix):
                marker=get_marker();entry=next(e for e in marker.menu_entries if e.title.startswith(prefix))
                f=InteractiveMarkerFeedback();f.client_id='ensayo_integrado';f.marker_name=marker.name
                f.header=marker.header;f.event_type=InteractiveMarkerFeedback.MENU_SELECT;f.menu_entry_id=entry.id
                publisher.publish(f);spin(.12)
            results=[]
            try:
                spin(.8);self.assertEqual(runtime.sent,0);self.assertFalse(sim.commands)
                for axis in range(6):
                    # InteractiveMarkerServer reserva 1 s al crear un marcador antes de aceptar otro cliente.
                    menu(f'J{axis+1} (');spin(1.15)
                    marker=get_marker();base=engine.q.copy();sent_before=runtime.sent
                    hold=None if engine.reference is None else engine.reference.copy()
                    command_index=len(sim.commands)
                    # Arrastre inválido: 1.5° supera el paso máximo. Nunca debe producir comandos.
                    f=InteractiveMarkerFeedback();f.client_id='ensayo_integrado';f.marker_name=marker.name
                    f.header=marker.header;f.event_type=InteractiveMarkerFeedback.POSE_UPDATE
                    f.pose=copy.deepcopy(marker.pose)
                    q=marker.pose.orientation
                    rot=multiply([q.x,q.y,q.z,q.w],[0,0,math.sin(math.radians(1.5)/2),math.cos(math.radians(1.5)/2)])
                    f.pose.orientation.x,f.pose.orientation.y,f.pose.orientation.z,f.pose.orientation.w=rot.tolist()
                    publisher.publish(f);spin(.12)
                    np.testing.assert_allclose(engine.target,base,atol=1e-8)
                    if axis%2==0:
                        menu('+0.1°')
                    else:
                        # También probar un arrastre válido, incluidos los offsets URDF de J4/J6.
                        marker=get_marker();f.marker_name=marker.name;f.header=marker.header;f.pose=copy.deepcopy(marker.pose)
                        q=marker.pose.orientation
                        rot=multiply([q.x,q.y,q.z,q.w],[0,0,math.sin(math.radians(.1)/2),math.cos(math.radians(.1)/2)])
                        f.pose.orientation.x,f.pose.orientation.y,f.pose.orientation.z,f.pose.orientation.w=rot.tolist()
                        publisher.publish(f);spin(.12)
                    if hold is None:self.assertEqual(runtime.sent,sent_before)
                    else:
                        for q in sim.commands[command_index:]:np.testing.assert_allclose(q,hold,atol=1e-8)
                    self.assertAlmostEqual(engine.target[axis],base[axis]+.1,places=8)
                    menu('3. ARMAR');self.assertEqual(engine.state,'ARMADO',engine.reason)
                    menu('4. EJECUTAR')
                    deadline=time.monotonic()+4
                    while engine.state not in ('MANTENIENDO','FALLO') and time.monotonic()<deadline:spin(.02)
                    self.assertEqual(engine.state,'MANTENIENDO',engine.reason)
                    commands=np.array(sim.commands)[sent_before:]
                    for other in set(range(6))-{axis}:
                        np.testing.assert_allclose(commands[:,other],base[other],atol=1e-8)
                    self.assertLessEqual(float(np.max(np.abs(engine.q-engine.target))),engine.policy.start_drift)
                    results.append({'axis':axis+1,'measured_deg':engine.q.tolist(),'target_deg':engine.target.tolist(),
                                    'packets_sent':runtime.sent-sent_before})
                    if axis%2==1:
                        menu('DESARMAR');spin(.15);count=runtime.sent;spin(.1);self.assertEqual(runtime.sent,count)
                # Sin callbacks ROS no hay heartbeat: el hilo EGM debe dejar de mandar.
                menu('Sincronizar');spin(.7);menu('3. ARMAR')
                time.sleep(.4)
                self.assertEqual(engine.state,'FALLO',engine.reason)
                count=runtime.sent;time.sleep(.08);self.assertEqual(runtime.sent,count)
                print('RESULTADO INTEGRADO RVIZ/EGM:',json.dumps(results),flush=True)
            finally:
                runtime.close();sim.close();node.destroy_node();rclpy.shutdown()


if __name__=='__main__':unittest.main()
