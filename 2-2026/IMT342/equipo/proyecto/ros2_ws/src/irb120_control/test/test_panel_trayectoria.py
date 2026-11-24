"""Panel: ejecución de trayectorias, vista previa, buzón de puntos y testigo HTTP. Sin ROS ni robot."""
import json
import math
import os
from pathlib import Path
import stat
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
from irb120_control.panel.buzon import MAX_ENTRADAS, Buzon
from irb120_control.panel.cinematica import convertir_herramienta, kinematics, pose_desde_cuaternion, pose_of
from irb120_control.panel.estado import Panel
from irb120_control.panel.ordenes import Ordenes
from irb120_control.panel.simulado import SimulatedMover
from irb120_control.panel.trayectoria import Ejecutor, comparar_ordenes
from irb120_control.panel.web import serve
from irb120_control.rws_j6 import Refused
from irb120_control.trayectorias import Punto, Trayectoria, a_ordenes, planificar

A, B, C = [20, 10, -10, 0, 40, 0], [-20, 15, -5, 0, 45, 10], [0, -10, 10, 0, 60, 0]


def tray(**kw):
    return Trayectoria('abc', [Punto('A', q=A), Punto('B', q=B), Punto('C', q=C)], **kw)


def esperar(condicion, segundos=20.):
    limite = time.monotonic() + segundos
    while not condicion() and time.monotonic() < limite:
        time.sleep(.005)
    assert condicion(), 'tiempo agotado'


class Base(unittest.TestCase):
    def panel(self, ganchos=None):
        """Panel simulado rápido; `ganchos` se llama en cada espera del robot (hilo de ejecución)."""
        mover = SimulatedMover(speed=3000., sleep=(lambda dt: (ganchos or (lambda: None))() or time.sleep(.001)))
        panel = Panel(mover, simulated=True)
        panel.poll()
        return panel

    @staticmethod
    def cuerpo(panel, t):
        q0 = panel.ejecutor.leer_q()
        plan = planificar(t, q0, panel.speed_pct)
        assert plan.ok, plan.resumen
        return {'trayectoria': t.to_dict(), 'ordenes': a_ordenes(plan), 'velocidad_pct': panel.speed_pct}

    @staticmethod
    def terminar(panel):
        if panel.worker is not None:
            panel.worker.join(timeout=20.)
        assert not panel.busy


