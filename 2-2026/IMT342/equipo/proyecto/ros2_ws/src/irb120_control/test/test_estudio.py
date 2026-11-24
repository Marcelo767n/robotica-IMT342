"""Estudio (CustomTkinter): cliente HTTP, editor de puntos, datos de gráficas y prueba de humo de la interfaz."""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import tempfile
import threading
import unittest
from pathlib import Path

import numpy as np

from irb120_control.estudio import biblioteca as bib
from irb120_control.estudio import cliente as cl
from irb120_control.estudio import validacion_datos as vd
from irb120_control.estudio.datos import concatenar
from irb120_control.estudio.modelo_editor import Editor
from irb120_control.trayectorias import Punto, planificar, Trayectoria

TOKEN = 'testigo-de-prueba'


class PanelFalso(ThreadingHTTPServer):
    def __init__(self):
        self.recibido = []
        super().__init__(('127.0.0.1', 0), self._handler())

    def _handler(self):
        panel = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def responder(self, codigo, datos):
                cuerpo = json.dumps(datos).encode()
                self.send_response(codigo)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(cuerpo)))
                self.end_headers()
                self.wfile.write(cuerpo)

            def do_GET(self):
                self.responder(200, {'medido': [0, 0, 0, 0, 30, 0], 'modo': 'AUTO'}) if self.path == '/estado' \
                    else self.responder(404, {})

            def do_POST(self):
                largo = int(self.headers.get('Content-Length', 0))
                cuerpo = json.loads(self.rfile.read(largo) or b'{}')
                if self.headers.get('X-Panel-Token') != TOKEN:
                    return self.responder(403, {'ok': False})
                panel.recibido.append((self.path, cuerpo))
                if self.path == '/api/falla':
                    return self.responder(200, {'ok': False, 'error': 'rechazado'})
                self.responder(200, {'ok': True, 'eco': cuerpo})
        return H


class ClienteTest(unittest.TestCase):
    def setUp(self):
        self.srv = PanelFalso()
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.dir = tempfile.TemporaryDirectory()
        self.cl = cl.Cliente(self.srv.server_address[1], carpeta=self.dir.name)

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.dir.cleanup()

    def poner_testigo(self, texto=TOKEN):
        (Path(self.dir.name) / f'panel_token_{self.cl.puerto}').write_text(texto + '\n')

    def test_estado(self):
        self.assertFalse(self.cl.conectado)
        self.cl.leer_una_vez()
        estado, error = self.cl.instantanea()
        self.assertIsNone(error)
        self.assertEqual(estado['modo'], 'AUTO')
        self.assertTrue(self.cl.conectado)

    def test_post_con_testigo(self):
        self.poner_testigo()
        r = self.cl.accion('buzon_tomar', {'desde_id': 3})
        self.assertTrue(r['ok'])
        self.assertEqual(self.srv.recibido, [('/api/buzon_tomar', {'desde_id': 3})])

    def test_post_testigo_incorrecto(self):
        self.poner_testigo('otro')
        r = self.cl.accion('pausar')
        self.assertFalse(r['ok'])
        self.assertIn('testigo', r['error'])
        self.assertEqual(self.srv.recibido, [])

    def test_post_sin_archivo_de_testigo(self):
        r = self.cl.accion('pausar')
        self.assertFalse(r['ok'])
        self.assertIn('testigo', r['error'])

    def test_error_del_panel_y_sin_conexion(self):
        self.poner_testigo()
        self.assertEqual(self.cl.accion('falla')['error'], 'rechazado')
        self.srv.shutdown()
        self.srv.server_close()
        r = self.cl.accion('pausar', timeout=.5)
        self.assertFalse(r['ok'])
        self.cl.leer_una_vez()
        self.assertIn('Sin conexión', self.cl.instantanea()[1])

    def test_demo_no_envia(self):
        d = cl.Cliente(demo=True)
        self.assertFalse(d.accion('trayectoria', {})['ok'])
        self.assertFalse(d.conectado)
        self.assertEqual(len(d.instantanea()[0]['medido']), 6)


