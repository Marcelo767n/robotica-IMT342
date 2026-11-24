"""Mover el IRB 120 desde la PC mediante RWS y el módulo LabJointRws v5 (ServidorPC).

La PC no arranca RAPID, no enciende motores ni cambia el modo. El operador deja
ServidorPC en ejecución desde el FlexPendant (manual reducido, habilitador
presionado) y la PC solo escribe objetivos articulares absolutos en grados:

    pcTarget  <- objetivo J1..J6 (lectura de vuelta comprobada)
    pcTipo    <- 0 = MoveAbsJ a pcTarget, 1 = MoveL a pcPose (solo v5)
    pcPose    <- robtarget de tool0 en wobj0 (solo si pcTipo = 1; lectura de vuelta comprobada)
    pcSeq     <- pcSeq + 1      (ordena ejecutar el objetivo ya escrito)
    rbCodigo  -> resultado del robot (2 = llegada; negativo = rechazo)
    rbSeq     -> copia de pcSeq cuando el robot terminó o rechazó

En manual, ABB exige el permiso remoto RMMP para escribir variables PERS: el
FlexPendant muestra una solicitud que el operador debe aceptar. El permiso se
mantiene consultando /users/rmmp/poll periódicamente.
"""
import argparse
from datetime import datetime, timezone
import getpass
import json
import math
from pathlib import Path
import shlex
import threading
import time

from irb120_conexion.rutas import PROJECT
from irb120_conexion.comunicacion.lectura_rws import error_details, state_records
from irb120_conexion.nodos.lectura_articular.puente_rws import build_base_url
from irb120_control.rws_j6 import MASTERSHIP
from irb120_control.rws_j6 import (Client, Refused, EMPTY, LIMITS, SYMBOL, SERVER_CANDIDATE,
    SERVER_MODULE_SHA256, SERVER_AUTO_MODULE_SHA256, ORIGINAL_NORMALIZED_SHA256, J6_MODULE_SHA256,
    SERVER_V2_SHA256, SERVER_V2_AUTO_SHA256, SERVER_V3_SHA256, SERVER_V3_AUTO_SHA256, SERVER_LABELS,
    SERVER_V4_SHA256, SERVER_V4_AUTO_SHA256,
    SERVER_V4_CUT_SHA256, SERVER_V4_30S_SHA256, SERVER_V4_30S_AUTO_SHA256,
    measured_target, module_label, parse_target, literal, same_target, single, source_fingerprint)

BASE_SYMBOL = '/rw/rapid/symbol/data/RAPID/T_ROB1/LabJointRws/'
NUM_SYMBOLS = ('pcSeq', 'pcFin', 'rbSeq', 'rbCodigo', 'rbActivo', 'pcVelPct', 'pcTipo')
SPEED_MAX_MM_S, SPEED_MAX_DEG_S = 250., 60.   # vMax del RAPID v4/v5: 100 %
RMMP = '/users/rmmp'
RMMP_POLL = '/users/rmmp/poll'
RAPID_MAX_STEP_DEG = 360.0  # maxPasoDeg del módulo RAPID v5 (la v3/v4 admitían 45°)
MAX_STEP_DEG = 355.0        # paso máximo de la PC: 5° de margen para el error residual de llegada
POSE_DECIMALS, QUAT_DECIMALS = 3, 6   # mm y cuaternión de pcPose
POSE_TOL_MM, POSE_TOL_Q = 1e-3, 1e-6  # lectura de vuelta de pcPose
LINEAL_CORRECTION_MAX_DEG = 5.0       # tras un MoveL no se corrige a ciegas más que esto (otra configuración)
POSE_LIMITS = ((-700., 700.), (-700., 700.), (-50., 900.))   # x, y, z de tool0 (mm), holgados para el IRB 120
TIPOS = {'articular': 0, 'lineal': 1}
DECIMALS = 3                # RWS devuelve 6 cifras: con ejes ≥ 100° solo 3 decimales sobreviven
READBACK_TOL_DEG = 2e-3
ARRIVAL_DEG = 0.02          # si al terminar falta más, se envía una orden de corrección
MARGIN_DEG = 2.0         # igual a margenDeg del módulo RAPID
# La postura se relee entre el cálculo del tramo y su envío: el ruido de medida y el
# error residual de llegada (centésimas de grado) no deben rechazar un «j6 +5» con paso 5.
STEP_TOL_DEG = 0.05
AUTO_OFF = 'CONST bool permitirAuto := FALSE;'
AUTO_ON = 'CONST bool permitirAuto := TRUE;'
CODES = {0: 'listo', 1: 'moviendo', 2: 'llegada', -1: 'objetivo vacío o no válido',
         -2: 'fuera de límites con margen de 2°', -3: 'algún eje cambia más de lo que admite maxPasoDeg en una orden',
         -4: 'modo no permitido por el módulo (¿AUTO sin permitirAuto?)',
         -5: 'pcTipo no válido (solo 0 = MoveAbsJ o 1 = MoveL)'}
FORM = {'Content-Type': 'application/x-www-form-urlencoded'}
PCP = '/rw/rapid/tasks/T_ROB1/pcp'
SERVER_MODULE, SERVER_ROUTINE = 'LabJointRws', 'ServidorPC'
START_FORM = {'regain': 'continue', 'execmode': 'continue', 'cycle': 'once', 'condition': 'none',
              'stopatbp': 'disabled', 'alltaskbytsp': 'false'}


