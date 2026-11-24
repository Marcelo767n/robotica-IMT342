"""Bloque E: Jacobiano geométrico propio frente a referencia independiente y curva de diferencias finitas.

Convención (declarada): twist V = [v; ω] (lineal arriba), expresado en el marco base {B}; v es la velocidad del punto
indicado (TCP a 0.150 m o tool0), ω la velocidad angular espacial (Ṙ Rᵀ = [ω]×). J propio: hito2/irb120/jacobian.py
(columna i = [z_{i-1} × (p − o_{i-1}); z_{i-1}]).

Referencia INDEPENDIENTE: diferenciación numérica central de la FK de rosi_model (ROS-Industrial). Jv por (p(q+h eᵢ) −
p(q−h eᵢ))/2h; Jω por log(R(q+h eᵢ) R(q−h eᵢ)ᵀ)/2h. Limitación: la referencia comparte con el modelo propio la geometría
nominal ABB; solo es independiente de la fórmula z×(p−o), de la tabla DH y del código del Jacobiano. Además arrastra el error
de truncamiento O(h²) y de redondeo O(ε/h) de la diferenciación, que se caracterizan con la curva h → E(h).
"""

import numpy as np

from . import datos_irc5 as D, graficos, metricas as M, rutas, util
from . import fk as FK
from irb120.dh import JOINT_LIMITS_RAD, TCP_Z_M, forward_kinematics, tcp_transform  # noqa: E402
from irb120.jacobian import geometric_jacobian  # noqa: E402
from irb120.rosi_model import rosi_forward_kinematics  # noqa: E402

QD_TEST = np.array([0.10, -0.20, 0.15, 0.30, -0.25, 0.40])  # rad/s (declarado)
H_FIJO = 1.0e-6
PASOS = [10.0 ** (-k) for k in range(1, 11)]  # h = 1e-1 ... 1e-10 rad


def fk_ref(punto):
    if punto == "tool0":
        return rosi_forward_kinematics
    Ttcp = tcp_transform(TCP_Z_M)
    return lambda q: rosi_forward_kinematics(q) @ Ttcp


def fk_own(punto):
    if punto == "tool0":
        return forward_kinematics
    Ttcp = tcp_transform(TCP_Z_M)
    return lambda q: forward_kinematics(q) @ Ttcp


def posturas():
    q1 = D.q_rad(FK._fila_modal(D.cargar_postura("N1")))
    q2 = D.q_rad(FK._fila_modal(D.cargar_postura("N2")))
    lim = JOINT_LIMITS_RAD
    return {
        "J-N1": ("q de FK-N1 (real S1)", q1),
        "J-N2": ("q de FK-N2 (real S1)", q2),
        "J-N3": ("sintética genérica", np.array([0.3, -0.5, 0.6, -0.8, 1.1, 0.4])),
        "J-N4": ("sintética a 5° de límites alternados", np.where(np.arange(6) % 2 == 0, lim[:, 1] - np.deg2rad(5), lim[:, 0] + np.deg2rad(5))),
    }


def curva_fd(q, punto="tcp"):
    """E_i(h): error por columna ||Jv_propio[:,i] - Jv_FD(h)[:,i]||₂ con FK de referencia y con FK propia."""
    J = geometric_jacobian(q, punto)
    filas = []
    for etiqueta, f in (("rosi", fk_ref(punto)), ("propia", fk_own(punto))):
        for h in PASOS:
            Jfd = M.jacobiano_fd(f, q, h)
            d = J - Jfd
            cols_v = np.linalg.norm(d[:3], axis=0)
            filas.append({"fk": etiqueta, "h": h, "E_cols_v": cols_v, "E_v_fro": float(np.linalg.norm(d[:3], "fro")),
                          "E_w_fro": float(np.linalg.norm(d[3:], "fro"))})
    return filas


def pendiente(h, E):
    return float(np.polyfit(np.log10(h), np.log10(E), 1)[0])