class EditorTest(unittest.TestCase):
    def editor(self):
        e = Editor()
        for q in ([0, 0, 0, 0, 30, 0], [10, 0, 0, 0, 30, 0], [20, 0, 0, 0, 30, 0]):
            e.agregar(Punto('P', q=q))
        return e

    def test_nombres_unicos(self):
        e = self.editor()
        self.assertEqual(e.nombres(), ['P', 'P 2', 'P 3'])
        self.assertEqual(e.nombre_nuevo(), 'A')
        e.agregar(Punto('A', q=[0, 0, 0, 0, 30, 0]))
        self.assertEqual(e.nombre_nuevo(), 'B')

    def test_subir_bajar_borrar(self):
        e = self.editor()
        self.assertEqual(e.subir(2), 1)
        self.assertEqual(e.nombres(), ['P', 'P 3', 'P 2'])
        self.assertEqual(e.subir(0), 0)
        self.assertEqual(e.bajar(0), 1)
        self.assertEqual(e.nombres(), ['P 3', 'P', 'P 2'])
        self.assertEqual(e.bajar(2), 2)
        self.assertEqual(e.borrar(2), 1)
        self.assertEqual(e.nombres(), ['P 3', 'P'])
        e.borrar(0)
        self.assertEqual(e.borrar(0), -1)
        self.assertEqual(len(e), 0)

    def test_editar_rechaza_nombre_repetido(self):
        e = self.editor()
        with self.assertRaises(ValueError):
            e.editar(0, Punto('P 2', q=[1, 1, 1, 1, 1, 1]))
        e.editar(0, Punto('Z', q=[1, 1, 1, 1, 1, 1]))
        self.assertEqual(e.nombres()[0], 'Z')

    def test_a_trayectoria_y_json(self):
        e = self.editor()
        t = e.a_trayectoria(' Ruta ', cerrar=False, repeticiones=3)
        self.assertEqual((t.nombre, t.cerrar, t.repeticiones, len(t.puntos)), ('Ruta', False, 3, 3))
        with self.assertRaises(ValueError):
            e.a_trayectoria('  ')
        with tempfile.TemporaryDirectory() as d:
            t.guardar(Path(d) / 'r.json')
            e2 = Editor()
            e2.cargar(Trayectoria.cargar(Path(d) / 'r.json'))
            self.assertEqual(e2.nombres(), e.nombres())

    def test_desde_buzon(self):
        e = Editor()
        n, ultimo = e.desde_buzon([
            {'id': 5, 'origen': 'vision', 'nombre': 'taza', 'pose': [300, 0, 200, 0, 90, 0], 'q': None},
            {'id': 4, 'origen': 'rviz', 'nombre': 'rviz', 'pose': [300, 50, 200, 0, 90, 0], 'q': [0, 0, 0, 0, 30, 0]},
            {'id': 6, 'origen': 'rviz', 'nombre': 'mala', 'pose': [1, 2], 'q': None}])
        self.assertEqual((n, ultimo), (2, 6))
        self.assertEqual(e.nombres(), ['rviz', 'taza'])
        self.assertEqual([p.origen for p in e.puntos], ['rviz', 'vision'])


Q_DEMO = ([20, 10, -10, 0, 40, 0], [-20, 15, -5, 0, 45, 10], [0, -10, 10, 0, 60, 0])


def _plan():
    t = Trayectoria('t', [Punto(n, q=q, origen='angulos') for n, q in zip('ABC', Q_DEMO)], cerrar=True)
    return planificar(t, [0, 0, 0, 0, 30, 0], 20.)


class DatosTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = _plan()

    def test_concatenacion(self):
        d = concatenar(self.plan)
        n = sum(len((tr.opciones[tr.tipo]).muestras.t) for tr in self.plan.tramos)
        self.assertEqual(len(d['t']), n)
        self.assertEqual(d['q'].shape, (n, 6))
        self.assertTrue(np.all(np.diff(d['t']) >= 0))
        self.assertAlmostEqual(d['duracion'], d['t'][-1])
        self.assertEqual(len(d['cortes']), len(self.plan.tramos))
        self.assertEqual(d['cortes'][0][1], 'Inicio→A')
        self.assertEqual(d['cortes'][-1][1], 'C→A')
        for clave in ('qd', 'qdd', 'tau'):
            self.assertEqual(d[clave].shape, (n, 6))
        self.assertEqual(d['sigma'].shape, (n,))

    def test_sin_muestras(self):
        class Plan:
            tramos = []
        self.assertIsNone(concatenar(Plan()))

    def test_figura_sin_pyplot(self):
        import matplotlib
        matplotlib.use('Agg')
        from irb120_control.estudio.vistas.graficas import construir_figura
        for oscuro in (False, True):
            fig = construir_figura(concatenar(self.plan), oscuro)
            self.assertEqual(len(fig.axes), 6)
        self.assertEqual(len(construir_figura(None, True).axes), 0)

    def test_tolerancias_para_la_tabla(self):
        from irb120_control.estudio.vistas.reglas import filas_tolerancias
        filas = filas_tolerancias()
        self.assertEqual(len(filas), 9)
        self.assertEqual(filas[0], ('σ_min(J) a lo largo del tramo', '< 0,04', '< 0,02'))


