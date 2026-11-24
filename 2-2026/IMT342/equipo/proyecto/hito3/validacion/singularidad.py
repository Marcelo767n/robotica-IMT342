"""Bloque F: singularidades, escala L, SVD, esfuerzo estático J^T F frente a dinámica completa.

Tarea: twist completo de 6 componentes del TCP (0.150 m) en {B}. Se analiza J (6x6) y J_s = [Jv/L; Jω].
Escala L = 0.58 m = L2 + L3 (0.270 + 0.310 m): máxima palanca hombro→centro de muñeca, del orden de los brazos con que
Jv convierte rad/s en m/s; así las columnas de Jv/L y Jω son comparables (ambas O(1)).
"""

import numpy as np

from . import datos_irc5 as D, graficos, metricas as M, rutas, util
from . import fk as FK
from irb120.dh import JOINT_LIMITS_RAD, TCP_Z_M  # noqa: E402
from irb120.dynamics import gravity_vector, inverse_dynamics  # noqa: E402
from irb120.jacobian import geometric_jacobian, joint_frames  # noqa: E402
from irb120.pieper import DELTA, L2, L3  # noqa: E402
from irb120.dh import MAX_SPEED_RAD_S  # noqa: E402

L_ESCALA = L2 + L3
ETIQ_TWIST = ["vx", "vy", "vz", "ωx", "ωy", "ωz"]
QD = np.array([0.20, -0.30, 0.25, 0.40, -0.35, 0.50])  # rad/s declarado para τ_act
QDD = np.array([0.5, -0.4, 0.6, 1.0, -0.8, 1.2])  # rad/s² declarado
F_PESO = np.array([0.0, 0.0, -10.0, 0.0, 0.0, 0.0])  # N, N·m en el TCP, marco base


def _centro_muneca(q):
    return joint_frames(q)[4][:3, 3]


def q_hombro(q_base):
    """Postura con el centro de muñeca sobre el eje 1: resuelve q3 para q2 dado (radial = 0)."""
    from scipy.optimize import brentq
    q = np.array(q_base, float)

    def radial(q3):
        qq = q.copy()
        qq[2] = q3
        c = _centro_muneca(qq)
        return c[0] * np.cos(qq[0]) + c[1] * np.sin(qq[0])  # componente en el plano del brazo (signo)
    xs = np.linspace(JOINT_LIMITS_RAD[2, 0], JOINT_LIMITS_RAD[2, 1], 400)
    v = [radial(x) for x in xs]
    for a, b, va, vb in zip(xs[:-1], xs[1:], v[:-1], v[1:]):
        if va * vb < 0:
            q[2] = brentq(radial, a, b, xtol=1e-14)
            return q
    raise RuntimeError("no hay q3 dentro de límites con el centro de muñeca sobre el eje 1")


def posturas():
    q_n1 = D.q_rad(FK._fila_modal(D.cargar_postura("N1")))
    reg = q_n1.copy()
    cerca = q_n1.copy(); cerca[4] = np.deg2rad(0.5)
    exacta = q_n1.copy(); exacta[4] = 0.0
    codo = np.array([q_n1[0], 0.35, DELTA - np.pi / 2.0, 0.5, 0.9, 0.3])
    hombro = q_hombro(np.array([q_n1[0], -np.pi / 6.0, 0.0, 0.5, 0.9, 0.3]))
    return {
        "F-reg": ("regular (q de FK-N1)", reg, "ninguna"),
        "F-q5": ("cerca de q5 = 0 (q5 = 0.5°)", cerca, "muñeca"),
        "F-q5-0": ("q5 = 0 exacto", exacta, "muñeca"),
        "F-codo": ("codo extendido (q3 = δ − π/2)", codo, "codo"),
        "F-hombro": ("hombro: centro de muñeca sobre el eje 1", hombro, "hombro"),
    }