class Ejecucion(Base):
    def test_a_b_c_a_con_dos_repeticiones(self):
        panel = self.panel()
        t = tray(repeticiones=2)
        panel.handle('trayectoria', self.cuerpo(panel, t))
        self.assertTrue(panel.busy)
        self.terminar(panel)
        estado = panel.snapshot()['trayectoria']
        self.assertEqual(estado['fase'], 'terminada', estado['mensaje'])
        self.assertEqual((estado['vueltas'], estado['total']), (2, 4))
        filas = estado['resultados']
        # vuelta 1: A, B, C, A; vuelta 2: ya está en A (sin movimiento) y B, C, A
        self.assertEqual([(f['vuelta'], f['hasta']) for f in filas],
                         [(1, 'A'), (1, 'B'), (1, 'C'), (1, 'A'), (2, 'B'), (2, 'C'), (2, 'A')])
        for fila in filas:
            self.assertLess(max(abs(e) for e in fila['error_deg']), .05)
            self.assertLess(fila['pos_mm'], .5)
            self.assertEqual(len(fila['error_pct']), 6)
        self.assertLess(max(abs(a - b) for a, b in zip(panel.target, A)), .05)

    def test_busy_y_objetivo_naranja_durante_la_ejecucion(self):
        vistos = []
        panel = None

        def gancho():
            vistos.append((panel.busy, list(panel.target)))
            try:
                panel.handle('objetivo', {'q': A})
            except Refused as exc:
                vistos.append(str(exc))
        panel = self.panel(gancho)
        panel.handle('trayectoria', self.cuerpo(panel, tray(cerrar=False)))
        self.terminar(panel)
        busy, target = vistos[0]
        self.assertTrue(busy)
        self.assertLess(max(abs(a - b) for a, b in zip(target, A)), 1e-9)   # destino del primer tramo
        self.assertTrue(any('en curso' in v for v in vistos if isinstance(v, str)))
        with self.assertRaises(Refused):
            panel.handle('trayectoria', {})   # no hay trayectoria válida
        self.assertEqual(panel.ejecutor.estado()['fase'], 'terminada')

    def test_postura_cambiada_se_rechaza(self):
        panel = self.panel()
        cuerpo = self.cuerpo(panel, tray())
        cuerpo['ordenes'][1]['q'][0] += .5          # otra q
        with self.assertRaisesRegex(Refused, 'volver a planificar en el Estudio'):
            panel.handle('trayectoria', cuerpo)
        cuerpo = self.cuerpo(panel, tray())
        cuerpo['ordenes'][0]['tipo'] = 'lineal' if cuerpo['ordenes'][0]['tipo'] == 'articular' else 'articular'
        with self.assertRaisesRegex(Refused, 'tipo distinto'):
            panel.handle('trayectoria', cuerpo)
        cuerpo = self.cuerpo(panel, tray())
        cuerpo['ordenes'][2]['pose_tool0'][0] += .1  # 0,1 mm
        with self.assertRaisesRegex(Refused, 'posición'):
            panel.handle('trayectoria', cuerpo)
        cuerpo = self.cuerpo(panel, tray())
        del cuerpo['ordenes'][-1]
        with self.assertRaisesRegex(Refused, 'órdenes'):
            panel.handle('trayectoria', cuerpo)
        self.assertFalse(panel.busy)
        self.assertEqual(panel.ejecutor.estado()['fase'], 'lista')

    def test_comparar_ordenes_tolera_el_signo_del_cuaternion(self):
        panel = self.panel()
        esperadas = self.cuerpo(panel, tray())['ordenes']
        iguales = json.loads(json.dumps(esperadas))
        iguales[0]['pose_tool0'][3:] = [-v for v in iguales[0]['pose_tool0'][3:]]
        self.assertIsNone(comparar_ordenes(iguales, esperadas))

    def test_plan_no_apto_se_rechaza(self):
        panel = self.panel()
        fuera = Trayectoria('lejos', [Punto('X', pose=[1500, 0, 300, 0, 90, 0])])
        with self.assertRaisesRegex(Refused, 'no es apto'):
            panel.handle('trayectoria', {'trayectoria': fuera.to_dict(), 'ordenes': []})

    def test_pausar_y_reanudar_entre_tramos(self):
        pedido = []
        panel = None

        def gancho():
            if not pedido:
                pedido.append(panel.handle('pausar', {}))
        panel = self.panel(gancho)
        panel.handle('trayectoria', self.cuerpo(panel, tray(cerrar=False)))
        esperar(lambda: panel.ejecutor.estado()['fase'] == 'pausada')
        time.sleep(.1)
        estado = panel.ejecutor.estado()
        self.assertEqual(estado['fase'], 'pausada')
        self.assertEqual(len(estado['resultados']), 1)          # terminó el tramo en curso y no siguió
        self.assertTrue(panel.busy)
        q_pausa = list(panel.mover.q)
        self.assertLess(max(abs(a - b) for a, b in zip(q_pausa, A)), .05)
        with self.assertRaises(Refused):                        # alguien movió el robot: no se reanuda
            panel.mover.q[0] += 1.
            try:
                panel.handle('reanudar', {})
            finally:
                panel.mover.q[0] -= 1.
        panel.handle('reanudar', {})
        self.terminar(panel)
        estado = panel.ejecutor.estado()
        self.assertEqual(estado['fase'], 'terminada')
        self.assertEqual([f['hasta'] for f in estado['resultados']], ['A', 'B', 'C'])
        with self.assertRaises(Refused):
            panel.handle('pausar', {})

    def test_cancelar_termina_el_tramo_en_curso(self):
        pedido = []
        panel = None

        def gancho():
            if not pedido:
                pedido.append(True)
                panel.handle('cancelar', {})
        panel = self.panel(gancho)
        panel.handle('trayectoria', self.cuerpo(panel, tray()))
        self.terminar(panel)
        estado = panel.ejecutor.estado()
        self.assertEqual(estado['fase'], 'cancelada', estado['mensaje'])
        self.assertEqual([f['hasta'] for f in estado['resultados']], ['A'])
        self.assertLess(max(abs(a - b) for a, b in zip(panel.mover.q, A)), .05)

    def test_cancelar_estando_pausada(self):
        panel = None

        def gancho():
            panel.ejecutor.pausa.set()
        panel = self.panel(gancho)
        panel.handle('trayectoria', self.cuerpo(panel, tray()))
        esperar(lambda: panel.ejecutor.estado()['fase'] == 'pausada')
        panel.handle('cancelar', {})
        self.terminar(panel)
        self.assertEqual(panel.ejecutor.estado()['fase'], 'cancelada')

    def test_la_verificacion_contra_el_controlador_bloquea(self):
        panel = self.panel()
        original = panel.mover.controller_pose

        def desviado():
            q, pose = original()
            return q, [pose[0] + 5., *pose[1:]]       # el «ABB» dice estar 5 mm más allá
        panel.mover.controller_pose = desviado
        panel.handle('trayectoria', self.cuerpo(panel, tray()))
        self.terminar(panel)
        estado = panel.ejecutor.estado()
        self.assertEqual(estado['fase'], 'error')
        self.assertIn('modelo y controlador', estado['mensaje'])
        self.assertEqual(estado['resultados'], [])
        self.assertLess(max(abs(a - b) for a, b in zip(panel.mover.q, [0, 0, 0, 0, 30, 0])), 1e-9)   # no se movió

    def test_puntos_con_pose_pasan_ik_fk_e_ida_y_vuelta(self):
        panel = self.panel()
        t = Trayectoria('poses', [Punto('A', pose=pose_of(A, 'tcp')), Punto('B', pose=pose_of(B, 'tcp'))])
        panel.handle('trayectoria', self.cuerpo(panel, t))
        self.terminar(panel)
        self.assertEqual(panel.ejecutor.estado()['fase'], 'terminada', panel.ejecutor.estado()['mensaje'])


