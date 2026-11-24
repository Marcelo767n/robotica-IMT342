"""Pruebas del traductor PLC ↔ brazo y del reparto de órdenes lentas del puente (sin ROS ni red)."""
import json
from pathlib import Path
import tempfile
import threading
import unittest

from irb120_control.celda import config
from irb120_control.celda.traductor import ORDENES, Traductor
from irb120_control.panel.despacho import Despachador, OCUPADO
from irb120_control.trayectorias import Punto, Trayectoria, a_ordenes, planificar

REPOSO = [0, 0, 0, 0, 30, 0]
A, B, C = [20, 10, -10, 0, 40, 0], [-20, 15, -5, 0, 45, 10], [0, -10, 10, 0, 60, 0]


class Reloj:
    def __init__(self):
        self.t = 100.

    def __call__(self):
        return self.t


def brazo(**kw):
    d = {'medido': REPOSO, 'pose_medida': [374., 0., 630., 180., 30., 180.], 'velocidad_pct': 30, 'modo': 'AUTO',
         'motores': 'motoron', 'servidor_activo': True, 'listo': True, 'ocupado': False, 'faltas': [],
         'simulado': False, 'respuesta': None,
         'trayectoria': {'fase': 'lista', 'vuelta': 0, 'vueltas': 0, 'tramo': 0, 'total': 0, 'mensaje': ''}}
    d.update(kw)
    return d


def con_fase(fase, **kw):
    return brazo(trayectoria={'fase': fase, 'vuelta': 1, 'vueltas': 2, 'tramo': 2, 'total': 4}, ocupado=True,
                 listo=False, **kw)


def plc(*bits, valor=1, **kw):
    """Entrada del PLC con los bits de orden indicados a 1."""
    d = {'enlace': True, 'formato': 'completo', 'habilitar': True,
         'ordenes': {n: n in bits for n in ORDENES}, 'valor': valor, 'velocidad_pct': 0, 'repeticiones': 0,
         'pose': [400., 0., 450., 180., 0., 180.]}
    d.update(kw)
    return d


class Base(unittest.TestCase):
    def setUp(self):
        self.reloj = Reloj()
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.ruta = Path(self.dir.name) / 'abc.json'
        Trayectoria('abc', [Punto('A', q=A), Punto('B', q=B), Punto('C', q=C)]).guardar(self.ruta)
        self.t = Traductor({1: self.ruta, 2: Path(self.dir.name) / 'no_existe.json'}, self.reloj)
        self.t.estado_brazo(brazo())
        self.t.entrada_plc(plc())             # línea base: todo a 0

    def pedir(self, *bits, **kw):
        """Sube los bits (el PLC los mantiene) y devuelve las órdenes al panel."""
        self.t.entrada_plc(plc(*bits, **kw))
        return self.t.tomar_ordenes()

    def bajar(self, **kw):
        self.t.entrada_plc(plc(**kw))

    def responder(self, ident, ok=True, error=None, **kw):
        self.t.estado_brazo(brazo(respuesta={'id': ident, 'accion': 'x', 'ok': ok, 'error': error}, **kw))

    def saludo(self):
        e = self.t.salida()['estado']
        return 'aceptada' if e['aceptada'] else 'rechazada' if e['rechazada'] else None

    def codigo(self):
        return self.t.salida()['valor']