def direccion_perdida_analitica(q, tipo):
    """Predicción geométrica independiente de la dirección perdida (para verificar la SVD)."""
    fr = joint_frames(q)
    if tipo == "muñeca":
        z3, z4 = fr[3][:3, 2], fr[4][:3, 2]
        n = np.cross(z3, z4)
        return np.concatenate([np.zeros(3), n / np.linalg.norm(n)]), "parte angular de la dirección perdida ∥ z3×z4 (⟂ al plano de los ejes 4 y 5)"
    s = np.array([0.0, 0.0, 0.29])
    w = fr[4][:3, 3]
    if tipo == "codo":
        d = w - s
        return np.concatenate([d / np.linalg.norm(d), np.zeros(3)]), "v del centro de muñeca a lo largo de hombro→muñeca"
    if tipo == "hombro":
        z1 = fr[1][:3, 2]  # eje de la junta 2
        return np.concatenate([z1, np.zeros(3)]), "v del centro de muñeca a lo largo del eje de la junta 2 (⟂ plano del brazo)"
    return None, ""


def analizar(pid, desc, q, tipo):
    J = geometric_jacobian(q, "tcp")
    Js = M.escalar_jacobiano(J, L_ESCALA)
    r, rs = M.rango_numerico(J), M.rango_numerico(Js)
    u, sig, vt = np.linalg.svd(Js)
    u_min, v_min = u[:, -1], vt[-1]
    # dirección en unidades físicas del twist (v en m/s, ω en rad/s)
    fis = np.concatenate([L_ESCALA * u_min[:3], u_min[3:]])
    fis = fis / np.linalg.norm(fis)
    u_ana, texto = direccion_perdida_analitica(q, tipo)
    # comparación en el espacio de J_s sin centro de muñeca: verifico con J en el centro de muñeca (3x3 de posición para codo/hombro)
    cos_ana = None
    if u_ana is not None:
        # Con el centro de muñeca como punto, J es triangular por bloques (ver jacobian.py): la dirección perdida tiene
        # parte angular n (muñeca) o es [d; 0] (codo, hombro). Se compara con la SVD de J en ese punto.
        u_wc = np.linalg.svd(geometric_jacobian(q, "wrist"))[0][:, -1]
        if tipo == "muñeca":  # u = [a; n] con a = −Jp⁻ᵀ Jω_brazoᵀ n: la parte angular es n
            cos_ana = float(abs(u_wc[3:] @ u_ana[3:]) / np.linalg.norm(u_wc[3:]))
        else:
            cos_ana = float(abs(u_wc @ u_ana))
    # efecto en velocidad articular
    dir_min, dir_max = u[:, -1], u[:, 0]
    qd_min = v_min / sig[-1] if sig[-1] > 0 else np.full(6, np.inf)
    amplif = float(1.0 / sig[-1]) if sig[-1] > 0 else float("inf")
    qd_unit = np.abs(vt[-1]) / max(sig[-1], 1e-300)
    v_alcanzable = float(np.min(MAX_SPEED_RAD_S / np.maximum(qd_unit, 1e-300))) if np.isfinite(amplif) else 0.0
    qd_unit_max = np.abs(vt[0]) / sig[0]
    v_alc_max = float(np.min(MAX_SPEED_RAD_S / qd_unit_max))
    # τ_ext = J^T F frente a τ_act (dinámica completa) en la misma postura
    tau_ext = J.T @ F_PESO
    F_perd = 10.0 * np.linalg.svd(J)[0][:, -1]  # wrench de 10 (N / N·m mezclados, solo por escala) en la dirección menos transmitida
    tau_perd = J.T @ F_perd
    tau_act = inverse_dynamics(q, QD, QDD)
    tau_g = gravity_vector(q)
    return {"id": pid, "descripcion": desc, "tipo": tipo, "q_rad": q, "J": J, "Js": Js, "L": L_ESCALA,
            "sigma_J": r["sigma"], "tau_num_J": r["tau_num"], "rango_J": r["rango"], "kappa_J_mixto": r["kappa"], "sigma_min_J": r["sigma_min"],
            "sigma_Js": rs["sigma"], "tau_num_Js": rs["tau_num"], "rango_Js": rs["rango"], "kappa_Js": rs["kappa"], "sigma_min_Js": rs["sigma_min"],
            "ratio_sigma": float(rs["sigma_min"] / rs["sigma_max"]),
            "dir_perdida_escalada": u_min, "dir_perdida_fisica": fis, "dir_perdida_dominante": ETIQ_TWIST[int(np.argmax(np.abs(fis)))],
            "q_dot_nulo_v_min": v_min, "dir_perdida_analitica": u_ana, "dir_perdida_analitica_texto": texto, "cos_dir_perdida_vs_analitica": cos_ana,
            "amplificacion_qdot_dir_min": amplif, "twist_max_dir_min_escalado": v_alcanzable, "twist_max_dir_max_escalado": v_alc_max,
            "tau_ext_peso": tau_ext, "norma_tau_ext_peso": float(np.linalg.norm(tau_ext)), "norma_tau_ext_dir_perdida": float(np.linalg.norm(tau_perd)),
            "norma_F_dir_perdida": float(np.linalg.norm(F_perd)),
            "tau_act": tau_act, "norma_tau_act": float(np.linalg.norm(tau_act)), "tau_gravedad": tau_g, "norma_tau_g": float(np.linalg.norm(tau_g)),
            "dif_tau_ext_vs_tau_act": float(np.linalg.norm(tau_ext - tau_act)),
            "dif_tau_ext_vs_gravedad": float(np.linalg.norm(tau_ext - tau_g)),
            "finito": bool(np.all(np.isfinite(tau_ext)) and np.all(np.isfinite(tau_act)))}


