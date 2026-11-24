"""Estado compartido del panel: objetivo, lectura del robot, envío en segundo plano y registro.

Lo usan por igual el panel de RViz (tópicos ROS), los controles 3D y la página web opcional.
Sin ROS ni HTTP: se prueba solo.
"""
import collections
from datetime import datetime
import threading
import time

from irb120_control.rws_j6 import Refused
from irb120_control.rws_mover import CODES, MAX_STEP_DEG, SPEED_MAX_DEG_S, SPEED_MAX_MM_S, move_to, split_path
from irb120_control.panel.buzon import Buzon
from irb120_control.panel.cinematica import clean_tool, convertir_herramienta, pose_of, solve_pose
from irb120_control.panel.limites import BOUNDS, EXT, clean_target
from irb120_control.panel import verificacion
from irb120_control.panel.trayectoria import Ejecutor

FRESH_S = 3.0            # una medida más antigua no se dibuja como postura actual
ACTIONS = ('objetivo', 'enviar', 'cancelar', 'sincronizar', 'paso', 'terminar', 'ik', 'herramienta', 'posicion',
           'velocidad', 'trayectoria', 'vista_previa', 'pausar', 'reanudar', 'buzon_tomar', 'buzon_vaciar',
           'punto_externo')
ACCIONES_GRANDES = ('trayectoria', 'vista_previa')   # llevan la trayectoria entera: hasta 64 KiB
MAX_ORDEN_BYTES = 4096
MAX_ORDEN_GRANDE_BYTES = 65536
DEFAULT_SPEED_PCT = 20
# Posición 0 = calibración ABB (todos los ejes en 0°). Reposo = igual con la muñeca doblada (J5 30°),
# fuera de la singularidad de muñeca de J5 = 0°, cómoda para empezar a arrastrar la pose.
POSICIONES = {'cero': [0.] * 6, 'reposo': [0., 0., 0., 0., 30., 0.]}