def check_target(target, current, step):
    """Comprobación local (además de la del robot): límites con margen y paso máximo."""
    target = parse_target(literal(target))
    for index, (q, (lo, hi)) in enumerate(zip(target[0], LIMITS), start=1):
        if not lo + MARGIN_DEG <= q <= hi - MARGIN_DEG:
            raise Refused(f'J{index}={q:.3f}° fuera de [{lo + MARGIN_DEG}, {hi - MARGIN_DEG}].')
    worst = max(abs(a - b) for a, b in zip(target[0], current[0]))
    if worst > step + STEP_TOL_DEG:
        raise Refused(f'Cambio de {worst:.3f}° mayor que el paso permitido de {step}°.')
    # Redondear antes de escribir: lo que se escribe es exactamente lo que el ABB devuelve.
    target = [[round(v, DECIMALS) for v in target[0]], target[1]]
    return target


def _num(value):
    value = round(float(value), 12)
    return format(value + 0.0, '.15g')   # sin «-0»


def normalize_pose(pose):
    """[x, y, z mm, qw, qx, qy, qz] → pose comprobada, redondeada (3 y 6 decimales) y con cuaternión unitario."""
    if (not isinstance(pose, (list, tuple)) or len(pose) != 7 or
            any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in pose)):
        raise Refused('pose_tool0 debe ser [x, y, z mm, qw, qx, qy, qz] con números finitos.')
    for name, v, (lo, hi) in zip('xyz', pose[:3], POSE_LIMITS):
        if not lo <= v <= hi:
            raise Refused(f'Pose: {name}={v:.3f} mm fuera de [{lo:g}, {hi:g}].')
    norm = math.sqrt(sum(v * v for v in pose[3:]))
    if abs(norm - 1.) > 1e-3:
        raise Refused(f'Pose: el cuaternión no está normalizado (norma {norm:.6f}).')
    return ([round(float(v), POSE_DECIMALS) + 0. for v in pose[:3]] +
            [round(v / norm, QUAT_DECIMALS) + 0. for v in pose[3:]])


def format_robtarget(pose):
    """Literal RAPID del robtarget: cf = [0,0,0,0] (con ConfL \\Off) y ejes externos 9E9."""
    pose = normalize_pose(pose)
    return ('[[' + ','.join(_num(v) for v in pose[:3]) + '],[' + ','.join(_num(v) for v in pose[3:]) +
            '],[0,0,0,0],[9E9,9E9,9E9,9E9,9E9,9E9]]')


def parse_robtarget(text):
    """Literal robtarget → [x, y, z, qw, qx, qy, qz] (el cuaternión se devuelve normalizado)."""
    try:
        value = json.loads(text, parse_constant=lambda x: None)
        if (not isinstance(value, list) or len(value) != 4 or [len(v) for v in value] != [3, 4, 4, 6] or
                any(type(v) not in (int, float) or not math.isfinite(v) for group in value for v in group)):
            raise ValueError('formato robtarget')
        norm = math.sqrt(sum(v * v for v in value[1]))
        if abs(norm - 1.) > 1e-3:
            raise ValueError('cuaternión no normalizado')
        return [float(v) for v in value[0]] + [v / norm for v in value[1]]
    except (ValueError, TypeError) as exc:
        raise Refused('robtarget inválido: ' + str(exc)) from exc


def same_pose(left, right, tol_mm=POSE_TOL_MM, tol_q=POSE_TOL_Q):
    return (all(abs(a - b) <= tol_mm for a, b in zip(left[:3], right[:3])) and
            all(abs(a - b) <= tol_q for a, b in zip(left[3:], right[3:])))


def check_tipo(tipo, pose_tool0):
    """('articular'|'lineal', pose) → (0|1, pose normalizada o None)."""
    if tipo not in TIPOS:
        raise Refused(f"Tipo de movimiento «{tipo}»: debe ser 'articular' o 'lineal'.")
    if tipo == 'articular':
        return 0, None
    if pose_tool0 is None:
        raise Refused('El movimiento lineal necesita pose_tool0 [x, y, z mm, qw, qx, qy, qz].')
    return 1, normalize_pose(pose_tool0)


def split_path(current, goal, step):
    """Divide un recorrido articular en tramos rectos de como máximo `step` grados por eje."""
    if not 0 < step <= MAX_STEP_DEG:
        raise Refused(f'--paso debe estar entre 0 y {MAX_STEP_DEG}°.')
    goal = parse_target(literal(goal))
    for index, (q, (lo, hi)) in enumerate(zip(goal[0], LIMITS), start=1):
        if not lo + MARGIN_DEG <= q <= hi - MARGIN_DEG:
            raise Refused(f'Destino J{index}={q:.3f}° fuera de [{lo + MARGIN_DEG}, {hi - MARGIN_DEG}].')
    worst = max(abs(a - b) for a, b in zip(goal[0], current[0]))
    # Observado en el IRC5 (16/11/2026): un «j6 +5» medido como 5,000004° se partía en
    # dos órdenes. Se tolera el ruido de medida sin superar nunca el máximo del robot.
    tolerance = min(STEP_TOL_DEG, RAPID_MAX_STEP_DEG - step)
    count = max(1, math.ceil((worst - tolerance) / step - 1e-9))
    return [[[c + (g - c) * k / count for c, g in zip(current[0], goal[0])], [9e9] * 6]
            for k in range(1, count + 1)]


