"""Pruebas de la pasarela PLC (sin ROS): telegramas, transporte TCP y simulador."""
import math
import socket
import struct
import time
import unittest

from irb120_control.plc import telegrama as tg
from irb120_control.plc.simulador import PlcSimulado
from irb120_control.plc.transporte import Transporte


def esperar(condicion, limite=5.):
    fin = time.monotonic() + limite
    while time.monotonic() < fin:
        if condicion():
            return True
        time.sleep(.02)
    return condicion()


def orden_ejemplo(**c):
    base = dict(mando=3, valor=2, velocidad_pct=30, repeticiones=1, pose=[400., 0., 450., 180., 0., 180.])
    base.update(c)
    return tg.Orden(**base)


class TestTelegramas(unittest.TestCase):
    def test_tamanos(self):
        self.assertEqual((tg.LARGO_NUCLEO, tg.LARGO_ORDEN_COMPLETA, tg.LARGO_ESTADO_COMPLETO), (4, 36, 68))
        self.assertEqual(len(tg.Orden().pack(False)), 4)
        self.assertEqual(len(tg.Orden(pose=[0] * 6).pack()), 36)
        self.assertEqual(len(tg.Estado().pack(False)), 4)
        self.assertEqual(len(tg.Estado().pack()), 68)
        self.assertEqual((tg.largo_orden('nucleo'), tg.largo_orden('completo')), (4, 36))
        self.assertEqual((tg.largo_estado('nucleo'), tg.largo_estado('completo')), (4, 68))

    def test_oro_orden_nucleo(self):
        o = tg.Orden.unpack(bytes([0x80, 0x03, 0x00, 0x63]))
        self.assertEqual((o.mando, o.valor, o.pose), (0x8003, 99, None))
        self.assertTrue(o.habilitar and o.vida and o.ordenes['ejecutar'] and not o.ordenes['pausar'])
        self.assertEqual(o.pack(False), bytes([0x80, 0x03, 0x00, 0x63]))

    def test_oro_orden_completa(self):
        b = bytearray(36)
        for off, val in ((0, 0x0181), (2, 7), (4, 55), (6, 1000), (8, 0), (10, 0)):
            b[off:off + 2] = val.to_bytes(2, 'big')
        for i, v in enumerate((1.5, -2.25, 3., 4., 5., 6.)):
            b[12 + 4 * i:16 + 4 * i] = struct.pack('>f', v)
        o = tg.Orden.unpack(bytes(b))
        self.assertEqual((o.mando, o.valor, o.velocidad_pct, o.repeticiones), (0x0181, 7, 55, 1000))
        self.assertEqual(o.pose, [1.5, -2.25, 3., 4., 5., 6.])
        self.assertTrue(o.ordenes['velocidad'] and o.ordenes['punto'] and o.habilitar and not o.vida)
        self.assertEqual(o.pack(), bytes(b))

    def test_oro_estado_nucleo(self):
        e = tg.Estado.unpack(bytes([0x84, 0x01, 0x00, 0x05]))
        self.assertEqual((e.estado, e.valor), (0x8401, 5))
        self.assertTrue(e.bit('enlace') and e.bit('aceptada') and e.vida and not e.bit('rechazada'))
        self.assertEqual(e.pack(False), bytes([0x84, 0x01, 0x00, 0x05]))

    def test_oro_estado_completo(self):
        b = bytearray(68)
        for off, val in ((0, 0x8005), (2, 6), (4, 1), (6, 2), (8, 4), (10, 3), (12, 30), (14, 9), (16, 0), (18, 0)):
            b[off:off + 2] = val.to_bytes(2, 'big')
        b[20:24] = struct.pack('>f', 10.)
        b[40:44] = struct.pack('>f', -5.5)          # q6
        b[44:48] = struct.pack('>f', 374.)
        b[64:68] = struct.pack('>f', 180.)
        e = tg.Estado.unpack(bytes(b))
        self.assertEqual((e.estado, e.valor, e.fase, e.tramo, e.tramos, e.vuelta, e.velocidad_pct, e.codigo),
                         (0x8005, 6, 1, 2, 4, 3, 30, 9))
        self.assertEqual((e.q[0], e.q[5], e.pose[0], e.pose[5]), (10., -5.5, 374., 180.))
        self.assertTrue(e.bit('enlace') and e.bit('moviendo') and not e.bit('listo') and e.vida)
        self.assertEqual(e.pack(), bytes(b))

    def test_mascaras(self):
        self.assertEqual([1 << (i + 1) for i in range(8)], [2, 4, 8, 0x10, 0x20, 0x40, 0x80, 0x100])
        self.assertEqual(tg.MASCARA_ORDENES, 0x1FE)
        self.assertEqual(tg.BITS_ESTADO.index('aceptada'), 10)
        self.assertEqual(tg.BITS_ESTADO.index('rechazada'), 11)
        self.assertEqual(tg.BITS_ESTADO.index('habilitar_recibido'), 12)
        self.assertEqual(tg.BIT_VIDA, 0x8000)

    def test_ida_y_vuelta(self):
        o = orden_ejemplo()
        self.assertEqual(tg.Orden.unpack(o.pack()), o)
        e = tg.Estado(0x1FFF, 2, 4, 5, 6, 7, 8, 9, [1., 2., 3., 4., 5., 6.], [.5] * 6)
        self.assertEqual(tg.Estado.unpack(e.pack()), e)

    def test_largo_incorrecto(self):
        for n in (0, 3, 5, 35, 37):
            with self.assertRaises(ValueError):
                tg.Orden.unpack(b'\0' * n)
        for n in (0, 36, 67, 69):
            with self.assertRaises(ValueError):
                tg.Estado.unpack(b'\0' * n)

    def test_orden_a_dict(self):
        d = tg.orden_a_dict(orden_ejemplo(mando=0x8003), True, 12.5, 3)
        self.assertEqual((d['enlace'], d['t'], d['errores_trama'], d['formato'], d['mando'], d['habilitar'],
                          d['valor']), (True, 12.5, 3, 'completo', 3, True, 2))
        self.assertTrue(d['ordenes']['ejecutar'] and not d['ordenes']['pausar'])
        self.assertEqual(set(d['ordenes']), set(tg.BITS_ORDEN))
        self.assertEqual((d['velocidad_pct'], d['repeticiones'], d['pose'][0]), (30, 1, 400.))
        n = tg.orden_a_dict(tg.Orden.unpack(bytes([0, 3, 0, 5])), True, 0, 0, 'nucleo')
        self.assertEqual((n['velocidad_pct'], n['repeticiones'], n['pose'], n['valor'], n['formato']),
                         (0, 0, None, 5, 'nucleo'))
        self.assertFalse(tg.orden_a_dict(None, False, 0, 0)['enlace'])

    def test_estado_desde_dict_y_vida(self):
        d = {'estado': {'enlace': True, 'moviendo': True, 'aceptada': True, 'habilitar_recibido': True},
             'valor': 2, 'fase': 1, 'tramo': 2, 'tramos': 4, 'vuelta': 1, 'velocidad_pct': 30, 'codigo': 0,
             'q': [0, 0, 0, 0, 30, 0], 'pose': [374., 0., 630., 180., 30., 180.]}
        e = tg.estado_desde_dict(d, False)
        self.assertEqual(e.estado, 0x0001 | 0x0004 | 0x0400 | 0x1000)
        self.assertEqual((e.valor, e.q[4]), (2, 30.))
        self.assertEqual(tg.estado_desde_dict(d, True).estado, e.estado | 0x8000)

    def test_estado_tolerante(self):
        e = tg.estado_desde_dict({}, False)
        self.assertEqual((e.estado, e.q, e.valor), (0, [0.] * 6, 0))
        e = tg.estado_desde_dict({'fase': 99999, 'valor': -5, 'tramo': 'x', 'velocidad_pct': float('nan'),
                                  'q': [float('nan'), float('inf'), 1e300, 2], 'pose': None, 'estado': 'no'}, True)
        self.assertEqual((e.fase, e.valor, e.tramo, e.velocidad_pct, e.estado), (65535, 0, 0, 0, 0x8000))
        self.assertTrue(all(math.isfinite(v) for v in e.q + e.pose))
        self.assertEqual(len(tg.Estado.unpack(e.pack()).q), 6)
        self.assertEqual(tg.estado_desde_dict(None, False).estado, 0)

    def test_estado_sin_brazo(self):
        e = tg.estado_sin_brazo(True)
        self.assertTrue(e.bit('error') and not e.bit('enlace') and e.vida)
        self.assertEqual((e.valor, e.codigo), (3, 3))