class VistaPrevia(Base):
    def rapido(self, panel, ganchos=None):
        panel.ejecutor = Ejecutor(panel, sleep=lambda dt: (ganchos or (lambda: None))())

    def test_mueve_el_objetivo_y_no_envia_nada(self):
        panel = self.panel()
        enviados = []
        panel.mover.send = lambda *a, **k: enviados.append(a)
        trazas = []
        self.rapido(panel, lambda: trazas.append(list(panel.target)))
        cuerpo = self.cuerpo(panel, tray())
        cuerpo['factor'] = 4
        respuesta = panel.handle('vista_previa', cuerpo)
        self.assertIn('activa', respuesta['vista_previa'])
        panel.worker.join(timeout=20.)
        self.assertEqual(enviados, [])
        self.assertFalse(panel.busy)
        self.assertFalse(panel.ejecutor.previsualizando)
        self.assertGreater(len(trazas), 10)
        self.assertGreater(len({tuple(round(v, 3) for v in q) for q in trazas}), 10)
        self.assertLess(max(abs(a - b) for a, b in zip(panel.target, A)), 1e-6)   # cerrar: termina en A
        self.assertEqual(panel.mover.q, [0, 0, 0, 0, 30, 0])

    def test_factor_invalido_y_cancelar(self):
        panel = self.panel()
        cuerpo = self.cuerpo(panel, tray())
        for malo in (0, 5, -1, True, 'x'):
            with self.assertRaises(Refused):
                panel.handle('vista_previa', {**cuerpo, 'factor': malo})
        self.rapido(panel, lambda: panel.handle('cancelar', {}))
        panel.handle('vista_previa', cuerpo)
        panel.worker.join(timeout=20.)
        self.assertGreater(max(abs(a - b) for a, b in zip(panel.target, A)), 1.)   # no llegó al final
        self.assertFalse(panel.ejecutor.previsualizando)

    def test_no_se_permite_durante_una_ejecucion_ni_se_mezclan(self):
        panel = None
        intentos = []

        def gancho():
            try:
                panel.handle('vista_previa', body)
            except Refused as exc:
                intentos.append(str(exc))
        panel = self.panel(gancho)
        body = self.cuerpo(panel, tray(cerrar=False))
        panel.handle('trayectoria', body)
        self.terminar(panel)
        self.assertTrue(intentos and 'en curso' in intentos[0])
        # y al revés: durante la vista previa no se ejecuta ni se cambia el objetivo
        panel = self.panel()
        cuerpo = self.cuerpo(panel, tray(cerrar=False))
        bloqueos = []

        def gancho2():
            for accion in ('trayectoria', 'enviar', 'objetivo'):
                try:
                    panel.handle(accion, cuerpo if accion == 'trayectoria' else {'q': A})
                    bloqueos.append(None)
                except Refused as exc:
                    bloqueos.append(str(exc))
        self.rapido(panel, gancho2)
        panel.handle('vista_previa', cuerpo)
        panel.worker.join(timeout=20.)
        self.assertTrue(bloqueos and all(b for b in bloqueos), bloqueos[:3])


