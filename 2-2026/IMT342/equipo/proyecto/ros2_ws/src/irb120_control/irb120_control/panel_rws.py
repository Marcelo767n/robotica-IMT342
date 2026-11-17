"""Panel + RViz para enviar objetivos articulares al IRB 120 por RWS (mismo canal que rws_mover).

El panel es una página local (127.0.0.1) con los seis ángulos. RViz muestra el robot
medido (sólido) y el objetivo (naranja translúcido). «Enviar al robot» usa Mover.send:
mismas validaciones, mismos límites y mismo registro que la terminal.

También acepta una pose cartesiana: la cinemática inversa de Pieper del Hito 2
(hito2/irb120/pieper.py) calcula las ramas, se elige la más cercana a la postura medida
y sus ángulos pasan a ser el objetivo. Nada se envía hasta pulsar «Enviar al robot».

No arranca RAPID ni motores: el operador sigue arrancando ServidorPC en el FlexPendant.
Cerrar el panel NO detiene el robot: habilitador, Stop o paro de emergencia.
"""
import argparse
import collections
from datetime import datetime, timezone
import fcntl
import getpass
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import tempfile
import threading
import time
import types
import webbrowser

from irb120_conexion.rutas import PROJECT
from irb120_conexion.nodos.lectura_articular.puente_rws import build_base_url
from irb120_control.rws_j6 import LIMITS, Refused
from irb120_control.rws_mover import (CODES, MARGIN_DEG, MAX_STEP_DEG, Mover, check_target, logout,
                                      split_path)

BOUNDS = [(lo + MARGIN_DEG, hi - MARGIN_DEG) for lo, hi in LIMITS]
EXT = [9e9] * 6
FRESH_S = 3.0            # una medida más antigua no se dibuja como postura actual
ACTIONS = ('objetivo', 'enviar', 'cancelar', 'sincronizar', 'paso', 'terminar', 'ik', 'herramienta')
# Punto cuya pose se muestra y se pide: el TCP del proyecto (150 mm sobre z de la brida) o la brida.
TOOLS = ('tcp', 'brida')


def clean_target(values):
    """Seis ángulos finitos en grados dentro de los límites con margen; si no, Refused."""
    if not isinstance(values, (list, tuple)) or len(values) != 6:
        raise Refused('Se esperan exactamente seis ángulos (J1..J6) en grados.')
    result = []
    for index, (value, (lo, hi)) in enumerate(zip(values, BOUNDS), start=1):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise Refused(f'J{index} no es un número válido.')
        if not lo <= value <= hi:
            raise Refused(f'J{index}={value:.3f}° fuera de [{lo:g}, {hi:g}]°.')
        result.append(float(value))
    return result


def kinematics():
    """Modelo DH y Pieper del Hito 2 (los mismos que usa supervisor.py); sin duplicar fórmulas."""
    import numpy as np
    path = str(PROJECT / 'hito2')
    if path not in sys.path:
        sys.path.insert(0, path)
    from irb120 import dh, pieper, transforms
    return np, dh, pieper, transforms


def clean_tool(tool):
    if tool not in TOOLS:
        raise Refused('Herramienta desconocida: usar «tcp» o «brida».')
    return tool


def pose_of(q_deg, tool='tcp'):
    """Cinemática directa: [x, y, z en mm, roll, pitch, yaw en grados], R = Rz(yaw) Ry(pitch) Rx(roll)."""
    np, dh, _, transforms = kinematics()
    forward = dh.forward_kinematics_tcp if clean_tool(tool) == 'tcp' else dh.forward_kinematics
    transform = forward(np.deg2rad(q_deg))
    return [float(v) for v in (*(transform[:3, 3] * 1000.), *transforms.matrix_to_rpy_deg(transform[:3, :3]))]


