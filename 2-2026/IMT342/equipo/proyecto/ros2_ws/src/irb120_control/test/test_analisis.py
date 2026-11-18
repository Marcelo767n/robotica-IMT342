"""Interfaz de análisis: cálculos del Hito 2 y lectura del estado (sin pantalla ni red real)."""
import io
import json
import math
import unittest

import numpy as np

from irb120_control.analisis import calculos, fuente
from irb120_control.analisis.modelo import hito2


def pose_de(q_deg, tool='tcp'):
    h = hito2()
    q = np.deg2rad(q_deg)
    T = h['dh'].forward_kinematics_tcp(q) if tool == 'tcp' else h['dh'].forward_kinematics(q)
    return [*(T[:3, 3] * 1000.), *h['transforms'].matrix_to_rpy_deg(T[:3, :3])]


def entrada(medido, objetivo, pose=None, tool='tcp', inicio=None, pct=20.):
    estado = {'medido': medido, 'objetivo': objetivo, 'herramienta': tool, 'velocidad_pct': pct,
              'verificacion': {'origen': 'ik' if pose else 'angulos', 'pose_deseada': pose, 'inicio': inicio}}
    return fuente.entrada(estado)


class Calculos(unittest.TestCase):
    MED = [7.02, 10.22, -33.33, 48.94, -1.48, 103.57]
    OBJ = [10., -4., 8., 5., 35., -6.]

    def test_fk_and_round_trip_within_a_thousandth(self):
        for tool in ('tcp', 'brida'):
            r = calculos.cinematica(entrada(self.MED, self.OBJ, pose_de(self.OBJ, tool), tool))
            self.assertLess(r['fk']['pos_mm'], 1e-6)
            self.assertLess(r['fk']['rot_deg'], 1e-6)
            self.assertTrue(r['fk']['ok'])
            for row in r['ida_vuelta']:
                self.assertLess(abs(row['error_deg']), 1e-6, row)
            self.assertEqual(r['rama_recuperada'], 1)

    def test_wrong_pose_is_flagged(self):
        pose = pose_de(self.OBJ); pose[0] += .01   # 10 µm: por encima del criterio de 1 µm
        r = calculos.cinematica(entrada(self.MED, self.OBJ, pose))
        self.assertFalse(r['fk']['ok'])
        self.assertAlmostEqual(r['fk']['pos_mm'], .01, places=6)

    def test_robot_errors_per_joint_and_percent(self):
        start = [0., 0., 0., 0., 30., 0.]
        r = calculos.cinematica(entrada([9.9, -4., 8., 5., 35., -6.], self.OBJ, inicio=start))
        self.assertAlmostEqual(r['robot'][0]['error_deg'], -.1)
        self.assertAlmostEqual(r['robot'][0]['error_pct'], 1.)       # 0,1° de 10°
        self.assertGreater(r['robot_pose']['pos_mm'], 0.)

    def test_branches_lspb_jacobian_dynamics(self):
        e = calculos.redondear(entrada(self.MED, self.OBJ, pose_de(self.OBJ), pct=50.))
        result = calculos.analizar(e)
        self.assertEqual(len(result['ramas']['filas']), 8)
        self.assertIsNotNone(result['ramas']['elegida'])
        tr = result['trayectoria']
        np.testing.assert_allclose(tr['q'][-1], self.OBJ, atol=1e-9)
        np.testing.assert_allclose(tr['q'][0], self.MED, atol=1e-9)
        self.assertTrue(tr['check']['paso'])
        slower = calculos.trayectoria(entrada(self.MED, self.OBJ, pct=10.))
        self.assertGreater(slower['tf'], tr['tf'])                 # menos % → más lento
        self.assertEqual(result['jacobiano']['J'].shape, (6, 6))
        self.assertEqual(result['jacobiano']['rango'], 6)
        d = result['dinamica']
        self.assertEqual(d['tau'].shape, (calculos.DINAMICA_MUESTRAS, 6))
        self.assertTrue(np.all(np.isfinite(d['tau'])))
        self.assertGreater(d['j2_completo_max'], 1.)              # la gravedad carga el hombro
        key = calculos.redondear(e)
        self.assertIs(calculos._pesado(key), calculos._pesado(key))   # caché de la parte pesada
        self.assertLess(result['cinematica']['ik_fk']['pos_mm'] if 'ik_fk' in result['cinematica'] else 0., 1e-6)

    def test_singular_wrist_is_detected(self):
        r = calculos.analizar(calculos.redondear(entrada([0.] * 6, [0., 0., 0., 0., 0., 0.])))
        self.assertTrue(r['jacobiano']['singular'])


class Fuente(unittest.TestCase):
    def test_entrada_validation(self):
        self.assertIsNone(fuente.entrada({'medido': [1, 2, 3]}))
        self.assertIsNone(fuente.entrada(None))
        e = fuente.entrada(fuente.DEMO)
        self.assertEqual(e.herramienta, 'tcp')
        self.assertIsNone(e.pose_deseada)
        self.assertEqual(fuente.entrada({**fuente.DEMO, 'velocidad_pct': 500}).velocidad_pct, 100.)

    def test_polling_reads_and_reports_errors(self):
        class Resp(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *a): return False
        source = fuente.Fuente(opener=lambda url, timeout: Resp(json.dumps(fuente.DEMO).encode()))
        source.leer_una_vez()
        data, error = source.instantanea()
        self.assertIsNone(error)
        self.assertEqual(data['medido'], fuente.DEMO['medido'])

        def broken(url, timeout):
            raise OSError('connection refused')
        source.opener = broken
        source.leer_una_vez()
        data, error = source.instantanea()
        self.assertIn('Sin conexión', error)
        self.assertEqual(data['medido'], fuente.DEMO['medido'])   # conserva el último dato


if __name__ == '__main__':
    unittest.main()