class OrdenesTest(Base):
    def test_bits_a_1_al_arrancar_no_cuentan(self):
        t = Traductor({}, self.reloj)
        t.estado_brazo(brazo())
        t.entrada_plc(plc('pausar'))
        t.entrada_plc(plc('pausar'))
        self.assertEqual(t.tomar_ordenes(), [])
        self.assertFalse(t.salida()['estado']['aceptada'])

    def test_saludo_completo(self):
        o = self.pedir('pausar')
        self.assertEqual([x['accion'] for x in o], ['pausar'])
        self.assertIsNone(self.saludo())
        self.responder(o[0]['id'])
        self.assertEqual(self.saludo(), 'aceptada')
        self.pedir('pausar')                                 # mantiene el bit: sigue aceptada, sin repetir
        self.assertEqual(self.t.tomar_ordenes(), [])
        self.assertEqual(self.saludo(), 'aceptada')
        self.bajar()                                         # el PLC baja: se baja el saludo
        self.assertIsNone(self.saludo())

    def test_flanco_no_repetido(self):
        o = self.pedir('reanudar')
        self.responder(o[0]['id'])
        for _ in range(3):
            self.assertEqual(self.pedir('reanudar'), [])
            self.t.tic()
        self.bajar()
        self.assertEqual(len(self.pedir('reanudar')), 1)     # nuevo flanco, nueva orden

    def test_dos_bits_rechazo_1(self):
        self.assertEqual(self.pedir('pausar', 'reanudar'), [])
        self.assertEqual((self.saludo(), self.codigo()), ('rechazada', 1))
        self.bajar()
        self.assertIsNone(self.saludo())
        self.assertEqual(self.pedir('ejecutar', 'reposo'), [])
        self.assertEqual((self.saludo(), self.codigo()), ('rechazada', 1))

    def test_dos_ordenes_seguidas_se_atienden_en_orden(self):
        self.t.entrada_plc(plc('reanudar'))
        o = self.t.tomar_ordenes()
        self.t.entrada_plc(plc())                            # baja antes de que el panel conteste
        self.assertEqual(self.t.tomar_ordenes(), [])
        self.responder(o[0]['id'])
        self.assertIsNone(self.saludo())                     # el bit ya estaba a 0: no hay saludo que mostrar
        self.assertEqual(len(self.pedir('velocidad', velocidad_pct=40)), 1)

    def test_sin_habilitar(self):
        for bit in ('ejecutar', 'reposo', 'velocidad'):
            self.assertEqual(self.pedir(bit, habilitar=False, velocidad_pct=20), [])
            self.assertEqual((self.saludo(), self.codigo()), ('rechazada', 2), bit)
            self.bajar(habilitar=False)

    def test_pausar_cancelar_sin_habilitar(self):
        for bit in ('pausar', 'cancelar'):
            o = self.pedir(bit, habilitar=False)
            self.assertEqual([x['accion'] for x in o], [bit])
            self.responder(o[0]['id'])
            self.assertEqual(self.saludo(), 'aceptada')
            self.bajar(habilitar=False)
        self.pedir('acusar', habilitar=False)
        self.assertEqual(self.saludo(), 'aceptada')
        self.assertFalse(self.t.salida()['estado']['habilitar_recibido'])

    def test_pausar_es_inmediato_aunque_haya_otra_orden(self):
        self.pedir('reanudar')                               # esperando respuesta del panel
        self.bajar()
        o = self.pedir('pausar')
        self.assertEqual([x['accion'] for x in o], ['pausar'])

    def test_respuesta_no_ok_rechazo_7_y_8(self):
        o = self.pedir('pausar')
        self.responder(o[0]['id'], ok=False, error='No hay ninguna trayectoria en ejecución.')
        self.assertEqual((self.saludo(), self.codigo()), ('rechazada', 7))
        self.assertTrue(any('No hay ninguna' in r for r in self.t.registro()))
        self.bajar()
        o = self.pedir('reanudar')
        self.responder(o[0]['id'], ok=False, error='Hay un envío o una trayectoria en curso.')
        self.assertEqual(self.codigo(), 8)

    def test_respuesta_de_otro_id_se_ignora(self):
        o = self.pedir('pausar')
        self.responder(o[0]['id'] + 5)
        self.assertIsNone(self.saludo())

    def test_sin_respuesta_caduca(self):
        self.pedir('reanudar')
        for _ in range(11):
            self.reloj.t += 1
            self.t.estado_brazo(brazo())
            self.t.entrada_plc(plc('reanudar'))
        self.assertEqual((self.saludo(), self.codigo()), ('rechazada', 7))

    def test_reposo_envia_posicion_y_enviar(self):
        o = self.pedir('reposo')
        self.assertEqual((o[0]['accion'], o[0]['valor']), ('posicion', 'reposo'))
        self.assertIsNone(self.saludo())
        self.responder(o[0]['id'])
        o2 = self.t.tomar_ordenes()
        self.assertEqual((o2[0]['accion'], o2[0]['q']), ('enviar', [0., 0., 0., 0., 30., 0.]))
        self.assertIsNone(self.saludo())                     # falta la respuesta al enviar
        self.responder(o2[0]['id'])
        self.assertEqual(self.saludo(), 'aceptada')

    def test_reposo_rechazado_no_envia(self):
        o = self.pedir('reposo')
        self.responder(o[0]['id'], ok=False, error='x')
        self.assertEqual(self.t.tomar_ordenes(), [])
        self.assertEqual(self.codigo(), 7)

    def test_velocidad_con_pct_y_en_nucleo(self):
        o = self.pedir('velocidad', velocidad_pct=40, valor=0)[0]
        self.assertEqual((o['accion'], o['valor']), ('velocidad', 40))
        self.responder(o['id'])
        self.bajar()
        o = self.pedir('velocidad', formato='nucleo', valor=55, velocidad_pct=0)[0]
        self.assertEqual(o['valor'], 55)
        self.responder(o['id'])
        self.assertEqual(self.saludo(), 'aceptada')
        self.bajar()
        self.assertEqual(self.pedir('velocidad', valor=0, velocidad_pct=0), [])
        self.assertEqual(self.codigo(), 1)

    def test_punto(self):
        o = self.pedir('punto')[0]
        self.assertEqual((o['accion'], o['pose']), ('punto_externo', [400., 0., 450., 180., 0., 180.]))
        self.responder(o['id'])
        self.assertEqual(self.saludo(), 'aceptada')
        self.bajar()
        self.assertEqual(self.pedir('punto', formato='nucleo', pose=None), [])
        self.assertEqual((self.saludo(), self.codigo()), ('rechazada', 1))
        self.bajar()
        self.assertEqual(self.pedir('punto', pose=[1, 2]), [])
        self.assertEqual(self.codigo(), 1)

    def test_ocupado_y_faltas(self):
        self.t.estado_brazo(con_fase('ejecutando'))
        for bit in ('ejecutar', 'reposo'):
            self.assertEqual(self.pedir(bit), [])
            self.assertEqual(self.codigo(), 8)
            self.bajar()
        self.t.estado_brazo(brazo(faltas=['motores apagados'], listo=False))
        self.assertEqual(self.pedir('ejecutar'), [])
        self.assertEqual(self.codigo(), 4)
        self.bajar()
        self.assertEqual(self.pedir('velocidad', velocidad_pct=10), [])
        self.assertEqual(self.codigo(), 4)

    def test_acusar_borra_error(self):
        self.t.estado_brazo(con_fase('ejecutando'))
        self.t.entrada_plc({'enlace': False})
        self.t.tomar_ordenes()
        self.t.entrada_plc(plc())
        self.assertEqual(self.t.salida()['codigo'], 9)
        self.pedir('acusar')
        s = self.t.salida()
        self.assertEqual((s['codigo'], s['estado']['error']), (0, False))
        self.assertEqual(self.saludo(), 'aceptada')