class TestTransporte(unittest.TestCase):
    def servidor(self, **kw):
        recibidas = []
        t = Transporte(recibidas.append, modo='servidor', host='127.0.0.1', puerto=0, **kw).iniciar()
        self.addCleanup(t.cerrar)
        return t, recibidas

    def test_tramas_partidas_y_juntadas(self):
        t, rx = self.servidor()
        s = socket.create_connection(('127.0.0.1', t.puerto))
        self.addCleanup(s.close)
        a, b, c = (orden_ejemplo(valor=i).pack() for i in (1, 2, 3))
        s.sendall(a[:7]); time.sleep(.1); s.sendall(a[7:] + b)          # partida y junta
        s.sendall(c[:35]); time.sleep(.1); s.sendall(c[35:])
        self.assertTrue(esperar(lambda: len(rx) == 3))
        self.assertEqual([o.valor for o in rx], [1, 2, 3])
        self.assertEqual(t.errores_trama, 0)

    def test_formato_nucleo(self):
        t, rx = self.servidor(largo=4)
        s = socket.create_connection(('127.0.0.1', t.puerto))
        self.addCleanup(s.close)
        s.sendall(tg.Orden(mando=1, valor=1).pack(False) + tg.Orden(mando=2, valor=2).pack(False))
        self.assertTrue(esperar(lambda: len(rx) == 2))
        self.assertEqual([o.valor for o in rx], [1, 2])

    def test_trama_incorrecta_no_rompe(self):
        t, rx = self.servidor()
        s = socket.create_connection(('127.0.0.1', t.puerto))
        self.addCleanup(s.close)
        s.sendall(b'\1' * 25)
        self.assertTrue(esperar(lambda: t.errores_trama == 1))
        s.sendall(orden_ejemplo(valor=9).pack())
        self.assertTrue(esperar(lambda: [o.valor for o in rx] == [9]))
        self.assertTrue(t.enlace)

    def test_servidor_sustituye_cliente(self):
        t, rx = self.servidor()
        s1 = socket.create_connection(('127.0.0.1', t.puerto))
        self.addCleanup(s1.close)
        self.assertTrue(esperar(lambda: t.conectado))
        s2 = socket.create_connection(('127.0.0.1', t.puerto))
        self.addCleanup(s2.close)
        time.sleep(.3)
        s2.sendall(orden_ejemplo(valor=5).pack())
        self.assertTrue(esperar(lambda: len(rx) == 1))
        s2.settimeout(2.)
        self.assertTrue(t.enviar(b'xy'))
        self.assertEqual(s2.recv(2), b'xy')
        self.assertEqual(s1.recv(2), b'')                              # el anterior quedó cerrado

    def test_cliente_reconecta(self):
        escucha = socket.socket()
        escucha.bind(('127.0.0.1', 0))
        escucha.listen(1)
        escucha.settimeout(5.)
        self.addCleanup(escucha.close)
        t = Transporte(lambda o: None, modo='cliente', ip='127.0.0.1',
                       puerto=escucha.getsockname()[1]).iniciar()
        self.addCleanup(t.cerrar)
        c1, _ = escucha.accept()
        self.assertTrue(esperar(lambda: t.conectado))
        c1.close()
        c2, _ = escucha.accept()                                       # reconecta sola
        self.addCleanup(c2.close)
        self.assertTrue(esperar(lambda: t.conectado))
        c2.sendall(orden_ejemplo().pack())
        self.assertTrue(esperar(lambda: t.enlace))

    def test_cliente_exige_ip(self):
        with self.assertRaises(ValueError):
            Transporte(lambda o: None, modo='cliente')


