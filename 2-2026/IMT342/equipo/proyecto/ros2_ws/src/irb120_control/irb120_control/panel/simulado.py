"""Robot ficticio con la misma interfaz que Mover, para practicar sin conexión."""
import threading
import time
import types

from irb120_control.rws_mover import MAX_STEP_DEG, check_target
from irb120_control.panel.limites import EXT


class SimulatedMover:
    """Robot ficticio para practicar con el panel sin conexión: 5°/s y los mismos rechazos locales."""
    module_version = 'simulado'

    def __init__(self, start=(0., 0., 0., 0., 30., 0.), speed=None, sleep=time.sleep):
        self.q, self.sleep = list(start), sleep
        self.pct = 20
        self.fixed_speed = speed                 # grados/s fijos (pruebas); None = según el %
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
                'rbSeq': float(self.seq), 'rbCodigo': 2. if self.seq else 0., 'rbActivo': 1., 'pcFin': 0.,
                'pcVelPct': float(self.pct)}

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
        speed = self.fixed_speed or 0.6 * self.pct    # 100 % ≈ 60°/s, como vMax del RAPID v4
        duration = max(abs(a - b) for a, b in zip(target[0], start[0])) / speed
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

    def set_speed(self, pct):
        from irb120_control.rws_j6 import Refused
        if isinstance(pct, bool) or not isinstance(pct, (int, float)) or not 1 <= pct <= 100:
            raise Refused('La velocidad debe estar entre 1 y 100 %.')
        self.pct = int(round(pct))
        return self.pct

    def controller_pose(self):
        """Como el robtarget del ABB, pero con la FK propia (el simulador no tiene otro modelo)."""
        from irb120_control.panel.cinematica import pose_of
        q = self.joints()[0]
        return q, pose_of(q, 'brida')

    def finish(self):
        pass
