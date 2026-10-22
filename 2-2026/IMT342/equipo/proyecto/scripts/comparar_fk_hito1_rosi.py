#!/usr/bin/env python3
"""Evidencia Gate 2 (FK): modelo propio del Hito 1 contra la referencia ROS-Industrial.

Modelo propio: ros2_ws/src/irb120_hito1/irb120_hito1/kinematics/dh.py (DH clasico,
Bahani 2023) con el TCP de config/tcp.yaml. Referencia: hito2/irb120/rosi_model.py,
transcripcion del xacro oficial abb_irb120_support/irb120_3_58_macro.xacro
(traslaciones + ejes, sin DH). Condiciones alineadas: mismo {B} = base_link,
mismo orden joint_1..joint_6, rad y m, mismo eslabon terminal tool0.

Metricas del protocolo de semana 12:
    e_p = ||p_own - p_ref||_2  [m]
    e_R = acos(clip((tr(R_ref^T R_own) - 1) / 2, -1, 1))  [rad]
(se calcula con atan2(seno, coseno), equivalente y estable cerca de 0).

Casos: pose cero, poses A/B de verify_model, casos G2_* de validation_cases.csv y
100 posturas aleatorias (semilla fija) dentro de los limites del URDF. En tool0
la comparacion es independiente; en gripper_tcp ambos lados usan el MISMO TCP
supuesto (no verificado en el robot), asi que solo comprueba la composicion.

Uso, desde la raiz del proyecto (Python del sistema):
    /usr/bin/python3 scripts/comparar_fk_hito1_rosi.py
    /usr/bin/python3 scripts/comparar_fk_hito1_rosi.py --output /tmp/fk.csv

Es un calculo offline: no abre red ni se conecta al controlador.
"""

import argparse
import csv
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from xml.etree import ElementTree

import numpy as np


PROJECT_DIR = Path(__file__).resolve().parents[1]
PACKAGE_DIR = PROJECT_DIR / "ros2_ws" / "src" / "irb120_hito1"
DH_PATH = PACKAGE_DIR / "irb120_hito1" / "kinematics" / "dh.py"
TCP_CONFIG_PATH = PACKAGE_DIR / "config" / "tcp.yaml"
URDF_PATH = PACKAGE_DIR / "urdf" / "irb120.urdf"
ROSI_MODEL_PATH = PROJECT_DIR / "hito2" / "irb120" / "rosi_model.py"
CASES_PATH = PROJECT_DIR / "docs" / "conexion_abb" / "validation_cases.csv"
DEFAULT_OUTPUT = PROJECT_DIR / "docs" / "conexion_abb" / "evidencias" / "fk_hito1_vs_rosi.csv"

FIELDS = (
    "case_id", "case_type", "q_rad_vector", "base_frame", "tcp_frame", "model_version",
    "reference_version", "position_error_m", "orientation_error_rad", "jacobian_error_fro",
    "rank_threshold", "rank_observed", "acceptance_result", "evidence_link", "notes",
)
# Tolerancias declaradas antes de calcular (mismas que test_tcp_and_reference.py).
POSITION_TOLERANCE_M = 1.0e-9
ORIENTATION_TOLERANCE_RAD = 1.0e-9
RANDOM_SEED = 342
RANDOM_SAMPLES = 100
# Poses A/B de irb120_hito1/verify_model.py [deg].
NAMED_POSES_DEG = (
    ("FK_H1_ZERO", (0.0, 0.0, 0.0, 0.0, 0.0, 0.0), "Pose cero / calibracion ABB (q5=0: singularidad de muneca)"),
    ("FK_H1_A", (30.0, -20.0, 15.0, 40.0, -35.0, 60.0), "Pose A de verify_model"),
    ("FK_H1_B", (90.0, -60.0, 60.0, 90.0, 60.0, 180.0), "Pose B de verify_model"),
)


