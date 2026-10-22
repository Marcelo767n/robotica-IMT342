"""El URDF versionado (que leen launch, pruebas y verify_model) debe ser la expansion actual del xacro."""

import shutil
import subprocess
import unittest
from pathlib import Path
from xml.etree import ElementTree


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
URDF_PATH = PACKAGE_ROOT / "urdf" / "irb120.urdf"
XACRO_PATH = PACKAGE_ROOT / "urdf" / "irb120.urdf.xacro"


def _canonical(root: ElementTree.Element) -> list[tuple[str, tuple[tuple[str, str], ...]]]:
    """Elementos y atributos en orden de documento; ignora comentarios y espacios."""
    return [(element.tag, tuple(sorted(element.attrib.items()))) for element in root.iter()]


class TestUrdfExpansion(unittest.TestCase):
    def test_versioned_urdf_matches_xacro_expansion(self) -> None:
        if shutil.which("xacro") is None:
            self.skipTest("xacro no esta disponible (cargar /opt/ros/jazzy/setup.bash)")
        result = subprocess.run(
            ["xacro", str(XACRO_PATH)], capture_output=True, text=True, check=False
        )
        if result.returncode != 0 and "irb120_hito1" in result.stderr:
            self.skipTest("irb120_hito1 no esta en el indice ament (cargar install/setup.bash)")
        self.assertEqual(result.returncode, 0, result.stderr)
        expanded = ElementTree.fromstring(result.stdout)
        versioned = ElementTree.parse(URDF_PATH).getroot()
        self.assertEqual(
            _canonical(versioned),
            _canonical(expanded),
            "urdf/irb120.urdf esta desactualizado: regenerar con "
            "xacro urdf/irb120.urdf.xacro -o urdf/irb120.urdf",
        )


if __name__ == "__main__":
    unittest.main()
