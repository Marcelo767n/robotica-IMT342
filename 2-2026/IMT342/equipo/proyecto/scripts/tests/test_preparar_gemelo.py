"""El preparador del gemelo RViz: genera archivos fuera del repositorio y no deja mallas sin resolver."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

import yaml

spec = importlib.util.spec_from_file_location("preparar_gemelo", Path(__file__).parents[1] / "preparar_gemelo.py")
twin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(twin)


class TwinPreparationTests(unittest.TestCase):
    def test_package_paths_become_absolute_file_uris(self):
        text = twin.build_urdf()
        self.assertNotIn("package://", text)
        self.assertIn(f"file://{twin.PACKAGE}/meshes/visual/link_1.stl", text)

    def test_every_mesh_of_the_real_urdf_exists(self):
        self.assertEqual(twin.missing_meshes(twin.build_urdf()), [])

    def test_a_missing_mesh_is_reported(self):
        broken = twin.build_urdf(package=Path("/ruta/que/no/existe"))
        self.assertTrue(twin.missing_meshes(broken))

    def test_urdf_without_package_uris_is_rejected(self):
        with self.assertRaises(ValueError):
            twin.build_urdf("<robot/>")

    def test_prepare_writes_a_loadable_parameter_file_and_rviz_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = twin.prepare(tmp)
            params = yaml.safe_load((out / "robot_state_publisher.yaml").read_text())
            description = params["/**"]["ros__parameters"]["robot_description"]
            self.assertTrue(description.lstrip().startswith("<?xml"))
            self.assertEqual(description.count('filename="file://'), 16)
            self.assertTrue((out / "gemelo.rviz").read_text().startswith("Panels:"))

    def test_nothing_is_written_inside_the_repository(self):
        before = sorted(p.name for p in twin.PROJECT.iterdir())
        with tempfile.TemporaryDirectory() as tmp:
            twin.prepare(tmp)
        self.assertEqual(sorted(p.name for p in twin.PROJECT.iterdir()), before)


if __name__ == "__main__":
    unittest.main()