class Rmmp:
    """Solicita y mantiene RMMP. El sondeo usa una sesión paralela con las mismas cookies,
    renovada cada 30 s, porque el ABB revoca el permiso si se pierde esa conexión."""

    def __init__(self, client, session_factory):
        self.client, self.factory = client, session_factory
        self.poll_session = None
        self.poll_started = 0.
        self.granted = False
        self.last_poll = 0.

    def _status(self, session):
        response = session.get(self.client.base + RMMP_POLL, params={'json': '1'},
                               timeout=self.client.timeout, allow_redirects=False)
        if response.status_code != 200:
            raise Refused(f'RMMP poll: HTTP {response.status_code}; {error_details(response.text)}')
        return single(state_records(response.text), 'status')

    def _new_session(self):
        session = self.factory()
        session.trust_env = False
        session.auth = self.client.session.auth
        for cookie in self.client.session.cookies:
            session.cookies.set_cookie(cookie)
        return session

    def request(self, wait=90., sleep=time.sleep):
        response = self.client.session.post(self.client.base + RMMP, params={'json': '1'},
                                            data={'privilege': 'modify'}, headers=FORM,
                                            timeout=self.client.timeout, allow_redirects=False)
        if response.status_code not in (200, 201, 202, 204):
            raise Refused(f'Solicitud RMMP: HTTP {response.status_code}; {error_details(response.text)}')
        print('>>> En el FlexPendant aparece una solicitud de acceso remoto: el operador debe ACEPTARLA.',
              flush=True)
        started = time.monotonic()
        while time.monotonic() - started < wait:
            status = self._status(self.client.session)
            if status == 'GRANTED':
                self.granted = True
                self.keep(force=True)
                print('RMMP concedido: la PC puede escribir objetivos en manual.', flush=True)
                return
            if status != 'PENDING':
                raise Refused(f'RMMP no concedido (estado {status}). El operador lo rechazó o caducó.')
            sleep(.25)
        raise Refused('RMMP no concedido a tiempo. Repetir y aceptar en el FlexPendant.')

    def keep(self, force=False):
        if not self.granted:
            return
        now = time.monotonic()
        if not force and now - self.last_poll < 2.:
            return
        old = None
        if self.poll_session is None or now - self.poll_started > 30.:
            old, self.poll_session, self.poll_started = self.poll_session, self._new_session(), now
        status = self._status(self.poll_session)
        self.last_poll = now
        if old is not None:
            try:
                old.close()
            except Exception:
                pass
        if status != 'GRANTED':
            self.granted = False
            raise Refused(f'Se perdió RMMP (estado {status}). Pedirlo de nuevo con el operador.')

    def close(self):
        if self.poll_session is not None:
            try:
                self.poll_session.close()
            except Exception:
                pass