def _tray(nombre, n=2):
    return Trayectoria(nombre, [Punto(f'P{i}', q=[i, 0, 0, 0, 30, 0]) for i in range(n)], cerrar=False)


class BibliotecaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name) / 'trayectorias'

    def tearDown(self):
        self.tmp.cleanup()

    def test_nombre_archivo(self):
        self.assertEqual(bib.nombre_archivo('Paletizado', 3), '03_paletizado.json')
        self.assertEqual(bib.nombre_archivo('Inspección  A/B', None), 'inspeccion-a-b.json')
        self.assertEqual(bib.nombre_archivo('¡¡', 12), '12_trayectoria.json')
        for malo in (0, 100, True, 2.5):
            with self.assertRaises(ValueError):
                bib.nombre_archivo('x', malo)
        self.assertEqual(bib.numero_de('/x/03_paletizado.json'), 3)
        self.assertIsNone(bib.numero_de('/x/paletizado.json'))
        self.assertIsNone(bib.numero_de('/x/00_cero.json'))

    def test_guardar_listar_y_orden(self):
        bib.guardar(_tray('Zeta'), self.d, None)
        bib.guardar(_tray('Beta'), self.d, 5)
        bib.guardar(_tray('Alfa', 3), self.d, 2)
        (self.d / 'roto.json').write_text('{no')
        es = bib.listar(self.d)
        self.assertEqual([(e.numero, e.nombre, e.puntos) for e in es], [(2, 'Alfa', 3), (5, 'Beta', 2), (None, 'Zeta', 2)])
        self.assertTrue((self.d / '02_alfa.json').exists())
        self.assertEqual(bib.etiqueta(es[0]), '02 · Alfa  (3 pts)')
        self.assertEqual(bib.listar(self.d / 'no_existe'), [])

    def test_numero_libre_y_ocupado(self):
        bib.guardar(_tray('A'), self.d, 1)
        bib.guardar(_tray('B'), self.d, 2)
        self.assertEqual(bib.numero_libre(self.d), 3)
        with self.assertRaises(bib.Ocupado) as cm:
            bib.guardar(_tray('C'), self.d, 2)
        self.assertEqual(cm.exception.entrada.nombre, 'B')
        self.assertFalse((self.d / '02_c.json').exists())
        # reemplazar: la anterior va a la papelera
        bib.guardar(_tray('C'), self.d, 2, reemplazar=True)
        self.assertEqual([e.nombre for e in bib.listar(self.d)], ['A', 'C'])
        self.assertTrue(any((self.d / bib.PAPELERA).glob('02_b*.json')))

    def test_guardar_sobrescribe_el_propio_y_renombra(self):
        ruta = bib.guardar(_tray('A'), self.d, 4)
        bib.guardar(_tray('A', 5), self.d, 4, ruta)              # mismo número y nombre: sin conflicto
        self.assertEqual(bib.listar(self.d)[0].puntos, 5)
        t = _tray('A', 5)
        t.nombre = 'Nuevo'
        nueva = bib.guardar(t, self.d, 7, ruta)                  # cambia nombre y número: se mueve
        self.assertEqual(nueva.name, '07_nuevo.json')
        self.assertFalse(ruta.exists())
        self.assertEqual(len(bib.listar(self.d)), 1)

    def test_renombrar_duplicar(self):
        ruta = bib.guardar(_tray('Uno'), self.d, 1)
        nueva = bib.renombrar(ruta, 'Primero', 9)
        self.assertEqual(nueva.name, '09_primero.json')
        self.assertEqual(bib.listar(self.d)[0].nombre, 'Primero')
        copia = bib.duplicar(nueva, self.d, 'Primero copia', bib.numero_libre(self.d))
        self.assertEqual(copia.name, '01_primero-copia.json')
        self.assertEqual(len(bib.listar(self.d)), 2)
        with self.assertRaises(bib.Ocupado):
            bib.duplicar(nueva, self.d, 'Otra', 9)
        self.assertEqual(bib.nombre_unico(self.d, 'Primero'), 'Primero 2')

    def test_papelera_no_borra(self):
        ruta = bib.guardar(_tray('Uno'), self.d, 1)
        nueva = bib.a_papelera(ruta)
        self.assertFalse(ruta.exists())
        self.assertTrue(nueva.exists())
        self.assertEqual(bib.listar(self.d), [])
        ruta2 = bib.guardar(_tray('Uno'), self.d, 1)
        nueva2 = bib.a_papelera(ruta2)                           # mismo nombre: no pisa la anterior
        self.assertNotEqual(nueva, nueva2)
        self.assertTrue(nueva.exists() and nueva2.exists())