def barrido_q5(q_base):
    """‖q̇‖ para un twist unitario fijo vs q5 → 0, y ‖J^T F‖ (finito) para el mismo barrido."""
    grados = np.array([30, 10, 3, 1, 0.3, 0.1, 0.03, 0.01, 0.003, 0.001])
    out = []
    V = np.array([0.05, 0.02, -0.03, 0.10, -0.05, 0.08])
    for g in grados:
        q = np.array(q_base, float); q[4] = np.deg2rad(g)
        J = geometric_jacobian(q, "tcp")
        sig = np.linalg.svd(J, compute_uv=False)
        qd = np.linalg.solve(J, V)
        out.append({"q5_deg": float(g), "norma_qdot": float(np.linalg.norm(qd)), "sigma_min": float(sig[-1]), "kappa": float(sig[0] / sig[-1]),
                    "norma_tau_ext": float(np.linalg.norm(J.T @ F_PESO))})
    return out


def sensibilidad_L(q):
    J = geometric_jacobian(q, "tcp")
    filas = []
    for L in (0.1, 0.3, L_ESCALA, 1.0):
        rs = M.rango_numerico(M.escalar_jacobiano(J, L))
        filas.append({"L_m": L, "kappa": rs["kappa"], "sigma_min": rs["sigma_min"], "sigma_max": rs["sigma_max"]})
    return filas