class Buzones(Base):
    def test_ids_desde_id_y_limite(self):
        buzon = Buzon()
        for i in range(MAX_ENTRADAS + 10):
            buzon.agregar('http', [i, 0, 0, 0, 0, 0], 'tcp')
        entradas, ultimo = buzon.tomar(0)
        self.assertEqual((len(entradas), ultimo), (MAX_ENTRADAS, MAX_ENTRADAS + 10))
        self.assertEqual([e['id'] for e in entradas], list(range(11, MAX_ENTRADAS + 11)))
        self.assertEqual([e['id'] for e in buzon.tomar(MAX_ENTRADAS + 8)[0]], [MAX_ENTRADAS + 9, MAX_ENTRADAS + 10])
        self.assertEqual(len(buzon.tomar(0)[0]), MAX_ENTRADAS)       # tomar no borra
        buzon.vaciar()
        self.assertEqual(buzon.tomar(0)[0], [])
        self.assertEqual(buzon.agregar('rviz', [0] * 6, 'tcp')['id'], MAX_ENTRADAS + 11)   # los ids no se reinician
        with self.assertRaises(Refused):
            buzon.tomar(-1)
        with self.assertRaises(Refused):
            buzon.agregar('otro', [0] * 6, 'tcp')

    def test_acciones_del_panel(self):
        panel = self.panel()
        a = panel.handle('punto_externo', {'pose': pose_of(A, 'tcp'), 'nombre': 'taza'})['punto']
        b = panel.handle('punto_externo', {'pose': pose_of(B, 'tcp')})['punto']
        self.assertEqual((a['id'], a['origen'], a['nombre'], b['nombre']), (1, 'http', 'taza', 'P2'))
        for x, y in zip(a['pose'], pose_of(A, 'tcp')):
            self.assertAlmostEqual(x, y, places=6)
        self.assertEqual([e['id'] for e in panel.handle('buzon_tomar', {'desde_id': 1})['entradas']], [2])
        self.assertEqual(len(panel.snapshot()['buzon']), 2)
        panel.handle('buzon_vaciar', {})
        self.assertEqual(panel.snapshot()['buzon'], [])
        self.assertEqual(panel.handle('buzon_tomar', {})['ultimo_id'], 2)

    def test_pose_en_el_punto_del_panel(self):
        panel = self.panel()
        panel.set_tool('brida')
        entrada = panel.handle('punto_externo', {'pose': pose_of(A, 'tcp')})['punto']
        self.assertEqual(entrada['herramienta'], 'brida')
        for x, y in zip(entrada['pose'], pose_of(A, 'brida')):
            self.assertAlmostEqual(x, y, places=5)

    def test_punto_externo_inalcanzable_se_rechaza(self):
        panel = self.panel()
        for pose in ([1500., 0., 300., 0., 90., 0.], [5000., 0, 0, 0, 0, 0], [float('nan')] + [0.] * 5, [1, 2, 3]):
            with self.assertRaises(Refused):
                panel.handle('punto_externo', {'pose': pose})
        self.assertEqual(panel.handle('buzon_tomar', {})['entradas'], [])
        self.assertEqual(len(panel.snapshot()['buzon_rechazados']), 4)
        with self.assertRaises(Refused):
            panel.handle('punto_externo', {'pose': pose_of(A, 'tcp'), 'herramienta': 'pinza'})

    def test_desde_rviz(self):
        panel = self.panel()
        panel.handle('objetivo', {'q': A})
        a = panel.agregar_desde_rviz()
        self.assertEqual((a['origen'], a['nombre']), ('rviz', 'P1'))
        self.assertEqual(a['q'], A)
        self.assertEqual(a['pose'], pose_of(A, 'tcp'))
        m = panel.agregar_desde_rviz(medida=True)
        self.assertEqual(m['q'], [0, 0, 0, 0, 30, 0])

    def test_conversion_de_mensajes_ros(self):
        np, _, _, transforms = kinematics()
        pose = pose_of(A, 'tcp')
        x, y, z, w = transforms.matrix_to_quaternion(transforms.rpy_to_matrix(*np.deg2rad(pose[3:])))
        recuperada = pose_desde_cuaternion('base_link', [v / 1000. for v in pose[:3]], (x, y, z, w))
        for p, r in zip(pose, recuperada):
            self.assertAlmostEqual(p, r, places=5)
        escalada = pose_desde_cuaternion('base_link', [.3, .1, .2], (2 * x, 2 * y, 2 * z, 2 * w))   # normalizable
        self.assertAlmostEqual(escalada[3], recuperada[3], places=5)
        with self.assertRaisesRegex(Refused, 'base_link'):
            pose_desde_cuaternion('camara', [0, 0, 0], (0, 0, 0, 1))
        with self.assertRaisesRegex(Refused, 'finitos'):
            pose_desde_cuaternion('base_link', [float('nan'), 0, 0], (0, 0, 0, 1))
        with self.assertRaisesRegex(Refused, 'nulo'):
            pose_desde_cuaternion('base_link', [0, 0, 0], (0, 0, 0, 0))
        self.assertEqual(pose_desde_cuaternion('base_link', [.1, .2, .3], (0, 0, 0, 1))[:3], [100., 200., 300.])

    def test_cambio_de_herramienta_ida_y_vuelta(self):
        brida = convertir_herramienta(pose_of(A, 'tcp'), 'tcp', 'brida')
        for x, y in zip(brida, pose_of(A, 'brida')):
            self.assertAlmostEqual(x, y, places=6)
        self.assertEqual(convertir_herramienta(brida, 'brida', 'brida'), brida)