class PuntosEditorTest(unittest.TestCase):
    def test_insertar_y_duplicar(self):
        e = Editor([Punto('A', q=[0] * 6), Punto('B', q=[1] * 6), Punto('C', q=[2] * 6)])
        self.assertEqual(e.insertar(0, Punto('X', q=[3] * 6)), 1)
        self.assertEqual(e.nombres(), ['A', 'X', 'B', 'C'])
        self.assertEqual(e.insertar(None, Punto('Y', q=[3] * 6)), 4)
        self.assertEqual(e.insertar(-1, Punto('A', q=[3] * 6)), 5)
        self.assertEqual(e.nombres()[-1], 'A 2')
        j = e.duplicar(2)
        self.assertEqual((j, e.puntos[3].nombre), (3, 'B 2'))
        e.puntos[3].q[0] = 99
        self.assertEqual(e.puntos[2].q[0], 1)                      # copia independiente

    def test_buzon_inserta_despues_del_seleccionado(self):
        e = Editor([Punto('A', q=[0] * 6), Punto('B', q=[1] * 6)])
        e.desde_buzon([{'id': 1, 'origen': 'rviz', 'nombre': 'r1', 'pose': [300, 0, 200, 0, 90, 0]},
                       {'id': 2, 'origen': 'rviz', 'nombre': 'r2', 'pose': [300, 10, 200, 0, 90, 0]}], 0)
        self.assertEqual(e.nombres(), ['A', 'r1', 'r2', 'B'])


class ContextoBibliotecaTest(unittest.TestCase):
    def test_nueva_guardar_abrir_sucio(self):
        from irb120_control.estudio.contexto import Contexto
        with tempfile.TemporaryDirectory() as tmp:
            c = Contexto(cl.Cliente(demo=True), tmp)
            c.nueva()
            self.assertFalse(c.cerrar)
            self.assertFalse(c.sucio())
            c.editor.agregar(Punto('A', q=[0, 0, 0, 0, 30, 0]))
            self.assertTrue(c.sucio())
            c.numero = 3
            ruta = c.guardar()
            self.assertEqual(ruta.name, '03_trayectoria-nueva.json')
            self.assertFalse(c.sucio())
            c.nombre = 'Otra'
            self.assertTrue(c.sucio())
            c.guardar()
            self.assertEqual([e.numero for e in bib.listar(tmp)], [3])
            c.nueva()
            c.abrir(c.carpeta / '03_otra.json')
            self.assertEqual((c.nombre, c.numero, len(c.editor)), ('Otra', 3, 1))
            c.borrar_archivo(c.ruta)
            self.assertEqual(bib.listar(tmp), [])
            self.assertTrue(c.sucio())

    def test_doce_puntos_planifican(self):
        import time
        qs = [[20 * ((i % 3) - 1), 10 + i, -10, 0, 40 + 2 * i, 0] for i in range(12)]
        t = Trayectoria('doce', [Punto(f'P{i}', q=q) for i, q in enumerate(qs)], cerrar=False)
        t0 = time.monotonic()
        plan = planificar(t, [0, 0, 0, 0, 30, 0], 30.)
        self.assertEqual(len(plan.tramos), 12)
        print(f'(12 puntos: {time.monotonic() - t0:.1f} s, ok={plan.ok})', end=' ')


