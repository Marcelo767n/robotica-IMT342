"""Control interactivo nativo RViz: girar = previsualizar; menú = armar/ejecutar."""
import json
import math
import time
import textwrap
import unicodedata
import xml.etree.ElementTree as ET
import numpy as np
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from geometry_msgs.msg import Pose, TransformStamped
from visualization_msgs.msg import InteractiveMarker, InteractiveMarkerControl, InteractiveMarkerFeedback, Marker
from interactive_markers.interactive_marker_server import InteractiveMarkerServer
from interactive_markers.menu_handler import MenuHandler
from tf2_ros.static_transform_broadcaster import StaticTransformBroadcaster
from irb120_conexion.rutas import PACKAGE
from irb120_control.supervisor import Rejected, JOINT_LIMITS_DEG


def multiply(a,b):
    x,y,z,w=a;X,Y,Z,W=b
    return np.array([w*X+x*W+y*Z-z*Y,w*Y-x*Z+y*W+z*X,w*Z+x*Y-y*X+z*W,w*W-x*X-y*Y-z*Z])


def origin_quaternion(rpy):
    r,p,y=np.array(rpy)/2
    return np.array([math.sin(r)*math.cos(p)*math.cos(y)-math.cos(r)*math.sin(p)*math.sin(y),
        math.cos(r)*math.sin(p)*math.cos(y)+math.sin(r)*math.cos(p)*math.sin(y),
        math.cos(r)*math.cos(p)*math.sin(y)-math.sin(r)*math.sin(p)*math.cos(y),
        math.cos(r)*math.cos(p)*math.cos(y)+math.sin(r)*math.sin(p)*math.sin(y)])


def model_joints():
    root=ET.parse(PACKAGE/'urdf/irb120.urdf').getroot();result=[]
    for i in range(6):
        joint=root.find(f"joint[@name='joint_{i+1}']")
        lo,hi=[math.degrees(float(joint.find('limit').get(k))) for k in ('lower','upper')]
        if not np.allclose([lo,hi],JOINT_LIMITS_DEG[i],atol=1e-6,rtol=0):
            raise Rejected(f'Los límites del URDF y del modelo difieren en J{i+1}.')
        origin=joint.find('origin')
        result.append((joint.find('parent').get('link'),
                       [float(v) for v in origin.get('xyz','0 0 0').split()],
                       origin_quaternion([float(v) for v in origin.get('rpy','0 0 0').split()])))
    return result