class Testigo(Base):
    def test_archivo_0600_y_se_borra(self):
        with tempfile.TemporaryDirectory() as carpeta:
            anterior = os.environ.get('IRB120_CACHE')
            os.environ['IRB120_CACHE'] = str(Path(carpeta) / 'cache')
            try:
                server, token = serve(self.panel(), 0, page='<p>__TOKEN__</p>')
                puerto = server.server_address[1]
                ruta = Path(carpeta) / 'cache' / f'panel_token_{puerto}'
                self.assertEqual(server.ruta_testigo, ruta)
                self.assertEqual(ruta.read_text(), token)
                self.assertEqual(stat.S_IMODE(ruta.stat().st_mode), 0o600)
                self.assertEqual(stat.S_IMODE(ruta.parent.stat().st_mode), 0o700)
                server.shutdown()
                server.server_close()
                self.assertFalse(ruta.exists())
            finally:
                if anterior is None:
                    os.environ.pop('IRB120_CACHE', None)
                else:
                    os.environ['IRB120_CACHE'] = anterior

    def test_tamano_maximo_por_accion(self):
        panel = self.panel()
        relleno = 'x' * 6000
        orden = Ordenes(panel)
        self.assertIn('demasiado grande', orden.atender(json.dumps({'accion': 'objetivo', 'q': [0] * 6, 'r': relleno}))['error'])
        respuesta = orden.atender(json.dumps({'accion': 'trayectoria', 'r': relleno}))
        self.assertNotIn('demasiado grande', respuesta['error'])
        self.assertIn('demasiado grande', orden.atender(json.dumps({'accion': 'trayectoria', 'r': 'x' * 70000}))['error'])
        with tempfile.TemporaryDirectory() as carpeta:
            os.environ['IRB120_CACHE'] = carpeta
            try:
                server, token = serve(panel, 0, page='x')
            finally:
                os.environ.pop('IRB120_CACHE')
            puerto = server.server_address[1]

            def post(accion, cuerpo):
                req = urllib.request.Request(f'http://127.0.0.1:{puerto}/api/{accion}', json.dumps(cuerpo).encode(),
                                             {'X-Panel-Token': token, 'Content-Type': 'application/json'})
                try:
                    with urllib.request.urlopen(req, timeout=10) as r:
                        return r.status, json.loads(r.read())
                except urllib.error.HTTPError as exc:
                    return exc.code, json.loads(exc.read())
            self.assertEqual(post('objetivo', {'q': [0] * 6, 'r': relleno})[0], 400)
            status, datos = post('trayectoria', {'r': relleno})
            self.assertEqual(status, 200)
            self.assertFalse(datos['ok'])
            self.assertEqual(post('trayectoria', {'r': 'x' * 70000})[0], 400)
            self.assertTrue(post('punto_externo', {'pose': pose_of(A, 'tcp')})[1]['ok'])
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    unittest.main()