def solve_pose(pose, reference_deg, tool='tcp'):
    """Cinemática inversa de Pieper para una pose [x, y, z mm, roll, pitch, yaw °].

    Devuelve las 8 ramas con el criterio de selección del proyecto (rank_candidates) respecto a
    la postura de referencia, y marca cuáles caben además en los límites con margen del panel.
    """
    np, dh, pieper, transforms = kinematics()
    clean_tool(tool)
    if not isinstance(pose, (list, tuple)) or len(pose) != 6 or any(
            isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in pose):
        raise Refused('Se esperan seis números: X, Y, Z en mm y roll, pitch, yaw en grados.')
    if any(abs(v) > 2000. for v in pose[:3]) or any(abs(v) > 360. for v in pose[3:]):
        raise Refused('Pose fuera de rango: posición hasta ±2000 mm y ángulos hasta ±360°.')
    x, y, z = (v / 1000. for v in pose[:3])
    try:
        target = transforms.pose_from_xyz_rpy_deg(x, y, z, *pose[3:])
        if tool == 'brida':  # analyze_pose recibe la pose del TCP: T_tcp = T_brida · Tz(150 mm)
            target = target @ dh.tcp_transform()
        reference = np.deg2rad(reference_deg)
        report = pieper.analyze_pose(target, reference)
        decisions = pieper.rank_candidates(report, reference)
    except (ValueError, FloatingPointError, np.linalg.LinAlgError) as exc:
        raise Refused(f'La cinemática inversa no pudo evaluar la pose: {exc}') from exc
    rows = []
    for decision in decisions:
        candidate = decision.candidate
        q = None if candidate.q is None else [float(v) for v in np.rad2deg(candidate.q)]
        usable, status = False, decision.status
        if decision.admissible:
            try:
                clean_target(q)
                usable = True
            except Refused as exc:
                status = f'fuera del margen de {MARGIN_DEG:g}° del panel: {exc}'
        rows.append({'rama': candidate.branch, 'brazo': candidate.arm, 'codo': candidate.elbow,
                     'muneca': candidate.wrist, 'q': q, 'estado': status, 'puesto': decision.rank,
                     'usable': usable, 'costo': decision.weighted_cost if usable else None,
                     'cambio_max': None if q is None else max(abs(a - b) for a, b in zip(q, reference_deg))})
    usable = [row for row in rows if row['usable']]
    ranked = sorted((row for row in usable if row['puesto'] is not None), key=lambda row: row['puesto'])
    chosen = (ranked or sorted(usable, key=lambda row: row['costo']) or [None])[0]
    verdict = report.verdict
    if report.reachable and chosen is None:
        verdict = f'NO UTILIZABLE: las ramas admisibles quedan a menos de {MARGIN_DEG:g}° de un límite articular.'
    return {'veredicto': verdict, 'ramas': rows, 'elegida': None if chosen is None else chosen['rama'],
            'pose': list(pose), 'herramienta': tool}


class SimulatedMover:
    """Robot ficticio para practicar con el panel sin conexión: 5°/s y los mismos rechazos locales."""
    module_version = 'simulado'

    def __init__(self, start=(0., 0., 0., 0., 30., 0.), speed=5., sleep=time.sleep):
        self.q, self.speed, self.sleep = list(start), speed, sleep
        self.lock = threading.RLock()
        self.on_joints = None
        self.seq = 0
        self.rmmp = types.SimpleNamespace(granted=True, close=lambda: None)

    def joints(self):
        if self.on_joints is not None:
            self.on_joints(list(self.q))
        return [list(self.q), list(EXT)]

    def status(self):
        return {'opmode': 'SIMULADO', 'ctrlstate': 'motoron', 'execution': 'running',
                'joints_deg': self.joints()[0], 'module': self.module_version, 'pcSeq': float(self.seq),
                'rbSeq': float(self.seq), 'rbCodigo': 2. if self.seq else 0., 'rbActivo': 1., 'pcFin': 0.}

    def ready(self, state):
        return []

    def ensure_rmmp(self, state):
        pass

    def start_keeper(self):
        return threading.Event()

    def send(self, target, step=MAX_STEP_DEG, timeout=120., echo=print):
        start = self.joints()
        target = check_target(target, start, step)
        self.seq += 1
        duration = max(abs(a - b) for a, b in zip(target[0], start[0])) / self.speed
        began = time.monotonic()
        while True:
            k = 1. if duration <= 0 else min(1., (time.monotonic() - began) / duration)
            self.q = [a + (b - a) * k for a, b in zip(start[0], target[0])]
            q = self.joints()[0]
            error = max(abs(a - b) for a, b in zip(q, target[0]))
            echo(f'  falta {error:7.3f}° | robot: {"llegada" if k >= 1 else "moviendo"}')
            if k >= 1:
                return {'seq': self.seq, 'code': 2, 'joints_deg': q, 'max_error_deg': error}
            self.sleep(.1)

    def finish(self):
        pass