class EnlaceBrazoTest(Base):
    def test_estado_viejo(self):
        self.reloj.t += 2.5
        self.t.entrada_plc(plc())
        self.assertFalse(self.t.salida()['estado']['enlace'])
        self.assertEqual(self.pedir('reposo'), [])
        self.assertEqual((self.saludo(), self.codigo()), ('rechazada', 3))
        self.bajar()
        o = self.pedir('cancelar')                           # cancelar se envía aunque no haya confirmación
        self.assertEqual(o[0]['accion'], 'cancelar')
        self.assertEqual(self.codigo(), 3)

    def test_bits_y_fase(self):
        s = self.t.salida()
        e = s['estado']
        self.assertTrue(all(e[k] for k in ('enlace', 'servidor_activo', 'motores_on', 'listo', 'auto',
                                           'habilitar_recibido')))
        self.assertFalse(any(e[k] for k in ('moviendo', 'pausada', 'error', 'terminado', 'simulado',
                                            'aceptada', 'rechazada')))
        self.assertEqual((s['fase'], s['q'], s['velocidad_pct'], s['valor'], s['codigo']), (0, REPOSO, 30, 0, 0))
        self.assertEqual(s['pose'], [374., 0., 630., 180., 30., 180.])
        self.assertNotIn('vida', s)
        json.dumps(s)
        for fase, n in (('ejecutando', 1), ('pausada', 2), ('terminada', 3), ('cancelada', 4), ('error', 5)):
            self.t.estado_brazo(con_fase(fase))
            s = self.t.salida()
            self.assertEqual((s['fase'], s['tramo'], s['tramos'], s['vuelta']), (n, 2, 4, 1))
            self.assertTrue(s['estado']['moviendo'])
            self.assertEqual(s['estado']['pausada'], fase == 'pausada')
            self.assertEqual(s['estado']['terminado'], fase == 'terminada')
            self.assertEqual(s['estado']['error'], fase == 'error')
            self.assertEqual(s['valor'], 7 if fase == 'error' else 2 if n in (1, 2) else 0)
        self.t.estado_brazo(brazo(modo='MANR', motores='motoroff', simulado=True))
        e = self.t.salida()['estado']
        self.assertFalse(e['auto'] or e['motores_on'])
        self.assertTrue(e['simulado'])


