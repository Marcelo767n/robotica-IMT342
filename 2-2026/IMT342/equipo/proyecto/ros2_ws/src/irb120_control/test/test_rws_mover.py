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
    SERVER_MODULE_SHA256, SERVER_AUTO_MODULE_SHA256, SERVER_V4_SHA256, SERVER_V4_AUTO_SHA256, SERVER_LABELS,
    J6_MODULE_SHA256, literal, source_fingerprint, diagnose_inspection, module_label)
from irb120_control.rws_j6 import parse_target
from irb120_control.rws_mover import (Mover, Refused, BASE_SYMBOL, RMMP, RMMP_POLL, split_path,
    check_target, parse_goal, format_robtarget, parse_robtarget, same_pose, normalize_pose, move_tramo,
    MAX_STEP_DEG, RAPID_MAX_STEP_DEG)

ROOT = Path(__file__).resolve().parents[1]
V2 = (ROOT / 'rapid/rws_mover/LabJointRws.mod').read_text(encoding='utf-8')
J6 = (ROOT / 'rapid/rws_j6/LabJointRws.mod').read_text(encoding='utf-8')
V4 = (ROOT / 'test/fixtures/LabJointRws_v4.mod').read_text(encoding='utf-8')   # v4 anterior (45° por orden)
POSE = [300., 50., 250., 0., 1., 0., 0.]
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
        self.nums = {'pcSeq': 0., 'pcFin': 0., 'rbSeq': 0., 'rbCodigo': 0., 'rbActivo': 1., 'pcVelPct': 20., 'pcTipo': 0.}
        self.pose_text = '[[9E+09,9E+09,9E+09],[1,0,0,0],[0,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]]'
        self.max_step = 360        # maxPasoDeg del módulo
        self.arrival_offset = 0.   # error de llegada (°) en J1 tras un MoveL, p. ej. otra configuración
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
        if path == BASE_SYMBOL + 'pcPose': return Response([{'_type': 'rap-data', 'value': self.pose_text}])
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
        assert name in ('pcSeq', 'pcFin', 'pcVelPct', 'pcTipo', 'pcPose'), name
        if name == 'pcPose':
            self.pose_text = data['value']; return Response(status=204)
        self.nums[name] = float(data['value'])
        if name == 'pcSeq' and self.respond:
            self.robot(int(self.nums['pcSeq']))
        return Response(status=204)

    def robot(self, seq):
        """Réplica de Validar() de LabJointRws v2."""
        q, now = self.target[0], self.current
        if any(abs(v) > 1000 for v in q): code = -1
        elif any(not lo + 2 <= v <= hi - 2 for v, (lo, hi) in zip(q, LIMITS)): code = -2
        elif any(abs(a - b) > self.max_step for a, b in zip(q, now)): code = -3
        elif self.nums.get('pcTipo', 0.) not in (0., 1.): code = -5
        else: code = 0
        if code:
            self.nums['rbCodigo'] = float(code); self.nums['rbSeq'] = float(seq)
        else:
            end = list(q)
            if self.nums.get('pcTipo', 0.) == 1.: end[0] += self.arrival_offset
            self.nums['rbCodigo'] = 1.; self.pending = [float(seq), self.reads_until_done, end]


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
        self.assertEqual(module_label(SERVER_MODULE_SHA256), 'servidor_v5')
        self.assertEqual(module_label(SERVER_AUTO_MODULE_SHA256), 'servidor_v5_auto')
        self.assertEqual(SERVER_LABELS, ('servidor_v5', 'servidor_v5_auto'))

    def test_v4_is_recognised_for_replacement(self):
        self.assertEqual(source_fingerprint(V4), SERVER_V4_SHA256)
        self.assertEqual(source_fingerprint(V4.replace('permitirAuto := FALSE', 'permitirAuto := TRUE')),
                         SERVER_V4_AUTO_SHA256)
        self.assertEqual(module_label(SERVER_V4_SHA256), 'servidor_v4')
        self.assertEqual(module_label(SERVER_V4_AUTO_SHA256), 'servidor_v4_auto')

    def test_v5_size_and_new_pers(self):
        from irb120_control.rws_j6 import MODULE_TEXT_MAX
        self.assertLessEqual(len(V2), MODULE_TEXT_MAX)
        self.assertLessEqual(len(V2.replace('FALSE', 'TRUE')), MODULE_TEXT_MAX)
        self.assertRegex(V2, r'PERS num pcTipo := 0;')
        self.assertRegex(V2, r'PERS robtarget pcPose := ')
        self.assertIn('CONST num maxPasoDeg := 360;', V2)
        self.assertIn('RETURN -5;', V2)

    def test_v5_moves_with_fine_and_conf_off_only_around_movel(self):
        code = '\n'.join(line.split('!')[0] for line in V2.splitlines())
        self.assertEqual(len(re.findall(r'\bMoveL\b', code)), 1)
        self.assertEqual(len(re.findall(r'\bMoveAbsJ\b', code)), 1)
        self.assertRegex(code, r'ConfL\\Off;\s*MoveL destino,vOrden,fine,tool0\\WObj:=wobj0;\s*ConfL\\On;')
        self.assertNotRegex(code, r'\bz\d+\b')   # ninguna zona de paso: siempre fine
        # pcTipo y pcPose se copian a locales al tomar la orden, junto con pcTarget.
        self.assertRegex(code, r'tipo := pcTipo;\s*destino := pcPose;')
        self.assertLess(code.index('tipo := pcTipo'), code.index('Validar(objetivo.robax'))

    def test_fingerprint_ignores_live_values_of_new_pers(self):
        live = V2.replace('pcTipo := 0;', 'pcTipo := 1;').replace(
            '[[9E9,9E9,9E9],[1,0,0,0],[0,0,0,0]', '[[300.5,50,250],[0,1,0,0],[0,0,0,0]')
        self.assertNotEqual(live, V2)
        self.assertEqual(source_fingerprint(live), SERVER_MODULE_SHA256)

    def test_structure(self):
        for routine in ('PROC MostrarObjetivo()', 'PROC ServidorPC()', 'LOCAL FUNC num Validar(',
                        'LOCAL FUNC bool ModoPermitido()'):
            self.assertIn(routine, V2)
        self.assertNotRegex(V2, r'PROC\s+main\b')
        code = '\n'.join(line.split('!')[0] for line in V2.splitlines())
        self.assertEqual(len(re.findall(r'\bMoveAbsJ\b', code)), 1)
        for name in ('pcTarget', 'pcSeq', 'pcFin', 'rbSeq', 'rbCodigo', 'rbActivo', 'pcTipo', 'pcPose'):
            self.assertRegex(V2, r'PERS (num|jointtarget|robtarget) ' + name + r' :=')
        # Error de la primera carga (40322): NOT después de OR/AND. No debe repetirse.
        self.assertNotRegex(V2, r'\b(OR|AND)\s+NOT\b')
        # Bloques equilibrados.
        for opening, closing in (('PROC', 'ENDPROC'), ('FUNC', 'ENDFUNC'), ('WHILE', 'ENDWHILE')):
            self.assertEqual(len(re.findall(r'\b' + opening + r'\b', V2)), len(re.findall(r'\b' + closing + r'\b', V2)))
        self.assertEqual(len(re.findall(r'\bIF\b', V2)), len(re.findall(r'\bENDIF\b', V2)))
        # rbCodigo se publica antes que rbSeq (la PC lee rbSeq y después rbCodigo).
        body = V2[V2.index('WHILE pcFin'):V2.index('ENDWHILE')]
        self.assertLess(body.rindex('rbCodigo := 2'), body.index('rbSeq := seq'))
        self.assertIn('CONST speeddata vMax := [250,60,250,60];', V2)
        self.assertIn('PERS num pcVelPct := 20;', V2)
        self.assertIn('CONST bool permitirAuto := FALSE;', V2)