class Panel:
    """Estado compartido entre la página, RViz y el hilo que envía. Sin ROS ni HTTP: se prueba solo."""

    def __init__(self, mover, step=5., timeout=120., simulated=False, clock=time.monotonic):
        self.mover, self.timeout, self.simulated, self.clock = mover, timeout, simulated, clock
        self.step = self.clean_step(step)
        self.mutex = threading.Lock()
        self.measured = None
        self.measured_at = None
        self.state = None
        self.problems = ['Todavía no hay lectura del robot.']
        self.target = None
        self.busy = False
        self.cancel = threading.Event()
        self.progress = ''
        self.log = collections.deque(maxlen=200)
        self.worker = None
        self.tool = 'tcp'
        mover.on_joints = self._measured

    # ---------- lectura ----------
    def _measured(self, q):
        with self.mutex:
            self.measured, self.measured_at = list(q), self.clock()
            if self.target is None:
                self.target = list(q)

    def say(self, text):
        stamp = datetime.now().strftime('%H:%M:%S')
        with self.mutex:
            self.log.append(f'{stamp}  {text}')

    def poll(self, full=True):
        """Lectura periódica; se salta mientras hay un envío (que ya refresca la postura)."""
        if self.busy or not self.mover.lock.acquire(timeout=.2):
            return
        try:
            if not full:
                self.mover.joints()
                return
            state = self.mover.status()
            problems = self.mover.ready(state)
        except Exception as exc:  # red caída, 401, 503...: se muestra y se reintenta
            with self.mutex:
                self.state, self.problems = None, [f'Sin lectura del robot: {exc}']
            return
        finally:
            self.mover.lock.release()
        with self.mutex:
            self.state, self.problems = state, problems

    # ---------- órdenes de la página ----------
    @staticmethod
    def clean_step(value):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < value <= MAX_STEP_DEG:
            raise Refused(f'El paso debe estar entre 0 y {MAX_STEP_DEG:g}°.')
        return float(value)

    def set_target(self, values):
        target = clean_target(values)
        with self.mutex:
            if self.busy:
                raise Refused('Hay un envío en curso: el objetivo no se cambia hasta que termine.')
            self.target = target
        return target

    def sync(self):
        with self.mutex:
            if self.busy:
                raise Refused('Hay un envío en curso.')
            if self.measured is None:
                raise Refused('Todavía no hay lectura del robot.')
            self.target = [min(hi, max(lo, v)) for v, (lo, hi) in zip(self.measured, BOUNDS)]
            return list(self.target)

    def send(self, values):
        target = clean_target(values)
        with self.mutex:
            if self.busy:
                raise Refused('Ya hay un envío en curso.')
            if self.problems:
                raise Refused('El robot no está listo: ' + '; '.join(self.problems))
            self.busy, self.target, self.progress = True, target, ''
            self.cancel.clear()
            step = self.step
        self.worker = threading.Thread(target=self._run, args=(target, step), daemon=True, name='panel-envio')
        self.worker.start()

    def _run(self, target, step):
        try:
            with self.mover.lock:
                state = self.mover.status()
                if state['opmode'] in ('MANR', 'MANF') and not self.mover.rmmp.granted:
                    self.say('Acceso remoto: pulsar «Conceder» en el FlexPendant.')
                    self.mover.ensure_rmmp(state)
                legs = split_path([state['joints_deg'], list(EXT)], [target, list(EXT)], step)
                self.say(f'Envío en {len(legs)} orden(es) de como máximo {step:g}° por eje → ' +
                         ', '.join(f'{v:.2f}' for v in target))
                result = None
                for index, leg in enumerate(legs, 1):
                    if self.cancel.is_set():
                        self.say(f'CANCELADO antes de la orden {index}/{len(legs)}. El robot queda donde está.')
                        return
                    self._progress(f'Orden {index}/{len(legs)}')
                    result = self.mover.send(leg, step=step, timeout=self.timeout,
                                             echo=lambda line, i=index, n=len(legs): self._echo(i, n, line))
                self.say(f"LLEGADA confirmada por el robot (orden {result['seq']}), "
                         f"error máximo {result['max_error_deg']:.3f}°.")
        except Exception as exc:
            self.say(f'DETENIDO: {exc}')
        finally:
            with self.mutex:
                self.busy, self.progress = False, ''
            self.poll()

    def _progress(self, text):
        with self.mutex:
            self.progress = text

    def _echo(self, index, total, line):
        if 'AVISO' in line:
            self.say(line.strip())
        else:
            self._progress(f'Orden {index}/{total} · ' + line.strip().split(' | ', 1)[-1])

    def request_cancel(self):
        with self.mutex:
            if not self.busy:
                raise Refused('No hay ningún envío en curso.')
        self.cancel.set()
        self.say('Cancelación pedida: se detendrá al terminar la orden en curso. '
                 'Para parar YA: soltar el habilitador, Stop o paro de emergencia.')

    def set_step(self, value):
        value = self.clean_step(value)
        with self.mutex:
            self.step = value

    def finish(self):
        with self.mutex:
            if self.busy:
                raise Refused('Hay un envío en curso.')
        with self.mover.lock:
            self.mover.finish()
        self.say('pcFin=1 enviado: ServidorPC termina en el robot.')
        self.poll()

    def solve(self, pose):
        """Pose → ángulos. La rama elegida pasa a ser el objetivo (vista previa); no envía nada."""
        with self.mutex:
            if self.busy:
                raise Refused('Hay un envío en curso.')
            reference, tool = self.measured or self.target, self.tool
        if reference is None:
            raise Refused('Todavía no hay lectura del robot.')
        result = solve_pose(pose, reference, tool)
        chosen = next((row for row in result['ramas'] if row['rama'] == result['elegida']), None)
        if chosen is not None:
            result['objetivo'] = self.set_target(chosen['q'])
            self.say('Cinemática inversa: rama {rama} ({brazo}, codo {codo}, {muneca}) → '.format(**chosen) +
                     ', '.join(f'{v:.2f}' for v in chosen['q']))
        else:
            self.say('Cinemática inversa: ' + result['veredicto'])
        return result

    def set_tool(self, tool):
        tool = clean_tool(tool)
        with self.mutex:
            self.tool = tool

    def handle(self, action, body):
        if action == 'objetivo':
            return {'objetivo': self.set_target(body.get('q'))}
        if action == 'ik':
            return self.solve(body.get('pose'))
        if action == 'herramienta':
            self.set_tool(body.get('valor'))
            return {}
        if action == 'enviar':
            self.send(body.get('q'))
        elif action == 'cancelar':
            self.request_cancel()
        elif action == 'sincronizar':
            return {'objetivo': self.sync()}
        elif action == 'paso':
            self.set_step(body.get('valor'))
        elif action == 'terminar':
            self.finish()
        else:
            raise Refused('Acción desconocida.')
        return {}

    # ---------- salida ----------
    def fresh_measurement(self):
        with self.mutex:
            if self.measured is None or self.clock() - self.measured_at > FRESH_S:
                return None
            return list(self.measured)

    def snapshot(self):
        with self.mutex:
            state = self.state or {}
            age = None if self.measured_at is None else self.clock() - self.measured_at
            orders = None
            if self.measured is not None and self.target is not None:
                worst = max(abs(a - b) for a, b in zip(self.measured, self.target))
                orders = 0 if worst < .01 else len(split_path([self.measured, EXT], [self.target, EXT], self.step))
            code = state.get('rbCodigo')
            poses = {}
            for name, q in (('pose_medida', self.measured), ('pose_objetivo', self.target)):
                try:
                    poses[name] = None if q is None else pose_of(q, self.tool)
                except Exception:  # el panel de ángulos sigue funcionando sin el modelo
                    poses[name] = None
            return {**poses, 'herramienta': self.tool, 'simulado': self.simulated, 'modo': state.get('opmode'), 'motores': state.get('ctrlstate'),
                    'rapid': state.get('execution'), 'modulo': state.get('module'),
                    'servidor_activo': state.get('rbActivo') == 1,
                    'ultimo': None if code is None else CODES.get(int(code), str(code)),
                    'medido': self.measured, 'edad_s': age, 'objetivo': self.target, 'limites': BOUNDS,
                    'paso': self.step, 'paso_max': MAX_STEP_DEG, 'ordenes': orders, 'ocupado': self.busy,
                    'faltas': list(self.problems), 'listo': not self.problems and not self.busy,
                    'progreso': self.progress, 'registro': list(self.log)}


