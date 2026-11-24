"""Pruebas del paquete puro irb120_control.trayectorias (sin ROS ni red)."""
import json
from pathlib import Path
import tempfile
import time
import unittest

import numpy as np

from irb120_control.trayectorias import (TOLERANCIAS, Punto, Tolerancias, Trayectoria, a_ordenes, planificar)
from irb120_control.trayectorias.reglas import tau_ref

CERO = [0, 0, 0, 0, 30, 0]
A, B, C = [20, 10, -10, 0, 40, 0], [-20, 15, -5, 0, 45, 10], [0, -10, 10, 0, 60, 0]


def tres_puntos(**kw):
    return Trayectoria('abc', [Punto('A', q=A), Punto('B', q=B), Punto('C', q=C)], **kw)


class ModeloTest(unittest.TestCase):
    def test_json_ida_y_vuelta(self):
        t = Trayectoria('demo', [Punto('A', q=A, origen='captura'),
                                 Punto('B', pose=[300, 100, 300, 0, 90, 0], tipo='lineal')],
                        cerrar=False, repeticiones=3, herramienta='brida')
        self.assertEqual(Trayectoria.from_dict(json.loads(json.dumps(t.to_dict()))), t)
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / 't.json'
            t.guardar(ruta)
            self.assertEqual(Trayectoria.cargar(ruta), t)

    def test_bucle_continuo_repeticiones_cero(self):
        t = Trayectoria('bucle', [Punto('A', q=A), Punto('B', q=B)], repeticiones=0)
        self.assertEqual(t.repeticiones, 0)
        self.assertEqual(Trayectoria.from_dict(json.loads(json.dumps(t.to_dict()))), t)
        self.assertEqual(Trayectoria.from_dict(t.to_dict()).repeticiones, 0)
        self.assertEqual(Trayectoria('mil', [Punto('A', q=A)], repeticiones=1000).repeticiones, 1000)

    def test_punto_con_q_y_con_pose(self):
        self.assertEqual(Punto('A', q=A).pose, None)
        self.assertEqual(Punto('B', pose=[1, 2, 3, 0, 0, 0]).q, None)

    def test_validacion(self):
        with self.assertRaisesRegex(ValueError, 'pose o los ángulos'):
            Punto('X')
        with self.assertRaisesRegex(ValueError, 'seis|6 números'):
            Punto('X', q=[1, 2, 3])
        with self.assertRaisesRegex(ValueError, 'finitos'):
            Punto('X', q=[0, 0, 0, 0, float('nan'), 0])
        with self.assertRaisesRegex(ValueError, 'tipo'):
            Punto('X', q=A, tipo='curvo')
        with self.assertRaisesRegex(ValueError, 'repetidos'):
            Trayectoria('t', [Punto('A', q=A), Punto('A', q=B)])
        for malo in (-1, 1001, 1.5, True):
            with self.assertRaisesRegex(ValueError, 'repeticiones'):
                Trayectoria('t', [Punto('A', q=A)], repeticiones=malo)
        with self.assertRaisesRegex(ValueError, 'Herramienta'):
            Trayectoria('t', [Punto('A', q=A)], herramienta='pinza')


class DemosTest(unittest.TestCase):
    """Las trayectorias de exhibición: en el repositorio y regeneradas, seguras y sin avisos."""

    def test_demos_regeneradas_son_validas_y_seguras(self):
        from irb120_control.trayectorias import demos
        for archivo, fabrica in demos.DEMOS:
            with self.subTest(archivo):
                tray = demos.construir(fabrica)
                self.assertEqual((tray.repeticiones, tray.cerrar), (0, True))
                self.assertTrue(all(p.tipo == 'articular' and p.q is not None for p in tray.puntos))
                res, problemas = demos.verificar(tray)
                self.assertEqual(problemas, [])
                self.assertTrue(res['ok'])
                self.assertTrue(6. <= res['duracion_s'] <= 20.)
                self.assertGreaterEqual(res['z_min'], 200.)
                self.assertGreaterEqual(res['margen_min'], 15.)

    def test_ocho_tiene_entre_12_y_16_puntos(self):
        from irb120_control.trayectorias import demos
        self.assertTrue(12 <= len(demos.construir(demos._ocho).puntos) <= 16)

    def test_archivos_de_la_biblioteca_coinciden(self):
        from irb120_control.trayectorias import demos
        for archivo, fabrica in demos.DEMOS:
            ruta = demos.CARPETA / f'{archivo}.json'
            if not ruta.exists():
                self.skipTest('salidas/trayectorias no existe en este árbol')
            self.assertEqual(Trayectoria.cargar(ruta), demos.construir(fabrica), archivo)