class Mover(Client):
    def __init__(self, session, base, session_factory=None, timeout=3., log=None, sleep=time.sleep):
        super().__init__(session, base, timeout)
        self.extra_reads = {BASE_SYMBOL + name for name in NUM_SYMBOLS} | {BASE_SYMBOL + 'pcPose', RMMP_POLL, PCP}
        self.rmmp = Rmmp(self, session_factory or (lambda: type(session)()))
        self.log, self.sleep = log, sleep
        self.module_version = 'no_leido'
        # Una sola operación HTTP a la vez: requests.Session no es segura entre hilos.
        self.lock = threading.RLock()
        self.keeper_error = None
        self.on_joints = None

    def is_v5(self):
        return self.module_version.startswith('servidor_v5')

    def start_keeper(self, period=2.):
        """Mantiene RMMP mientras el usuario escribe en el prompt (sin sondeo el ABB lo revoca)."""
        stop = threading.Event()

        def run():
            while not stop.wait(period):
                if self.lock.acquire(blocking=False):
                    try:
                        self.rmmp.keep()
                    except Exception as exc:  # se informa en la siguiente orden
                        self.keeper_error = str(exc)
                    finally:
                        self.lock.release()
        threading.Thread(target=run, daemon=True, name='rmmp-keeper').start()
        return stop

    def record(self, **row):
        row = {'at_utc': datetime.now(timezone.utc).isoformat(), **row}
        if self.log is not None:
            with self.log.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(row, ensure_ascii=False) + '\n')

    # ---------- lecturas ----------
    def num(self, name):
        value = single(self.read(BASE_SYMBOL + name), 'value')
        try:
            return float(value)
        except ValueError as exc:
            raise Refused(f'{name} no es numérico: {value}') from exc

    def get_pose(self):
        return parse_robtarget(single(self.read(BASE_SYMBOL + 'pcPose'), 'value'))

    def joints(self):
        target = measured_target(self.read('/rw/rapid/tasks/T_ROB1/motion', resource='jointtarget'))
        if self.on_joints is not None:  # p. ej. el panel refresca RViz durante un movimiento
            self.on_joints(list(target[0]))
        return target

    def status(self):
        state = {'opmode': single(self.read('/rw/panel/opmode'), 'opmode'),
                 'ctrlstate': single(self.read('/rw/panel/ctrlstate'), 'ctrlstate'),
                 'execution': single(self.read('/rw/rapid/execution'), 'ctrlexecstate'),
                 'joints_deg': self.joints()[0], 'module': self.module_version}
        if self.module_version.startswith('servidor_v'):
            for name in NUM_SYMBOLS:
                if name == 'pcVelPct' and not self.module_version.startswith(('servidor_v4', 'servidor_v5')):
                    continue   # la v2/v3 no tienen velocidad desde la PC: se instala la v5 antes
                if name == 'pcTipo' and not self.is_v5():
                    continue   # solo la v5 declara pcTipo/pcPose (leerlos en la v4 daría HTTP 400)
                state[name] = self.num(name)
        return state

    # ---------- escrituras ----------
    def write(self, name, value):
        path = SYMBOL if name == 'pcTarget' else BASE_SYMBOL + name
        if name not in ('pcTarget', 'pcSeq', 'pcFin', 'pcVelPct', 'pcTipo', 'pcPose'):
            raise Refused('Solo se escriben pcTarget, pcSeq, pcFin, pcVelPct, pcTipo y pcPose.')
        self.rmmp.keep()
        self.write_events.append({'at_utc': datetime.now(timezone.utc).isoformat(), 'symbol': name,
                                  'value': value, 'result': 'pending_or_unknown'})
        response = self.session.post(self.base + path, params={'action': 'set'}, data={'value': value},
                                     headers=FORM, timeout=self.timeout, allow_redirects=False)
        event = self.write_events[-1]
        event['http_status'] = response.status_code
        event['result'] = 'accepted' if response.status_code in (200, 204) else 'rejected'
        self.record(event='write', symbol=name, value=value, http_status=response.status_code)
        if response.status_code not in (200, 204):
            hint = ''
            if response.status_code == 403:
                hint = ' En manual hace falta RMMP aceptado en el FlexPendant.'
                if self.rmmp.granted:
                    # Observado en el IRC5 (16/11/2026): tras detener RAPID el sondeo seguía en GRANTED
                    # pero la escritura daba 403. Se descarta el permiso para pedirlo de nuevo.
                    self.rmmp.granted = False
                    hint = (' El controlador ya no acepta el permiso RMMP: repetir la orden y '
                            'pulsar «Conceder» otra vez en el FlexPendant.')
            raise Refused(f'POST {name}: HTTP {response.status_code}; {error_details(response.text)}.{hint}')

    def ensure_rmmp(self, state):
        if state['opmode'] in ('MANR', 'MANF') and not self.rmmp.granted:
            self.rmmp.request(sleep=self.sleep)

    # ---------- protocolo ----------
    def ready(self, state):
        problems = []
        if state.get('module') not in SERVER_LABELS:
            problems.append(f"módulo {state.get('module')}: instalar la v5 ('./brazo.sh instalar' o 'instalar-auto', "
                            "llave AUTO, motores apagados, RAPID detenido)")
        if state['opmode'] == 'MANF':
            problems.append('modo manual 100%: usar manual reducido')
        elif state['opmode'] == 'AUTO' and state.get('module') != 'servidor_v5_auto':
            problems.append('modo AUTO: el módulo solo acepta manual reducido (permitirAuto := FALSE)')
        if state['ctrlstate'] != 'motoron':
            problems.append(f"motores {state['ctrlstate']}: mantener el habilitador (manual) o Motors On (AUTO)")
        if state['execution'] != 'running':
            problems.append('RAPID detenido: PP to Routine → ServidorPC, Start y pulsar «Iniciar»')
        if state.get('rbActivo') != 1:
            problems.append('ServidorPC no está activo (rbActivo=0): arrancarlo y pulsar «Iniciar» en el FlexPendant')
        if state.get('pcFin', 0) != 0:
            problems.append('pcFin=1: el servidor terminó; arrancarlo de nuevo')
        if state.get('pcSeq') is not None and state.get('pcSeq') != state.get('rbSeq'):
            problems.append('hay una orden en curso (pcSeq≠rbSeq): esperar su respuesta')
        return problems

    def send(self, target, step=MAX_STEP_DEG, timeout=120., echo=print, tipo='articular', pose_tool0=None):
        """Una orden: 'articular' (MoveAbsJ a target) o 'lineal' (MoveL a pose_tool0; target sigue siendo
        el objetivo articular esperado, que el robot valida con los límites). Lineal solo en la v5."""
        tipo_num, pose = check_tipo(tipo, pose_tool0)
        if tipo_num and not self.is_v5():
            raise Refused(f'El módulo {self.module_version} no admite movimiento lineal: instalar la v5.')
        state = self.status()
        problems = self.ready(state)
        if problems:
            raise Refused('No listo: ' + '; '.join(problems))
        current = [state['joints_deg'], [9e9] * 6]
        target = check_target(target, current, step)
        self.ensure_rmmp(state)
        self.write('pcTarget', literal(target))
        readback = self.get_target()
        if not same_target(target, readback, tolerance=READBACK_TOL_DEG):
            raise Refused('La lectura de vuelta de pcTarget no coincide; no se ordena el movimiento.')
        if self.is_v5():
            if pose is not None:
                self.write('pcPose', format_robtarget(pose))
                if not same_pose(normalize_pose(pose), self.get_pose()):
                    raise Refused('La lectura de vuelta de pcPose no coincide; no se ordena el movimiento.')
            if state.get('pcTipo') != tipo_num:   # evita dejar un pcTipo=1 de la orden anterior
                self.write('pcTipo', str(tipo_num))
                if int(round(self.num('pcTipo'))) != tipo_num:
                    raise Refused('La lectura de vuelta de pcTipo no coincide; no se ordena el movimiento.')
        seq = int(state['pcSeq']) + 1
        self.record(event='order', seq=seq, tipo=tipo, from_deg=current[0], target_deg=target[0],
                    pose_tool0=pose)
        self.write('pcSeq', str(seq))
        started = time.monotonic(); warned = False
        while time.monotonic() - started < timeout:
            self.rmmp.keep()
            q = self.joints()[0]
            done = self.num('rbSeq') == seq
            code = int(self.num('rbCodigo'))
            error = max(abs(a - b) for a, b in zip(q, target[0]))
            echo('  ' + ' '.join(f'J{i}={v:8.3f}' for i, v in enumerate(q, 1)) +
                 f' | falta {error:7.3f}° | robot: {CODES.get(code, code)}')
            if done:
                self.record(event='result', seq=seq, code=code, joints_deg=q, max_error_deg=error)
                if code != 2:
                    raise Refused(f'El robot rechazó la orden {seq}: código {code} ({CODES.get(code, "?")}).')
                return {'seq': seq, 'code': code, 'joints_deg': q, 'max_error_deg': error}
            execution = single(self.read('/rw/rapid/execution'), 'ctrlexecstate')
            if execution != 'running' and not warned:
                warned = True
                echo('  AVISO: RAPID se detuvo (¿se soltó el habilitador?). Al pulsar Start de nuevo la orden continúa.')
            self.sleep(.25)
        raise Refused(f'Sin respuesta del robot a la orden {seq} en {timeout:.0f} s. '
                      'No enviar otra: revisar FlexPendant y ejecutar «estado».')

    def move_to(self, goal, step, timeout=120., echo=print, cancel=None):
        return move_to(self, goal, step, timeout, echo, cancel)

    def set_speed(self, pct):
        """Velocidad de las próximas órdenes en % de vMax (100 % = 250 mm/s y 60°/s)."""
        if isinstance(pct, bool) or not isinstance(pct, (int, float)) or not 1 <= pct <= 100:
            raise Refused('La velocidad debe estar entre 1 y 100 %.')
        pct = int(round(pct))
        if not self.module_version.startswith(('servidor_v4', 'servidor_v5')):
            raise Refused(f'El módulo {self.module_version} no admite velocidad desde la PC: instalar la v5.')
        state = self.status()
        self.ensure_rmmp(state)
        self.write('pcVelPct', str(pct))
        if int(round(self.num('pcVelPct'))) != pct:
            raise Refused('La lectura de vuelta de pcVelPct no coincide.')
        return pct

    def events(self, count=15):
        """Últimos mensajes del registro de eventos del controlador (solo lectura)."""
        response = self.session.get(self.base + '/rw/elog/0', params={'json': '1', 'lang': 'es'},
                                    timeout=self.timeout, allow_redirects=False)
        if response.status_code != 200:
            raise Refused(f'Registro de eventos: HTTP {response.status_code}; {error_details(response.text)}')
        rows = [r for r in state_records(response.text) if r.get('_type', '').startswith('elog-message')]
        return rows[:count]

    def pointer(self):
        """Módulo y rutina donde está el puntero de programa (PP) de T_ROB1."""
        rows = self.read(PCP)
        for row in rows:
            values = ' '.join(str(v) for v in row.values())
            if 'pcp' in str(row.get('_type', '')).lower() or 'progpointer' in str(row.get('_title', '')).lower():
                return row, values
        return (rows[0] if rows else {}), ' '.join(str(v) for row in rows for v in row.values())

    def start_server(self, echo=print):
        """Solo en AUTO: PP a LabJointRws/ServidorPC, comprobar el PP y arrancar RAPID (ciclo único).

        En AUTO el FlexPendant no permite «PP a rutina» y el controlador lleva el PP a main (que es
        de otro programa). El operador sigue confirmando con «Iniciar» en el FlexPendant."""
        state = self.status()
        if state['opmode'] != 'AUTO':
            raise Refused(f"Solo en AUTO (ahora {state['opmode']}). En manual: PP a rutina en el FlexPendant.")
        if state['module'] != 'servidor_v5_auto':
            raise Refused(f"El módulo es {state['module']}: instalar con ./brazo.sh instalar-auto.")
        if state['execution'] != 'stopped':
            raise Refused('RAPID ya está en ejecución: pulsar Stop en el FlexPendant antes de arrancar.')
        if state['ctrlstate'] != 'motoron':
            raise Refused(f"Motores {state['ctrlstate']}: pulsar el botón Motors On del controlador.")

        def post(path, params, data, expected):
            response = self.session.post(self.base + path, params=params, data=data, headers=FORM,
                                         timeout=self.timeout, allow_redirects=False)
            self.record(event='start_server', path=path, action=params.get('action'),
                        http_status=response.status_code)
            if response.status_code not in expected:
                raise Refused(f"{params.get('action')}: HTTP {response.status_code}; {error_details(response.text)}")

        held = False
        try:
            post(MASTERSHIP, {'action': 'request'}, {}, (200, 204)); held = True
            post(PCP, {'action': 'set-pp-routine'},
                 {'module': SERVER_MODULE, 'routine': SERVER_ROUTINE, 'userlevel': 'false'}, (200, 204))
            row, values = self.pointer()
            if SERVER_MODULE not in values or SERVER_ROUTINE not in values:
                raise Refused(f'El PP no quedó en {SERVER_MODULE}/{SERVER_ROUTINE} ({row}); NO se arranca.')
            echo(f'PP confirmado en {SERVER_MODULE}/{SERVER_ROUTINE}.')
            post('/rw/rapid/execution', {'action': 'start'}, START_FORM, (200, 204))
        finally:
            if held:
                try:
                    post(MASTERSHIP, {'action': 'release'}, {}, (200, 204, 403))
                except Exception:
                    pass
        echo('RAPID arrancado en ServidorPC. En el FlexPendant abrir la Ventana del operador y pulsar «Iniciar» '
             '(hay 2 minutos).')

    def finish(self):
        state = self.status()
        self.ensure_rmmp(state)
        self.write('pcFin', '1')

    def connect(self):
        """Lee identidad y versión del módulo una vez por sesión."""
        identity = self.verify_identity()
        self.module_version = module_label(source_fingerprint(self.module_source()))
        return identity

    def install(self, directory, auto=False):
        """auto=True instala la misma v5 con permitirAuto := TRUE (motores ON sin habilitador,
        solo con autorización del responsable). Se transfiere por RWS para que la huella sea
        exacta: editar la línea en el FlexPendant puede reformatearla."""
        path, sha = SERVER_CANDIDATE, SERVER_MODULE_SHA256
        if auto:
            source = SERVER_CANDIDATE.read_text(encoding='utf-8')
            if source.count(AUTO_OFF) != 1:
                raise Refused('El candidato no contiene exactamente una línea permitirAuto := FALSE.')
            directory.mkdir(parents=True, exist_ok=True)
            path, sha = directory / 'LabJointRws_auto.mod', SERVER_AUTO_MODULE_SHA256
            path.write_text(source.replace(AUTO_OFF, AUTO_ON), encoding='utf-8')
        return self.update_module(directory, candidate_path=path, candidate_sha=sha,
                                  accepted=(ORIGINAL_NORMALIZED_SHA256, J6_MODULE_SHA256,
                                            SERVER_MODULE_SHA256, SERVER_AUTO_MODULE_SHA256,
                                            SERVER_V2_SHA256, SERVER_V2_AUTO_SHA256,
                                            SERVER_V3_SHA256, SERVER_V3_AUTO_SHA256, SERVER_V4_SHA256,
                                            SERVER_V4_AUTO_SHA256, SERVER_V4_CUT_SHA256,
                                            SERVER_V4_30S_SHA256, SERVER_V4_30S_AUTO_SHA256))