def _sha256_short(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _urdf_limits_rad(joint_names) -> np.ndarray:
    limits = {}
    for joint in ElementTree.parse(URDF_PATH).getroot().findall("joint"):
        limit = joint.find("limit")
        if limit is not None:
            limits[joint.attrib["name"]] = (float(limit.attrib["lower"]), float(limit.attrib["upper"]))
    return np.array([limits[name] for name in joint_names])


def _g2_cases() -> list[tuple[str, np.ndarray, str]]:
    """Casos G2_* predefinidos en validation_cases.csv (solo su vector q)."""
    cases = []
    with CASES_PATH.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            q = np.array(json.loads(row["q_rad_vector"]), dtype=float)
            cases.append((f"FK_{row['case_id']}", q, f"q de {row['case_id']} ({row['case_type']})"))
    return cases


def build_rows() -> tuple[list[dict], dict]:
    sys.path.insert(0, str(PACKAGE_DIR))
    from irb120_hito1.kinematics import dh  # noqa: E402  (modelo propio del Hito 1)

    rosi = _load_module("rosi_model_reference", ROSI_MODEL_PATH)
    model_version = (
        f"irb120_hito1 dh.py sha256:{_sha256_short(DH_PATH)}; "
        f"tcp.yaml sha256:{_sha256_short(TCP_CONFIG_PATH)} (TCP={dh.GRIPPER_TCP_Z_M:.3f} m no verificado)"
    )
    reference_version = (
        "ROS-Industrial abb_irb120_support irb120_3_58_macro.xacro (kinetic-devel) via "
        f"hito2/irb120/rosi_model.py sha256:{_sha256_short(ROSI_MODEL_PATH)}"
    )
    evidence_link = "scripts/comparar_fk_hito1_rosi.py"
    tcp = dh.tcp_transform(dh.GRIPPER_TCP_Z_M)

    cases = [(case_id, np.deg2rad(q_deg), note) for case_id, q_deg, note in NAMED_POSES_DEG]
    cases += _g2_cases()
    named_count = len(cases)
    limits = _urdf_limits_rad(dh.JOINT_NAMES)
    generator = np.random.default_rng(seed=RANDOM_SEED)
    for index, q in enumerate(generator.uniform(limits[:, 0], limits[:, 1], size=(RANDOM_SAMPLES, 6))):
        cases.append((f"FK_RND_{index:03d}", q, f"Aleatoria uniforme en limites URDF, semilla {RANDOM_SEED}"))

    rows = []
    for number, (case_id, q, note) in enumerate(cases):
        own_tool0 = dh.forward_kinematics(q)
        ref_tool0 = rosi.rosi_forward_kinematics(q)
        frames = [("tool0", own_tool0, ref_tool0, "Referencia independiente en brida")]
        if number < named_count:
            frames.append(
                ("gripper_tcp", own_tool0 @ tcp, ref_tool0 @ tcp,
                 "Ambos con el mismo Tz(TCP) supuesto; solo comprueba la composicion")
            )
        for frame, own, reference, frame_note in frames:
            e_p = dh.position_error_m(reference, own)
            e_r = dh.rotation_error_rad(reference, own)
            passed = e_p < POSITION_TOLERANCE_M and e_r < ORIENTATION_TOLERANCE_RAD
            rows.append(
                {
                    "case_id": case_id if frame == "tool0" else f"{case_id}_TCP",
                    "case_type": "FK",
                    "q_rad_vector": json.dumps([float(value) for value in q]),
                    "base_frame": "base_link",
                    "tcp_frame": frame,
                    "model_version": model_version,
                    "reference_version": reference_version,
                    "position_error_m": f"{e_p:.3e}",
                    "orientation_error_rad": f"{e_r:.3e}",
                    "jacobian_error_fro": "",
                    "rank_threshold": "",
                    "rank_observed": "",
                    "acceptance_result": "PASS" if passed else "FAIL",
                    "evidence_link": evidence_link,
                    "notes": (
                        f"{note}. {frame_note}. Tol e_p<{POSITION_TOLERANCE_M:.0e} m, "
                        f"e_R<{ORIENTATION_TOLERANCE_RAD:.0e} rad. Offline; sin robot"
                    ),
                }
            )
    flange = [row for row in rows if row["tcp_frame"] == "tool0"]
    summary = {
        "tool0_cases": len(flange),
        "tcp_cases": len(rows) - len(flange),
        "max_e_p_tool0_m": max(float(row["position_error_m"]) for row in flange),
        "max_e_R_tool0_rad": max(float(row["orientation_error_rad"]) for row in flange),
        "max_e_p_all_m": max(float(row["position_error_m"]) for row in rows),
        "max_e_R_all_rad": max(float(row["orientation_error_rad"]) for row in rows),
        "failed": sum(row["acceptance_result"] != "PASS" for row in rows),
        "tcp_z_m": dh.GRIPPER_TCP_Z_M,
        "tcp_verified_on_robot": dh.TCP_VERIFIED_ON_ROBOT,
    }
    return rows, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="CSV de salida.")
    arguments = parser.parse_args(argv)

    rows, summary = build_rows()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"CSV: {arguments.output}")
    print(f"Casos en tool0: {summary['tool0_cases']}; casos en gripper_tcp: {summary['tcp_cases']}")
    print(f"max e_p (tool0): {summary['max_e_p_tool0_m']:.3e} m")
    print(f"max e_R (tool0): {summary['max_e_R_tool0_rad']:.3e} rad")
    print(f"max e_p (todos): {summary['max_e_p_all_m']:.3e} m")
    print(f"max e_R (todos): {summary['max_e_R_all_rad']:.3e} rad")
    print(
        f"TCP usado: {summary['tcp_z_m']:.3f} m "
        f"({'verificado' if summary['tcp_verified_on_robot'] else 'NO verificado en el robot'})"
    )
    print("RESULTADO: APROBADO" if summary["failed"] == 0 else f"RESULTADO: {summary['failed']} casos FUERA DE TOLERANCIA")
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