class PcFalsa:
    """PC de prueba: responde al saludo de `ejecutar` (rechaza con 2 si falta habilitar) y alterna vida."""

    def __init__(self, formato, **kw):
        self.formato, self.completo = formato, formato == tg.COMPLETO
        self.vida, self.ordenes, self.estado = False, [], 0
        self.t = Transporte(self.on_orden, modo='servidor', host='127.0.0.1', puerto=0,
                            largo=tg.largo_orden(formato), **kw).iniciar()

    def on_orden(self, o):
        self.ordenes.append(o)
        if o.ordenes['ejecutar']:
            self.estado, valor = (0x0400, o.valor) if o.habilitar else (0x0800, 2)
        else:
            self.estado, valor = 0, 0
        self.vida = not self.vida
        self.t.enviar(tg.Estado(self.estado | (tg.BIT_VIDA if self.vida else 0), valor).pack(self.completo))


class TestSimulador(unittest.TestCase):
    def prueba(self, formato):
        pc = PcFalsa(formato, guardian_s=.5)
        self.addCleanup(pc.t.cerrar)
        sim = PlcSimulado('cliente', '127.0.0.1', puerto=pc.t.puerto, formato=formato, saludo_s=3.).iniciar()
        self.addCleanup(sim.cerrar)
        self.assertTrue(esperar(lambda: sim.ultimo_estado is not None))
        self.assertIn('RECHAZADA código 2', sim.comando('ejecutar 3 40 2'))     # sin habilitar
        sim.comando('habilitar on')
        self.assertIn('ACEPTADA', sim.comando('ejecutar 3 40 2'))
        orden = next(o for o in pc.ordenes if o.ordenes['ejecutar'] and o.habilitar)
        self.assertEqual(orden.valor, 3)
        if pc.completo:
            self.assertEqual((orden.velocidad_pct, orden.repeticiones), (40, 2))
        self.assertTrue(esperar(lambda: not pc.ordenes[-1].ordenes['ejecutar']))   # el bit se baja
        self.assertTrue(esperar(lambda: sim.ultimo_estado.estado & 0x0C00 == 0))
        vidas = [o.vida for o in pc.ordenes[-6:]]
        self.assertTrue(all(a != b for a, b in zip(vidas, vidas[1:])))            # vida alterna
        self.assertIn('16#', sim.descripcion())
        self.assertTrue(pc.t.enlace)
        sim.cerrar()
        self.assertTrue(esperar(lambda: not pc.t.enlace, 3.))
        return pc

    def test_completo(self):
        self.prueba(tg.COMPLETO)

    def test_nucleo(self):
        self.prueba(tg.NUCLEO)

    def test_sin_respuesta(self):
        pc = PcFalsa(tg.COMPLETO)
        self.addCleanup(pc.t.cerrar)
        pc.t.al_recibir = lambda o: None                                         # PC muda
        sim = PlcSimulado('cliente', '127.0.0.1', puerto=pc.t.puerto, saludo_s=.5).iniciar()
        self.addCleanup(sim.cerrar)
        self.assertIn('sin respuesta', sim.comando('pausar'))

    def test_comandos_simples(self):
        sim = PlcSimulado('servidor', host='127.0.0.1', puerto=0)
        self.assertEqual(sim.comando('habilitar on'), 'mando=16#0001')
        self.assertIn('punto necesita', PlcSimulado(formato='nucleo', puerto=1).comando('punto 1 2 3 4 5 6'))
        self.assertIsNone(sim.comando('salir'))
        self.assertIn('desconocida', sim.comando('foo'))
        self.assertIn('no válidos', sim.comando('ejecutar'))


if __name__ == '__main__':
    unittest.main()