def logout(mover):
    """Cierra la sesión RWS: RW6 admite pocas sesiones simultáneas y tarda en caducarlas."""
    try:
        mover.session.get(mover.base + '/logout', timeout=2., allow_redirects=False)
    except Exception:
        pass


def move_to(mover, goal, step, timeout=120., echo=print, cancel=None):
    """Va al objetivo replanificando cada tramo desde la postura REAL (no acumula el error residual)
    y termina con una orden de corrección si al final falta más de ARRIVAL_DEG. Sirve para Mover y
    para el robot simulado (solo usa joints() y send())."""
    current = mover.joints()
    planned = len(split_path(current, goal, step))
    echo(f'Recorrido dividido en {planned} orden(es) de como máximo {step}° por eje.')
    result, index = None, 0
    while True:
        error = max(abs(a - b) for a, b in zip(current[0], goal[0]))
        if error <= ARRIVAL_DEG:
            return result or {'seq': 0, 'code': 2, 'joints_deg': current[0], 'max_error_deg': error}
        if cancel is not None and cancel.is_set():
            raise Refused(f'CANCELADO antes de la orden {index + 1}. El robot queda donde está.')
        index += 1
        if index > planned + 2:
            raise Refused(f'No se alcanzó el objetivo tras {index - 1} órdenes (falta {error:.3f}°); '
                          'revisar el FlexPendant.')
        leg = split_path(current, goal, step)[0]
        echo(f'Orden {index}/{max(planned, index)} → ' + ', '.join(f'{v:.3f}' for v in leg[0]))
        result = mover.send(leg, step=step, timeout=timeout, echo=echo)
        current = mover.joints()


