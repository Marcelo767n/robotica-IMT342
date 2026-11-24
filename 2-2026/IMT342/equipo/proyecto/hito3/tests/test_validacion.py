"""Pruebas de hito3.validacion: ejemplos sintéticos del documento W14-S02 y ejecución completa offline.

Ejecutar desde proyecto/:  python3 -m unittest hito3.tests.test_validacion -v
"""

import csv
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hito3.validacion import ejecutar, metricas as M, rutas  # noqa: E402

ESQUEMA = ("case_id,case_type,q_rad_vector,base_frame,tcp_frame,model_version,reference_version,position_error_m,"
           "orientation_error_rad,jacobian_error_fro,rank_threshold,rank_observed,acceptance_result,evidence_link,notes").split(",")


class MetricasSinteticas(unittest.TestCase):
    q = np.deg2rad([30.0, -45.0])

    def test_2r_posicion_jacobiano_det(self):
        np.testing.assert_allclose(M.fk_2r(self.q), [1.34898832, 0.37059048], atol=5e-9)
        J = M.jac_2r(self.q)
        np.testing.assert_allclose(J, [[-0.37059048, 0.12940952], [1.34898832, 0.48296291]], atol=5e-9)
        np.testing.assert_allclose(J @ [0.1, -0.2], [-0.06294095, 0.03830625], atol=5e-9)
        self.assertAlmostEqual(np.linalg.det(J), -0.35355339, places=8)

    def test_2r_fd_truncamiento(self):
        e = M.curva_fd_2r(self.q, [1e-2, 1e-3, 1e-4])
        for obtenido, esperado in zip(e, (2.33e-5, 2.33e-7, 2.33e-9)):
            self.assertAlmostEqual(obtenido / esperado, 1.0, delta=0.01)

    def test_ejemplo2_error_orientacion(self):
        Rz = M.Rz(np.deg2rad(10.0))
        self.assertAlmostEqual(M.error_rotacion(Rz, np.eye(3)), np.pi / 18, places=12)
        self.assertAlmostEqual(M.error_rotacion_atan2(Rz, np.eye(3)), np.pi / 18, places=14)
        self.assertFalse(np.isnan(M.error_rotacion(np.eye(3) * (1 + 1e-15), np.eye(3))))  # clip

    def test_ejemplo3_rango_uno(self):
        Jp = np.array([[1.0, 2.0], [2.0, 4.0]])
        r = M.rango_numerico(Jp)
        self.assertEqual(r["rango"], 1)
        u = np.linalg.svd(Jp)[0][:, -1]
        self.assertAlmostEqual(abs(u @ np.array([-2.0, 1.0])) / np.sqrt(5), 1.0, places=12)
        np.testing.assert_allclose(Jp.T @ [3.0, -7.0], [-11.0, -22.0])

    def test_comprobacion_rotacion_y_cuaternion(self):
        R = M.cuaternion_wxyz_a_R([np.cos(0.15), 0, 0, np.sin(0.15)])
        c = M.comprobar_rotacion(R)
        self.assertLess(c["ortogonalidad_max"], 1e-15)
        self.assertLess(abs(c["det_menos_1"]), 1e-15)
        np.testing.assert_allclose(M.R_a_cuaternion_wxyz(R), [np.cos(0.15), 0, 0, np.sin(0.15)], atol=1e-14)

    def test_escala_jacobiano_exige_L_positivo(self):
        with self.assertRaises(ValueError):
            M.escalar_jacobiano(np.eye(6), 0.0)


class EjecucionCompleta(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ejecutar.main([])

    def test_archivos_producidos(self):
        for rel in ("validation_cases.csv", "P1_fk.csv", "P2_ik.csv", "P3_jacobiano.csv", "P4_singularidad.csv", "resultados.json", "figuras/fk_real_errores_N1_N2.png",
                    "figuras/jacobiano_fd_curva_visual4.png", "latex/P1a_fk_identificacion.tex", "latex/P2b_ik_ramas.tex", "latex/P4_singularidad.tex"):
            self.assertTrue((rutas.RESULTADOS / rel).exists(), rel)

    def test_esquema_validation_cases_y_estados(self):
        with open(rutas.RESULTADOS / "validation_cases.csv", newline="", encoding="utf-8") as fh:
            lector = csv.DictReader(fh)
            self.assertEqual(lector.fieldnames, ESQUEMA)
            filas = list(lector)
        self.assertGreaterEqual(len(filas), 30)
        validos = {"verificado", "parcial", "fallido", "no ejecutado", "bloqueado por acceso"}
        self.assertTrue(all(f["acceptance_result"] in validos for f in filas))
        self.assertNotIn("fallido", {f["acceptance_result"] for f in filas})

    def test_un_manifiesto_por_caso(self):
        with open(rutas.RESULTADOS / "validation_cases.csv", newline="", encoding="utf-8") as fh:
            ids = [f["case_id"] for f in csv.DictReader(fh)]
        for cid in ids:
            self.assertTrue((rutas.MANIFIESTOS / f"{cid}.yaml").exists(), cid)
        try:
            import yaml
        except ImportError:
            return
        m = yaml.safe_load((rutas.MANIFIESTOS / "FK-N1.yaml").read_text(encoding="utf-8"))
        self.assertEqual(m["operador"], "por completar por el equipo")
        self.assertEqual(len(m["codigo_modelo"]["commit"]), 40)
        self.assertIsNone(m["tolerancias"]["umbral_aprobado"])

    def test_valores_fisicamente_razonables(self):
        import json
        r = json.loads((rutas.RESULTADOS / "resultados.json").read_text(encoding="utf-8"))
        self.assertLess(r["fk"]["FK-N1"]["estadistica_e_p_m"]["mediana"], 1e-6)
        self.assertAlmostEqual(r["fk"]["FK-D-TCP"]["estadistica_e_p_m"]["mediana"], 0.150, places=5)
        self.assertEqual(r["sing"]["casos"][2]["rango_Js"], 5)
        self.assertTrue(r["sint"]["todas_ok"])
        for pose in ("IK-1", "IK-2"):
            self.assertEqual(r["ik"]["poses"][pose]["resumen_dls"]["ramas_reales_halladas_por_DLS"], 8)


if __name__ == "__main__":
    unittest.main()
