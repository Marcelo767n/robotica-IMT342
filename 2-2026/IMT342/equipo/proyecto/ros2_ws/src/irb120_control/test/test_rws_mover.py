"""Pruebas offline de rws_mover con un IRC5 simulado que reproduce la lógica de ServidorPC."""
import copy
import json
from pathlib import Path
import re
import sys
import unittest

sys.path[:0] = [str(Path(__file__).resolve().parents[1]),
                str(Path(__file__).resolve().parents[3] / 'src/irb120_conexion')]
from irb120_control.rws_j6 import (EMPTY, SYMBOL, MODULE_PATH, MAIN_MODULE_PATH, MASTERSHIP,
    SERVER_MODULE_SHA256, SERVER_AUTO_MODULE_SHA256, J6_MODULE_SHA256, literal, source_fingerprint,
    diagnose_inspection, module_label)
from irb120_control.rws_mover import (Mover, Refused, BASE_SYMBOL, RMMP, RMMP_POLL, split_path,
    check_target, parse_goal)

ROOT = Path(__file__).resolve().parents[1]
V2 = (ROOT / 'rapid/rws_mover/LabJointRws.mod').read_text(encoding='utf-8')
J6 = (ROOT / 'rapid/rws_j6/LabJointRws.mod').read_text(encoding='utf-8')
LIMITS = ((-165, 165), (-110, 110), (-110, 70), (-160, 160), (-120, 120), (-400, 400))


class Response:
    def __init__(self, rows=None, status=200):
        self.status_code = status
        self.text = json.dumps({'_embedded': {'_state': rows or []}})
        self.content = self.text.encode()


class Cookies(list):
    pass


class Abb:
    """Sesión requests simulada. Al escribir pcSeq, ejecuta la validación de Validar() del RAPID."""

    def __init__(self, mode='MANR'):
        self.mode = mode; self.ctrl = 'motoron'; self.execution = 'running'
        self.source = V2
        self.current = [-4.28397, -12.4929, .697668, -.640559, 3.30636, 1.73935]
        self.target = copy.deepcopy(EMPTY)
        self.nums = {'pcSeq': 0., 'pcFin': 0., 'rbSeq': 0., 'rbCodigo': 0., 'rbActivo': 1.}
        self.calls = []; self.rmmp = None; self.rmmp_answer = 'GRANTED'
        self.require_rmmp = mode.startswith('MAN'); self.respond = True; self.reads_until_done = 2
        self.pending = None; self.edit_status = 200
        self.cookies = Cookies(); self.auth = None; self.trust_env = True

    def close(self):
        pass

    def get(self, url, **kw):
        assert kw['allow_redirects'] is False
        path = url.replace('http://127.0.0.1', '')
        self.calls.append(('GET', path, kw.get('params')))
        if path == '/rw/system':
            return Response([{'_type': 'sys-system-li', 'name': '120-101516', 'rwversionname': '6.12.01.00'}])
        if path == '/rw/panel/ctrlstate': return Response([{'_type': 'pnl-ctrlstate', 'ctrlstate': self.ctrl}])
        if path == '/rw/panel/opmode': return Response([{'_type': 'pnl-opmode', 'opmode': self.mode}])
        if path == '/rw/rapid/execution': return Response([{'_type': 'rap-execution', 'ctrlexecstate': self.execution}])
        if path == MODULE_PATH: return Response([{'_type': 'rap-module-text', 'module-text': self.source}])
        if path == MAIN_MODULE_PATH:
            return Response([{'_type': 'rap-module-text', 'module-text': 'MODULE Module1\nENDMODULE\n'}])
        if path == '/rw/rapid/modules':
            return Response([{'_type': 'rap-module-info-li', 'name': n} for n in ('LabJointRws', 'Module1')])
        if path == SYMBOL: return Response([{'_type': 'rap-data', 'value': literal(self.target)}])
        if path.startswith(BASE_SYMBOL):
            return Response([{'_type': 'rap-data', 'value': format(self.nums[path[len(BASE_SYMBOL):]], 'g')}])
        if path == '/rw/rapid/tasks/T_ROB1/motion':
            self.tick()
            row = {'_type': 'rapid-jointtarget', **{f'j{i}': str(v) for i, v in enumerate(self.current, 1)},
                   **{f'ej{i}': '9E+09' for i in range(1, 7)}}
            return Response([row])
        if path == RMMP_POLL: return Response([{'_type': 'user-rmmp-poll', 'status': self.rmmp or 'NONE'}])
        raise AssertionError('GET inesperado ' + path)

    def tick(self):
        if self.pending is None or self.execution != 'running':
            return
        self.pending[1] -= 1
        if self.pending[1] <= 0:
            seq, _, target = self.pending
            self.current = list(target)
            self.nums['rbCodigo'] = 2.; self.nums['rbSeq'] = seq; self.pending = None

    def post(self, url, params=None, data=None, headers=None, **kw):
        path = url.replace('http://127.0.0.1', '')
        self.calls.append(('POST', path, dict(params or {}), dict(data or {})))
        assert headers and headers.get('Content-Type') == 'application/x-www-form-urlencoded'
        if path == RMMP:
            assert data == {'privilege': 'modify'}
            self.rmmp = self.rmmp_answer
            return Response(status=202)
        if path == MASTERSHIP: return Response(status=204)
        if path == MODULE_PATH:
            self.source = data['text']; return Response(status=self.edit_status)
        if self.require_rmmp and self.rmmp != 'GRANTED':
            return Response([{'code': '-1073445879', 'msg': 'Operation not allowed'}], status=403)
        if path == SYMBOL:
            self.target = json.loads(data['value']); return Response(status=204)
        name = path[len(BASE_SYMBOL):]
        assert name in ('pcSeq', 'pcFin'), name
        self.nums[name] = float(data['value'])
        if name == 'pcSeq' and self.respond:
            self.robot(int(self.nums['pcSeq']))
        return Response(status=204)

    def robot(self, seq):
        """Réplica de Validar() de LabJointRws v2."""
        q, now = self.target[0], self.current
        if any(abs(v) > 1000 for v in q): code = -1
        elif any(not lo + 2 <= v <= hi - 2 for v, (lo, hi) in zip(q, LIMITS)): code = -2
        elif any(abs(a - b) > 10 for a, b in zip(q, now)): code = -3
        else: code = 0
        if code:
            self.nums['rbCodigo'] = float(code); self.nums['rbSeq'] = float(seq)
        else:
            self.nums['rbCodigo'] = 1.; self.pending = [float(seq), self.reads_until_done, list(q)]


