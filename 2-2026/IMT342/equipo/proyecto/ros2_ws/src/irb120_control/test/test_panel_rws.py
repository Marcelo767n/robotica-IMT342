"""Panel de ángulos: lógica y servidor local. Sin ROS, sin RViz y sin red externa."""
import json
import math
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from irb120_control.panel.cinematica import pose_of, solve_pose
from irb120_control.panel.estado import Panel
from irb120_control.panel.limites import BOUNDS, clean_target
from irb120_control.panel.ordenes import Ordenes, finite
from irb120_control.panel.simulado import SimulatedMover
from irb120_control.panel.web import serve
from irb120_control.rws_j6 import Refused
from test_rws_mover import Abb, mover
from irb120_control.panel import verificacion
from irb120_control.panel.cinematica import kinematics


class AbbConPose(Abb):
    """El ABB simulado responde también robtarget (Base/tool0) con la FK de su postura."""

    def __init__(self, *args, offset_mm=0., **kwargs):
        super().__init__(*args, **kwargs)
        self.offset_mm = offset_mm

    def get(self, url, **kw):
        if url.endswith('/rw/motionsystem/mechunits/ROB_1/robtarget'):
            np, _, _, transforms = kinematics()
            pose = pose_of(self.current, 'brida')
            x, y, z, w = transforms.matrix_to_quaternion(transforms.rpy_to_matrix(*np.deg2rad(pose[3:])))
            from test_rws_mover import Response
            return Response([{'_type': 'ms-robtargets', 'x': pose[0] + self.offset_mm, 'y': pose[1], 'z': pose[2],
                              'q1': w, 'q2': x, 'q3': y, 'q4': z}])
        return super().get(url, **kw)


def wait_idle(panel, seconds=5.):
    limit = time.monotonic() + seconds
    while panel.busy and time.monotonic() < limit:
        time.sleep(.01)
    if panel.worker is not None:
        panel.worker.join(timeout=seconds)
    assert not panel.busy


class PanelLogic(unittest.TestCase):
    def sim(self, **kw):
        kw.setdefault('step', 5.)   # tramos de 5° para comprobar la división
        panel = Panel(SimulatedMover(speed=5000., sleep=lambda _: None), simulated=True, **kw)
        panel.poll()
        return panel

    def test_clean_target_rejects_bad_input(self):
        good = [0., 0., 0., 0., 30., 0.]
        self.assertEqual(clean_target(good), good)
        for bad in ([0.] * 5, 'abc', None, [0., 0., 0., 0., float('nan'), 0.], [True, 0., 0., 0., 0., 0.],
                    [0., 0., 0., 0., 0., '5'], [164., 0., 0., 0., 0., 0.], [0., 0., 69., 0., 0., 0.]):
            with self.assertRaises(Refused):
                clean_target(bad)
        self.assertEqual(BOUNDS[2], (-108, 68))

    def test_first_reading_sets_target_and_snapshot(self):
        panel = self.sim()
        shot = panel.snapshot()
        self.assertEqual(shot['medido'], [0., 0., 0., 0., 30., 0.])
        self.assertEqual(shot['objetivo'], shot['medido'])
        self.assertTrue(shot['listo'] and shot['simulado'])
        self.assertEqual(shot['ordenes'], 0)
        json.dumps(shot, allow_nan=False)

    def test_preview_then_send_splits_and_arrives(self):
        panel = self.sim()
        panel.handle('objetivo', {'q': [12., 0., 0., 0., 30., 0.]})
        self.assertEqual(panel.snapshot()['ordenes'], 3)
        self.assertEqual(panel.mover.q[0], 0.)  # previsualizar no mueve
        panel.handle('enviar', {'q': [12., 0., 0., 0., 30., 0.]})
        wait_idle(panel)
        self.assertAlmostEqual(panel.mover.q[0], 12.)
        self.assertEqual(panel.mover.seq, 3)
        self.assertTrue(any('LLEGADA' in line for line in panel.log))

    def test_send_refused_when_not_ready_or_busy(self):
        panel = self.sim()
        panel.problems = ['motores guardstop']
        with self.assertRaisesRegex(Refused, 'no está listo'):
            panel.send([5., 0., 0., 0., 30., 0.])
        panel.problems = []
        panel.busy = True
        for action, body in (('enviar', {'q': [5., 0., 0., 0., 30., 0.]}), ('objetivo', {'q': [1.] * 6}),
                             ('sincronizar', {}), ('terminar', {})):
            with self.assertRaises(Refused):
                panel.handle(action, body)
        self.assertEqual(panel.mover.seq, 0)

    def test_cancel_stops_before_next_order(self):
        panel = self.sim()
        original = panel.mover.send

        def send(*args, **kw):
            result = original(*args, **kw)
            panel.cancel.set()
            return result
        panel.mover.send = send
        panel.send([20., 0., 0., 0., 30., 0.])
        wait_idle(panel)
        self.assertEqual(panel.mover.seq, 1)
        self.assertAlmostEqual(panel.mover.q[0], 5.)
        self.assertTrue(any('CANCELADO' in line for line in panel.log))
        with self.assertRaises(Refused):
            panel.request_cancel()

    def test_step_and_unknown_action(self):
        panel = self.sim()
        panel.handle('paso', {'valor': 2})
        self.assertEqual(panel.snapshot()['paso'], 2.)
        for bad in (0, 41, 'x', None, True):
            with self.assertRaises(Refused):
                panel.handle('paso', {'valor': bad})
        with self.assertRaises(Refused):
            panel.handle('borrar', {})

    def test_real_mover_protocol_through_panel(self):
        abb = AbbConPose('AUTO'); abb.source = abb.source.replace('permitirAuto := FALSE', 'permitirAuto := TRUE')
        abb.require_rmmp = False
        client = mover(abb)
        panel = Panel(client)
        panel.poll()
        self.assertEqual(panel.problems, [])
        goal = list(abb.current); goal[5] += 8.
        panel.send(goal)
        wait_idle(panel)
        self.assertAlmostEqual(abb.current[5], goal[5], places=3)
        self.assertEqual(abb.nums['rbSeq'], 1.)   # v3: 8° en una sola orden, sin paradas
        self.assertTrue(any('LLEGADA' in line for line in panel.log), list(panel.log))

    def test_robot_rejection_is_reported_not_raised(self):
        abb = Abb('MANR'); abb.execution = 'stopped'
        panel = Panel(mover(abb))
        panel.poll()
        self.assertTrue(any('RAPID detenido' in p for p in panel.problems))
        self.assertFalse(panel.snapshot()['listo'])
        with self.assertRaises(Refused):
            panel.send([v + 1 for v in abb.current])
        self.assertFalse(any(c[0] == 'POST' and 'pcSeq' in c[1] for c in abb.calls))


