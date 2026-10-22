"""Prueba del panel Qt sin pantalla (QT_QPA_PLATFORM=offscreen) y sin otros nodos."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import rclpy
    from python_qt_binding.QtWidgets import QApplication
    from rclpy.executors import SingleThreadedExecutor

    from irb120_hito1.nodes.slider_gui import SLIDER_STEPS_PER_DEG, ControlPanel, PanelNode
except ImportError as error:  # sin ROS 2 o sin Qt en el entorno de prueba
    IMPORT_ERROR: ImportError | None = error
else:
    IMPORT_ERROR = None

from irb120_hito1.slider_controls import JOINT_SLIDERS, PRESETS_DEG


@unittest.skipIf(IMPORT_ERROR is not None, f"ROS 2/Qt no disponible: {IMPORT_ERROR}")
class TestControlPanel(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        rclpy.init()
        cls.app = QApplication.instance() or QApplication([])

    @classmethod
    def tearDownClass(cls) -> None:
        rclpy.shutdown()

    def setUp(self) -> None:
        self.node = PanelNode()
        self.executor = SingleThreadedExecutor()
        self.executor.add_node(self.node)
        self.window = ControlPanel(self.node, self.executor)

    def tearDown(self) -> None:
        self.window.close()
        self.executor.remove_node(self.node)
        self.node.destroy_node()

    def test_six_sliders_with_official_limits(self) -> None:
        self.assertEqual(len(self.window._sliders), 6)
        for slider, spin, spec in zip(
            self.window._sliders, self.window._spins, JOINT_SLIDERS, strict=True
        ):
            self.assertEqual(slider.minimum(), int(spec.lower_deg * SLIDER_STEPS_PER_DEG))
            self.assertEqual(slider.maximum(), int(spec.upper_deg * SLIDER_STEPS_PER_DEG))
            self.assertEqual((spin.minimum(), spin.maximum()), (spec.lower_deg, spec.upper_deg))

    def test_preset_updates_sliders_and_spinboxes(self) -> None:
        self.window._apply_preset("Prueba B")
        self.assertEqual(self.window._values(), list(PRESETS_DEG["Prueba B"]))
        self.assertEqual(
            [slider.value() for slider in self.window._sliders],
            [int(v * SLIDER_STEPS_PER_DEG) for v in PRESETS_DEG["Prueba B"]],
        )

    def test_slider_and_spinbox_stay_synchronized(self) -> None:
        self.window._sliders[2].setValue(-123)  # -12.3 grados
        self.assertAlmostEqual(self.window._spins[2].value(), -12.3)
        self.window._spins[0].setValue(45.5)
        self.assertEqual(self.window._sliders[0].value(), 455)

    def test_demo_disables_manual_controls(self) -> None:
        self.window._demo_check.setChecked(True)
        self.assertFalse(any(slider.isEnabled() for slider in self.window._sliders))
        self.window._demo_check.setChecked(False)
        self.assertTrue(all(slider.isEnabled() for slider in self.window._sliders))

    def test_suite_tab_runs_and_reports_approval(self) -> None:
        self.window._random_count.setValue(5)
        self.window._run_suite()
        self.assertEqual(self.window._suite_table.rowCount(), (3 + 5) * 2)
        self.assertIn("APROBADO", self.window._suite_summary.text())
        self.assertNotIn("NO APROBADO", self.window._suite_summary.text())


if __name__ == "__main__":
    unittest.main()