class PerdidaPlcTest(Base):
    def test_perdida_en_ejecucion(self):
        self.t.estado_brazo(con_fase('ejecutando'))
        self.reloj.t += .5
        self.t.tic()
        self.assertEqual(self.t.tomar_ordenes(), [])
        for _ in range(5):                               # sin entrada > 1 s
            self.reloj.t += .5
            self.t.estado_brazo(con_fase('ejecutando'))
            self.t.tic()
        self.assertEqual([o['accion'] for o in self.t.tomar_ordenes()], ['pausar'])
        self.t.entrada_plc({'enlace': False})            # el nodo PLC avisa: mismo episodio
        self.t.tic()
        self.assertEqual(self.t.tomar_ordenes(), [])
        s = self.t.salida()
        self.assertEqual((s['codigo'], s['valor']), (9, 9))
        self.assertTrue(s['estado']['error'])
        self.assertFalse(s['estado']['habilitar_recibido'])

    def test_recuperar_enlace_no_cuenta_bits(self):
        self.t.estado_brazo(con_fase('ejecutando'))
        self.t.entrada_plc({'enlace': False})
        self.assertEqual([o['accion'] for o in self.t.tomar_ordenes()], ['pausar'])
        self.t.entrada_plc(plc('reanudar'))              # vuelve con un bit a 1: no es flanco
        self.assertEqual(self.t.tomar_ordenes(), [])
        self.assertEqual(self.t.salida()['codigo'], 9)

    def test_sin_ejecucion_no_pausa(self):
        self.reloj.t += 3
        self.t.tic()
        self.assertEqual(self.t.tomar_ordenes(), [])
        self.assertEqual(self.t.salida()['codigo'], 0)