class PanelKinematics(unittest.TestCase):
    Q = [0.386, 4.139, -3.719, 2.666, 31.382, 3.565]  # postura medida en el IRC5 el 16/11/2026

    def test_home_pose_matches_abb_tool0(self):
        pose = pose_of([0.] * 6, 'brida')
        for got, expected in zip(pose, (374., 0., 630., 0., 90., 0.)):
            self.assertAlmostEqual(got, expected, places=6)
        self.assertAlmostEqual(pose_of([0.] * 6, 'tcp')[0], 524., places=6)

    def test_inverse_recovers_measured_posture_for_both_tools(self):
        for tool in ('tcp', 'brida'):
            result = solve_pose(pose_of(self.Q, tool), self.Q, tool)
            chosen = next(row for row in result['ramas'] if row['rama'] == result['elegida'])
            for got, expected in zip(chosen['q'], self.Q):
                self.assertAlmostEqual(got, expected, places=6)
            self.assertEqual(len(result['ramas']), 8)
            json.dumps(result, allow_nan=False)

    def test_unreachable_and_bad_poses(self):
        result = solve_pose([1400., 100., 350., 0., 180., 0.], self.Q)
        self.assertIsNone(result['elegida'])
        self.assertIn('NO ALCANZABLE', result['veredicto'])
        json.dumps(result, allow_nan=False)
        for bad in ([1., 2., 3.], None, [float('inf')] * 6, [5000., 0., 0., 0., 0., 0.], ['1'] * 6):
            with self.assertRaises(Refused):
                solve_pose(bad, self.Q)
        with self.assertRaises(Refused):
            solve_pose([400., 100., 350., 0., 180., 0.], self.Q, 'pinza')

    def test_panel_solve_previews_but_does_not_move(self):
        panel = Panel(SimulatedMover(start=self.Q, speed=5000., sleep=lambda _: None), simulated=True)
        panel.poll()
        goal = list(self.Q); goal[0] += 12.; goal[2] += 6.
        result = panel.handle('ik', {'pose': pose_of(goal, 'tcp')})
        for got, expected in zip(result['objetivo'], goal):
            self.assertAlmostEqual(got, expected, places=6)
        self.assertEqual(panel.mover.seq, 0)
        self.assertEqual(panel.mover.q, self.Q)
        shot = panel.snapshot()
        self.assertEqual(shot['herramienta'], 'tcp')
        for got, expected in zip(shot['pose_objetivo'], pose_of(goal, 'tcp')):
            self.assertAlmostEqual(got, expected, places=6)
        panel.handle('herramienta', {'valor': 'brida'})
        self.assertAlmostEqual(panel.snapshot()['pose_medida'][0], pose_of(self.Q, 'brida')[0])
        with self.assertRaises(Refused):
            panel.handle('herramienta', {'valor': 'otra'})
        unreachable = panel.handle('ik', {'pose': [1400., 100., 350., 0., 180., 0.]})
        self.assertNotIn('objetivo', unreachable)
        with self.assertRaisesRegex(Refused, 'no es alcanzable'):   # el último pedido no era alcanzable
            panel.send(result['objetivo'])
        self.assertEqual(panel.mover.seq, 0)
        panel.handle('herramienta', {'valor': 'tcp'})
        panel.handle('ik', {'pose': pose_of(goal, 'tcp')})
        panel.send(result['objetivo'])
        wait_idle(panel)
        for got, expected in zip(panel.mover.q, goal):
            self.assertAlmostEqual(got, expected, places=6)