class RvizControl(Node):
    def __init__(self,engine,lock,runtime,mode):
        super().__init__('irb120_ensayo_articular',cli_args=['--ros-args','-r','/tf:=/irb120/control/tf',
                         '-r','/tf_static:=/irb120/control/tf_static'],use_global_arguments=False)
        self.engine,self.lock,self.runtime,self.mode=engine,lock,runtime,mode
        self.joints=model_joints()
        self.real=self.create_publisher(JointState,'/irb120/control/medido/joint_states',10)
        self.preview_pub=self.create_publisher(JointState,'/irb120/control/objetivo/joint_states',10)
        self.status=self.create_publisher(String,'/irb120/control/estado',10)
        self.text=self.create_publisher(Marker,'/irb120/control/texto',10)
        self.server=InteractiveMarkerServer(self,'/irb120/control/articulacion')
        self.menu=MenuHandler()
        joint_menu=self.menu.insert('1. Seleccionar eje')
        for i in range(6):
            self.menu.insert(f'J{i+1} ({JOINT_LIMITS_DEG[i,0]:g}° a {JOINT_LIMITS_DEG[i,1]:g}° nominal)',
                parent=joint_menu,callback=lambda f,i=i:self.action('select',i))
        step_menu=self.menu.insert('2. Ajustar objetivo (vista previa)')
        steps=[s for s in (-10.,-5.,-.5,-.1,.1,.5,5.,10.) if abs(s)<=engine.policy.step]
        for step in steps:
            self.menu.insert(f'{step:+g}°',parent=step_menu,callback=lambda f,s=step:self.increment(s))
        self.menu.insert('Sincronizar con el ángulo medido / reiniciar fallo',callback=lambda f:self.action('sync'))
        self.menu.insert('3. ARMAR prueba (mantener postura)',callback=lambda f:self.action('arm'))
        self.menu.insert('4. EJECUTAR objetivo de este eje',callback=lambda f:self.action('execute'))
        self.menu.insert('CANCELAR movimiento y mantener',callback=lambda f:self.action('cancel'))
        self.menu.insert('DESARMAR / cerrar envío (en reposo)',callback=lambda f:self.action('disarm'))
        self.marker_axis=None;self.marker_name=None;self.dragging=False;self.generation=0
        self.last_published_measurement=None
        self.static=StaticTransformBroadcaster(self)
        transforms=[]
        for prefix in ('medido/','objetivo/'):
            t=TransformStamped();t.header.frame_id='base_link';t.child_frame_id=prefix+'base_link';t.transform.rotation.w=1.
            t.header.stamp=self.get_clock().now().to_msg();transforms.append(t)
        self.static.sendTransform(transforms)
        self.create_timer(.05,self.update)

    def action(self,name,arg=None):
        with self.lock:
            e=self.engine;now=time.monotonic()
            try:
                if name=='select':e.select(arg)
                elif name=='sync':e.synchronize()
                elif name=='arm':e.arm(now)
                elif name=='execute':e.execute(now)
                elif name=='cancel':e.cancel(now)
                elif name=='disarm':e.disarm()
                if self.runtime:self.runtime.record('action',action=name,axis=e.axis+1,
                    target_deg=None if e.target is None else e.target.tolist())
                self.get_logger().info(e.reason)
            except (Rejected,ValueError) as exc:
                e.reason='RECHAZADO: '+str(exc)
                self.get_logger().warning(e.reason)
                if self.runtime:self.runtime.record('rejected',action=name,reason=e.reason)

    def increment(self,step):
        with self.lock:
            if self.engine.target is None:return
            try:self.engine.preview(float(self.engine.target[self.engine.axis]+step))
            except Rejected as exc:self.engine.reason='RECHAZADO: '+str(exc)

    def pose(self):
        e=self.engine;_,xyz,origin=self.joints[e.axis]
        angle=math.radians(float(e.target[e.axis]))
        rotation=multiply(origin,[0,0,math.sin(angle/2),math.cos(angle/2)])
        p=Pose();p.position.x,p.position.y,p.position.z=xyz
        p.orientation.x,p.orientation.y,p.orientation.z,p.orientation.w=rotation.tolist()
        return p

    def feedback(self,f):
        with self.lock:
            e=self.engine
            if f.marker_name!=self.marker_name:return
            if f.event_type==InteractiveMarkerFeedback.MOUSE_DOWN:self.dragging=True
            if f.event_type==InteractiveMarkerFeedback.MOUSE_UP:self.dragging=False
            if f.event_type!=InteractiveMarkerFeedback.POSE_UPDATE:return
            try:
                parent,xyz,origin=self.joints[e.axis]
                if f.header.frame_id!='objetivo/'+parent:
                    raise Rejected('Marco de la edición articular incorrecto.')
                if np.max(np.abs(np.array([f.pose.position.x,f.pose.position.y,f.pose.position.z])-xyz))>1e-4:
                    raise Rejected('El control solo permite girar el eje; no desplazar su origen.')
                q=f.pose.orientation
                feedback_q=np.array([q.x,q.y,q.z,q.w])
                if not np.isfinite(feedback_q).all() or abs(np.linalg.norm(feedback_q)-1)>.001:
                    raise Rejected('Orientación de edición inválida.')
                inverse=origin*np.array([-1,-1,-1,1])
                relative=multiply(inverse,feedback_q)
                if np.linalg.norm(relative[:2])>1e-3:raise Rejected('Rotación fuera del eje de la articulación.')
                wrapped=2*math.atan2(relative[2],relative[3])
                previous=math.radians(float(e.target[e.axis]))
                angle=previous+math.atan2(math.sin(wrapped-previous),math.cos(wrapped-previous))
                e.preview(math.degrees(angle))
            except Rejected as exc:
                e.reason='RECHAZADO: '+str(exc)
                self.dragging=False

    def update(self):
        with self.lock:
            e=self.engine;e.heartbeat(time.monotonic())
            if e.q is None:return
            stamp=self.get_clock().now().to_msg()
            for publisher,q in ((self.real,e.q),(self.preview_pub,e.target)):
                if q is None:continue
                if publisher is self.real:
                    if self.last_published_measurement==e.measured_at or time.monotonic()-e.measured_at>e.policy.state_timeout:
                        continue
                    self.last_published_measurement=e.measured_at
                message=JointState();message.header.stamp=stamp
                message.name=[f'joint_{i+1}' for i in range(6)];message.position=np.deg2rad(q).tolist()
                publisher.publish(message)
            if e.target is not None:
                if self.marker_axis!=e.axis:
                    self.server.clear();self.generation+=1
                    marker=InteractiveMarker();marker.header.frame_id='objetivo/'+self.joints[e.axis][0]
                    self.marker_name=f'j{e.axis+1}_{self.generation}';marker.name=self.marker_name
                    # El texto 3D de Ogre procesa bytes; los menús Qt sí admiten UTF-8.
                    marker.description=f'J{e.axis+1}:MENU'
                    marker.pose=self.pose();marker.scale=.22
                    control=InteractiveMarkerControl();control.name='girar_junta'
                    control.interaction_mode=InteractiveMarkerControl.ROTATE_AXIS
                    control.orientation.w=math.sqrt(.5);control.orientation.y=-math.sqrt(.5)
                    marker.controls.append(control)
                    self.server.insert(marker,feedback_callback=self.feedback)
                    self.menu.apply(self.server,self.marker_name);self.marker_axis=e.axis
                elif not self.dragging:self.server.setPose(self.marker_name,self.pose())
                self.server.applyChanges()
            payload={'mode':self.mode,'state':e.state,'reason':e.reason,'axis':e.axis+1,
                'measured_deg':e.q.tolist(),'target_deg':None if e.target is None else e.target.tolist(),
                'reference_deg':None if e.reference is None else e.reference.tolist(),
                'age_s':time.monotonic()-e.measured_at,'limits_deg':e.policy.limits.tolist(),
                'window_deg':e.policy.window.tolist(),'max_step_deg':e.policy.step,
                'guidance_running':e.guidance,'can_send':e.can_send,
                'sent_packets':0 if self.runtime is None else self.runtime.sent}
            message=String();message.data=json.dumps(payload,ensure_ascii=False,allow_nan=False);self.status.publish(message)
            marker=Marker();marker.header.frame_id='base_link';marker.header.stamp=stamp
            marker.ns='estado';marker.id=0;marker.type=Marker.TEXT_VIEW_FACING;marker.action=Marker.ADD
            marker.pose.orientation.w=1.;marker.pose.position.x=-.25;marker.pose.position.z=.95
            # Jazzy permite fijar el ancho del espacio en scale.x; su valor
            # predeterminado no se reajusta al reducir la altura de la fuente.
            marker.scale.x=.012;marker.scale.z=.023
            marker.color.r=1.;marker.color.g=1.;marker.color.b=1.;marker.color.a=1.
            measured=f'{e.q[e.axis]:.4f}';target='—' if e.target is None else f'{e.target[e.axis]:.4f}'
            lo,hi=e.policy.window[e.axis]
            reason=unicodedata.normalize('NFKD',e.reason).encode('ascii','ignore').decode()
            marker.text=(f'{self.mode.upper()} | {e.state}\nJ{e.axis+1}: medido {measured} / objetivo {target} deg\n'
                         f'Ventana [{lo:.2f}, {hi:.2f}] deg | paso max {e.policy.step:g} deg\n'
                         + '\n'.join(textwrap.wrap(reason,width=48)))
            self.text.publish(marker)