def ejecutar():
    graficos.estilo()
    res = {"L_m": L_ESCALA, "justificacion_L": "L = L2 + L3 = 0.270 + 0.310 m: palanca máxima hombro→centro de muñeca; hace comparables las columnas de Jv/L y Jω.",
           "F_peso": F_PESO, "qd_declarado": QD, "qdd_declarado": QDD, "casos": []}
    filas = []
    for pid, (desc, q, tipo) in posturas().items():
        c = analizar(pid, desc, q, tipo)
        res["casos"].append(c)
        filas.append([pid, desc, util.vec(q), c["rango_J"], c["rango_Js"], c["tau_num_Js"], c["kappa_J_mixto"], c["kappa_Js"], c["sigma_min_Js"], c["ratio_sigma"],
                      util.vec(c["dir_perdida_fisica"], 6), c["dir_perdida_dominante"], c["cos_dir_perdida_vs_analitica"], c["amplificacion_qdot_dir_min"],
                      c["norma_tau_ext_peso"], c["norma_tau_ext_dir_perdida"], c["norma_tau_act"], c["norma_tau_g"], c["dif_tau_ext_vs_tau_act"]])
    util.escribir_csv(rutas.RESULTADOS / "singularidad_svd.csv",
                      ["id", "postura", "q_rad", "rango_numerico_J", "rango_numerico_Js", "tau_num_Js", "kappa_J_mixto", "kappa_Js", "sigma_min_Js", "sigma_min_sobre_max",
                       "dir_perdida_fisica_vx_vy_vz_wx_wy_wz", "componente_dominante", "cos_vs_direccion_analitica", "amplificacion_qdot_1_sobre_sigma_min",
                       "norm_tau_ext_peso_Nm", "norm_tau_ext_wrench_dir_perdida_Nm", "norm_tau_act_Nm", "norm_gravedad_Nm", "norm_tau_ext_menos_tau_act_Nm"], filas)
    util.escribir_csv(rutas.RESULTADOS / "singularidad_sigma.csv", ["id", *[f"sigma{i}_Js" for i in range(1, 7)], *[f"sigma{i}_J" for i in range(1, 7)]],
                      [[c["id"], *c["sigma_Js"], *c["sigma_J"]] for c in res["casos"]])
    n1 = res["casos"][0]["q_rad"]
    res["barrido_q5"] = barrido_q5(n1)
    util.escribir_csv(rutas.RESULTADOS / "singularidad_barrido_q5.csv", ["q5_deg", "norma_qdot_rad_s", "sigma_min_J", "kappa_J", "norma_tau_ext_Nm"],
                      [[b["q5_deg"], b["norma_qdot"], b["sigma_min"], b["kappa"], b["norma_tau_ext"]] for b in res["barrido_q5"]])
    res["sensibilidad_L"] = {c["id"]: sensibilidad_L(c["q_rad"]) for c in res["casos"]}
    res["figuras"] = graficar(res)
    return res


def graficar(res):
    import matplotlib.pyplot as plt
    graficos.estilo()
    fig, ax = plt.subplots(1, 3, figsize=(14, 4.2))
    casos = res["casos"]
    for c in casos:
        ax[0].semilogy(range(1, 7), np.maximum(c["sigma_Js"], 1e-18), "o-", ms=4, label=c["id"])
    ax[0].set(title=f"σᵢ de J_s = [Jv/L; Jω], L = {res['L_m']:.2f} m", xlabel="i", ylabel="σᵢ")
    ax[0].legend(fontsize=7)
    b = res["barrido_q5"]
    q5 = np.array([x["q5_deg"] for x in b])
    ax[1].loglog(q5, [x["norma_qdot"] for x in b], "o-", label="‖q̇‖ para un twist fijo (diverge ~1/sin q5)")
    ax[1].loglog(q5, [x["norma_tau_ext"] for x in b], "s-", label="‖Jᵀ F‖, F = 10 N (finito)")
    ax[1].loglog(q5, [x["sigma_min"] for x in b], "^--", label="σ_min(J)")
    ax[1].invert_xaxis()
    ax[1].set(title="Aproximación a q5 → 0 (postura de FK-N1)", xlabel="q5 [°]", ylabel="magnitud (unidades mixtas)")
    ax[1].legend(fontsize=7)
    x = np.arange(len(casos))
    ax[2].bar(x - 0.27, [c["norma_tau_ext_peso"] for c in casos], 0.27, label="‖Jᵀ F‖, F = 10 N hacia abajo (estático)")
    ax[2].bar(x, [c["norma_tau_act"] for c in casos], 0.27, label="‖τ_act‖ dinámico (q̇, q̈ declarados)")
    ax[2].bar(x + 0.27, [max(c["norma_tau_ext_dir_perdida"], 1e-6) for c in casos], 0.27, label="‖Jᵀ F‖, F en la dirección perdida (≈ σ_min‖F‖)")
    ax[2].set_yscale("log")
    ax[2].set_ylim(1e-7, 1e5)
    ax[2].set_xticks(x, [c["id"] for c in casos], fontsize=7)
    ax[2].set(title="τ_ext = Jᵀ F ≠ τ_act (distinta magnitud física)", ylabel="[N·m]")
    ax[2].legend(fontsize=6)
    return {"singularidad": graficos.guardar(fig, "singularidad_svd_tau.png")}