class PanelOrders(unittest.TestCase):
    """Las órdenes que manda el panel C++ de RViz por /irb120/panel/orden."""

    def setUp(self):
        self.panel = Panel(SimulatedMover(speed=5000., sleep=lambda _: None), simulated=True)
        self.panel.poll()
        self.orders = Ordenes(self.panel)

    def state(self):
        return json.loads(self.orders.estado())

    def test_objective_ik_and_send_round_trip(self):
        self.orders.atender(json.dumps({'id': 1, 'accion': 'objetivo', 'q': [4., 0., 0., 0., 30., 0.]}))
        state = self.state()
        self.assertEqual(state['respuesta'], {'id': 1, 'accion': 'objetivo', 'ok': True, 'error': None})
        self.assertEqual(state['objetivo'], [4., 0., 0., 0., 30., 0.])
        goal = [10., -4., 8., 5., 35., -6.]
        self.orders.atender(json.dumps({'id': 2, 'accion': 'ik', 'pose': pose_of(goal, 'tcp')}))
        state = self.state()
        self.assertEqual(state['ik']['id'], 2)
        self.assertEqual(len(state['ik']['ramas']), 8)
        for got, expected in zip(state['objetivo'], goal):
            self.assertAlmostEqual(got, expected, places=6)
        self.orders.atender(json.dumps({'id': 3, 'accion': 'enviar', 'q': state['objetivo']}))
        wait_idle(self.panel)
        for got, expected in zip(self.panel.mover.q, goal):
            self.assertAlmostEqual(got, expected, places=6)
        self.assertTrue(self.state()['respuesta']['ok'])

    def test_bad_orders_are_reported_not_raised(self):
        for text, error in (('{no json', 'JSON'), ('[1, 2]', 'objeto'), ('{"id": 4, "accion": "borrar"}', 'desconocida'),
                            ('{"id": 5, "accion": "objetivo", "q": [999, 0, 0, 0, 0, 0]}', 'fuera'),
                            ('x' * 5000, 'grande')):
            answer = self.orders.atender(text)
            self.assertFalse(answer['ok'])
            self.assertIn(error, answer['error'])
        self.assertEqual(self.panel.mover.seq, 0)
        self.assertIn('rechazada', self.state()['registro'][-1])

    def test_state_is_strict_json(self):
        self.assertIsNone(finite(float('nan')))
        self.assertEqual(finite({'a': [1., float('inf')]}), {'a': [1., None]})
        unreachable = pose_of([0.] * 6, 'tcp'); unreachable[0] = 1400.
        self.orders.atender(json.dumps({'id': 6, 'accion': 'ik', 'pose': unreachable}))
        state = self.state()
        self.assertIsNone(state['ik']['elegida'])
        for key in ('modo', 'motores', 'medido', 'objetivo', 'limites', 'pose_medida', 'faltas', 'listo'):
            self.assertIn(key, state)