def move_tramo(mover, tipo, q_deg, pose_tool0, timeout=120., echo=print, cancel=None):
    """Un tramo = UNA orden (articular o lineal, con parada solo al final). Si al terminar falta más de
    ARRIVAL_DEG a q_deg se envía una corrección articular hacia q_deg (como move_to). Tras un lineal no se
    corrige a ciegas más de LINEAL_CORRECTION_MAX_DEG: sería otra configuración del brazo.
    Devuelve {'seq', 'code', 'joints_deg', 'max_error_deg'}."""
    goal = [[float(v) for v in q_deg], [9e9] * 6]
    if cancel is not None and cancel.is_set():
        raise Refused('CANCELADO antes del tramo. El robot queda donde está.')
    echo(f'Tramo {tipo} → ' + ', '.join(f'{v:.3f}' for v in goal[0]))
    result = mover.send(goal, step=MAX_STEP_DEG, timeout=timeout, echo=echo, tipo=tipo, pose_tool0=pose_tool0)
    current = mover.joints()
    for attempt in range(2):
        error = max(abs(a - b) for a, b in zip(current[0], goal[0]))
        if error <= ARRIVAL_DEG:
            break
        if tipo != 'articular' and error > LINEAL_CORRECTION_MAX_DEG:
            raise Refused(f'El tramo lineal terminó a {error:.3f}° de lo previsto (¿otra configuración del brazo?): '
                          'no se corrige a ciegas. Revisar la postura.')
        if cancel is not None and cancel.is_set():
            raise Refused('CANCELADO antes de la corrección. El robot queda donde está.')
        echo(f'Corrección articular {attempt + 1}: faltan {error:.3f}°.')
        result = mover.send(goal, step=MAX_STEP_DEG, timeout=timeout, echo=echo)
        current = mover.joints()
    error = max(abs(a - b) for a, b in zip(current[0], goal[0]))
    if error > ARRIVAL_DEG:
        raise Refused(f'No se alcanzó el objetivo del tramo (falta {error:.3f}°); revisar el FlexPendant.')
    return {'seq': result['seq'], 'code': result['code'], 'joints_deg': current[0], 'max_error_deg': error}


