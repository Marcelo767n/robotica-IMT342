import io
import os
import re
import unittest

import matplotlib
matplotlib.use('Agg')
import numpy as np

from irb120_control.analisis.modelo import hito2
from irb120_control.estudio import matematica as m

Q = [0, 0, 0, 0, 30, 0]


def _numeros(latex):
    return [float(x) for x in re.findall(r'-?\d+\.\d+', latex)]


class BloquesTest(unittest.TestCase):
    def test_cinematica_tcp_coincide_con_fk(self):
        dh = hito2()['dh']
        bl = m.bloques_cinematica(Q)
        self.assertEqual(len(bl), 11)
        T = dh.forward_kinematics_tcp(np.deg2rad(Q))
        Tm = T.copy()
        Tm[:3, 3] *= 1000
        nums = _numeros(bl[-1].latex)
        self.assertEqual(len(nums), 16)
        np.testing.assert_allclose(nums, Tm.ravel(), atol=6e-4)
        self.assertIn('519.000', bl[-1].latex)  # z del TCP con q5 = 30 y TCP 150 mm
        self.assertIn('150.000', bl[-2].latex)

    def test_cinematica_sin_tcp_y_offsets(self):
        bl = m.bloques_cinematica([10, 20, 30, 40, 50, 60], herramienta='tool0')
        self.assertEqual(len(bl), 9)
        self.assertIn('-70.00', bl[0].latex)    # 20 - 90
        self.assertIn('240.00', bl[0].latex)    # 60 + 180

    def test_jacobiano_sigma_min(self):
        jac = hito2()['jacobian']
        q = [10, 20, -30, 40, 50, 60]
        bl = m.bloques_jacobiano(q)
        smin = jac.smallest_singular_value(np.deg2rad(q))
        self.assertIn(f'{smin:.4f}', bl[-1].latex)
        self.assertIn('lejos', bl[-1].explicacion)
        J = jac.geometric_jacobian(np.deg2rad(q))
        self.assertIn(f'{J[0, 1]:.3f}', bl[1].latex)

    def test_jacobiano_singular(self):
        bl = m.bloques_jacobiano([0, 0, 0, 0, 0, 0])
        self.assertIn('BLOQUEO', bl[-1].explicacion)

    def test_lspb(self):
        lspb = hito2()['lspb']
        q0, qf = [0] * 6, [40, -30, 20, 60, -45, 90]
        bl = m.bloques_lspb(q0, qf, 25)
        vmax, amax = lspb.default_limits(.25)
        tr = lspb.plan_lspb(np.deg2rad(q0), np.deg2rad(qf), vmax, amax)
        self.assertIn(f'{tr.tb:.3f}', bl[1].latex)
        self.assertIn(f'{tr.tf:.3f}', bl[1].latex)
        self.assertIn('90.00', bl[2].latex)

    def test_dinamica(self):
        dy = hito2()['dynamics']
        q = np.deg2rad(Q)
        bl = m.bloques_dinamica(Q, [0] * 6, [0] * 6)
        g = dy.gravity_vector(q)
        nums = _numeros(bl[2].latex)
        self.assertTrue(any(abs(n - g[1]) < 1e-3 for n in nums))
        M = dy.mass_matrix(q)
        self.assertIn(f'{M[0, 0]:.5f}', bl[1].latex)


class RenderTest(unittest.TestCase):
    def _png(self, bloque, **kw):
        buf = io.BytesIO()
        fig = m.figura_bloque(bloque, tamano=14, **kw)
        fig.savefig(buf, format='png', dpi=m.DPI)
        self.assertGreater(len(buf.getvalue()), 1000)
        self.assertGreater(fig.get_size_inches().min(), .3)

    def test_fallback_mathtext(self):
        for bl in (m.bloques_cinematica(Q)[:3] + m.bloques_jacobiano(Q) + m.bloques_lspb([0] * 6, [30] * 6, 25)
                   + m.bloques_dinamica(Q, [1] * 6, [1] * 6)):
            self._png(bl, usetex=False)
            self._png(bl, usetex=False, oscuro=True)

    def test_variable_de_entorno(self):
        os.environ['IRB120_SIN_TEX'] = '1'
        try:
            self.assertFalse(m.usar_latex())
            self._png(m.bloques_jacobiano(Q)[1])
        finally:
            del os.environ['IRB120_SIN_TEX']

    def test_usetex(self):
        if not m.usar_latex():
            self.skipTest('TeX no disponible')
        for bl in (m.bloques_cinematica(Q)[0], m.bloques_lspb([0] * 6, [30] * 6, 25)[0]):
            self._png(bl, usetex=True)
        self._png(m.bloques_cinematica(Q)[1], oscuro=True)

    def test_png_bloque_y_cache(self):
        b = m.bloques_jacobiano(Q)[2]
        a = m.png_bytes_bloque(b, usetex=False)
        self.assertIs(a, m.png_bytes_bloque(b, usetex=False))
        self.assertTrue(a.startswith(b'\x89PNG'))


if __name__ == '__main__':
    unittest.main()
