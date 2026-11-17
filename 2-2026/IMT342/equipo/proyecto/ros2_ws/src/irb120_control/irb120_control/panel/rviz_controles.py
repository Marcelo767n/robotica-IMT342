"""Controles del panel DENTRO de RViz: pose arrastrable con cinemática inversa y menú de clic derecho.

- Marcador interactivo 6-DOF «pose objetivo» en la pose del TCP (o de la brida) del objetivo.
  Flechas = mover en X/Y/Z de la base; anillos = girar sobre los ejes de la herramienta.
  Al arrastrar se resuelve la cinemática inversa de Pieper y el robot naranja sigue la pose.
- Clic derecho sobre el marcador: ajustar ejes ±1°/±5°, copiar la postura actual, elegir punto
  de referencia, «Enviar al robot» (submenú de confirmación) y cancelar.
- Texto 3D con el estado. Usa el mismo objeto Panel que la página: un único objetivo.

Nada se envía al robot sin elegir «Enviar al robot → Sí, enviar objetivo naranja».
"""
import math
import time
import textwrap
import unicodedata

from geometry_msgs.msg import Pose
from interactive_markers.interactive_marker_server import InteractiveMarkerServer
from interactive_markers.menu_handler import MenuHandler
from visualization_msgs.msg import InteractiveMarker, InteractiveMarkerControl, InteractiveMarkerFeedback, Marker

from irb120_control.panel.cinematica import kinematics, pose_of
from irb120_control.rws_j6 import Refused

NAMESPACE = '/irb120/control/articulacion'
TEXT_TOPIC = '/irb120/control/texto'
NAME = 'pose_objetivo'
IK_PERIOD_S = .1


def ascii(text):
    # El texto 3D de Ogre trabaja con bytes: sin tildes ni símbolos.
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode()


def pose_message(pose):
    """[x, y, z mm, roll, pitch, yaw °] → geometry_msgs/Pose en metros y cuaternión."""
    np, _, _, transforms = kinematics()
    rotation = transforms.rpy_to_matrix(*np.deg2rad(pose[3:]))
    x, y, z, w = transforms.matrix_to_quaternion(rotation)
    message = Pose()
    message.position.x, message.position.y, message.position.z = (v / 1000. for v in pose[:3])
    message.orientation.x, message.orientation.y, message.orientation.z, message.orientation.w = x, y, z, w
    return message


def pose_from_message(message):
    """geometry_msgs/Pose → [x, y, z mm, roll, pitch, yaw °]; Refused si no es válida."""
    np, _, _, transforms = kinematics()
    p, q = message.position, message.orientation
    values = [p.x, p.y, p.z, q.x, q.y, q.z, q.w]
    if not all(math.isfinite(v) for v in values) or abs(math.sqrt(sum(v * v for v in values[3:])) - 1.) > .01:
        raise Refused('Pose de RViz no válida.')
    rotation = transforms.quaternion_to_matrix(q.x, q.y, q.z, q.w)
    return [p.x * 1000., p.y * 1000., p.z * 1000., *transforms.matrix_to_rpy_deg(rotation)]


def axis_control(name, mode, x, y, z, fixed):
    control = InteractiveMarkerControl()
    norm = math.sqrt(1. + x * x + y * y + z * z)
    control.orientation.w, control.orientation.x = 1. / norm, x / norm
    control.orientation.y, control.orientation.z = y / norm, z / norm
    control.name, control.interaction_mode = name, mode
    control.orientation_mode = (InteractiveMarkerControl.FIXED if fixed else InteractiveMarkerControl.INHERIT)
    return control


