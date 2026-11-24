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

from geometry_msgs.msg import Point, Pose
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
        self.menu.insert('Añadir a la trayectoria', callback=lambda f: self.add_point(False))
        self.menu.insert('Añadir postura actual del robot', callback=lambda f: self.add_point(True))
        places = self.menu.insert('Posiciones fijas')
        for name, label in (('cero', 'Posición 0 (calibración)'), ('reposo', 'Reposo (J5 30°)')):
            self.menu.insert(label, parent=places,
                             callback=lambda f, n=name, l=label: self.run(f'Objetivo = {l}',
                                                                          lambda: panel.handle('posicion', {'valor': n})))
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

    def add_point(self, measured):
        """Buzón de puntos: pose del objetivo naranja (o postura medida) → /trayectoria del Estudio."""
        try:
            entry = self.panel.agregar_desde_rviz(measured)
            self.note(f"Punto {entry['nombre']} añadido al buzón")
        except Refused as exc:
            self.note('RECHAZADO: ' + str(exc))
            self.panel.say('RViz: ' + str(exc))
        except Exception as exc:
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
        check = shot.get('verificacion') or {}
        if shot['ocupado']:
            head = 'MOVIENDO ' + (shot['progreso'] or '')
        elif shot['faltas']:
            head = 'NO LISTO: ' + shot['faltas'][0]
        else:
            head = 'LISTO'
        orders = shot['ordenes']
        lines = [('SIMULADO | ' if shot['simulado'] else '') + head,
                 'Objetivo (deg): ' + ' '.join(f'{v:.1f}' for v in target),
                 'Ordenes: ' + ('-' if orders is None else str(orders)) + f" de max {shot['paso']:g} deg"
                 + f" | punto: {shot['herramienta']}"]
        lines += verification_lines(check)
        if time.monotonic() - self.message_at < 20.:
            lines += textwrap.wrap(self.message, width=52)
        stamp = self.node.get_clock().now().to_msg()
        text = self.base_marker('estado', 0, Marker.TEXT_VIEW_FACING, stamp)
        text.pose.position.x, text.pose.position.z = -.25, .95
        text.scale.x, text.scale.z = .012, .028
        text.color.r = text.color.g = text.color.b = 1.
        text.text = ascii('\n'.join(textwrap.shorten(line, 70) if len(line) > 70 else line for line in lines))
        self.text.publish(text)
        self.publish_error_markers(check, shot, stamp)

    def base_marker(self, ns, ident, kind, stamp):
        marker = Marker()
        marker.header.frame_id, marker.header.stamp = 'base_link', stamp
        marker.ns, marker.id, marker.type, marker.action = ns, ident, kind, Marker.ADD
        marker.pose.orientation.w = 1.
        marker.color.a = 1.
        return marker

    def publish_error_markers(self, check, shot, stamp):
        """Esfera verde = pose pedida; esfera blanca = punto real (FK de lo medido); línea = error."""
        wanted = check.get('pose_deseada')
        measured = shot.get('pose_medida')
        if wanted is None or measured is None:
            return
        ok = bool(check.get('robot') and check['robot']['ok'])
        for ident, pose, (r, g, b) in ((1, wanted, (.1, .9, .2)), (2, measured, (.95, .95, .95))):
            sphere = self.base_marker('error', ident, Marker.SPHERE, stamp)
            sphere.pose.position.x, sphere.pose.position.y, sphere.pose.position.z = (v / 1000. for v in pose[:3])
            sphere.scale.x = sphere.scale.y = sphere.scale.z = .018
            sphere.color.r, sphere.color.g, sphere.color.b = r, g, b
            self.text.publish(sphere)
        line = self.base_marker('error', 3, Marker.LINE_LIST, stamp)
        line.scale.x = .004
        line.color.r, line.color.g, line.color.b = (.1, .9, .2) if ok else (1., .2, .1)
        for pose in (wanted, measured):
            point = Point()
            point.x, point.y, point.z = (v / 1000. for v in pose[:3])
            line.points.append(point)
        self.text.publish(line)
        label = self.base_marker('error', 4, Marker.TEXT_VIEW_FACING, stamp)
        label.pose.position.x, label.pose.position.y, label.pose.position.z = (
            (a + b) / 2000. for a, b in zip(wanted[:3], measured[:3]))
        label.pose.position.z += .05
        label.scale.x, label.scale.z = .010, .022   # scale.x = ancho del espacio en Jazzy
        label.color.r, label.color.g, label.color.b = line.color.r, line.color.g, line.color.b
        robot = check.get('robot') or {}
        label.text = f"error {robot.get('pos_mm', 0.):.2f} mm / {robot.get('rot_deg', 0.):.2f} deg"
        self.text.publish(label)


def _estado(row, valid=True):
    if row is None or not valid:
        return 'sin dato'
    return f"{row['pos_mm']:.3f} mm / {row['rot_deg']:.3f} deg {'OK' if row['ok'] else 'FUERA'}"


def verification_lines(check):
    """Las tres comprobaciones en texto 3D (ASCII)."""
    if not check:
        return []
    controller = check.get('controlador')
    lines = ['1 IK->FK:        ' + _estado(check.get('ik_fk')),
             '2 Robot->pedida: ' + _estado(check.get('robot')),
             '3 Modelo-ABB:    ' + _estado(controller, bool(controller and controller.get('valida')))]
    robot = check.get('robot')
    if robot:
        pct = '' if robot.get('pos_pct') is None else f" ({robot['pos_pct']:.2f} % del recorrido)"
        lines.append(f"  dx {robot['dx_mm']:+.2f} dy {robot['dy_mm']:+.2f} dz {robot['dz_mm']:+.2f} mm{pct}")
    rows = [r for r in check.get('ejes') or [] if r.get('error_deg') is not None]
    cells = [f"J{r['eje']} {r['error_deg']:+.2f}" + ('' if r['error_pct'] is None else f" ({r['error_pct']:.1f}%)")
             for r in rows]
    for first in range(0, len(cells), 3):
        lines.append(('  Ejes (deg): ' if first == 0 else '              ') + '  '.join(cells[first:first + 3]))
    if check.get('envio_permitido'):
        lines.append('ENVIO PERMITIDO')
    else:
        lines += textwrap.wrap('ENVIO BLOQUEADO: ' + (check.get('motivo') or ''), width=60)
    return lines