class BucleYCapturaTest(unittest.TestCase):
    def test_nombre_de_captura_p1_p2(self):
        e = Editor([Punto('A', q=[0, 0, 0, 0, 30, 0])])
        self.assertEqual(e.nombre_captura(), 'P1')
        e.agregar(Punto('P1', q=[0, 0, 0, 0, 30, 0]))
        e.agregar(Punto('P3', q=[0, 0, 0, 0, 30, 0]))
        self.assertEqual(e.nombre_captura(), 'P2')

    def test_texto_de_vuelta(self):
        from irb120_control.estudio.formato import texto_vuelta
        self.assertEqual(texto_vuelta({'vuelta': 7, 'vueltas': None, 'bucle': True}), 'vuelta 7 (bucle)')
        self.assertEqual(texto_vuelta({'vuelta': 2, 'vueltas': 3}), 'vuelta 2/3')
        self.assertIsNone(texto_vuelta({'vuelta': 0}))

    def test_bucle_se_guarda_como_repeticiones_cero(self):
        from irb120_control.estudio.contexto import Contexto
        with tempfile.TemporaryDirectory() as tmp:
            c = Contexto(cl.Cliente(demo=True), tmp)
            c.editor.agregar(Punto('A', q=[0, 0, 0, 0, 30, 0]))
            c.repeticiones = 0
            ruta = c.guardar()
            self.assertEqual(json.loads(ruta.read_text())['repeticiones'], 0)
            c.nueva()
            c.abrir(ruta)
            self.assertEqual(c.repeticiones, 0)


class ValidacionDatosTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.h = Path(self.tmp.name)
        res = self.h / 'resultados'
        res.mkdir()
        (res / 'casos_estado_evidencia.csv').write_text(
            'case_id,tipo,nivel_evidencia,estado_P5,justificacion\n'
            'FK-N1,FK real,S1,parcial,"umbral, no aprobado"\n'
            'FK-L,FK limites,S0,verificado,ok\n'
            'IK-1,IK,S0,verificado,ok\n'
            'IK-REAL,IK real,S3 (no alcanzado),bloqueado por acceso,sin acceso\n'
            'X-1,otro,S1,fallido,mal\n'
            'X-2,otro,S2,no ejecutado,nada\n', encoding='utf-8')
        (res / 'P1_fk.csv').write_text('ID,e_p_m,Decision\nFK-N1,7.45e-08,parcial\nFK-L1,0.0,verificado\n'
                                       'ZZ,1.5,\n', encoding='utf-8')
        (res / 'P2_ik.csv').write_text('ID_pose,rama\nIK-1,1\n', encoding='utf-8')   # faltan columnas
        (self.h / 'manifiestos').mkdir()
        (self.h / 'manifiestos' / 'FK-N1.yaml').write_text('id_prueba: FK-N1\n', encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def test_resumen(self):
        est, niv = vd.Modelo(self.h).resumen()
        self.assertEqual(est, {'verificado': 2, 'parcial': 1, 'fallido': 1, 'no ejecutado': 1, 'bloqueado': 1})
        self.assertEqual(niv, {'S0': 2, 'S1': 2, 'S2': 1, 'S3': 1})

    def test_tabla_fk_estado_nivel_y_prefijo(self):
        t = vd.Modelo(self.h).tablas['fk']
        self.assertEqual([c[0] for c in t.columnas], ['Estado', 'Nivel', 'Caso', 'e_p [m]'])   # solo las presentes
        self.assertEqual([f.estado for f in t.filas], ['parcial', 'verificado', ''])
        self.assertEqual(t.filas[1].caso, 'FK-L')                 # FK-L1 → caso FK-L
        self.assertEqual(t.filas[1].nivel, 'S0')
        self.assertEqual(t.filas[0].celdas[3], '7.45e-08')

    def test_detalle_y_manifiesto(self):
        m = vd.Modelo(self.h)
        d = m.detalle(m.tablas['fk'].filas[0])
        self.assertIn('umbral, no aprobado', d)
        self.assertIn('id_prueba: FK-N1', d)
        self.assertIn('no existe', m.detalle(m.tablas['fk'].filas[1]))

    def test_tolerante_a_faltantes_y_sin_resultados(self):
        m = vd.Modelo(self.h)
        self.assertEqual(len(m.tablas['ik'].filas), 1)
        self.assertEqual(m.tablas['jac'].filas, [])
        self.assertEqual(m.tablas['todos'].filas, [])
        self.assertTrue(m.hay_datos)
        vacio = vd.Modelo(self.h / 'no_existe')
        self.assertFalse(vacio.hay_datos)
        self.assertEqual(vacio.resumen()[0]['verificado'], 0)

    def test_normalizar(self):
        self.assertEqual(vd.normalizar_estado('bloqueado por acceso'), 'bloqueado')
        self.assertEqual(vd.normalizar_estado('Verificado'), 'verificado')
        self.assertEqual(vd.normalizar_estado('?'), '')
        self.assertEqual(vd.nivel_de('S3 técnico (registrado)'), 'S3')
        self.assertEqual(vd.nivel_de('sin dato'), '')


def _hay_pantalla():
    try:
        import tkinter
        tkinter.Tk().destroy()
        return True
    except Exception:
        return False


@unittest.skipUnless(_hay_pantalla(), 'sin DISPLAY')
class HumoTest(unittest.TestCase):
    def test_app_demo_recorre_pestanas(self):
        from irb120_control.estudio.app import App
        app = App(cl.Cliente(demo=True), oscuro=True)
        try:
            app.update()
            self.assertEqual(app.tabs.get(), 'Trayectoria')   # arranca en la pestaña Trayectoria
            app.cargar_demo()
            app.ctx.planificar()
            self.assertTrue(app.ctx.planificando)
            app.esperar_plan()
            self.assertIsNotNone(app.ctx.plan, app.ctx.plan_error)
            self.assertTrue(app.ctx.plan.ok, app.ctx.plan.resumen)
            self.assertFalse(app.ctx.puede_enviar())          # demo: no hay panel
            for v in app.vistas:
                app.tabs.set(v.titulo)
                app.refrescar()
                for _ in range(5):
                    app.update()
            self.assertEqual(len(app.vistas), 6)
            val = app.vistas[5]
            for clave in vd.ORDEN:
                val._elegir_bloque(vd.BLOQUES[clave][0])
                app.update()
            val.ampliar()
            app.update()
            # Matemática: los bloques se calculan y la imagen llega por la cola
            mat = app.vistas[4]
            mat.renderizar()
            self.assertGreater(len(mat.bloques), 5)
            for _ in range(200):
                app.ctx.drenar()
                app.update()
                if all(str(r.cget('text')) == '' for r in mat.rotulos):
                    break
                import time
                time.sleep(.05)
            # tema claro y edición invalidan el plan
            app.sw.deselect()
            app.cambiar_tema()
            app.update()
            vt = app.vistas[1]
            # casilla «Bucle continuo»: repeticiones = 0 y el campo se bloquea; al quitarla vuelve la cuenta
            vt.e_rep.delete(0, 'end')
            vt.e_rep.insert(0, '4')
            vt._parametros()
            self.assertEqual(app.ctx.repeticiones, 4)
            vt.v_bucle.set(True)
            vt._bucle()
            self.assertEqual(app.ctx.repeticiones, 0)
            self.assertEqual(str(vt.e_rep.cget('state')), 'disabled')
            vt._parametros()
            self.assertEqual(app.ctx.repeticiones, 0)
            vt.v_bucle.set(False)
            vt._bucle()
            self.assertEqual((app.ctx.repeticiones, str(vt.e_rep.cget('state'))), (4, 'normal'))
            # captura de la postura actual: q exacto, origen captura, nombre P1, P2…
            app.cliente.ultimo = dict(app.cliente.ultimo, medido=[1.234567, 2., -3., 4., 31.5, -6.])
            n0 = len(app.ctx.editor)
            vt.capturar()
            app.event_generate('<F2>')
            app.update()
            p = app.ctx.editor.puntos[-1]
            self.assertEqual(len(app.ctx.editor), n0 + 2)
            self.assertEqual((p.nombre, p.origen, p.q), ('P2', 'captura', [1.234567, 2., -3., 4., 31.5, -6.]))
            self.assertEqual(app.ctx.editor.puntos[-2].nombre, 'P1')
            for _ in range(2):
                vt.borrar()
            vt.tabla.selection_remove(*vt.tabla.selection())
            app.vistas[1].borrar()
            app.vistas[1].tabla.selection_set('0')
            app.vistas[1].borrar()
            self.assertIsNone(app.ctx.plan)
            self.assertEqual(len(app.ctx.editor), 2)
        finally:
            app.destruir()


if __name__ == '__main__':
    unittest.main()
