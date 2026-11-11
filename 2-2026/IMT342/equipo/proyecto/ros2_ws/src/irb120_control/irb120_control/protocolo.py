"""EGM UDP: acepta solamente el emisor configurado y no transmite al arrancar.

Se reutiliza el esquema Protobuf de abb_robot_client (Apache-2.0), no su cliente
que acepta automáticamente cualquier emisor. No contiene llamadas RWS de escritura.
"""
from dataclasses import dataclass
import ipaddress
from pathlib import Path
import select
import socket
import sys
import time

import numpy as np

try:
    import google.protobuf
except ModuleNotFoundError:
    # Esta PC ya tiene python3-protobuf puro en Debian; se añade al FINAL de la búsqueda.
    # ROS/Python 3.12 y las bibliotecas del venv conservan prioridad. No se instala nada.
    if Path('/usr/lib/python3/dist-packages/google/protobuf').is_dir():
        sys.path.append('/usr/lib/python3/dist-packages')
    try:
        import google.protobuf
    except ModuleNotFoundError as exc:
        raise RuntimeError('Falta protobuf. Instalar requirements-egm.txt en el entorno Python 3.12.') from exc

from irb120_control.vendor import egm_pb2 as pb
from google.protobuf.message import DecodeError
from irb120_control.supervisor import Rejected, vector


@dataclass
class Feedback:
    q: np.ndarray
    sequence: int
    healthy: bool
    received_at: float
    guidance: bool


class EGMTransport:
    def __init__(self, bind_ip, port, controller_ip):
        self.controller_ip = str(ipaddress.IPv4Address(controller_ip))
        ipaddress.IPv4Address(bind_ip)
        if not 0 <= port < 65536:
            raise Rejected('Puerto UDP inválido.')
        self.socket=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.socket.bind((bind_ip,port))
        self.socket.setblocking(False)
        self.peer=None
        self.received_sequence=None
        self.sequence=0
        self.rejected_packets=0

    @property
    def address(self):
        return self.socket.getsockname()

    def receive(self, timeout=.01):
        if not select.select([self.socket],[],[],timeout)[0]:
            return None
        newest=None
        # Drenar una cola acotada: no ejecutar referencias usando paquetes atrasados.
        for _ in range(128):
            try:
                data,addr=self.socket.recvfrom(4096)
            except BlockingIOError:
                break
            if addr[0]!=self.controller_ip or (self.peer is not None and addr!=self.peer):
                self.rejected_packets+=1; continue
            message=pb.EgmRobot()
            try:
                message.ParseFromString(data)
                if not message.IsInitialized() or not message.HasField('header') or not message.header.HasField('seqno'):
                    raise ValueError('Sin cabecera/secuencia')
                if message.header.mtype!=pb.EgmHeader.MSGTYPE_DATA or not message.HasField('feedBack'):
                    raise ValueError('No es feedback EGM')
                q=vector(message.feedBack.joints.joints)
                seq=message.header.seqno
                if self.received_sequence is not None:
                    jump=(seq-self.received_sequence)&0xffffffff
                    if not 0<jump<0x80000000:
                        raise ValueError('Secuencia duplicada/antigua; reiniciar sesión para otro controlador')
                healthy=(message.HasField('motorState') and message.motorState.state==pb.EgmMotorState.MOTORS_ON
                         and message.HasField('rapidExecState') and message.rapidExecState.state==pb.EgmRapidCtrlExecState.RAPID_RUNNING
                         and message.HasField('mciState') and message.mciState.state in (pb.EgmMCIState.MCI_RUNNING,pb.EgmMCIState.MCI_STOPPED))
                guidance=message.HasField('mciState') and message.mciState.state==pb.EgmMCIState.MCI_RUNNING
            except (ValueError,TypeError,DecodeError):
                # DecodeError es una excepción de protobuf; todo paquete inválido se descarta.
                self.rejected_packets+=1
                continue
            self.peer,self.received_sequence=addr,seq
            newest=Feedback(q,seq,bool(healthy),time.monotonic(),guidance)
        if select.select([self.socket],[],[],0)[0]:
            raise Rejected('Cola EGM atrasada: no se usa una muestra antigua para enviar consignas.')
        return newest

    def send(self, q):
        q=vector(q)
        if self.peer is None:
            raise Rejected('No hay un primer paquete del controlador configurado; no se transmite.')
        packet=pb.EgmSensor()
        packet.header.seqno=self.sequence
        self.sequence=(self.sequence+1)&0xffffffff
        packet.header.tm=int(time.monotonic()*1000)&0xffffffff
        packet.header.mtype=pb.EgmHeader.MSGTYPE_CORRECTION
        packet.planned.joints.joints.extend(q.tolist())
        self.socket.sendto(packet.SerializeToString(),self.peer)

    def close(self):
        self.socket.close()