def mover(abb):
    client = Mover(abb, 'http://127.0.0.1', session_factory=lambda: abb, sleep=lambda s: None)
    client.connect()
    return client


def quiet(*args):
    pass


class RapidModule(unittest.TestCase):
    def test_hash_and_auto_variant(self):
        self.assertEqual(source_fingerprint(V2), SERVER_MODULE_SHA256)
        auto = V2.replace('CONST bool permitirAuto := FALSE;', 'CONST bool permitirAuto := TRUE;')
        self.assertEqual(source_fingerprint(auto), SERVER_AUTO_MODULE_SHA256)
        self.assertEqual(module_label(SERVER_MODULE_SHA256), 'servidor_v2')

    def test_structure(self):
        for routine in ('PROC MostrarObjetivo()', 'PROC ServidorPC()', 'LOCAL FUNC num Validar(',
                        'LOCAL FUNC bool ModoPermitido()'):
            self.assertIn(routine, V2)
        self.assertNotRegex(V2, r'PROC\s+main\b')
        code = '\n'.join(line.split('!')[0] for line in V2.splitlines())
        self.assertEqual(len(re.findall(r'\bMoveAbsJ\b', code)), 1)
        for name in ('pcTarget', 'pcSeq', 'pcFin', 'rbSeq', 'rbCodigo', 'rbActivo'):
            self.assertRegex(V2, r'PERS (num|jointtarget) ' + name + r' :=')
        # Error de la primera carga (40322): NOT después de OR/AND. No debe repetirse.
        self.assertNotRegex(V2, r'\b(OR|AND)\s+NOT\b')
        # Bloques equilibrados.
        for opening, closing in (('PROC', 'ENDPROC'), ('FUNC', 'ENDFUNC'), ('WHILE', 'ENDWHILE')):
            self.assertEqual(len(re.findall(r'\b' + opening + r'\b', V2)), len(re.findall(r'\b' + closing + r'\b', V2)))
        self.assertEqual(len(re.findall(r'\bIF\b', V2)), len(re.findall(r'\bENDIF\b', V2)))
        # rbCodigo se publica antes que rbSeq (la PC lee rbSeq y después rbCodigo).
        body = V2[V2.index('WHILE pcFin'):V2.index('ENDWHILE')]
        self.assertLess(body.rindex('rbCodigo := 2'), body.index('rbSeq := seq'))
        self.assertIn('CONST speeddata vPc := [20,5,20,5];', V2)
        self.assertIn('CONST bool permitirAuto := FALSE;', V2)


