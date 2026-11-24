"""Panel: biblioteca de trayectorias, ejecución con bucle desde el panel y grabación. Sin ROS ni robot."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from irb120_control.panel.despacho import LENTAS
from irb120_control.panel.estado import Panel
from irb120_control.panel.ordenes import Ordenes
from irb120_control.panel.simulado import SimulatedMover
from irb120_control.rws_j6 import Refused
from irb120_control.trayectorias import Punto, Trayectoria

DEMOS = Path(__file__).resolve().parents[4] / 'salidas' / 'trayectorias'   # solo se LEE (copia a una temporal)
A, B, C = [20, 10, -10, 0, 40, 0], [-20, 15, -5, 0, 45, 10], [0, -10, 10, 0, 60, 0]


def esperar(condicion, segundos=30.):
    limite = time.monotonic() + segundos
    while not condicion() and time.monotonic() < limite:
        time.sleep(.005)
    assert condicion(), 'tiempo agotado'


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        for nombre in ('10_saludo.json', '11_reverencia.json'):
            origen = DEMOS / nombre
            if origen.is_file():
                shutil.copy(origen, self.tmp / nombre)
        self.assertTrue((self.tmp / '10_saludo.json').is_file(), 'faltan las demos en salidas/trayectorias')

    def panel(self, ganchos=None):
        mover = SimulatedMover(speed=3000., sleep=(lambda dt: (ganchos or (lambda: None))() or time.sleep(.001)))
        panel = Panel(mover, simulated=True, carpeta_trayectorias=self.tmp)
        panel.poll()
        return panel

    @staticmethod
    def terminar(panel):
        if panel.worker is not None:
            panel.worker.join(timeout=60.)
        assert not panel.busy


class Biblioteca(Base):
    def test_listar(self):
        panel = self.panel()
        filas = panel.handle('trayectorias_listar', {})['biblioteca']
        saludo = next(f for f in filas if f['archivo'] == '10_saludo.json')
        self.assertEqual((saludo['numero'], saludo['vistosa'], saludo['bucle_por_defecto']), (10, True, True))
        self.assertGreater(saludo['puntos'], 2)
        self.assertIn('biblioteca', panel.snapshot())
        self.assertEqual(panel.snapshot()['grabacion'], {'puntos': [], 'n': 0})

    def test_archivo_invalido(self):
        panel = self.panel()
        for malo in ('../x.json', 'nada.json', None, '/etc/passwd'):
            with self.assertRaises(Refused):
                panel.handle('trayectoria_ejecutar', {'archivo': malo, 'bucle': False})

    def test_despacho_en_hilo(self):
        self.assertIn('trayectoria_ejecutar', LENTAS)
        self.assertIn('trayectoria_vista_previa', LENTAS)


class Ejecucion(Base):
    def test_vistosa_en_bucle_dos_vueltas_y_detener_al_final(self):
        panel = self.panel()
        panel.handle('trayectoria_ejecutar', {'archivo': '10_saludo.json', 'bucle': True})
        self.assertTrue(panel.busy)
        esperar(lambda: panel.ejecutor.estado()['vuelta'] >= 2 or panel.ejecutor.fase != 'ejecutando')
        estado = panel.snapshot()['trayectoria']
        self.assertTrue(estado['bucle'])
        self.assertIsNone(estado['vueltas'])
        panel.handle('detener_al_final', {})
        self.terminar(panel)
        estado = panel.snapshot()['trayectoria']
        self.assertEqual(estado['fase'], 'terminada', estado['mensaje'])
        self.assertGreaterEqual(estado['vuelta'], 2)

    def test_sin_bucle_una_vuelta(self):
        panel = self.panel()
        panel.handle('trayectoria_ejecutar', {'archivo': '10_saludo.json', 'bucle': False})
        self.terminar(panel)
        estado = panel.snapshot()['trayectoria']
        self.assertEqual((estado['fase'], estado['vueltas'], estado['vuelta']), ('terminada', 1, 1), estado['mensaje'])

    def test_velocidad_opcional(self):
        panel = self.panel()
        panel.handle('trayectoria_ejecutar', {'archivo': '10_saludo.json', 'bucle': False, 'velocidad_pct': 30})
        self.assertEqual(panel.speed_pct, 30)
        self.terminar(panel)

    def test_vista_previa_no_mueve_el_robot(self):
        panel = self.panel()
        q0 = list(panel.mover.q)
        panel.handle('trayectoria_vista_previa', {'archivo': '10_saludo.json'})
        esperar(lambda: not panel.ejecutor.previsualizando)
        self.assertEqual(panel.mover.q, q0)
        self.assertNotEqual(panel.target, q0)
        self.assertIsNone(panel.mover.last_order)

    def test_rechazo_con_plan_no_apto(self):
        panel = self.panel()
        malo = Trayectoria('Fuera', [Punto('A', q=[0, 0, 0, 0, 30, 0]), Punto('B', q=[170, 120, 0, 0, 0, 0])],
                           repeticiones=1)   # J2 fuera de límites
        malo.guardar(self.tmp / '30_fuera.json')
        with self.assertRaises(Refused) as cm:
            panel.handle('trayectoria_ejecutar', {'archivo': '30_fuera.json', 'bucle': False})
        self.assertIn('no es apto', str(cm.exception))
        self.assertFalse(panel.busy)

    def test_v4_fuerza_articular(self):
        panel = self.panel()
        t = Trayectoria('Lineal', [Punto('A', q=A, tipo='lineal'), Punto('B', q=B, tipo='auto'),
                                   Punto('C', q=C, tipo='lineal')], repeticiones=1)
        t.guardar(self.tmp / '31_lineal.json')
        panel.state = {'module': 'servidor_v4'}
        self.assertFalse(panel.capacidades()['lineal'])
        cuerpo = panel.biblioteca._preparar({'archivo': '31_lineal.json'}, False)
        self.assertEqual({p['tipo'] for p in cuerpo['trayectoria']['puntos']}, {'articular'})
        self.assertTrue(any('v4' in linea for linea in panel.log))
        # con v5 no se toca
        panel.state = {'module': 'servidor_v5'}
        cuerpo = panel.biblioteca._preparar({'archivo': '31_lineal.json'}, False)
        self.assertEqual([p['tipo'] for p in cuerpo['trayectoria']['puntos']], ['lineal', 'auto', 'lineal'])


class Grabacion(Base):
    def mover_a(self, panel, q):
        panel.mover.q = list(q)
        panel.poll()

    def test_grabar_tres_guardar_aparece_y_se_ejecuta(self):
        panel = self.panel()
        for q in (A, B, C):
            self.mover_a(panel, q)
            panel.handle('grabar_punto', {})
        graba = panel.snapshot()['grabacion']
        self.assertEqual((graba['n'], [p['nombre'] for p in graba['puntos']]), (3, ['P1', 'P2', 'P3']))
        panel.handle('grabar_borrar_ultimo', {})
        self.assertEqual(panel.snapshot()['grabacion']['n'], 2)
        self.mover_a(panel, C)
        panel.handle('grabar_punto', {})
        with self.assertRaises(Refused):
            panel.handle('grabar_guardar', {'nombre': '  '})
        res = panel.handle('grabar_guardar', {'nombre': 'Mi ruta', 'bucle': False})
        self.assertGreaterEqual(res['numero'], 20)
        self.assertEqual(panel.snapshot()['grabacion']['n'], 0)
        fila = next(f for f in panel.snapshot()['biblioteca'] if f['archivo'] == res['archivo'])
        self.assertEqual((fila['nombre'], fila['puntos'], fila['vistosa']), ('Mi ruta', 3, False))
        guardada = json.loads((self.tmp / res['archivo']).read_text())
        self.assertEqual(guardada['repeticiones'], 1)
        self.assertTrue(guardada['cerrar'])
        self.assertEqual({p['tipo'] for p in guardada['puntos']}, {'articular'})
        # segunda grabación: siguiente número libre
        for q in (A, B):
            self.mover_a(panel, q)
            panel.handle('grabar_punto', {})
        res2 = panel.handle('grabar_guardar', {'nombre': 'Mi ruta', 'bucle': True})
        self.assertEqual(res2['numero'], res['numero'] + 1)
        self.assertEqual(json.loads((self.tmp / res2['archivo']).read_text())['repeticiones'], 0)
        self.assertEqual(json.loads((self.tmp / res2['archivo']).read_text())['nombre'], 'Mi ruta 2')
        self.mover_a(panel, A)
        panel.handle('trayectoria_ejecutar', {'archivo': res['archivo'], 'bucle': False})
        self.terminar(panel)
        self.assertEqual(panel.snapshot()['trayectoria']['fase'], 'terminada')

    def test_pocos_puntos_y_vaciar(self):
        panel = self.panel()
        panel.handle('grabar_punto', {})
        with self.assertRaises(Refused):
            panel.handle('grabar_guardar', {'nombre': 'x'})
        panel.handle('grabar_vaciar', {})
        self.assertEqual(panel.snapshot()['grabacion']['n'], 0)
        with self.assertRaises(Refused):
            panel.handle('grabar_borrar_ultimo', {})

    def test_menu_de_rviz_agrega_a_la_grabacion(self):
        panel = self.panel()
        panel.agregar_desde_rviz(medida=True)
        panel.agregar_desde_rviz(medida=False)
        self.assertEqual(panel.snapshot()['grabacion']['n'], 2)

    def test_por_ordenes_json(self):
        panel = self.panel()
        ordenes = Ordenes(panel)
        r = ordenes.atender(json.dumps({'id': 1, 'accion': 'trayectorias_listar'}))
        self.assertTrue(r['ok'])
        self.assertIn('biblioteca', json.loads(ordenes.estado()))


if __name__ == '__main__':
    unittest.main()
