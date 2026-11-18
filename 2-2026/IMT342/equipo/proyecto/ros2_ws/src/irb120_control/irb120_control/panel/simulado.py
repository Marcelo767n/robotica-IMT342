"""Robot ficticio con la misma interfaz que Mover, para practicar sin conexión."""
import threading
import time
import types

from irb120_control.rws_mover import MAX_STEP_DEG, check_target
from irb120_control.panel.limites import EXT


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

    def controller_pose(self):
        """Como el robtarget del ABB, pero con la FK propia (el simulador no tiene otro modelo)."""
        from irb120_control.panel.cinematica import pose_of
        q = self.joints()[0]
        return q, pose_of(q, 'brida')

    def finish(self):
        pass