class Geometry(unittest.TestCase):
    def test_split_and_limits(self):
        current = [[0, 0, 0, 0, 30, 0], [9e9] * 6]
        legs = split_path(current, [[0, 12, 0, 0, 30, -3], [9e9] * 6], 5)
        self.assertEqual(len(legs), 3)
        self.assertAlmostEqual(legs[-1][0][1], 12)
        self.assertLessEqual(max(abs(a - b) for a, b in zip(legs[0][0], current[0])), 5 + 1e-9)
        with self.assertRaises(Refused): split_path(current, [[0, 0, 69, 0, 30, 0], [9e9] * 6], 5)
        with self.assertRaises(Refused): split_path(current, [[0, 0, 0, 0, 30, 0], [9e9] * 6], 356)
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
        self.assertAlmostEqual(abb.current[5], 6.73935, places=3)   # se escribe con 3 decimales
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
        self.assertAlmostEqual(abb.current[1], -0.4929, places=3)

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

    def test_module_fits_the_rws_text_limit_and_long_ones_are_refused(self):
        # 17/11: la v4 de 5605 caracteres quedó cortada a 5000 en el IRC5.
        from irb120_control.rws_j6 import MODULE_TEXT_MAX
        self.assertLessEqual(len(V2.replace('permitirAuto := FALSE', 'permitirAuto := TRUE')), MODULE_TEXT_MAX)
        import tempfile
        abb = Abb('AUTO'); abb.source = V2; abb.ctrl = 'motoroff'; abb.execution = 'stopped'; abb.require_rmmp = False
        client = mover(abb)
        with tempfile.TemporaryDirectory() as folder:
            long = Path(folder) / 'largo.mod'
            text = V2.replace('MODULE LabJointRws', 'MODULE LabJointRws\n' + '    ! relleno\n' * 40)
            long.write_text(text)
            with self.assertRaisesRegex(Refused, 'cortaría'):
                client.update_module(Path(folder), candidate_path=long, candidate_sha=source_fingerprint(text))
        self.assertFalse([c for c in abb.calls if c[0] == 'POST'])

    def test_older_module_without_speed_variable_still_reads_status(self):
        # 17/11: el robot tenía la v3 (sin pcVelPct) y status() fallaba con HTTP 400 antes de instalar la v4.
        abb = Abb('AUTO'); del abb.nums['pcVelPct']; client = mover(abb)
        client.module_version = 'servidor_v3_auto'
        state = client.status()
        self.assertNotIn('pcVelPct', state)
        self.assertIn('instalar la v5', ' '.join(client.ready(state)))
        with self.assertRaisesRegex(Refused, 'instalar la v5'):
            client.set_speed(50)

    def test_speed_percent_is_written_and_validated(self):
        abb = Abb('MANR'); client = mover(abb)
        self.assertEqual(client.set_speed(55), 55)
        self.assertEqual(abb.nums['pcVelPct'], 55.)
        for bad in (0, 101, 'x', True, None):
            with self.assertRaises(Refused):
                client.set_speed(bad)
        self.assertEqual(abb.nums['pcVelPct'], 55.)

    def test_start_server_in_auto_sets_and_checks_pointer(self):
        class AbbPP(Abb):
            def __init__(self, mode, land='LabJointRws'):
                super().__init__(mode); self.pp = ('MainModule', 'main'); self.land = land
                self.source = V2.replace('permitirAuto := FALSE', 'permitirAuto := TRUE')
                self.execution = 'stopped'; self.require_rmmp = False

            def get(self, url, **kw):
                if url.endswith('/rw/rapid/tasks/T_ROB1/pcp'):
                    return Response([{'_type': 'pcp-info', '_title': 'progpointer',
                                      'modulemame': self.pp[0], 'routinename': self.pp[1]}])
                return super().get(url, **kw)

            def post(self, url, params=None, data=None, headers=None, **kw):
                path = url.replace('http://127.0.0.1', '')
                if path == '/rw/rapid/tasks/T_ROB1/pcp':
                    self.calls.append(('POST', path, dict(params), dict(data)))
                    self.pp = (self.land, data['routine']); return Response(status=200)
                if path == '/rw/rapid/execution':
                    self.calls.append(('POST', path, dict(params), dict(data)))
                    self.execution = 'running'; return Response(status=204)
                return super().post(url, params=params, data=data, headers=headers, **kw)
        abb = AbbPP('AUTO'); client = mover(abb)
        client.start_server(echo=quiet)
        posts = [c[1] for c in abb.calls if c[0] == 'POST']
        self.assertEqual(posts, [MASTERSHIP, '/rw/rapid/tasks/T_ROB1/pcp', '/rw/rapid/execution', MASTERSHIP])
        self.assertEqual(abb.execution, 'running')
        bad = AbbPP('AUTO', land='MainModule'); client = mover(bad)   # el PP no quedó donde debía
        with self.assertRaisesRegex(Refused, 'NO se arranca'):
            client.start_server(echo=quiet)
        self.assertNotIn('/rw/rapid/execution', [c[1] for c in bad.calls if c[0] == 'POST'])
        manual = AbbPP('MANR'); client = mover(manual)
        with self.assertRaisesRegex(Refused, 'Solo en AUTO'):
            client.start_server(echo=quiet)

    def test_readback_of_angles_over_100_deg_with_6_digits(self):
        # 16/11-17/11: el ABB devuelve 6 cifras (101.664) y la PC había escrito 101.664181… → «no coincide».
        abb = Abb('MANR'); abb.current = [5., 10., -30., 101.6641, -20., 112.33]
        original = abb.get

        def six_digits(url, **kw):
            response = original(url, **kw)
            if url.endswith('pcTarget'):
                rows = json.loads(response.text)['_embedded']['_state']
                q = parse_target(rows[0]['value'])
                rows[0]['value'] = literal([[float(f'{v:.6g}') for v in q[0]], q[1]])
                response = Response(rows)
            return response
        abb.get = six_digits
        client = mover(abb)
        goal = [[5., 10., -30., 101.664181580645, -20., 117.332818], [9e9] * 6]
        result = client.move_to(goal, 40, echo=quiet)
        self.assertEqual(result['code'], 2)
        self.assertAlmostEqual(abb.current[5], 117.333, places=3)

    def test_robot_rejection_is_reported(self):
        abb = Abb('MANR'); client = mover(abb)
        abb.max_step = 45    # un módulo con corte de 45°
        abb.current[0] = 60  # el robot está lejos de lo que la PC creyó al planificar (> 45° del RAPID)
        target = [[-4.28397 + 1, *abb.current[1:5], abb.current[5]], [9e9] * 6]
        client.joints = lambda: [[-4.28397, *abb.current[1:]], [9e9] * 6]
        with self.assertRaisesRegex(Refused, 'código -3'):
            client.send(target, echo=quiet)

    def test_auto_requires_auto_variant_and_needs_no_rmmp(self):
        abb = Abb('AUTO'); abb.source = V2.replace('permitirAuto := FALSE', 'permitirAuto := TRUE')
        client = mover(abb)
        self.assertEqual(client.module_version, 'servidor_v5_auto')
        client.move_to(parse_goal(['j1', '-2'], client.joints()), 5, echo=quiet)
        self.assertFalse([c for c in abb.calls if c[1] == RMMP])

    def test_timeout_without_answer(self):
        abb = Abb('MANR'); abb.respond = False; client = mover(abb)
        with self.assertRaisesRegex(Refused, 'Sin respuesta'):
            client.send([[*abb.current[:5], abb.current[5] + 1], [9e9] * 6], timeout=0.01, echo=quiet)

    def test_write_403_with_poll_still_granted_asks_rmmp_again(self):
        abb = Abb('MANR'); client = mover(abb)
        client.move_to(parse_goal(['j6', '+1'], client.joints()), 5, echo=quiet)
        original = abb.post

        def refuse_writes(url, **kw):  # el sondeo sigue en GRANTED, como en el robot real
            if SYMBOL in url:
                abb.calls.append(('POST', SYMBOL, {}, {}))
                return Response([{'code': '-1073445862', 'msg': 'rws_resource_rapid_symbol_data'}], status=403)
            return original(url, **kw)
        abb.post = refuse_writes
        with self.assertRaisesRegex(Refused, 'Conceder'):
            client.move_to(parse_goal(['j6', '+1'], client.joints()), 5, echo=quiet)
        self.assertFalse(client.rmmp.granted)
        abb.post = original
        before = len([c for c in abb.calls if c[0] == 'POST' and c[1] == RMMP])
        result = client.move_to(parse_goal(['j6', '+1'], client.joints()), 5, echo=quiet)
        self.assertEqual(result['code'], 2)
        self.assertEqual(len([c for c in abb.calls if c[0] == 'POST' and c[1] == RMMP]), before + 1)

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

    def test_install_auto_variant_and_back(self):
        import tempfile
        abb = Abb('AUTO'); abb.source = V2; abb.ctrl = 'motoroff'; abb.execution = 'stopped'
        abb.require_rmmp = False
        client = mover(abb)
        with tempfile.TemporaryDirectory() as folder:
            self.assertTrue(client.install(Path(folder), auto=True)['passed'])
            self.assertEqual(source_fingerprint(abb.source), SERVER_AUTO_MODULE_SHA256)
            self.assertIn('CONST bool permitirAuto := TRUE;', abb.source)
            self.assertTrue(client.install(Path(folder))['passed'])
        self.assertEqual(source_fingerprint(abb.source), SERVER_MODULE_SHA256)

    def test_install_replaces_v4_with_v5(self):
        import tempfile
        for auto, sha in ((False, SERVER_MODULE_SHA256), (True, SERVER_AUTO_MODULE_SHA256)):
            abb = Abb('AUTO'); abb.source = V4 if not auto else V4.replace('permitirAuto := FALSE', 'permitirAuto := TRUE')
            abb.ctrl = 'motoroff'; abb.execution = 'stopped'; abb.require_rmmp = False
            client = mover(abb)
            self.assertEqual(client.module_version, 'servidor_v4_auto' if auto else 'servidor_v4')
            with tempfile.TemporaryDirectory() as folder:
                self.assertTrue(client.install(Path(folder), auto=auto)['passed'])
            self.assertEqual(source_fingerprint(abb.source), sha)

    def test_diagnosis_accepts_v2(self):
        rows = lambda key, value: {'ok': True, 'records': [{key: value}]}
        inspection = {'resources': {
            'system': {'ok': True, 'records': [{'name': '120-101516', 'rwversionname': '6.12.01.00'}]},
            'mode': rows('opmode', 'MANR'), 'controller': rows('ctrlstate', 'motoroff'),
            'execution': rows('ctrlexecstate', 'stopped'), 'target': rows('value', literal(EMPTY)),
            'module': rows('module-text', V2)}}
        report = diagnose_inspection(inspection)
        self.assertEqual(report['module_version'], 'servidor_v5')
        self.assertTrue(report['local_navigation_prerequisites_observed'], report['issues'])
        inspection['resources']['module'] = rows('module-text', V4)
        report = diagnose_inspection(inspection)
        self.assertEqual(report['module_version'], 'servidor_v4')
        self.assertTrue(report['local_navigation_prerequisites_observed'], report['issues'])


