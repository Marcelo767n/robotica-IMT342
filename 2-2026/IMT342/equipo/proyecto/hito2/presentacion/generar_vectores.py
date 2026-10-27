"""Genera casos de referencia con el paquete Python para verificar la traduccion JavaScript (irb120.js).

Uso (desde hito2/):  python presentacion/generar_vectores.py   ->   presentacion/vectores.json
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from irb120 import dynamics  # noqa: E402
from irb120.dh import HOME_Q, JOINT_LIMITS_RAD, forward_kinematics_tcp  # noqa: E402
from irb120.dynamics_1r import shoulder_model  # noqa: E402
from irb120.jacobian import geometric_jacobian, rank_analysis  # noqa: E402
from irb120.lspb import default_limits, plan_lspb  # noqa: E402
from irb120.pieper import analyze_pose, rank_candidates  # noqa: E402
from irb120.transforms import pose_from_xyz_rpy_deg  # noqa: E402


def nan_none(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else x


rng = np.random.default_rng(2026)
poses = [(0.40, 0.10, 0.35, 0, 180, 0), (0.45, -0.10, 0.60, 90, 90, 0), (0.40, 0.20, 0.60, 0, 135, 0),
         (0.90, 0.0, 0.40, 0, 90, 0), (-0.055, -0.253, 0.343, 93.5, -4.4, -11.9)]
for _ in range(60):
    q = rng.uniform(JOINT_LIMITS_RAD[:, 0], JOINT_LIMITS_RAD[:, 1])
    poses.append(forward_kinematics_tcp(q).tolist())
for _ in range(40):
    poses.append((*rng.uniform([-0.6, -0.6, -0.1], [0.7, 0.6, 0.9]), *rng.uniform(-180, 180, 3)))

cases = []
for spec in poses:
    T = np.asarray(spec, float) if isinstance(spec, list) else pose_from_xyz_rpy_deg(*spec)
    rep = analyze_pose(T, HOME_Q)
    dec = rank_candidates(rep, HOME_Q)
    case = {"T": T.tolist(), "verdict_reachable": rep.reachable, "geo": rep.geometrically_reachable,
            "cands": [{"real": c.real, "qraw": None if c.q_raw is None else list(c.q_raw),
                       "q": None if c.q is None else list(c.q), "out": list(c.out_of_limits), "wrist": c.wrist,
                       "singular": c.singular_wrist} for c in rep.candidates],
            "rank": [{"rank": d.rank, "sigma": nan_none(float(d.sigma_min)), "margin": nan_none(float(d.limit_margin_deg)),
                      "cost": nan_none(float(d.weighted_cost)), "tf": nan_none(float(d.lspb_tf))} for d in dec]}
    chosen = next((d.candidate for d in dec if d.rank == 1), None)
    if chosen is not None:
        qf = np.array(chosen.q)
        tr = plan_lspb(HOME_Q, qf, *default_limits())
        ts = [0.0, tr.tb / 2, tr.tf / 2, tr.tf - tr.tb / 3, tr.tf, tr.tf + 0.1]
        samples = [[list(map(float, v)) for v in tr.sample(t)] for t in ts]
        m = shoulder_model(0.5 * (HOME_Q + qf))
        qm, qdm, qddm = tr.sample(tr.tf * 0.37)
        J = geometric_jacobian(qf)
        case.update({"qf": qf.tolist(), "tf": tr.tf, "tb": tr.tb, "ts": ts, "samples": samples,
                     "sv": rank_analysis(J).singular_values.tolist(), "J": J.tolist(),
                     "model": [m.mass_kg, m.lc_m, m.inertia_com_kg_m2, m.inertia_kg_m2, m.phi0_rad],
                     "tau_full_q": [qm.tolist(), qdm.tolist(), qddm.tolist()],
                     "tau_full": dynamics.inverse_dynamics(qm, qdm, qddm).tolist()})
    cases.append(case)

out = Path(__file__).with_name("vectores.json")
out.write_text(json.dumps(cases))
print(f"{len(cases)} casos -> {out}")