class PanelVerification(unittest.TestCase):
    """IK → FK, robot real frente a la pose pedida y modelo frente al controlador; bloqueo del envío."""
    Q = [0.386, 4.139, -3.719, 2.666, 31.382, 3.565]

    def test_exact_ik_and_controller_allow_sending(self):
        goal = [10., -4., 8., 5., 35., -6.]
        check = verificacion.evaluar(goal, self.Q, pose_of(goal, 'tcp'), 'tcp',
                                     abb=(self.Q, pose_of(self.Q, 'brida'), 0.), now=1.)
        self.assertTrue(check['envio_permitido'], check['motivo'])
        self.assertLess(check['ik_fk']['pos_mm'], 1e-6)
        self.assertLess(check['controlador']['pos_mm'], 1e-6)
        self.assertFalse(check['robot']['ok'])          # todavía no ha llegado
        self.assertAlmostEqual(check['robot']['max_eje_deg'], 11.719, places=3)
        arrived = verificacion.evaluar(goal, goal, pose_of(goal, 'tcp'), 'tcp', abb=(goal, pose_of(goal, 'brida'), 0.), now=1.)
        self.assertTrue(arrived['robot']['ok'])

    def test_blocking_reasons(self):
        good_abb = (self.Q, pose_of(self.Q, 'brida'), 0.)
        far = pose_of(self.Q, 'brida'); far[0] += 2.
        cases = [
            (dict(abb=None), 'controlador'),
            (dict(abb=(self.Q, far, 0.)), 'difieren'),
            (dict(abb=good_abb, busy=True), 'orden en curso'),
            (dict(abb=good_abb, now=60.), 'controlador'),                       # dato viejo
            (dict(abb=good_abb, reachable=False), 'alcanzable'),
        ]
        for kwargs, reason in cases:
            kwargs.setdefault('now', 1.)
            check = verificacion.evaluar(self.Q, self.Q, None, 'tcp', **kwargs)
            self.assertFalse(check['envio_permitido'], kwargs)
            self.assertIn(reason, check['motivo'])
        wrong = pose_of(self.Q, 'tcp'); wrong[2] += 1.
        check = verificacion.evaluar(self.Q, self.Q, wrong, 'tcp', abb=good_abb, now=1.)
        self.assertIn('IK→FK', check['motivo'])
        check = verificacion.evaluar([0., 0., 69.5, 0., 0., 0.], self.Q, None, 'tcp', abb=good_abb, now=1.)
        self.assertFalse(check['limites_ok'])
        json.dumps(check, allow_nan=False)

    def test_model_controller_mismatch_blocks_real_send(self):
        abb = AbbConPose('AUTO', offset_mm=3.); abb.source = abb.source.replace('permitirAuto := FALSE', 'permitirAuto := TRUE')
        abb.require_rmmp = False
        panel = Panel(mover(abb)); panel.poll()
        goal = list(abb.current); goal[5] += 5.
        with self.assertRaisesRegex(Refused, 'difieren'):
            panel.send(goal)
        self.assertFalse(any(c[0] == 'POST' and 'pcSeq' in c[1] for c in abb.calls))

    def test_arrival_is_verified_in_the_log(self):
        panel = Panel(SimulatedMover(speed=5000., sleep=lambda _: None), simulated=True); panel.poll()
        goal = [8., -3., 6., 0., 40., 5.]
        panel.handle('ik', {'pose': pose_of(goal, 'tcp')})
        panel.send(panel.target_copy())
        wait_idle(panel)
        line = next(l for l in panel.log if 'Verificación tras la llegada' in l)
        self.assertIn('dentro de tolerancia', line)
        self.assertTrue(any('Error por eje' in l for l in panel.log))
        check = panel.snapshot()['verificacion']
        self.assertTrue(check['robot']['ok'])
        self.assertEqual(check['inicio'], [0., 0., 0., 0., 30., 0.])
        self.assertLess(abs(check['robot']['dx_mm']), 1e-6)
        self.assertIsNone(check['ejes'][3]['error_pct'])          # J4 no se movió: sin %
        self.assertLess(check['ejes'][0]['error_pct'], 1e-6)       # J1 recorrió 8°

    def test_percent_error_per_joint_and_mm(self):
        rows = verificacion.ejes([10., 0., 5., 0., 30., 0.], [9.9, 0., 5.2, 0., 30., 0.], [0., 0., 0., 0., 30., 0.])
        self.assertAlmostEqual(rows[0]['error_pct'], 1.0)          # 0,1° de 10°
        self.assertAlmostEqual(rows[2]['error_pct'], 4.0)          # 0,2° de 5°
        self.assertIsNone(rows[1]['error_pct'])
        q = [10., 0., 5., 0., 30., 0.]
        check = verificacion.evaluar(q, [9.9, 0., 5.2, 0., 30., 0.], None, 'tcp',
                                     abb=(q, pose_of(q, 'brida'), 0.), now=1., start=[0., 0., 0., 0., 30., 0.])
        robot = check['robot']
        self.assertAlmostEqual(robot['pos_mm'], math.dist((0, 0, 0), (robot['dx_mm'], robot['dy_mm'], robot['dz_mm'])))
        self.assertGreater(robot['pos_pct'], 0.)

    def test_round_trip_and_matrices(self):
        q = [10., -4., 8., 5., 35., -6.]
        rows, ok = verificacion.ida_vuelta(q, 'tcp')
        self.assertTrue(ok)
        self.assertLess(max(r['error_deg'] for r in rows), 1e-6)
        check = verificacion.evaluar(q, q, pose_of(q, 'tcp'), 'tcp', abb=(q, pose_of(q, 'brida'), 0.), now=1.)
        self.assertTrue(check['ida_vuelta_ok'])
        self.assertEqual(len(check['matrices']['T_fk']), 4)
        diff = max(abs(a - b) for ra, rb in zip(check['matrices']['T_pedida'], check['matrices']['T_fk'])
                   for a, b in zip(ra, rb))
        self.assertLess(diff, 1e-9)
        self.assertEqual(check['tolerancias']['ik_mm'], 0.001)

    def test_speed_action(self):
        panel = Panel(SimulatedMover(), simulated=True); panel.poll()
        self.assertEqual(panel.snapshot()['velocidad_pct'], 20)
        panel.handle('velocidad', {'valor': 60})
        shot = panel.snapshot()
        self.assertEqual((shot['velocidad_pct'], shot['velocidad_mm_s']), (60, 150.))
        for bad in (0, 101, 'x'):
            with self.assertRaises(Refused):
                panel.handle('velocidad', {'valor': bad})

    def test_quick_reads_do_not_freeze_the_panel(self):
        panel = Panel(SimulatedMover(), simulated=True)
        for full in (False, True, False, True):
            panel.poll(full=full)
        self.assertTrue(panel.mover.lock.acquire(timeout=.1))     # nadie se quedó con el candado
        panel.mover.lock.release()
        self.assertIsNotNone(panel.abb)


