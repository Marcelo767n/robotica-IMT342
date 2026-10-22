"""TCP unico (URDF = DH = config/tcp.yaml) y FK propia contra la referencia ROS-Industrial.

La referencia es hito2/irb120/rosi_model.py, transcripcion del xacro oficial
abb_irb120_support/irb120_3_58_macro.xacro (traslaciones + ejes, sin DH). Se
carga por ruta de archivo para no depender del paquete irb120_hito2.
"""

import importlib.util
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

import numpy as np
import yaml

from irb120_hito1.kinematics.dh import (
    GRIPPER_TCP_Z_M,
    JOINT_NAMES,
    TCP_VERIFIED_ON_ROBOT,
    forward_kinematics,
    forward_kinematics_tcp,
    load_tcp_config,
    position_error_m,
    rotation_error_rad,
)
from irb120_hito1.kinematics.urdf_chain import chain_transform, load_joints


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
URDF_PATH = PACKAGE_ROOT / "urdf" / "irb120.urdf"
XACRO_PATH = PACKAGE_ROOT / "urdf" / "irb120.urdf.xacro"
TCP_CONFIG_PATH = PACKAGE_ROOT / "config" / "tcp.yaml"
PROJECT_ROOT = PACKAGE_ROOT.parents[2]
ROSI_MODEL_PATH = PROJECT_ROOT / "hito2" / "irb120" / "rosi_model.py"
HITO2_DH_PATH = PROJECT_ROOT / "hito2" / "irb120" / "dh.py"

# Tolerancias declaradas para la comparacion en brida (tool0). Ambos modelos
# usan las mismas cotas nominales, por lo que la diferencia esperada es solo
# redondeo de coma flotante (~1e-16).
FLANGE_POSITION_TOLERANCE_M = 1.0e-9
FLANGE_ORIENTATION_TOLERANCE_RAD = 1.0e-9
# ROS-Industrial publica los limites con 5-6 decimales.
LIMIT_TOLERANCE_RAD = 1.0e-5


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _urdf_limits_rad() -> np.ndarray:
    root = ElementTree.parse(URDF_PATH).getroot()
    limits = {}
    for joint in root.findall("joint"):
        limit = joint.find("limit")
        if limit is not None:
            limits[joint.attrib["name"]] = (float(limit.attrib["lower"]), float(limit.attrib["upper"]))
    return np.array([limits[name] for name in JOINT_NAMES])