class Panel:
    """Estado compartido entre la página, RViz y el hilo que envía. Sin ROS ni HTTP: se prueba solo."""

    def __init__(self, mover, step=MAX_STEP_DEG, timeout=120., simulated=False, clock=time.monotonic):
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
        self.desired = None        # pose pedida por IK [mm, °] en self.tool; None si el objetivo son ángulos
        self.reachable = True
        self.abb = None            # (q leído, pose tool0 del ABB, instante) para la verificación 3
        self.start = None          # ejes al empezar la última orden (base del error en %)
        self.speed_pct = None      # velocidad en % de vMax; se lee del robot (pcVelPct)
        self.buzon = Buzon()
        self.ejecutor = Ejecutor(self)
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
        """Lectura periódica; se salta mientras hay un envío (que ya refresca la postura).

        full=False solo lee los ejes; full=True lee además estado, faltas y la pose del ABB."""
        if self.busy or not self.mover.lock.acquire(timeout=.2):
            return
        abb = None
        try:
            if not full:
                self.mover.joints()
                return
            state = self.mover.status()
            problems = self.mover.ready(state)
            try:
                q_abb, abb_pose = verificacion.pose_controlador(self.mover)
                abb = (q_abb, abb_pose, self.clock())
            except Exception:  # sin robtarget: la verificación 3 queda sin dato y el envío bloqueado
                abb = None
        except Exception as exc:  # red caída, 401, 503...: se muestra y se reintenta
            with self.mutex:
                self.state, self.problems = None, [f'Sin lectura del robot: {exc}']
            return
        finally:
            self.mover.lock.release()
        with self.mutex:
            self.state, self.problems = state, problems
            if state.get('pcVelPct') is not None:
                self.speed_pct = int(round(state['pcVelPct']))
            if abb is not None:
                self.abb = abb

    # ---------- órdenes de la página ----------
    @staticmethod
    def clean_step(value):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < value <= MAX_STEP_DEG:
            raise Refused(f'El paso debe estar entre 0 y {MAX_STEP_DEG:g}°.')
        return float(value)

    def set_target(self, values, desired=None):
        """desired: pose [mm, °] que se pidió por IK; None si el objetivo se dio en ángulos."""
        target = clean_target(values)
        with self.mutex:
            if self.busy or self.ejecutor.previsualizando:
                raise Refused('Hay un envío o una vista previa en curso: el objetivo no se cambia hasta que termine.')
            self.target, self.desired, self.reachable = target, desired, True
            self.start = None   # el error en % se mide desde el inicio de la próxima orden
        return target

    def verification(self):
        with self.mutex:
            target, measured, desired, tool = self.target, self.measured, self.desired, self.tool
            abb, busy, reachable, start = self.abb, self.busy, self.reachable, self.start
        return verificacion.evaluar(target, measured, desired, tool, abb, busy, self.simulated, self.clock(),
                                    reachable, start)

    def sync(self):
        with self.mutex:
            if self.busy or self.ejecutor.previsualizando:
                raise Refused('Hay un envío en curso.')
            if self.measured is None:
                raise Refused('Todavía no hay lectura del robot.')
            self.target = [min(hi, max(lo, v)) for v, (lo, hi) in zip(self.measured, BOUNDS)]
            return list(self.target)

    def send(self, values):
        target = clean_target(values)
        with self.mutex:
            same = self.target is not None and all(abs(a - b) < 1e-9 for a, b in zip(target, self.target))
        if not same:
            self.set_target(target)   # ángulos nuevos: se verifican como objetivo articular
        check = self.verification()
        if not check['envio_permitido']:
            raise Refused('Envío bloqueado por la verificación: ' + check['motivo'])
        with self.mutex:
            if self.busy or self.ejecutor.previsualizando:
                raise Refused('Ya hay un envío o una vista previa en curso.')
            if self.problems:
                raise Refused('El robot no está listo: ' + '; '.join(self.problems))
            self.busy, self.progress = True, ''
            self.start = None if self.measured is None else list(self.measured)
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
                self.say('Envío → ' + ', '.join(f'{v:.2f}' for v in target))
                result = move_to(self.mover, [target, list(EXT)], step, self.timeout, echo=self._echo,
                                 cancel=self.cancel)
                self._arrival_note = True
                self.say(f"LLEGADA confirmada por el robot (orden {result['seq']}), "
                         f"error máximo {result['max_error_deg']:.3f}°.")
        except Exception as exc:
            self.say(f'DETENIDO: {exc}')
        finally:
            with self.mutex:
                self.busy, self.progress = False, ''
            self.poll()
            if getattr(self, '_arrival_note', False):
                self._arrival_note = False
                check = self.verification()
                if check and check['robot']:
                    robot = check['robot']
                    self.say(f"Verificación tras la llegada: pose real frente a la pedida {robot['pos_mm']:.3f} mm "
                             f"(dx {robot['dx_mm']:+.3f}, dy {robot['dy_mm']:+.3f}, dz {robot['dz_mm']:+.3f} mm) / "
                             f"{robot['rot_deg']:.3f}°, error articular máx. {robot['max_eje_deg']:.3f}° "
                             f"({'dentro' if robot['ok'] else 'FUERA'} de tolerancia).")
                    pct = ', '.join(f"J{row['eje']} {row['error_deg']:+.3f}°"
                                    + ('' if row['error_pct'] is None else f" ({row['error_pct']:.2f} %)")
                                    for row in check['ejes'] if row['error_deg'] is not None)
                    self.say('Error por eje (respecto al recorrido de la orden): ' + pct)

    def _progress(self, text):
        with self.mutex:
            self.progress = text

    def _echo(self, line):
        line = line.strip()
        if line.startswith('Orden '):
            self._order = line.split(' →')[0]
            self._progress(self._order)
        elif line.startswith(('Recorrido', 'AVISO')):
            self.say(line)
        else:
            self._progress(getattr(self, '_order', 'Orden') + ' · ' + line.split(' | ', 1)[-1])

    def request_cancel(self):
        with self.mutex:
            if not self.busy and not self.ejecutor.previsualizando:
                raise Refused('No hay ningún envío en curso.')
        self.cancel.set()
        self.say('Cancelación pedida: se detendrá al terminar la orden en curso. '
                 'Para parar YA: soltar el habilitador, Stop o paro de emergencia.')

    def set_speed(self, value):
        """Velocidad de las próximas órdenes en % (100 % = 250 mm/s y 60°/s). No durante un envío."""
        with self.mutex:
            if self.busy:
                raise Refused('Hay una orden en curso: cambiar la velocidad cuando termine.')
        with self.mover.lock:
            pct = self.mover.set_speed(value)
        with self.mutex:
            self.speed_pct = pct
        self.say(f'Velocidad = {pct} % (≈ {SPEED_MAX_MM_S * pct / 100:.0f} mm/s, {SPEED_MAX_DEG_S * pct / 100:.0f}°/s).')
        return pct

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

    def solve(self, pose, quiet=False):
        """Pose → ángulos. La rama elegida pasa a ser el objetivo (vista previa); no envía nada.

        quiet=True no escribe en el registro (se usa mientras se arrastra el control de RViz)."""
        with self.mutex:
            if self.busy or self.ejecutor.previsualizando:
                raise Refused('Hay un envío en curso.')
            reference, tool = self.measured or self.target, self.tool
        if reference is None:
            raise Refused('Todavía no hay lectura del robot.')
        result = solve_pose(pose, reference, tool)
        chosen = next((row for row in result['ramas'] if row['rama'] == result['elegida']), None)
        if chosen is not None:
            result['objetivo'] = self.set_target(chosen['q'], desired=list(result['pose']))
        else:
            with self.mutex:
                self.reachable = False   # se conserva el objetivo anterior, pero no se envía
        if quiet:
            pass
        elif chosen is not None:
            self.say('Cinemática inversa: rama {rama} ({brazo}, codo {codo}, {muneca}) → '.format(**chosen) +
                     ', '.join(f'{v:.2f}' for v in chosen['q']))
        else:
            self.say('Cinemática inversa: ' + result['veredicto'])
        return result

    def nudge(self, axis, delta):
        """Suma delta grados a un eje del objetivo (vista previa)."""
        with self.mutex:
            base = None if self.target is None else list(self.target)
        if base is None or axis not in range(6):
            raise Refused('Todavía no hay objetivo.')
        base[axis] += delta
        return self.set_target(base)

    def target_copy(self):
        with self.mutex:
            return None if self.target is None else list(self.target)

    def set_tool(self, tool):
        tool = clean_tool(tool)
        with self.mutex:
            if tool != self.tool and self.desired is not None and self.target is not None:
                self.desired = pose_of(self.target, tool)   # la misma pose, vista desde el otro punto
            self.tool = tool

    # ---------- buzón de puntos ----------
    def agregar_desde_rviz(self, medida=False):
        """Mete en el buzón la pose del objetivo naranja (o, con medida=True, la postura real del robot)."""
        with self.mutex:
            q = self.measured if medida else self.target
            q, tool = None if q is None else list(q), self.tool
        if q is None:
            raise Refused('Todavía no hay lectura del robot.' if medida else 'Todavía no hay objetivo.')
        entry = self.buzon.agregar('rviz', pose_of(q, tool), tool, q=q)
        self.say(f"Buzón: punto {entry['nombre']} ({'postura medida' if medida else 'objetivo'}) desde RViz.")
        return entry

    def punto_externo(self, pose, nombre=None, origen='vision', herramienta='tcp'):
        """Punto de la visión o de un script. `pose` [x, y, z mm, roll, pitch, yaw °] en base_link y referida al
        punto `herramienta` (por defecto el TCP del proyecto). Debe ser alcanzable por IK; si no, se registra como
        rechazado y no entra al buzón. En el buzón queda referida al punto de referencia del panel."""
        try:
            clean_tool(herramienta)
            with self.mutex:
                reference, tool = self.measured or self.target, self.tool
            if reference is None:
                raise Refused('Todavía no hay lectura del robot para evaluar la cinemática inversa.')
            result = solve_pose(pose, reference, herramienta)
            if result['elegida'] is None:
                raise Refused('Pose no alcanzable: ' + result['veredicto'])
            entry = self.buzon.agregar(origen, convertir_herramienta(result['pose'], herramienta, tool), tool,
                                       nombre=nombre)
        except Refused as exc:
            self.buzon.rechazar(origen, str(exc))
            self.say(f'Buzón: punto de {origen} rechazado: {exc}')
            raise
        self.say(f"Buzón: punto {entry['nombre']} de {origen}.")
        return entry

    def handle(self, action, body):
        if action == 'trayectoria':
            return {'trayectoria': self.ejecutor.preparar(body)}
        if action == 'vista_previa':
            return self.ejecutor.vista_previa(body)
        if action == 'pausar':
            return {'trayectoria': self.ejecutor.pausar()}
        if action == 'reanudar':
            return {'trayectoria': self.ejecutor.reanudar()}
        if action == 'buzon_tomar':
            entries, last = self.buzon.tomar(body.get('desde_id', 0))
            return {'entradas': entries, 'ultimo_id': last}
        if action == 'buzon_vaciar':
            self.buzon.vaciar()
            return {}
        if action == 'punto_externo':
            return {'punto': self.punto_externo(body.get('pose'), body.get('nombre'), 'http',
                                                body.get('herramienta', 'tcp'))}
        if action == 'objetivo':
            return {'objetivo': self.set_target(body.get('q'))}
        if action == 'ik':
            return self.solve(body.get('pose'))
        if action == 'velocidad':
            return {'velocidad_pct': self.set_speed(body.get('valor'))}
        if action == 'posicion':
            name = body.get('valor')
            if name not in POSICIONES:
                raise Refused('Posición desconocida: usar «cero» o «reposo».')
            target = self.set_target(POSICIONES[name])
            self.say(f'Objetivo = posición {name}: ' + ', '.join(f'{v:g}' for v in target) +
                     '. Revisar el robot naranja y pulsar «Enviar al robot».')
            return {'objetivo': target}
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
        shot = self._snapshot()
        try:
            shot['verificacion'] = self.verification()
        except Exception as exc:  # el panel sigue funcionando aunque falle el modelo
            shot['verificacion'] = None
            shot['faltas'] = shot['faltas'] + [f'Verificación no disponible: {exc}']
        return shot

    def _snapshot(self):
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
                    'paso': self.step, 'paso_max': MAX_STEP_DEG, 'posiciones': POSICIONES,
                    'velocidad_pct': self.speed_pct,
                    'velocidad_mm_s': None if self.speed_pct is None else SPEED_MAX_MM_S * self.speed_pct / 100,
                    'velocidad_deg_s': None if self.speed_pct is None else SPEED_MAX_DEG_S * self.speed_pct / 100, 'ordenes': orders, 'ocupado': self.busy,
                    'faltas': list(self.problems), 'listo': not self.problems and not self.busy,
                    'progreso': self.progress, 'registro': list(self.log),
                    'buzon': self.buzon.ultimas(), 'buzon_rechazados': self.buzon.ultimos_rechazos(),
                    'trayectoria': self.ejecutor.estado()}
