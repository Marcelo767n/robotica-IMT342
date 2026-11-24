"""Puesta en marcha guiada en AUTO: pide solo lo que falta y en orden."""
import threading
import unittest

from irb120_control.panel.sesion import preparar_auto
from irb120_control.rws_j6 import EMPTY


class FakeRobot:
    """El «operador» cambia el estado cada vez que la sesión espera (sleep)."""

    def __init__(self, module='servidor_v3_auto', opmode='MANR', ctrl='motoron', execution='running'):
        self.lock = threading.RLock()
        self.s = {'opmode': opmode, 'module': module, 'ctrlstate': ctrl, 'execution': execution, 'rbActivo': 0.}
        self.target = [[1.] * 6, [9e9] * 6]
        self.calls = []
        self.operator = []          # acciones del operador, una por espera
        self.ours = False           # True cuando el programa en marcha es ServidorPC

    def status(self):
        return dict(self.s)

    def sleep(self, _):
        if self.operator:
            self.operator.pop(0)(self.s)

    def get_target(self):
        return self.target

    def set_target(self, target):
        self.calls.append('limpiar'); self.target = target

    def install(self, folder, auto=False):
        assert auto and self.s['ctrlstate'] == 'motoroff' and self.target == EMPTY
        self.calls.append('instalar'); self.s['module'] = 'servidor_v5_auto'
        return {'passed': True}

    def connect(self):
        self.calls.append('connect')

    def pointer(self):
        where = 'LabJointRws ServidorPC' if self.s['execution'] == 'running' and self.ours else 'MainModule main'
        return {}, where

    def start_server(self, echo=print):
        assert self.s['ctrlstate'] == 'motoron' and self.s['opmode'] == 'AUTO'
        self.calls.append('arrancar'); self.s['execution'] = 'running'; self.ours = True


class Sesion(unittest.TestCase):
    def test_full_guided_start_from_manual_with_old_module(self):
        robot = FakeRobot()
        lines = []
        robot.operator = [lambda s: s.update(opmode='AUTO'),                      # llave a AUTO
                          lambda s: s.update(execution='stopped', ctrlstate='motoroff'),  # Stop + Motors Off
                          lambda s: s.update(ctrlstate='motoron'),                 # Motors On
                          lambda s: s.update(rbActivo=1.)]                         # «Iniciar»
        preparar_auto(robot, None, echo=lines.append, sleep=robot.sleep, timeout=5.)
        self.assertEqual(robot.calls, ['limpiar', 'instalar', 'connect', 'arrancar'])
        text = '\n'.join(lines)
        for step in ('AUTO', 'Motors Off', 'Motors On', 'Iniciar', 'ServidorPC activo'):
            self.assertIn(step, text)

    def test_missed_confirmation_restarts_and_other_program_is_stopped_first(self):
        # Reconexión: el robot quedó con main de otro grupo en marcha; el primer «Iniciar» se pasa del plazo.
        robot = FakeRobot(module='servidor_v5_auto', opmode='AUTO', ctrl='motoron', execution='running')
        lines = []
        robot.operator = [lambda s: s.update(execution='stopped'),     # el operador pulsa Stop
                          lambda s: s.update(execution='stopped'),     # nadie pulsa Iniciar: ServidorPC termina
                          lambda s: s.update(rbActivo=1.)]             # segundo intento: «Iniciar»
        preparar_auto(robot, None, echo=lines.append, sleep=robot.sleep, timeout=5.)
        self.assertEqual(robot.calls, ['arrancar', 'arrancar'])
        text = '\n'.join(lines)
        self.assertIn('otro programa', text)
        self.assertIn('intento 1/3', text)

    def test_v4_found_in_auto_is_replaced_even_if_running(self):
        # La v4 (45° por orden, sin pcTipo) ya no es válida: se reinstala la v5 aunque ServidorPC esté activo.
        robot = FakeRobot(module='servidor_v4_auto', opmode='AUTO', ctrl='motoron', execution='running')
        robot.s['rbActivo'] = 1.
        lines = []
        robot.operator = [lambda s: s.update(execution='stopped', ctrlstate='motoroff'),   # Stop + Motors Off
                          lambda s: s.update(ctrlstate='motoroff'),
                          lambda s: s.update(ctrlstate='motoron'),                          # Motors On
                          lambda s: s.update(rbActivo=1.)]                                  # «Iniciar»
        preparar_auto(robot, None, echo=lines.append, sleep=robot.sleep, timeout=5.)
        self.assertEqual(robot.calls[:3], ['limpiar', 'instalar', 'connect'])
        self.assertEqual(robot.s['module'], 'servidor_v5_auto')
        self.assertIn('v5', '\n'.join(lines))

    def test_already_running_does_nothing(self):
        robot = FakeRobot(module='servidor_v5_auto', opmode='AUTO'); robot.s['rbActivo'] = 1.
        preparar_auto(robot, None, echo=lambda _: None, sleep=robot.sleep, timeout=1.)
        self.assertEqual(robot.calls, [])

    def test_ready_module_only_needs_motors_and_start(self):
        robot = FakeRobot(module='servidor_v5_auto', opmode='AUTO', ctrl='motoroff', execution='stopped')
        robot.operator = [lambda s: s.update(ctrlstate='motoron'), lambda s: s.update(rbActivo=1.)]
        preparar_auto(robot, None, echo=lambda _: None, sleep=robot.sleep, timeout=5.)
        self.assertEqual(robot.calls, ['arrancar'])


if __name__ == '__main__':
    unittest.main()