class Lineal(unittest.TestCase):
    def setUp(self):
        self.abb = Abb('MANR'); self.client = mover(self.abb)
        self.goal = [[*self.abb.current[:5], self.abb.current[5] + 30.], [9e9] * 6]

    def posts(self):
        return [(c[1][len(BASE_SYMBOL):] if c[1].startswith(BASE_SYMBOL) else c[1], c[3].get('value'))
                for c in self.abb.calls if c[0] == 'POST' and c[1] != RMMP]

    def test_robtarget_format_and_readback(self):
        text = format_robtarget([300.12349, -50., 250., 0., 1., 0., 0.])
        self.assertEqual(text, '[[300.123,-50,250],[0,1,0,0],[0,0,0,0],[9E9,9E9,9E9,9E9,9E9,9E9]]')
        pose = parse_robtarget(text)
        self.assertEqual(pose, [300.123, -50., 250., 0., 1., 0., 0.])
        # El ABB devuelve 9E+09 y 6 cifras: sigue coincidiendo
        back = parse_robtarget('[[300.123,-50,250],[0,1,0,0],[0,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]]')
        self.assertTrue(same_pose(pose, back))
        self.assertFalse(same_pose(pose, parse_robtarget(text.replace('300.123', '300.125'))))
        self.assertFalse(same_pose(pose, parse_robtarget(text.replace('[0,1,0,0]', '[0.01,1,0,0]'))))
        # cuaternión: se normaliza y redondea a 6 decimales
        self.assertEqual(normalize_pose([0, 0, 100, 0.7071068, 0.7071068, 0, 0])[3:], [0.707107, 0.707107, 0., 0.])
        for bad in ('[[1,2,3],[1,0,0,0]]', '[[1,2],[1,0,0,0],[0,0,0,0],[9E9,9E9,9E9,9E9,9E9,9E9]]',
                    '[[1,2,3],[2,0,0,0],[0,0,0,0],[9E9,9E9,9E9,9E9,9E9,9E9]]', 'x'):
            with self.assertRaises(Refused):
                parse_robtarget(bad)

    def test_pose_validation(self):
        for pose in (None, [1, 2, 3], [0, 0, 300, 1, 1, 0, 0], [0, 0, 5000, 1, 0, 0, 0],
                     [0, 0, -500, 1, 0, 0, 0], [float('nan'), 0, 300, 1, 0, 0, 0], [0, 0, 300, 0, 0, 0, 0],
                     [True, 0, 300, 1, 0, 0, 0]):
            with self.assertRaises(Refused, msg=pose):
                self.client.send(self.goal, tipo='lineal', pose_tool0=pose, echo=quiet)
        with self.assertRaises(Refused):
            self.client.send(self.goal, tipo='circular', echo=quiet)
        self.assertFalse(self.posts())   # nada se escribió

    def test_send_lineal_writes_tipo_and_pose_before_seq(self):
        result = self.client.send(self.goal, tipo='lineal', pose_tool0=POSE, echo=quiet)
        self.assertEqual(result['code'], 2)
        names = [n for n, _ in self.posts()]
        self.assertEqual(names, ['pcTarget', 'pcPose', 'pcTipo', 'pcSeq'])
        values = dict(self.posts())
        self.assertEqual(values['pcTipo'], '1')
        self.assertEqual(values['pcPose'], '[[300,50,250],[0,1,0,0],[0,0,0,0],[9E9,9E9,9E9,9E9,9E9,9E9]]')
        self.assertEqual(self.abb.nums['pcTipo'], 1.)

    def test_articular_after_lineal_resets_tipo(self):
        self.client.send(self.goal, tipo='lineal', pose_tool0=POSE, echo=quiet)
        back = [list(self.abb.current), [9e9] * 6]; back[0][5] -= 10
        self.abb.calls.clear()
        self.client.send(back, echo=quiet)
        names = [n for n, _ in self.posts()]
        self.assertEqual(names, ['pcTarget', 'pcTipo', 'pcSeq'])
        self.assertEqual(self.abb.nums['pcTipo'], 0.)
        # y una articular seguida de otra articular no reescribe pcTipo ni pcPose
        self.abb.calls.clear()
        self.client.send([[*self.abb.current[:5], self.abb.current[5] + 5], [9e9] * 6], echo=quiet)
        self.assertEqual([n for n, _ in self.posts()], ['pcTarget', 'pcSeq'])

    def test_pose_readback_mismatch_does_not_move(self):
        original = self.abb.post

        def corrupt(url, **kw):
            response = original(url, **kw)
            if url.endswith('pcPose'):
                self.abb.pose_text = self.abb.pose_text.replace('300', '301')
            return response
        self.abb.post = corrupt
        with self.assertRaisesRegex(Refused, 'pcPose'):
            self.client.send(self.goal, tipo='lineal', pose_tool0=POSE, echo=quiet)
        self.assertNotIn('pcSeq', [n for n, _ in self.posts()])

    def test_v4_rejects_lineal_and_does_not_read_pctipo(self):
        abb = Abb('MANR'); abb.source = V4; del abb.nums['pcTipo']
        client = mover(abb)
        self.assertEqual(client.module_version, 'servidor_v4')
        state = client.status()
        self.assertNotIn('pcTipo', state)
        self.assertIn('pcVelPct', state)
        goal = [[*abb.current[:5], abb.current[5] + 1.], [9e9] * 6]
        with self.assertRaisesRegex(Refused, 'lineal.*v5'):
            client.send(goal, tipo='lineal', pose_tool0=POSE, echo=quiet)
        self.assertFalse([c for c in abb.calls if c[0] == 'POST'])
        # la v4 ya no es un módulo «listo»: ni siquiera la articular se envía hasta reinstalar
        with self.assertRaisesRegex(Refused, 'instalar la v5'):
            client.send(goal, echo=quiet)
        self.assertFalse([c for c in abb.calls if c[0] == 'POST'])

    def test_one_order_for_a_long_move(self):
        goal = [[100., 50., -60., 120., -50., 0.], [9e9] * 6]
        self.abb.current = [-100., -50., 60., -120., 50., 0.]
        client = mover(self.abb)
        result = move_tramo(client, 'articular', goal[0], None, echo=quiet)
        seqs = [v for n, v in self.posts() if n == 'pcSeq']
        self.assertEqual(seqs, ['1'])     # sin cortes cada 40°: 240° en una sola orden
        self.assertEqual(result['code'], 2)
        self.assertLess(result['max_error_deg'], 0.02)
        self.assertEqual(MAX_STEP_DEG, 355.); self.assertEqual(RAPID_MAX_STEP_DEG, 360.)

    def test_move_tramo_lineal_single_order_and_correction(self):
        result = move_tramo(self.client, 'lineal', self.goal[0], POSE, echo=quiet)
        self.assertEqual([v for n, v in self.posts() if n == 'pcSeq'], ['1'])
        self.assertEqual(set(result), {'seq', 'code', 'joints_deg', 'max_error_deg'})
        # el MoveL termina 1° corrido: una corrección articular (pcTipo=0) y listo
        abb = Abb('MANR'); abb.arrival_offset = 1.; client = mover(abb)
        goal = [*abb.current[:5], abb.current[5] + 20.]
        result = move_tramo(client, 'lineal', goal, POSE, echo=quiet)
        seqs = [c[3]['value'] for c in abb.calls if c[0] == 'POST' and c[1].endswith('pcSeq')]
        self.assertEqual(seqs, ['1', '2'])
        self.assertEqual(abb.nums['pcTipo'], 0.)
        self.assertLess(result['max_error_deg'], 0.02)

    def test_move_tramo_does_not_correct_blindly_after_big_lineal_error(self):
        abb = Abb('MANR'); abb.arrival_offset = 30.; client = mover(abb)
        goal = [*abb.current[:5], abb.current[5] + 20.]
        with self.assertRaisesRegex(Refused, 'configuración'):
            move_tramo(client, 'lineal', goal, POSE, echo=quiet)
        self.assertEqual([c[3]['value'] for c in abb.calls if c[0] == 'POST' and c[1].endswith('pcSeq')], ['1'])

    def test_move_tramo_cancel(self):
        import threading
        stop = threading.Event(); stop.set()
        with self.assertRaisesRegex(Refused, 'CANCELADO'):
            move_tramo(self.client, 'articular', self.goal[0], None, echo=quiet, cancel=stop)
        self.assertFalse(self.posts())

    def test_robot_rejects_invalid_pctipo_with_code_5(self):
        self.abb.nums['pcTipo'] = 7.   # valor ajeno escrito a mano en el robot
        self.abb.nums['pcTipo'] = 7.
        with self.assertRaisesRegex(Refused, 'código -5'):
            # la PC reescribe pcTipo=0 si difiere; se fuerza que el robot lo vea mal
            original = self.abb.robot
            self.abb.robot = lambda seq: (self.abb.nums.__setitem__('pcTipo', 7.), original(seq))[1]
            self.client.send(self.goal, echo=quiet)


if __name__ == '__main__':
    unittest.main()