class Geometry(unittest.TestCase):
    def test_split_and_limits(self):
        current = [[0, 0, 0, 0, 30, 0], [9e9] * 6]
        legs = split_path(current, [[0, 12, 0, 0, 30, -3], [9e9] * 6], 5)
        self.assertEqual(len(legs), 3)
        self.assertAlmostEqual(legs[-1][0][1], 12)
        self.assertLessEqual(max(abs(a - b) for a, b in zip(legs[0][0], current[0])), 5 + 1e-9)
        with self.assertRaises(Refused): split_path(current, [[0, 0, 69, 0, 30, 0], [9e9] * 6], 5)
        with self.assertRaises(Refused): split_path(current, [[0, 0, 0, 0, 30, 0], [9e9] * 6], 11)
        with self.assertRaises(Refused): check_target([[0, 6, 0, 0, 30, 0], [9e9] * 6], current, 5)

    def test_parse_goal(self):
        current = [[1, 2, 3, 4, 5, 6], [9e9] * 6]
        self.assertEqual(parse_goal(['j2', '+5'], current)[0], [1, 7, 3, 4, 5, 6])
        self.assertEqual(parse_goal(['J6=', '-10'], current)[0], [1, 2, 3, 4, 5, -10])
        self.assertEqual(parse_goal('abs 0 0 0 0 30 0'.split(), current)[0], [0, 0, 0, 0, 30, 0])
        with self.assertRaises(Refused): parse_goal(['j7', '1'], current)
        with self.assertRaises(Refused): parse_goal(['abs', '1'], current)