class TrayectoriaTest(Base):
    def test_ejecutar_trayectoria_valida(self):
        self.assertEqual(self.pedir('ejecutar', valor=1), [])   # planificar no bloquea
        self.assertIsNone(self.saludo())
        self.t.planificar_pendiente()
        ordenes = self.t.tomar_ordenes()
        self.assertEqual(len(ordenes), 1)
        o = ordenes[0]
        self.assertEqual(o['accion'], 'trayectoria')
        esperado = a_ordenes(planificar(Trayectoria.cargar(self.ruta), REPOSO, 30))
        self.assertEqual(o['ordenes'], esperado)
        self.assertEqual(o['trayectoria'], Trayectoria.cargar(self.ruta).to_dict())
        self.assertEqual(o['velocidad_pct'], 30)
        self.responder(o['id'])
        self.assertEqual(self.saludo(), 'aceptada')
        self.bajar()
        self.assertIsNone(self.saludo())

    def test_velocidad_de_la_orden_primero(self):
        self.assertEqual(self.pedir('ejecutar', valor=1, velocidad_pct=50)[0]['accion'], 'velocidad')
        self.responder(self.t._id, velocidad_pct=50)
        self.assertEqual(self.t.tomar_ordenes(), [])
        self.t.planificar_pendiente()
        o = self.t.tomar_ordenes()[0]
        self.assertEqual((o['accion'], o['velocidad_pct']), ('trayectoria', 50))
        self.assertEqual(o['ordenes'], a_ordenes(planificar(Trayectoria.cargar(self.ruta), REPOSO, 50)))

    def test_velocidad_no_reflejada(self):
        v = self.pedir('ejecutar', valor=1, velocidad_pct=50)[0]
        self.responder(v['id'], velocidad_pct=30)        # ok pero el estado aún no la refleja
        self.assertIsNone(self.t.tomar_trabajo())
        for _ in range(13):                                # 6,5 s con PLC y brazo vivos
            self.reloj.t += .5
            self.t.entrada_plc(plc('ejecutar', valor=1, velocidad_pct=50))
            self.t.estado_brazo(brazo(velocidad_pct=30))
        self.assertEqual((self.saludo(), self.codigo()), ('rechazada', 7))

    def test_velocidad_rechazada(self):
        v = self.pedir('ejecutar', valor=1, velocidad_pct=50)[0]
        self.responder(v['id'], ok=False, error='fuera de rango')
        self.assertEqual(self.codigo(), 7)

    def test_repeticiones_de_la_orden(self):
        self.pedir('ejecutar', valor=1, repeticiones=3)
        self.t.planificar_pendiente()
        self.assertEqual(self.t.tomar_ordenes()[0]['trayectoria']['repeticiones'], 3)

    def test_archivo_inexistente(self):
        self.assertEqual(self.pedir('ejecutar', valor=2), [])
        self.t.planificar_pendiente()
        self.assertEqual((self.saludo(), self.codigo()), ('rechazada', 5))
        self.assertTrue(any('no_existe' in r for r in self.t.registro()))
        self.bajar()
        self.pedir('ejecutar', valor=55)                 # número sin archivo configurado
        self.assertEqual(self.codigo(), 5)

    def test_archivo_invalido(self):
        self.ruta.write_text('{no es json', encoding='utf-8')
        self.pedir('ejecutar', valor=1)
        self.t.planificar_pendiente()
        self.assertEqual(self.codigo(), 5)

    def test_plan_no_apto(self):
        Trayectoria('lejos', [Punto('A', q=A), Punto('X', pose=[1500, 0, 300, 0, 0, 0])]).guardar(self.ruta)
        self.pedir('ejecutar', valor=1)
        self.t.planificar_pendiente()
        self.assertEqual(self.t.tomar_ordenes(), [])
        self.assertEqual((self.saludo(), self.codigo()), ('rechazada', 6))
        self.assertTrue(any('NO apto' in r for r in self.t.registro()))

    def test_planificar_en_hilo_aparte(self):
        self.pedir('ejecutar', valor=1)
        trabajo = self.t.tomar_trabajo()
        self.assertIsNone(self.t.tomar_trabajo())        # ya tomado
        self.assertIsNone(self.saludo())
        self.t.completar(trabajo, ('plan', 'x'))
        self.assertEqual(self.codigo(), 6)
        self.t.completar(trabajo, ('plan', 'x'))         # repetido o tardío: se ignora
        self.assertEqual(self.codigo(), 6)

    def test_enlace_plc_perdido_aborta_planificacion(self):
        self.pedir('ejecutar', valor=1)
        trabajo = self.t.tomar_trabajo()
        self.t.entrada_plc({'enlace': False})
        self.t.completar(trabajo, ('ok', Trayectoria.cargar(self.ruta), []))
        self.assertEqual(self.t.tomar_ordenes(), [])