class RvizControls:
    def __init__(self, node, panel):
        self.node, self.panel = node, panel
        self.server = InteractiveMarkerServer(node, NAMESPACE)
        self.text = node.create_publisher(Marker, TEXT_TOPIC, 10)
        self.inserted = False
        self.dragging = False
        self.shown = None          # (objetivo, herramienta) dibujado en el marcador
        self.last_ik = 0.
        self.message = 'Arrastrar la pose o clic derecho para el menu.'
        self.message_at = time.monotonic()
        self.menu = MenuHandler()
        axes = self.menu.insert('Ajustar eje (vista previa)')
        for i in range(6):
            sub = self.menu.insert(f'J{i + 1}', parent=axes)
            for delta in (5., 1., -1., -5.):
                self.menu.insert(f'{delta:+g}°', parent=sub,
                                 callback=lambda f, i=i, d=delta: self.run(f'J{i + 1} {d:+g}°',
                                                                           lambda: panel.nudge(i, d)))
        self.menu.insert('Copiar postura actual', callback=lambda f: self.run('Objetivo = postura actual', panel.sync))
        tools = self.menu.insert('Punto de referencia')
        for tool, label in (('tcp', 'TCP del proyecto (150 mm)'), ('brida', 'Brida (tool0)')):
            self.menu.insert(label, parent=tools,
                             callback=lambda f, t=tool, l=label: self.run(f'Punto: {l}', lambda: panel.set_tool(t)))
        send = self.menu.insert('Enviar al robot')
        self.menu.insert('Sí, enviar objetivo naranja', parent=send,
                         callback=lambda f: self.run('Enviado: ver progreso', lambda: panel.send(panel.target_copy())))
        self.menu.insert('Cancelar tras la orden en curso',
                         callback=lambda f: self.run('Cancelacion pedida', panel.request_cancel))
        node.create_timer(.1, self.update)

    def note(self, text):
        self.message, self.message_at = text, time.monotonic()

    def run(self, done, action):
        try:
            action()
            self.note(done)
        except Refused as exc:
            self.note('RECHAZADO: ' + str(exc))
            self.panel.say('RViz: ' + str(exc))
        except Exception as exc:  # p. ej. error de red al leer: se muestra y se sigue
            self.note('FALLO: ' + str(exc))

    def marker(self, pose):
        marker = InteractiveMarker()
        marker.header.frame_id = 'base_link'
        marker.name, marker.scale = NAME, .16
        marker.description = 'Pose objetivo: arrastrar / clic derecho = menu'
        marker.pose = pose_message(pose)
        handle = InteractiveMarkerControl()
        handle.name, handle.interaction_mode, handle.always_visible = 'menu', InteractiveMarkerControl.MENU, True
        sphere = Marker()
        sphere.type, sphere.scale.x, sphere.scale.y, sphere.scale.z = Marker.SPHERE, .035, .035, .035
        sphere.color.r, sphere.color.g, sphere.color.b, sphere.color.a = 1., .5, .05, .9
        handle.markers.append(sphere)
        marker.controls.append(handle)
        for axis, (x, y, z) in (('x', (1., 0., 0.)), ('y', (0., 0., 1.)), ('z', (0., 1., 0.))):
            marker.controls.append(axis_control('mover_' + axis, InteractiveMarkerControl.MOVE_AXIS, x, y, z, True))
            marker.controls.append(axis_control('girar_' + axis, InteractiveMarkerControl.ROTATE_AXIS, x, y, z, False))
        return marker

    def feedback(self, feedback):
        if feedback.marker_name != NAME:
            return
        kind = feedback.event_type
        if kind == InteractiveMarkerFeedback.MOUSE_DOWN:
            self.dragging = True
            return
        if kind not in (InteractiveMarkerFeedback.POSE_UPDATE, InteractiveMarkerFeedback.MOUSE_UP):
            return
        final = kind == InteractiveMarkerFeedback.MOUSE_UP
        if final:
            self.dragging = False
        elif time.monotonic() - self.last_ik < IK_PERIOD_S:
            return
        self.last_ik = time.monotonic()
        try:
            if feedback.header.frame_id != 'base_link':
                raise Refused('Marco de la pose distinto de base_link.')
            result = self.panel.solve(pose_from_message(feedback.pose), quiet=not final)
            if result['elegida'] is None:
                self.note(result['veredicto'] + (' Se conserva el objetivo anterior.' if final else ''))
            else:
                chosen = next(r for r in result['ramas'] if r['rama'] == result['elegida'])
                self.note(f"IK rama {chosen['rama']} ({chosen['brazo']}, codo {chosen['codo']}, {chosen['muneca']})")
        except Refused as exc:
            self.note('RECHAZADO: ' + str(exc))
        if final:
            self.shown = None   # devolver el marcador a la pose del objetivo vigente

    def update(self):
        with self.panel.mutex:
            target = None if self.panel.target is None else list(self.panel.target)
            tool = self.panel.tool
        if target is None:
            return
        try:
            pose = pose_of(target, tool)
        except Exception:
            return
        if not self.inserted:
            self.server.insert(self.marker(pose), feedback_callback=self.feedback)
            self.menu.apply(self.server, NAME)
            self.server.applyChanges()
            self.inserted, self.shown = True, (target, tool)
        elif not self.dragging and self.shown != (target, tool):
            self.server.setPose(NAME, pose_message(pose))
            self.server.applyChanges()
            self.shown = (target, tool)
        self.publish_text(target)

    def publish_text(self, target):
        shot = self.panel.snapshot()
        if shot['ocupado']:
            head = 'MOVIENDO ' + (shot['progreso'] or '')
        elif shot['faltas']:
            head = 'NO LISTO: ' + shot['faltas'][0]
        else:
            head = 'LISTO para enviar'
        orders = shot['ordenes']
        lines = [('SIMULADO | ' if shot['simulado'] else '') + head,
                 'Objetivo (deg): ' + ' '.join(f'{v:.1f}' for v in target),
                 'Ordenes: ' + ('-' if orders is None else str(orders)) + f" de max {shot['paso']:g} deg"
                 + f" | punto: {shot['herramienta']}"]
        if time.monotonic() - self.message_at < 20.:
            lines += textwrap.wrap(self.message, width=52)
        marker = Marker()
        marker.header.frame_id, marker.header.stamp = 'base_link', self.node.get_clock().now().to_msg()
        marker.ns, marker.id, marker.type, marker.action = 'estado', 0, Marker.TEXT_VIEW_FACING, Marker.ADD
        marker.pose.orientation.w, marker.pose.position.x, marker.pose.position.z = 1., -.25, .95
        marker.scale.x, marker.scale.z = .012, .028
        marker.color.r, marker.color.g, marker.color.b, marker.color.a = 1., 1., 1., 1.
        marker.text = ascii('\n'.join(textwrap.shorten(line, 70) if len(line) > 70 else line for line in lines))
        self.text.publish(marker)
