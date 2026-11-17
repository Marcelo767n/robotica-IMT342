"""Estado compartido del panel: objetivo, lectura del robot, envío en segundo plano y registro.

Lo usan por igual el panel de RViz (tópicos ROS), los controles 3D y la página web opcional.
Sin ROS ni HTTP: se prueba solo.
"""
import collections
from datetime import datetime
import threading
import time

from irb120_control.rws_j6 import Refused
from irb120_control.rws_mover import CODES, MAX_STEP_DEG, split_path
from irb120_control.panel.cinematica import clean_tool, pose_of, solve_pose
from irb120_control.panel.limites import BOUNDS, EXT, clean_target

FRESH_S = 3.0            # una medida más antigua no se dibuja como postura actual
ACTIONS = ('objetivo', 'enviar', 'cancelar', 'sincronizar', 'paso', 'terminar', 'ik', 'herramienta')


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

    def solve(self, pose, quiet=False):
        """Pose → ángulos. La rama elegida pasa a ser el objetivo (vista previa); no envía nada.

        quiet=True no escribe en el registro (se usa mientras se arrastra el control de RViz)."""
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