class ConfigTest(unittest.TestCase):
    def test_rutas_y_defecto(self):
        with tempfile.TemporaryDirectory() as d:
            y = Path(d) / 'c.yaml'
            y.write_text('celda:\n  trayectorias: {1: "a.json", 2: "b.json", x: "c.json"}\n  carpeta: t\n', encoding='utf-8')
            rutas, reposo = config.cargar('/base', y)
            self.assertEqual(rutas, {1: Path('/base/t/a.json'), 2: Path('/base/t/b.json')})
            self.assertEqual(reposo, [0, 0, 0, 0, 30, 0])
            self.assertEqual(config.cargar('/base', y, '/otra')[0][1], Path('/otra/a.json'))
            self.assertEqual(config.cargar('/base', Path(d) / 'no.yaml')[0], {})


class FalsaOrdenes:
    def __init__(self):
        self.atendidas, self.fallos, self.entrar, self.seguir = [], [], threading.Event(), threading.Event()

    def atender(self, texto):
        self.atendidas.append(texto)
        if '"trayectoria"' in texto:
            self.entrar.set()
            self.seguir.wait(5)

    def _fallo(self, ident, accion, error):
        self.fallos.append((ident, accion, error))


class DespachoTest(unittest.TestCase):
    def test_lentas_en_hilo_y_una_a_la_vez(self):
        ordenes, publicados = FalsaOrdenes(), []
        d = Despachador(ordenes, lambda: publicados.append(1))
        d.atender(json.dumps({'id': 1, 'accion': 'trayectoria'}))
        self.assertTrue(ordenes.entrar.wait(5))
        d.atender(json.dumps({'id': 2, 'accion': 'vista_previa'}))   # mientras planifica: rechazo
        self.assertEqual(ordenes.fallos, [(2, 'vista_previa', OCUPADO)])
        d.atender(json.dumps({'id': 3, 'accion': 'trayectoria'}))
        self.assertEqual(len(ordenes.fallos), 2)
        d.atender(json.dumps({'id': 4, 'accion': 'pausar'}))          # las demás no esperan
        self.assertEqual(len(ordenes.atendidas), 2)
        ordenes.seguir.set()
        for _ in range(100):
            if not d.planificando:
                break
            threading.Event().wait(.02)
        self.assertFalse(d.planificando)
        self.assertGreaterEqual(len(publicados), 3)
        d.atender(json.dumps({'id': 5, 'accion': 'vista_previa'}))    # libre otra vez
        self.assertEqual(len(ordenes.fallos), 2)

    def test_basura_va_al_camino_normal(self):
        ordenes = FalsaOrdenes()
        Despachador(ordenes, lambda: None).atender('no es json')
        self.assertEqual(ordenes.atendidas, ['no es json'])


class PruebaCatalogo(unittest.TestCase):
    """Trayectorias del PLC por nombre de archivo NN_nombre.json, releídas en cada consulta."""

    def test_descubre_numerados_y_relee(self):
        with tempfile.TemporaryDirectory() as d:
            cat = config.rutas({}, d, '/base')
            self.assertEqual(dict(cat), {})
            (Path(d) / '03_paletizado.json').write_text('{}')
            (Path(d) / 'sin_numero.json').write_text('{}')
            (Path(d) / '120_fuera.json').write_text('{}')
            self.assertEqual(dict(cat), {3: Path(d) / '03_paletizado.json'})   # aparece sin reiniciar
            (Path(d) / '7_pick.json').write_text('{}')
            self.assertEqual(cat.get(7), Path(d) / '7_pick.json')

    def test_yaml_manda_y_repetidos_no_se_usan(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / '02_a.json').write_text('{}')
            (Path(d) / '02_b.json').write_text('{}')
            (Path(d) / '05_c.json').write_text('{}')
            cat = config.rutas({5: 'fija.json'}, d, '/base')
            self.assertIsNone(cat.get(2))                       # ambiguo: dos archivos con el nº 2
            self.assertEqual(cat[5], Path(d) / 'fija.json')     # el YAML manda


if __name__ == '__main__':
    unittest.main()