class PanelHttp(unittest.TestCase):
    def setUp(self):
        self.panel = Panel(SimulatedMover(speed=5000., sleep=lambda _: None), simulated=True)
        self.panel.poll()
        self.server, self.token = serve(self.panel, 0, page='<html>__TOKEN__</html>')
        self.url = f'http://127.0.0.1:{self.server.server_address[1]}'
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def call(self, path, body=None, token=None, host=None):
        headers = {'Content-Type': 'application/json'}
        if token is not None:
            headers['X-Panel-Token'] = token
        if host is not None:
            headers['Host'] = host
        request = urllib.request.Request(self.url + path, headers=headers,
                                         data=None if body is None else json.dumps(body).encode())
        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.read()

    def test_page_and_state(self):
        status, body = self.call('/')
        self.assertEqual(status, 200)
        self.assertIn(self.token.encode(), body)
        status, body = self.call('/estado')
        self.assertEqual(json.loads(body)['medido'], [0., 0., 0., 0., 30., 0.])
        self.assertEqual(self.call('/otra')[0], 404)

    def test_orders_need_token_and_local_host(self):
        goal = {'q': [5., 0., 0., 0., 30., 0.]}
        self.assertEqual(self.call('/api/enviar', goal)[0], 403)
        self.assertEqual(self.call('/api/enviar', goal, token='x' * 32)[0], 403)
        self.assertEqual(self.call('/api/enviar', goal, token=self.token, host='evil.example:80')[0], 403)
        self.assertEqual(self.call('/estado', host='evil.example:80')[0], 403)
        self.assertEqual(self.call('/api/apagar', {}, token=self.token)[0], 403)
        self.assertEqual(self.panel.mover.seq, 0)
        status, body = self.call('/api/enviar', goal, token=self.token)
        self.assertEqual((status, json.loads(body)), (200, {'ok': True}))
        wait_idle(self.panel)
        self.assertAlmostEqual(self.panel.mover.q[0], 5.)

    def test_bad_bodies_and_refusals(self):
        status, body = self.call('/api/objetivo', {'q': [999.] * 6}, token=self.token)
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(body)['ok'])
        self.assertEqual(self.call('/api/objetivo', [1, 2], token=self.token)[0], 400)
        request = urllib.request.Request(self.url + '/api/objetivo', data=b'{no json',
                                         headers={'X-Panel-Token': self.token})
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=3)
        self.assertEqual(caught.exception.code, 400)


if __name__ == '__main__':
    unittest.main()