def print_status(state):
    print(f"Modo: {state['opmode']} | Motores: {state['ctrlstate']} | RAPID: {state['execution']} | "
          f"Módulo: {state.get('module')}")
    print('Ejes (°): ' + ', '.join(f'J{i}={v:.3f}' for i, v in enumerate(state['joints_deg'], 1)))
    if 'rbActivo' in state:
        code = int(state['rbCodigo'])
        print(f"ServidorPC activo: {'SI' if state['rbActivo'] == 1 else 'NO'} | pcSeq={state['pcSeq']:.0f} "
              f"rbSeq={state['rbSeq']:.0f} | último resultado: {CODES.get(code, code)}")


def parse_goal(words, current):
    """abs a b c d e f  |  j<N> <delta>  |  j<N>= <valor>"""
    goal = [list(current[0]), [9e9] * 6]
    if words[0] == 'abs':
        if len(words) != 7:
            raise Refused('Uso: abs J1 J2 J3 J4 J5 J6 (grados)')
        goal[0] = [float(w) for w in words[1:]]
        return goal
    if len(words) == 2 and words[0].lower().startswith('j'):
        name = words[0].lower()
        absolute = name.endswith('=')
        index = int(name.strip('j=')) - 1
        if not 0 <= index < 6:
            raise Refused('Eje entre J1 y J6.')
        value = float(words[1])
        goal[0][index] = value if absolute else goal[0][index] + value
        return goal
    raise Refused('Orden no reconocida.')


HELP = """Órdenes:
  estado                 modo, motores, RAPID y ángulos
  j2 +5 / j6 -10         mover un eje de forma relativa (grados)
  j3= 20                 llevar un eje a un valor absoluto
  abs 0 -10 20 0 30 0    llevar los seis ejes a valores absolutos
  paso 5                 cambiar el tamaño máximo de cada orden (0 a 355°)
  fin                    terminar ServidorPC en el robot (pcFin=1)
  salir                  cerrar este programa (el robot sigue esperando)
Ctrl+C no detiene el robot: para eso, soltar el habilitador o pulsar Stop/emergencia."""


def interactive(mover, step, timeout):
    print(HELP)
    with mover.lock:
        state = mover.status()
        print_status(state)
        # Pedir RMMP ahora, con el robot quieto, y no en medio de la primera orden.
        mover.ensure_rmmp(state)
    stop = mover.start_keeper()
    try:
        return _interactive(mover, step, timeout)
    finally:
        stop.set()