class PlanificadorTest(unittest.TestCase):
    def test_ciclo_tipico_ok_y_vuelve_a_a(self):
        plan = planificar(tres_puntos(), CERO, 25)
        self.assertTrue(plan.ok, plan.resumen)
        self.assertEqual(len(plan.tramos), 4)            # Inicio→A, A→B, B→C, C→A
        np.testing.assert_allclose(plan.tramos[-1].qf, A, atol=1e-9)
        self.assertEqual(plan.tramos[-1].hasta, 'A')
        np.testing.assert_allclose(plan.tramos[0].q0, CERO)

    def test_duraciones_motivo_y_opciones(self):
        plan = planificar(tres_puntos(), CERO, 25)
        self.assertGreater(plan.duracion_s, 0)
        for t in plan.tramos:
            self.assertEqual(set(t.opciones), {'articular', 'lineal'})
            self.assertTrue(t.motivo.strip())
            self.assertIn(t.tipo, ('articular', 'lineal'))
            self.assertGreater(t.opciones[t.tipo].duracion_s, 0)
            m = t.opciones[t.tipo].muestras
            self.assertTrue(50 <= len(m.t) <= 400)
            for campo in (m.q, m.qd, m.qdd, m.tau):
                self.assertEqual(campo.shape, (len(m.t), 6))
            self.assertEqual(m.tcp.shape, (len(m.t), 3))

    def test_abierta_cada_vuelta_empieza_volviendo_a_a(self):
        # vuelta ≥ 2 de un bucle abierto: se planifica desde el último punto y el tramo 0 lleva a A
        plan = planificar(tres_puntos(cerrar=False, repeticiones=0), C, 25.)
        self.assertTrue(plan.ok, plan.resumen)
        self.assertEqual((plan.tramos[0].desde, plan.tramos[0].hasta), ('Inicio', 'A'))
        self.assertLess(max(abs(a - b) for a, b in zip(plan.tramos[0].qf, A)), 1e-6)
        self.assertGreater(plan.tramos[0].opciones[plan.tramos[0].tipo].duracion_s, 0)

    def test_sin_cerrar(self):
        plan = planificar(tres_puntos(cerrar=False), CERO, 25)
        self.assertEqual(len(plan.tramos), 3)

    def test_a_ordenes_serializable(self):
        plan = planificar(tres_puntos(), CERO, 25)
        ordenes = a_ordenes(plan)
        self.assertEqual(len(ordenes), len(plan.tramos))
        json.dumps(ordenes)
        for i, o in enumerate(ordenes):
            self.assertEqual(o['tramo'], i)
            self.assertEqual(len(o['q']), 6)
            self.assertEqual(len(o['pose_tool0']), 7)
            self.assertIn(o['tipo'], ('articular', 'lineal'))
            self.assertAlmostEqual(float(np.linalg.norm(o['pose_tool0'][3:])), 1.0, places=6)

    def test_pose_tool0_coincide_con_fk(self):
        from irb120_control.analisis.modelo import hito2
        plan = planificar(tres_puntos(), CERO, 25)
        T = hito2()['dh'].forward_kinematics(np.deg2rad(B))
        self.assertTrue(np.allclose(plan.tramos[1].pose_tool0_fin[:3], T[:3, 3] * 1000., atol=1e-6))

    def test_punto_con_pose_ida_y_vuelta(self):
        from irb120_control.analisis.modelo import hito2
        h = hito2()
        T = h['dh'].forward_kinematics_tcp(np.deg2rad(A))
        pose = [*(T[:3, 3] * 1000.), *h['transforms'].matrix_to_rpy_deg(T[:3, :3])]
        t = Trayectoria('p', [Punto('A', pose=pose), Punto('B', q=B)])
        plan = planificar(t, CERO, 25)
        self.assertTrue(plan.ok, plan.resumen)
        err = np.abs(np.array(plan.q_puntos[0]) - A).max()
        self.assertLess(err, 1e-3)
        reglas_ik = [r for r in plan.tramos[0].opciones['articular'].reglas if r.nombre.startswith('IK→FK')]
        self.assertEqual(reglas_ik[0].estado, 'ok')

    def test_singularidad_de_muneca_detectada(self):
        t = Trayectoria('sing', [Punto('A', q=[0, 0, 0, 0, 30, 0]), Punto('B', q=[0, 0, 0, 0, -30, 0])],
                        cerrar=False)
        plan = planificar(t, CERO, 25)
        art = plan.tramos[1].opciones['articular']
        sigma = next(r for r in art.reglas if r.nombre == 'σ_min(J)')
        self.assertEqual(sigma.estado, 'falla')
        self.assertIn('σ_min', sigma.detalle)
        self.assertIn('J5', sigma.detalle)
        self.assertIsNotNone(sigma.t)
        self.assertFalse(art.factible)
        # el tramo no debe elegir el movimiento articular que cruza J5 = 0
        self.assertTrue(plan.tramos[1].tipo == 'lineal' or not plan.tramos[1].ok)

    def test_tipo_forzado_articular_falla_con_sugerencias(self):
        t = Trayectoria('sing', [Punto('A', q=[0, 0, 0, 0, 30, 0]),
                                 Punto('B', q=[0, 0, 0, 0, -30, 0], tipo='articular')], cerrar=False)
        plan = planificar(t, CERO, 25)
        self.assertFalse(plan.ok)
        tramo = plan.tramos[1]
        self.assertFalse(tramo.ok)
        self.assertEqual(tramo.tipo, 'articular')
        self.assertTrue(any('punto intermedio' in s for s in tramo.sugerencias))
        self.assertEqual(set(tramo.opciones), {'articular', 'lineal'})   # la otra se evalúa igual
        self.assertIn('NO apto', plan.resumen)
        with self.assertRaises(ValueError):
            a_ordenes(plan)

    def test_tipo_forzado_se_respeta(self):
        for tipo in ('articular', 'lineal'):
            t = Trayectoria('f', [Punto('A', q=A), Punto('B', q=B, tipo=tipo)], cerrar=False)
            plan = planificar(t, A, 25)
            self.assertTrue(plan.ok, plan.resumen)
            self.assertEqual(plan.tramos[1].tipo, tipo)
            self.assertIn('forzado', plan.tramos[1].motivo)

    def test_punto_fuera_de_alcance(self):
        t = Trayectoria('lejos', [Punto('A', q=A), Punto('X', pose=[1500, 0, 300, 0, 0, 0])])
        plan = planificar(t, CERO, 25)
        self.assertFalse(plan.ok)
        malo = next(t for t in plan.tramos if not t.ok)
        self.assertEqual(malo.hasta, 'X')
        self.assertIn('alcance', malo.motivo)
        self.assertIn('NO apto', plan.resumen)

    def test_punto_fuera_de_limites(self):
        t = Trayectoria('lim', [Punto('A', q=[200, 0, 0, 0, 30, 0])])
        plan = planificar(t, CERO, 25)
        self.assertFalse(plan.ok)
        self.assertIn('límites', plan.tramos[0].motivo)

    def test_margen_a_limites_bloquea(self):
        t = Trayectoria('m', [Punto('A', q=[160, 0, 0, 0, 30, 0])], cerrar=False)   # 5° del tope de J1
        plan = planificar(t, CERO, 25)
        self.assertFalse(plan.ok)
        reglas = plan.tramos[0].opciones['articular'].reglas
        self.assertEqual(next(r for r in reglas if r.nombre == 'Margen a los límites').estado, 'falla')

    def test_altura_tcp(self):
        t = Trayectoria('z', [Punto('A', q=[0, 60, 40, 0, 0, 0])], cerrar=False)   # brazo muy bajo
        plan = planificar(t, CERO, 25)
        reglas = plan.tramos[0].opciones['articular'].reglas
        self.assertNotEqual(next(r for r in reglas if r.nombre == 'Altura del TCP').estado, 'ok')

    def test_tramo_quieto(self):
        plan = planificar(Trayectoria('q', [Punto('A', q=A)]), A, 25)
        self.assertTrue(plan.ok)
        self.assertEqual([t.opciones['articular'].duracion_s for t in plan.tramos], [0., 0.])
        self.assertEqual(plan.duracion_s, 0.)

    def test_velocidad_invalida(self):
        for v in (0, 0.5, 101, True):
            with self.assertRaises(ValueError):
                planificar(tres_puntos(), CERO, v)

    def test_mas_rapido_dura_menos(self):
        lento = planificar(tres_puntos(), CERO, 10).duracion_s
        rapido = planificar(tres_puntos(), CERO, 40).duracion_s
        self.assertLess(rapido, lento)

    def test_tolerancias(self):
        with self.assertRaises(Exception):
            TOLERANCIAS.sigma_aviso = 1.      # congelada
        self.assertEqual(Tolerancias().sigma_bloqueo, 0.02)
        ref = tau_ref()
        self.assertTrue(np.all(ref > 0) and np.all(ref[3:] >= 2.))

    def test_rendimiento_cuatro_puntos(self):
        t = Trayectoria('4p', [Punto('A', q=A), Punto('B', q=B), Punto('C', q=C),
                               Punto('D', q=[10, 20, 0, 0, 50, 0])])
        t0 = time.perf_counter()
        plan = planificar(t, CERO, 25)
        dt = time.perf_counter() - t0
        self.assertTrue(plan.ok, plan.resumen)
        self.assertLess(dt, 3.0)


if __name__ == '__main__':
    unittest.main()