def serve(panel, port, page=None):
    """Servidor solo en 127.0.0.1. Las órdenes exigen el testigo de la página y Host local."""
    token = secrets.token_urlsafe(24)
    page = (page or Path(__file__).with_name('panel_rws.html').read_text(encoding='utf-8'))
    page = page.replace('__TOKEN__', token).encode()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, body, mime='application/json'):
            if not isinstance(body, bytes):
                body = json.dumps(body, allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def local(self):
            real_port = self.server.server_address[1]
            return self.headers.get('Host', '') in (f'127.0.0.1:{real_port}', f'localhost:{real_port}')

        def do_GET(self):
            if not self.local():
                return self.reply(403, {'ok': False, 'error': 'Solo acceso local.'})
            if self.path == '/':
                return self.reply(200, page, 'text/html; charset=utf-8')
            if self.path == '/estado':
                return self.reply(200, panel.snapshot())
            self.reply(404, {'ok': False, 'error': 'No existe.'})

        def do_POST(self):
            action = self.path[len('/api/'):] if self.path.startswith('/api/') else None
            sent = self.headers.get('X-Panel-Token', '')
            if not self.local() or action not in ACTIONS or not hmac.compare_digest(sent.encode(), token.encode()):
                return self.reply(403, {'ok': False, 'error': 'Petición no autorizada.'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 <= length <= 4096:
                    raise ValueError('tamaño')
                body = json.loads(self.rfile.read(length) or b'{}')
                if not isinstance(body, dict):
                    raise ValueError('forma')
            except ValueError:
                return self.reply(400, {'ok': False, 'error': 'Cuerpo no válido.'})
            try:
                self.reply(200, {'ok': True, **panel.handle(action, body)})
            except Refused as exc:
                self.reply(200, {'ok': False, 'error': str(exc)})
            except Exception as exc:  # p. ej. fallo de red al terminar
                self.reply(200, {'ok': False, 'error': f'Fallo: {exc}'})

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True, name='panel-http').start()
    return server, token


def prepare_view(folder):
    """Reutiliza los dos modelos (medido/objetivo) del control por RViz, sin los marcadores EGM."""
    import yaml
    from irb120_control.arranque import prepare_models
    folder = prepare_models(folder)
    config = yaml.safe_load((folder / 'control.rviz').read_text())
    manager = config['Visualization Manager']
    manager['Displays'] = [d for d in manager['Displays'] if d.get('Class') not in
                           ('rviz_default_plugins/InteractiveMarkers', 'rviz_default_plugins/Marker')]
    for display in manager['Displays']:
        if display.get('TF Prefix') == 'medido':
            display['Name'] = 'ROBOT · postura medida'
        elif display.get('TF Prefix') == 'objetivo':
            display['Name'] = 'OBJETIVO del panel · naranja'
    (folder / 'panel.rviz').write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False))
    return folder


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--host', default='192.168.125.1')
    parser.add_argument('--user', default='Default User')
    parser.add_argument('--http-port', type=int, default=80, help='Puerto RWS; distinto de 80 solo en 127.0.0.1')
    parser.add_argument('--panel-port', type=int, default=8770, help='Puerto local de la página del panel')
    parser.add_argument('--paso', type=float, default=5., help='Máximo cambio por eje en cada orden (≤10°)')
    parser.add_argument('--timeout', type=float, default=120., help='Segundos de espera por orden')
    parser.add_argument('--simulado', action='store_true', help='Sin robot: practicar con un robot ficticio')
    parser.add_argument('--no-rviz', action='store_true')
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--duration', type=float, default=0, help=argparse.SUPPRESS)
    parser.add_argument('--log-dir', type=Path, default=PROJECT / 'salidas/control_articular/rws_mover')
    args = parser.parse_args(argv)
    if not 0 < args.paso <= MAX_STEP_DEG:
        parser.error('--paso debe estar entre 0 y 10')
    if not 1024 <= args.panel_port <= 65535:
        parser.error('--panel-port debe estar entre 1024 y 65535')
    try:
        base = build_base_url(args.host, args.http_port)
    except ValueError as exc:
        parser.error(str(exc))
    from irb120_control.rviz_control import model_joints
    model_joints()  # no se inicia si modelo/URDF discrepan
    args.log_dir.mkdir(parents=True, exist_ok=True)
    # Mismos tópicos que control_*: nunca las dos sesiones a la vez.
    instance_lock = PROJECT / 'salidas/control_articular/instancia.lock'
    instance_lock.parent.mkdir(parents=True, exist_ok=True)
    instance_file = instance_lock.open('a')
    try:
        fcntl.flock(instance_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        instance_file.close()
        parser.error('Ya hay una sesión de control o de panel abierta. Cerrarla antes de iniciar otra.')

    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import JointState
    session = mover = keeper = server = node = None
    children = []
    stop = threading.Event()
    try:
        if args.simulado:
            mover = SimulatedMover()
            print('MODO SIMULADO: no se conecta a ningún robot.')
        else:
            import requests
            from requests.auth import HTTPDigestAuth
            password = getpass.getpass(f'Contraseña RWS de "{args.user}" (no se guarda): ')
            session = requests.Session()
            session.trust_env = False
            session.auth = HTTPDigestAuth(args.user, password)
            stamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%fZ')
            mover = Mover(session, base, session_factory=requests.Session, log=args.log_dir / f'panel_{stamp}.jsonl')
            identity = mover.connect()
            print(f"Controlador {identity['name']} | RobotWare {identity['rwversionname']} | "
                  f"módulo {mover.module_version}")
        panel = Panel(mover, step=args.paso, timeout=args.timeout, simulated=args.simulado)
        panel.poll()
        if not args.simulado and panel.state is not None:
            # Pedir RMMP ahora, con el robot quieto, y no en medio del primer envío.
            try:
                mover.ensure_rmmp(panel.state)
            except Refused as exc:
                print('AVISO:', exc, '— se volverá a pedir en el primer envío.', flush=True)
        keeper = mover.start_keeper()

        def reader():
            count = 0
            while not stop.wait(.3):
                panel.poll(full=count % 5 == 0)
                count += 1
        threading.Thread(target=reader, daemon=True, name='panel-lectura').start()

        server, _ = serve(panel, args.panel_port)
        url = f'http://127.0.0.1:{server.server_address[1]}/'
        rclpy.init(args=[])
        node = Node('irb120_panel_rws', cli_args=['--ros-args', '-r', '/tf:=/irb120/control/tf',
                                                 '-r', '/tf_static:=/irb120/control/tf_static'],
                    use_global_arguments=False)
        # Los dos árboles (frame_prefix medido/ y objetivo/) cuelgan del Fixed Frame de RViz.
        from geometry_msgs.msg import TransformStamped
        from tf2_ros.static_transform_broadcaster import StaticTransformBroadcaster
        static = StaticTransformBroadcaster(node)
        anchors = []
        for prefix in ('medido/', 'objetivo/'):
            anchor = TransformStamped()
            anchor.header.stamp = node.get_clock().now().to_msg()
            anchor.header.frame_id, anchor.child_frame_id = 'base_link', prefix + 'base_link'
            anchor.transform.rotation.w = 1.
            anchors.append(anchor)
        static.sendTransform(anchors)
        measured_pub = node.create_publisher(JointState, '/irb120/control/medido/joint_states', 10)
        target_pub = node.create_publisher(JointState, '/irb120/control/objetivo/joint_states', 10)

        def publish():
            stamp = node.get_clock().now().to_msg()
            with panel.mutex:
                target = None if panel.target is None else list(panel.target)
            for publisher, q in ((measured_pub, panel.fresh_measurement()), (target_pub, target)):
                if q is None:
                    continue
                message = JointState()
                message.header.stamp = stamp
                message.name = [f'joint_{i + 1}' for i in range(6)]
                message.position = [math.radians(v) for v in q]
                publisher.publish(message)
        node.create_timer(.1, publish)

        with tempfile.TemporaryDirectory(prefix='irb120_panel_') as directory:
            folder = prepare_view(directory)
            for name in ('medido', 'objetivo'):
                children.append(subprocess.Popen(
                    ['/opt/ros/jazzy/lib/robot_state_publisher/robot_state_publisher', '--ros-args',
                     '--params-file', str(folder / (name + '.yaml')), '-r', f'__node:=irb120_rsp_{name}',
                     '-r', f'joint_states:=/irb120/control/{name}/joint_states',
                     '-r', f'/robot_description:=/irb120/control/{name}/robot_description',
                     '-r', '/tf:=/irb120/control/tf', '-r', '/tf_static:=/irb120/control/tf_static']))
            if not args.no_rviz:
                children.append(subprocess.Popen(['rviz2', '-d', str(folder / 'panel.rviz'), '--ros-args',
                                                  '-r', '/tf:=/irb120/control/tf',
                                                  '-r', '/tf_static:=/irb120/control/tf_static']))
            print(f'\nPANEL: {url}\n'
                  'RViz: robot sólido = postura medida; naranja = objetivo del panel.\n'
                  'Escribir o deslizar los ángulos (grados) y pulsar «Enviar al robot».\n'
                  'Cerrar el panel NO detiene el robot: habilitador, Stop o paro de emergencia.\n'
                  'Ctrl+C aquí cierra panel y RViz.\n', flush=True)
            if not args.no_browser:
                threading.Thread(target=lambda: webbrowser.open(url), daemon=True).start()

            def interrupt(*_):
                raise KeyboardInterrupt
            signal.signal(signal.SIGTERM, interrupt)
            started = time.monotonic()
            while rclpy.ok():
                rclpy.spin_once(node, timeout_sec=.05)
                if any(child.poll() is not None for child in children):
                    break
                if args.duration and time.monotonic() - started >= args.duration:
                    break
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    except Refused as exc:
        print('DETENIDO:', exc, flush=True)
        return 2
    except OSError as exc:  # incluye errores de red de requests y puerto ocupado
        print('No se pudo iniciar el panel:', exc, flush=True)
        return 2
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        stop.set()
        if keeper is not None:
            keeper.set()
        if server is not None:
            server.shutdown()
        if mover is not None and not args.simulado:
            mover.rmmp.close()
            logout(mover)
        if session is not None:
            session.close()
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        instance_file.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