def _interactive(mover, step, timeout):
    while True:
        try:
            line = input(f'irb120 (paso {step}°)> ').strip()
        except EOFError:
            return 0
        if not line:
            continue
        try:
            words = shlex.split(line)
        except ValueError as exc:
            print('NO ENVIADO:', exc)
            continue
        if mover.keeper_error:
            print('AVISO:', mover.keeper_error, '— la siguiente escritura volverá a pedir RMMP.')
            mover.keeper_error = None
        try:
            mover.lock.acquire()
            if words[0] in ('salir', 'exit', 'q'):
                return 0
            if words[0] in ('ayuda', 'help', '?'):
                print(HELP)
            elif words[0] == 'estado':
                state = mover.status()
                print_status(state)
                for problem in mover.ready(state):
                    print('FALTA:', problem)
            elif words[0] == 'paso':
                value = float(words[1])
                if not 0 < value <= MAX_STEP_DEG:
                    raise Refused(f'El paso debe estar entre 0 y {MAX_STEP_DEG:g}°.')
                step = value
            elif words[0] == 'fin':
                mover.finish(); print('pcFin=1 enviado: ServidorPC termina en el robot.')
            else:
                current = mover.joints()
                goal = parse_goal(words, current)
                legs = len(split_path(current, goal, step))
                if legs > 1 or words[0] == 'abs':
                    # Un «abs» en radianes o un destino lejano moverían varios ejes sin avisar.
                    shown = ', '.join(f'J{i}={v:.2f}' for i, v in enumerate(goal[0], 1))
                    if input(f'{legs} orden(es) hasta {shown} (grados). ¿Confirmar? [s/N] ').strip().lower() != 's':
                        print('Cancelado: no se envió nada.')
                        continue
                result = mover.move_to(goal, step, timeout)
                print(f"LLEGADA confirmada por el robot (orden {result['seq']}), error máximo "
                      f"{result['max_error_deg']:.3f}°.")
        except (Refused, ValueError, IndexError) as exc:
            print('NO ENVIADO / DETENIDO:', exc)
        finally:
            mover.lock.release()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('action', choices=('estado', 'eventos', 'instalar', 'arrancar', 'mover', 'interactivo',
                                           'terminar'))
    parser.add_argument('valores', nargs='*', help='mover: "abs J1..J6", "j2 +5" o "j3= 20"')
    parser.add_argument('--host', default='192.168.125.1')
    parser.add_argument('--user', default='Default User')
    parser.add_argument('--http-port', type=int, default=80, help='Distinto de 80 solo en 127.0.0.1')
    parser.add_argument('--paso', type=float, default=5., help=f'Máximo cambio por eje en cada orden (≤{MAX_STEP_DEG:g}°)')
    parser.add_argument('--timeout', type=float, default=120., help='Segundos de espera por orden')
    parser.add_argument('--auto', action='store_true',
                        help='instalar: variante con permitirAuto := TRUE (modo AUTO, motores ON sin habilitador)')
    parser.add_argument('--log-dir', type=Path, default=PROJECT / 'salidas/control_articular/rws_mover')
    args = parser.parse_args(argv)
    if not 0 < args.paso <= MAX_STEP_DEG:
        parser.error(f'--paso debe estar entre 0 y {MAX_STEP_DEG:g}')
    if args.action == 'mover' and not args.valores:
        parser.error('mover necesita valores, por ejemplo: mover j6 +5')
    try:
        base = build_base_url(args.host, args.http_port)
    except ValueError as exc:
        parser.error(str(exc))
    import requests
    from requests.auth import HTTPDigestAuth
    args.log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%fZ')
    log = args.log_dir / f'{args.action}_{stamp}.jsonl'
    password = getpass.getpass(f'Contraseña RWS de "{args.user}" (no se guarda): ')
    mover = None
    try:
        with requests.Session() as session:
            session.trust_env = False
            session.auth = HTTPDigestAuth(args.user, password)
            mover = Mover(session, base, session_factory=requests.Session, log=log)
            identity = mover.connect()
            print(f"Controlador {identity['name']} | RobotWare {identity['rwversionname']} | "
                  f"módulo {mover.module_version}")
            if args.action == 'estado':
                state = mover.status()
                print_status(state)
                problems = mover.ready(state)
                for problem in problems:
                    print('FALTA:', problem)
                if not problems:
                    print('LISTO para recibir órdenes.')
                return 0
            if args.action == 'instalar':
                report = mover.install(args.log_dir, auto=args.auto)
                report['write_events'] = mover.write_events
                path = args.log_dir / f'instalar_{stamp}.json'
                path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
                print(json.dumps({k: v for k, v in report.items() if k != 'write_events'},
                                 ensure_ascii=False, indent=2))
                print('Informe:', path)
                if report['passed']:
                    print(('Módulo v5 (variante AUTO) instalado. ' if args.auto else 'Módulo v5 instalado. ') +
                          'En el FlexPendant: Editor de programas → Verificar programa. '
                          'El puntero pudo restablecerse: NO pulsar Start sobre main.')
                return 0 if report['passed'] else 2
            if args.action == 'eventos':
                state = mover.status()
                print_status(state)
                try:
                    row, values = mover.pointer()
                    print('Puntero de programa:', values)
                except Exception as exc:
                    print('Puntero de programa: no se pudo leer:', exc)
                print('Últimos eventos del controlador (más reciente primero):')
                for row in mover.events():
                    kind = {'1': 'info', '2': 'AVISO', '3': 'ERROR'}.get(str(row.get('msgtype')), row.get('msgtype'))
                    print(f"  {row.get('tstamp', '')}  [{kind}] {row.get('code', '')}  {row.get('title', '')}")
                    if row.get('desc'):
                        print('      ' + str(row['desc'])[:200].replace('\n', ' '))
                return 0
            if args.action == 'arrancar':
                mover.start_server()
                return 0
            if args.action == 'terminar':
                mover.finish(); print('pcFin=1 enviado.')
                return 0
            if args.action == 'mover':
                goal = parse_goal(args.valores, mover.joints())
                result = mover.move_to(goal, args.paso, args.timeout)
                print(f"LLEGADA confirmada (orden {result['seq']}), error máximo {result['max_error_deg']:.3f}°.")
                return 0
            return interactive(mover, args.paso, args.timeout)
    except (Refused, ValueError, requests.RequestException, OSError) as exc:
        print('DETENIDO:', exc)
        if mover is not None and mover.write_events:
            print('Registro:', log)
        return 2
    except KeyboardInterrupt:
        print('\nInterrumpido en la PC. Esto NO detiene el robot: el operador suelta el habilitador o pulsa Stop.')
        return 130
    finally:
        if mover is not None:
            mover.rmmp.close()
            logout(mover)


if __name__ == '__main__':
    raise SystemExit(main())