class Protocol(unittest.TestCase):
    def test_manual_requests_rmmp_then_moves(self):
        abb = Abb('MANR'); client = mover(abb)
        result = client.move_to(parse_goal(['j6', '+5'], client.joints()), 5, echo=quiet)
        self.assertEqual(result['code'], 2)
        self.assertAlmostEqual(abb.current[5], 6.73935, places=5)
        posts = [c for c in abb.calls if c[0] == 'POST']
        self.assertEqual(posts[0][1], RMMP)
        self.assertEqual([p[1] for p in posts[1:]], [SYMBOL, BASE_SYMBOL + 'pcSeq'])
        self.assertEqual(posts[2][3]['value'], '1')
        self.assertTrue(any(c[1] == RMMP_POLL for c in abb.calls))

    def test_large_move_is_split_and_sequenced(self):
        abb = Abb('MANR'); client = mover(abb)
        client.move_to(parse_goal(['j2', '+12'], client.joints()), 5, echo=quiet)
        seqs = [c[3]['value'] for c in abb.calls if c[0] == 'POST' and c[1].endswith('pcSeq')]
        self.assertEqual(seqs, ['1', '2', '3'])
        self.assertAlmostEqual(abb.current[1], -0.4929, places=4)

    def test_rmmp_denied_writes_nothing(self):
        abb = Abb('MANR'); abb.rmmp_answer = 'DENIED'; client = mover(abb)
        with self.assertRaisesRegex(Refused, 'RMMP no concedido'):
            client.move_to(parse_goal(['j6', '+1'], client.joints()), 5, echo=quiet)
        self.assertEqual(abb.target, EMPTY)
        self.assertEqual(abb.nums['pcSeq'], 0)

    def test_not_ready_states_refuse_before_writing(self):
        cases = (('execution', 'stopped', 'RAPID detenido'), ('ctrl', 'motoroff', 'motores'),
                 ('mode', 'AUTO', 'modo AUTO'), ('mode', 'MANF', 'manual 100%'))
        for attr, value, message in cases:
            abb = Abb('MANR'); setattr(abb, attr, value); client = mover(abb)
            with self.assertRaisesRegex(Refused, message):
                client.send([[*abb.current[:5], abb.current[5] + 1], [9e9] * 6], echo=quiet)
            self.assertFalse([c for c in abb.calls if c[0] == 'POST'])
        abb = Abb('MANR'); abb.nums['rbActivo'] = 0; client = mover(abb)
        with self.assertRaisesRegex(Refused, 'rbActivo'):
            client.send([[*abb.current[:5], abb.current[5] + 1], [9e9] * 6], echo=quiet)
        abb = Abb('MANR'); abb.nums['pcSeq'] = 4; abb.nums['rbSeq'] = 3; client = mover(abb)
        with self.assertRaisesRegex(Refused, 'orden en curso'):
            client.send([[*abb.current[:5], abb.current[5] + 1], [9e9] * 6], echo=quiet)

    def test_wrong_module_refuses(self):
        abb = Abb('MANR'); abb.source = J6; client = mover(abb)
        self.assertEqual(client.module_version, 'J6_revisado')
        with self.assertRaisesRegex(Refused, 'instalar'):
            client.send([[*abb.current[:5], abb.current[5] + 1], [9e9] * 6], echo=quiet)

    def test_robot_rejection_is_reported(self):
        abb = Abb('MANR'); client = mover(abb)
        abb.current[0] = 20  # el robot está lejos de lo que la PC creyó al planificar
        target = [[-4.28397 + 1, *abb.current[1:5], abb.current[5]], [9e9] * 6]
        client.joints = lambda: [[-4.28397, *abb.current[1:]], [9e9] * 6]
        with self.assertRaisesRegex(Refused, 'código -3'):
            client.send(target, echo=quiet)

    def test_auto_requires_auto_variant_and_needs_no_rmmp(self):
        abb = Abb('AUTO'); abb.source = V2.replace('permitirAuto := FALSE', 'permitirAuto := TRUE')
        client = mover(abb)
        self.assertEqual(client.module_version, 'servidor_v2_auto')
        client.move_to(parse_goal(['j1', '-2'], client.joints()), 5, echo=quiet)
        self.assertFalse([c for c in abb.calls if c[1] == RMMP])

    def test_timeout_without_answer(self):
        abb = Abb('MANR'); abb.respond = False; client = mover(abb)
        with self.assertRaisesRegex(Refused, 'Sin respuesta'):
            client.send([[*abb.current[:5], abb.current[5] + 1], [9e9] * 6], timeout=0.01, echo=quiet)

    def test_lost_rmmp_stops_next_write(self):
        abb = Abb('MANR'); client = mover(abb)
        client.move_to(parse_goal(['j6', '+1'], client.joints()), 5, echo=quiet)
        abb.rmmp = 'NONE'; client.rmmp.last_poll = -1e9
        with self.assertRaisesRegex(Refused, 'Se perdió RMMP'):
            client.move_to(parse_goal(['j6', '+1'], client.joints()), 5, echo=quiet)

    def test_finish_writes_pcfin(self):
        abb = Abb('MANR'); client = mover(abb)
        client.finish()
        self.assertEqual(abb.nums['pcFin'], 1)

    def test_install_from_j6_requires_auto_motors_off(self):
        import tempfile
        abb = Abb('AUTO'); abb.source = J6; abb.ctrl = 'motoroff'; abb.execution = 'stopped'
        abb.require_rmmp = False
        client = mover(abb)
        with tempfile.TemporaryDirectory() as folder:
            report = client.install(Path(folder))
        self.assertTrue(report['passed'], report)
        self.assertEqual(source_fingerprint(abb.source), SERVER_MODULE_SHA256)
        abb2 = Abb('MANR'); abb2.source = J6
        with tempfile.TemporaryDirectory() as folder, self.assertRaises(Refused):
            mover(abb2).install(Path(folder))

    def test_diagnosis_accepts_v2(self):
        rows = lambda key, value: {'ok': True, 'records': [{key: value}]}
        inspection = {'resources': {
            'system': {'ok': True, 'records': [{'name': '120-101516', 'rwversionname': '6.12.01.00'}]},
            'mode': rows('opmode', 'MANR'), 'controller': rows('ctrlstate', 'motoroff'),
            'execution': rows('ctrlexecstate', 'stopped'), 'target': rows('value', literal(EMPTY)),
            'module': rows('module-text', V2)}}
        report = diagnose_inspection(inspection)
        self.assertEqual(report['module_version'], 'servidor_v2')
        self.assertTrue(report['local_navigation_prerequisites_observed'], report['issues'])


if __name__ == '__main__':
    unittest.main()