class TestSingleTcp(unittest.TestCase):
    def test_tcp_yaml_is_the_value_used_by_dh(self) -> None:
        config = load_tcp_config(TCP_CONFIG_PATH)
        self.assertEqual(config["tool0_to_tcp_z_m"], GRIPPER_TCP_Z_M)
        self.assertEqual(config["verified_on_robot"], TCP_VERIFIED_ON_ROBOT)

    def test_tcp_is_explicitly_not_verified_on_robot(self) -> None:
        # El TCP fisico es desconocido: si alguien lo mide, debe cambiar este
        # test junto con model_manifest.yaml (physical_tcp).
        raw = yaml.safe_load(TCP_CONFIG_PATH.read_text(encoding="utf-8"))
        self.assertIs(raw["verified_on_robot"], False)

    def test_expanded_urdf_tcp_matches_dh(self) -> None:
        tcp_joint = load_joints(URDF_PATH)["gripper_tcp"]
        self.assertEqual(tcp_joint.name, "gripper_tcp_joint")
        np.testing.assert_allclose(tcp_joint.xyz, [0.0, 0.0, GRIPPER_TCP_Z_M], atol=1.0e-12)
        np.testing.assert_allclose(tcp_joint.rpy, [0.0, 0.0, 0.0], atol=0.0)

    def test_tcp_matches_hito2_model(self) -> None:
        if not HITO2_DH_PATH.is_file():
            self.skipTest(f"No existe {HITO2_DH_PATH}")
        hito2_dh = _load_module("hito2_dh_reference", HITO2_DH_PATH)
        self.assertAlmostEqual(hito2_dh.TCP_Z_M, GRIPPER_TCP_Z_M, places=12)

    def test_urdf_tcp_chain_matches_dh_tcp(self) -> None:
        generator = np.random.default_rng(seed=120)
        limits = _urdf_limits_rad()
        worst_position_m = 0.0
        worst_rotation_rad = 0.0
        for joints_rad in generator.uniform(limits[:, 0], limits[:, 1], size=(50, 6)):
            joint_map = dict(zip(JOINT_NAMES, joints_rad, strict=True))
            urdf_transform = chain_transform(URDF_PATH, joint_map, target_link="gripper_tcp")
            analytic = forward_kinematics_tcp(joints_rad)
            worst_position_m = max(worst_position_m, position_error_m(analytic, urdf_transform))
            worst_rotation_rad = max(worst_rotation_rad, rotation_error_rad(analytic, urdf_transform))
        self.assertLess(worst_position_m, 1.0e-9)
        self.assertLess(worst_rotation_rad, 1.0e-9)

    def test_xacro_reads_tcp_from_config(self) -> None:
        """Expand the xacro with another tcp.yaml: the URDF TCP must follow it."""
        if shutil.which("xacro") is None:
            self.skipTest("xacro no esta disponible (cargar /opt/ros/jazzy/setup.bash)")
        with tempfile.TemporaryDirectory() as directory:
            other_config = Path(directory) / "tcp_prueba.yaml"
            other_config.write_text("tool0_to_tcp_z_m: 0.123\nverified_on_robot: false\n")
            result = subprocess.run(
                ["xacro", str(XACRO_PATH), f"tcp_config:={other_config}"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0 and "irb120_hito1" in result.stderr:
                self.skipTest("irb120_hito1 no esta en el indice ament (cargar install/setup.bash)")
            self.assertEqual(result.returncode, 0, result.stderr)
            expanded_urdf = Path(directory) / "irb120.urdf"
            expanded_urdf.write_text(result.stdout)
            np.testing.assert_allclose(
                load_joints(expanded_urdf)["gripper_tcp"].xyz, [0.0, 0.0, 0.123], atol=1.0e-12
            )


@unittest.skipUnless(ROSI_MODEL_PATH.is_file(), f"No existe {ROSI_MODEL_PATH}")
class TestFlangeAgainstRosIndustrial(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rosi = _load_module("rosi_model_reference", ROSI_MODEL_PATH)

    def _assert_flange_matches(self, joints_rad: np.ndarray) -> tuple[float, float]:
        own = forward_kinematics(joints_rad)
        reference = self.rosi.rosi_forward_kinematics(joints_rad)
        e_p = position_error_m(reference, own)
        e_r = rotation_error_rad(reference, own)
        self.assertLess(e_p, FLANGE_POSITION_TOLERANCE_M, joints_rad)
        self.assertLess(e_r, FLANGE_ORIENTATION_TOLERANCE_RAD, joints_rad)
        return e_p, e_r

    def test_zero_pose_flange_matches(self) -> None:
        self._assert_flange_matches(np.zeros(6))
        # Misma base y misma brida: tool0 en (0.374, 0, 0.630) m con su Z
        # apuntando a +X de base_link en ambos modelos.
        own = forward_kinematics(np.zeros(6))
        np.testing.assert_allclose(own[:3, 3], [0.374, 0.0, 0.630], atol=1.0e-15)
        np.testing.assert_allclose(own[:3, 2], [1.0, 0.0, 0.0], atol=1.0e-15)

    def test_random_postures_within_limits_match_at_flange(self) -> None:
        generator = np.random.default_rng(seed=342)
        limits = _urdf_limits_rad()
        for joints_rad in generator.uniform(limits[:, 0], limits[:, 1], size=(100, 6)):
            self._assert_flange_matches(joints_rad)

    def test_urdf_tool0_matches_reference_directly(self) -> None:
        """La cadena URDF (otro evaluador) tambien coincide con ROS-I en tool0."""
        generator = np.random.default_rng(seed=7)
        limits = _urdf_limits_rad()
        for joints_rad in generator.uniform(limits[:, 0], limits[:, 1], size=(20, 6)):
            joint_map = dict(zip(JOINT_NAMES, joints_rad, strict=True))
            urdf_transform = chain_transform(URDF_PATH, joint_map, target_link="tool0")
            reference = self.rosi.rosi_forward_kinematics(joints_rad)
            self.assertLess(position_error_m(reference, urdf_transform), FLANGE_POSITION_TOLERANCE_M)
            self.assertLess(rotation_error_rad(reference, urdf_transform), FLANGE_ORIENTATION_TOLERANCE_RAD)

    def test_joint_order_and_limits_match_reference(self) -> None:
        self.assertEqual(JOINT_NAMES, tuple(f"joint_{index}" for index in range(1, 7)))
        np.testing.assert_allclose(_urdf_limits_rad(), self.rosi.ROSI_LIMITS_RAD, atol=LIMIT_TOLERANCE_RAD)

    def test_joint_senses_match_reference(self) -> None:
        """Mover un solo eje +10 grados debe dar la misma pose en ambos modelos."""
        for index in range(6):
            joints_rad = np.zeros(6)
            joints_rad[index] = np.deg2rad(10.0)
            self._assert_flange_matches(joints_rad)
            joints_rad[index] = np.deg2rad(-10.0)
            self._assert_flange_matches(joints_rad)


if __name__ == "__main__":
    unittest.main()