def ejecutar():
    graficos.estilo()
    res = {"qd_test_rad_s": QD_TEST, "h_fijo": H_FIJO, "pasos": PASOS, "puntos": {"tcp": f"TCP a {TCP_Z_M} m sobre z de tool0", "tool0": "origen de tool0"}}
    # curva h -> E (posición de partida: N2, TCP) y h* observado
    q_curva = posturas()["J-N2"][1]
    curva = curva_fd(q_curva, "tcp")
    ros = [c for c in curva if c["fk"] == "rosi"]
    E = np.array([c["E_v_fro"] for c in ros])
    h = np.array([c["h"] for c in ros])
    i_min = int(np.argmin(E))
    # región de truncamiento (h >= 1e-3) y de redondeo (h <= 1e-8): pendientes log-log
    m_trunc = h >= 1e-3
    m_red = h <= 1e-8
    estable = [float(x) for x in h[E <= 3.0 * E[i_min]]]
    res["curva"] = {"punto": "tcp", "q_rad": q_curva, "h_min": float(h[i_min]), "E_min": float(E[i_min]), "pendiente_truncamiento": pendiente(h[m_trunc], E[m_trunc]),
                    "pendiente_redondeo": pendiente(h[m_red], E[m_red]), "region_estable_h": [min(estable), max(estable)],
                    "criterio_estable": "E(h) <= 3·E_min", "autoconvergencia_E_h_min_vs_vecinos": [float(E[max(i_min - 1, 0)]), float(E[i_min]), float(E[min(i_min + 1, len(E) - 1)])],
                    "h_teorico_cbrt_eps": float(np.cbrt(M.EPS))}
    util.escribir_csv(rutas.RESULTADOS / "jacobiano_fd_curva.csv", ["fk_referencia", "h_rad", "E_v_fro_m_rad", "E_w_fro_rad_rad", *[f"E_col{i}_m_rad" for i in range(1, 7)]],
                      [[c["fk"], c["h"], c["E_v_fro"], c["E_w_fro"], *c["E_cols_v"]] for c in curva])
    h_star = float(h[i_min])
    res["h_usado"] = h_star
    # comparación J propio vs referencia en >= 3 posturas, dos puntos
    filas, casos = [], []
    for pid, (desc, q) in posturas().items():
        for punto in ("tcp", "tool0"):
            J_own = geometric_jacobian(q, punto)
            J_h = M.jacobiano_fd(fk_ref(punto), q, h_star)
            J_1e6 = M.jacobiano_fd(fk_ref(punto), q, H_FIJO)
            e_h, e_6 = M.error_jacobiano(J_own, J_h), M.error_jacobiano(J_own, J_1e6)
            # prueba J·qd contra la velocidad del punto por diferencia central en la dirección qd
            eps_t = 1.0e-6  # s
            f = fk_ref(punto)
            Tp, Tm = f(q + eps_t * QD_TEST), f(q - eps_t * QD_TEST)
            v_fd = (Tp[:3, 3] - Tm[:3, 3]) / (2 * eps_t)
            w_fd = M.logaritmo_rotacion(Tp[:3, :3] @ Tm[:3, :3].T) / (2 * eps_t)
            V_own, V_ref = J_own @ QD_TEST, J_h @ QD_TEST
            caso = {"id": pid, "descripcion": desc, "punto": punto, "q_rad": q, "J_own": J_own, "J_ref": J_h,
                    "eJv_h": e_h["eJv_fro"], "eJw_h": e_h["eJw_fro"], "eJv_1e6": e_6["eJv_fro"], "eJw_1e6": e_6["eJw_fro"],
                    "V_own": V_own, "V_ref_J": V_ref, "V_fd_dir": np.concatenate([v_fd, w_fd]),
                    "e_v_own_vs_fd_m_s": float(np.linalg.norm(V_own[:3] - v_fd)), "e_w_own_vs_fd_rad_s": float(np.linalg.norm(V_own[3:] - w_fd)),
                    "e_v_own_vs_Jref_m_s": float(np.linalg.norm(V_own[:3] - V_ref[:3])), "e_w_own_vs_Jref_rad_s": float(np.linalg.norm(V_own[3:] - V_ref[3:])),
                    "norma_Jv": float(np.linalg.norm(J_own[:3], "fro")), "norma_Jw": float(np.linalg.norm(J_own[3:], "fro"))}
            casos.append(caso)
            filas.append([pid, punto, desc, util.vec(q), caso["eJv_h"], caso["eJw_h"], caso["eJv_1e6"], caso["eJw_1e6"], caso["e_v_own_vs_Jref_m_s"],
                          caso["e_w_own_vs_Jref_rad_s"], caso["e_v_own_vs_fd_m_s"], caso["e_w_own_vs_fd_rad_s"], util.vec(V_own[:3]), util.vec(V_own[3:])])
    res["casos"] = casos
    util.escribir_csv(rutas.RESULTADOS / "jacobiano_errores.csv",
                      ["id", "punto", "postura", "q_rad", "eJv_h*_m_rad", "eJw_h*_rad_rad", "eJv_h1e-6_m_rad", "eJw_h1e-6_rad_rad", "e_v_Jqd_vs_Jref_m_s", "e_w_Jqd_vs_Jref_rad_s",
                       "e_v_Jqd_vs_FDdir_m_s", "e_w_Jqd_vs_FDdir_rad_s", "v_Jqd_m_s", "w_Jqd_rad_s"], filas)
    res["figuras"] = graficar(res, curva)
    return res


