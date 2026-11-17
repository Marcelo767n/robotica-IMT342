"""Panel de ángulos: lógica y servidor local. Sin ROS, sin RViz y sin red externa."""
import json
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from irb120_control.panel_rws import BOUNDS, Panel, SimulatedMover, clean_target, pose_of, serve, solve_pose
from irb120_control.rws_j6 import Refused
from test_rws_mover import Abb, mover


def wait_idle(panel, seconds=5.):
    limit = time.monotonic() + seconds
    while panel.busy and time.monotonic() < limit:
        time.sleep(.01)
    if panel.worker is not None:
        panel.worker.join(timeout=seconds)
    assert not panel.busy


class PanelLogic(unittest.TestCase):
    def sim(self, **kw):
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
        for bad in (0, 11, 'x', None, True):
            with self.assertRaises(Refused):
                panel.handle('paso', {'valor': bad})
        with self.assertRaises(Refused):
            panel.handle('borrar', {})

    def test_real_mover_protocol_through_panel(self):
        abb = Abb('AUTO'); abb.source = abb.source.replace('permitirAuto := FALSE', 'permitirAuto := TRUE')
        abb.require_rmmp = False
        client = mover(abb)
        panel = Panel(client)
        panel.poll()
        self.assertEqual(panel.problems, [])
        goal = list(abb.current); goal[5] += 8.
        panel.send(goal)
        wait_idle(panel)
        self.assertAlmostEqual(abb.current[5], goal[5], places=4)
        self.assertEqual(abb.nums['rbSeq'], 2.)
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
        panel.send(result['objetivo'])
        wait_idle(panel)
        for got, expected in zip(panel.mover.q, goal):
            self.assertAlmostEqual(got, expected, places=6)


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
