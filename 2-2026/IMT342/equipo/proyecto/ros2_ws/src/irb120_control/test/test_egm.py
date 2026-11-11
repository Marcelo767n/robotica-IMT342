from pathlib import Path
import socket
import sys
import time
import unittest
import tempfile
import threading
import numpy as np
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[3]/'src/irb120_conexion')]
from irb120_control.protocolo import EGMTransport,pb
from irb120_control.supervisor import Rejected


def packet(seq=0,q=None):
    m=pb.EgmRobot();m.header.seqno=seq;m.header.mtype=pb.EgmHeader.MSGTYPE_DATA
    m.feedBack.joints.joints.extend(q or [0,-20,20,0,30,0])
    m.motorState.state=pb.EgmMotorState.MOTORS_ON;m.rapidExecState.state=pb.EgmRapidCtrlExecState.RAPID_RUNNING
    m.mciState.state=pb.EgmMCIState.MCI_RUNNING
    return m.SerializeToString()


class EgmTests(unittest.TestCase):
    def setUp(self):
        self.transport=EGMTransport('127.0.0.1',0,'127.0.0.1');self.addCleanup(self.transport.close)
        self.robot=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);self.robot.bind(('127.0.0.1',0));self.robot.settimeout(.1)
        self.addCleanup(self.robot.close)

    def test_no_send_before_feedback_and_degrees_are_preserved(self):
        with self.assertRaises(Rejected):self.transport.send([0]*6)
        self.robot.sendto(packet(),self.transport.address);f=self.transport.receive(.1)
        self.assertTrue(f.healthy);self.assertTrue(f.guidance)
        target=[0,-20,20,0,30,370.5];self.transport.send(target)
        data,_=self.robot.recvfrom(4096);m=pb.EgmSensor();m.ParseFromString(data)
        self.assertEqual(list(m.planned.joints.joints),target)
        self.assertEqual(m.header.mtype,pb.EgmHeader.MSGTYPE_CORRECTION)

    def test_malformed_nonfinite_short_replayed_and_other_port_are_rejected(self):
        for data in [b'bad',packet(q=[1,2]),packet(q=[1,2,3,4,5,float('nan')])]:
            self.robot.sendto(data,self.transport.address);self.assertIsNone(self.transport.receive(.1))
        self.robot.sendto(packet(5),self.transport.address);self.assertIsNotNone(self.transport.receive(.1))
        self.robot.sendto(packet(5),self.transport.address);self.assertIsNone(self.transport.receive(.1))
        other=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        try:other.sendto(packet(6),self.transport.address);self.assertIsNone(self.transport.receive(.1))
        finally:other.close()

    def test_wrong_controller_ip_never_becomes_destination(self):
        t=EGMTransport('127.0.0.1',0,'192.0.2.1')
        try:
            self.robot.sendto(packet(),t.address);self.assertIsNone(t.receive(.1));self.assertIsNone(t.peer)
        finally:t.close()

    def test_stream_and_missing_status_are_not_assumed_guidance(self):
        m=pb.EgmRobot();m.ParseFromString(packet());m.mciState.state=pb.EgmMCIState.MCI_STOPPED
        self.robot.sendto(m.SerializeToString(),self.transport.address);f=self.transport.receive(.1)
        self.assertTrue(f.healthy);self.assertFalse(f.guidance)
        m.header.seqno=1;m.ClearField('motorState')
        self.robot.sendto(m.SerializeToString(),self.transport.address);self.assertFalse(self.transport.receive(.1).healthy)

    def test_receive_only_runtime_has_no_path_to_send_commands(self):
        from irb120_control.supervisor import Policy,Supervisor
        from irb120_control.runtime import Runtime
        from irb120_control.simulador import SimulatedController
        t=EGMTransport('127.0.0.1',0,'127.0.0.1')
        # Recibir en el límite nominal está permitido en modo sin envío; no hereda margen de movimiento.
        sim=SimulatedController(t.address,q=[165,-110,70,-160,120,400])
        engine=Supervisor(Policy.demo(),can_send=False)
        with tempfile.TemporaryDirectory() as tmp:
            runtime=Runtime(engine,t,threading.RLock(),Path(tmp)/'received.jsonl');sim.start();runtime.start()
            try:
                deadline=time.monotonic()+1
                while engine.q is None and time.monotonic()<deadline:time.sleep(.01)
                self.assertIsNotNone(engine.q)
                np.testing.assert_allclose(engine.q,[165,-110,70,-160,120,400])
                with self.assertRaises(Rejected):engine.arm(time.monotonic())
                self.assertEqual(runtime.sent,0);self.assertFalse(sim.commands)
            finally:runtime.close();sim.close()


if __name__=='__main__':unittest.main()