def graficar(res, curva):
    import matplotlib.pyplot as plt
    graficos.estilo()
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    ros = [c for c in curva if c["fk"] == "rosi"]
    pro = [c for c in curva if c["fk"] == "propia"]
    h = np.array([c["h"] for c in ros])
    for i in range(6):
        ax[0].loglog(h, np.maximum([c["E_cols_v"][i] for c in ros], 1e-17), "o-", ms=3, lw=1, label=f"columna {i + 1}")
    ax[0].loglog(h, np.maximum([c["E_v_fro"] for c in ros], 1e-17), "k-s", ms=4, lw=2, label="‖·‖_F de Jv")
    hh = np.array([1e-3, 1e-1])
    Ec = res["curva"]
    ax[0].loglog(hh, [c["E_v_fro"] for c in ros][2] * (hh / 1e-3) ** 2, "k:", lw=0.9, label="pendiente +2 (truncamiento)")
    hh2 = np.array([1e-10, 1e-8])
    ax[0].loglog(hh2, [c["E_v_fro"] for c in ros][8] * (1e-9 / hh2), "k--", lw=0.9, label="pendiente −1 (redondeo)")
    ax[0].axvline(Ec["h_min"], color="#c0504d", ls="--", lw=1)
    ax[0].text(Ec["h_min"] * 1.3, 1e-14, f"h* = {Ec['h_min']:.0e}", color="#c0504d", fontsize=8)
    ax[0].set(title="Visual 4: error de Jv por diferencias finitas (FK de referencia)", xlabel="paso h [rad]", ylabel="E_i(h) = ‖Jv,propio − Jv,FD‖ [m/rad]")
    ax[0].legend(fontsize=7, ncol=2)
    ax[1].loglog(h, np.maximum([c["E_v_fro"] for c in ros], 1e-17), "k-s", ms=4, label="Jv, FD sobre FK rosi (independiente)")
    ax[1].loglog(h, np.maximum([c["E_v_fro"] for c in pro], 1e-17), "-o", ms=4, label="Jv, FD sobre FK propia (autoconsistencia)")
    ax[1].loglog(h, np.maximum([c["E_w_fro"] for c in ros], 1e-17), "--^", ms=4, label="Jω, FD sobre FK rosi [rad/rad]")
    ax[1].set(title="Jv y Jω, referencia independiente vs autoconsistencia", xlabel="paso h [rad]", ylabel="error de Frobenius")
    ax[1].legend(fontsize=7)
    fig1 = graficos.guardar(fig, "jacobiano_fd_curva_visual4.png")
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    etiquetas = [f"{c['id']}\n{c['punto']}" for c in res["casos"]]
    x = np.arange(len(etiquetas))
    ax.bar(x - 0.2, [max(c["eJv_h"], 1e-17) for c in res["casos"]], 0.4, label="eJv [m/rad]")
    ax.bar(x + 0.2, [max(c["eJw_h"], 1e-17) for c in res["casos"]], 0.4, label="eJω [rad/rad]")
    ax.set_yscale("log")
    ax.set_xticks(x, etiquetas, fontsize=7)
    ax.set(title=f"J propio vs referencia (h = {res['h_usado']:.0e}); métricas separadas", ylabel="norma de Frobenius")
    ax.legend()
    fig2 = graficos.guardar(fig, "jacobiano_errores_separados.png")
    return {"fd_curva": fig1, "jacobiano_errores": fig2}
