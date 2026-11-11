"""Controlador EGM simulado, enlazado exclusivamente a loopback."""
import socket
import threading
import time
import numpy as np
from irb120_control.protocolo import pb
from irb120_control.supervisor import vector


class SimulatedController:
    def __init__(self,destination,q=None,period=.008):
        if destination[0]!='127.0.0.1':
            raise ValueError('El simulador solo puede enviar a 127.0.0.1.')
        self.destination,self.period=destination,period
        self.q=vector([0,-20,20,0,30,0] if q is None else q)
        self.command=self.q.copy()
        self.socket=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.socket.bind(('127.0.0.1',0)); self.socket.setblocking(False)
        self.stop=threading.Event();self.commands=[];self.motors=True
        self.thread=threading.Thread(target=self.run,daemon=True)

    def start(self):
        self.thread.start()

    def run(self):
        sequence=0
        while not self.stop.wait(self.period):
            while True:
                try: data,_=self.socket.recvfrom(4096)
                except BlockingIOError: break
                packet=pb.EgmSensor();packet.ParseFromString(data)
                q=vector(packet.planned.joints.joints)
                self.commands.append(q.copy());self.command=q
            self.q+=np.clip(self.command-self.q,-2*self.period,2*self.period)
            message=pb.EgmRobot()
            message.header.seqno=sequence;message.header.mtype=pb.EgmHeader.MSGTYPE_DATA
            message.header.tm=int(time.monotonic()*1000)&0xffffffff
            message.feedBack.joints.joints.extend(self.q.tolist())
            message.motorState.state=pb.EgmMotorState.MOTORS_ON if self.motors else pb.EgmMotorState.MOTORS_OFF
            message.rapidExecState.state=pb.EgmRapidCtrlExecState.RAPID_RUNNING
            message.mciState.state=pb.EgmMCIState.MCI_RUNNING
            self.socket.sendto(message.SerializeToString(),self.destination)
            sequence=(sequence+1)&0xffffffff

    def close(self):
        self.stop.set();self.thread.join(timeout=1);self.socket.close()
