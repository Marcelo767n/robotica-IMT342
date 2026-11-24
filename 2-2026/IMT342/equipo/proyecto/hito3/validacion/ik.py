"""Bloque D: validación de la cinemática inversa (Pieper propia) con referencia numérica independiente.

* IK propia: hito2/irb120/pieper.py, `enumerate_candidates` devuelve SIEMPRE las 8 ramas (brazo × codo × muñeca).
* Residuos por rama: FK propia (DH) y FK de referencia independiente (rosi_model, ROS-Industrial).
* IK de referencia independiente: Levenberg-Marquardt/DLS numérico sobre la FK de rosi_model (Jacobiano por
  diferencias finitas de ESA FK, sin usar el J propio). Semillas, tolerancia, iteraciones y timeout registrados.
* T_d es la pose de la brida (tool0) obtenida de la FK de q documentadas; NUNCA se mezcla brida con TCP.
"""

import time

import numpy as np

from . import datos_irc5 as D, graficos, metricas as M, rutas, util
from . import fk as FK
from irb120.dh import JOINT_LIMITS_RAD, forward_kinematics  # noqa: E402
from irb120.jacobian import geometric_jacobian  # noqa: E402
from irb120.pieper import enumerate_candidates  # noqa: E402
from irb120.rosi_model import rosi_forward_kinematics  # noqa: E402

TOL_RESIDUO = FK.CRIBADO_SINTETICO  # e_p <= 1e-6 m, e_R <= 1e-5 rad (exploratorio, pendiente de aprobación)
KAPPA_SINGULAR = 1.0e8  # κ(J_s) por encima del cual la rama se marca numéricamente singular (declarado)
L_ESCALA = 0.58  # m, ver singularidad.py

DLS = {"metodo": "Levenberg-Marquardt/DLS sobre rosi_forward_kinematics (tool0)", "lambda": 1.0e-3, "tol_p_m": 1.0e-9, "tol_R_rad": 1.0e-9,
       "max_iter": 200, "timeout_s": 2.0, "paso_max_rad": 0.5, "h_fd_rad": 1.0e-6, "peso_orientacion": 0.5,
       "limites": "no impuestos durante la iteración; se verifican a posteriori", "semillas_aleatorias": 24, "rng_seed": 12345}


def _error_pose6(T_d, T, w):
    return np.concatenate([T_d[:3, 3] - T[:3, 3], w * M.logaritmo_rotacion(T_d[:3, :3] @ T[:3, :3].T)])


def ik_dls(T_d, q0):
    """Un intento de IK numérica. Devuelve dict con q, estado, iteraciones, tiempo y residuos."""
    q = np.asarray(q0, float).copy()
    w, lam, h = DLS["peso_orientacion"], DLS["lambda"], DLS["h_fd_rad"]
    t0 = time.perf_counter()
    estado, it = "max_iter", 0
    for it in range(1, DLS["max_iter"] + 1):
        T = rosi_forward_kinematics(q)
        e = _error_pose6(T_d, T, w)
        ep, eR = np.linalg.norm(e[:3]), np.linalg.norm(e[3:]) / w
        if ep < DLS["tol_p_m"] and eR < DLS["tol_R_rad"]:
            estado = "convergido"
            break
        if time.perf_counter() - t0 > DLS["timeout_s"]:
            estado = "timeout"
            break
        J = M.jacobiano_fd(rosi_forward_kinematics, q, h)
        J[3:] *= w
        dq = J.T @ np.linalg.solve(J @ J.T + lam ** 2 * np.eye(6), e)
        n = np.linalg.norm(dq)
        if n > DLS["paso_max_rad"]:
            dq *= DLS["paso_max_rad"] / n
        q = q + dq
    T = rosi_forward_kinematics(q)
    e = M.error_pose(T, T_d)
    return {"q": q, "estado": estado, "iteraciones": it, "tiempo_s": time.perf_counter() - t0, "e_p_m": e["e_p_m"], "e_R_rad": e["e_R_atan2_rad"]}


def envolver(q):
    return (np.asarray(q, float) + np.pi) % (2 * np.pi) - np.pi


def semillas(candidatos, q_doc):
    rng = np.random.default_rng(DLS["rng_seed"])
    lista = [("cero", np.zeros(6)), ("q_doc+0.3", np.asarray(q_doc) + 0.3)]
    for c in candidatos:
        if c.real:
            lista.append((f"rama{c.branch}+ruido0.2", np.array(c.q_raw) + rng.normal(0, 0.2, 6)))
    for k in range(DLS["semillas_aleatorias"]):
        lista.append((f"aleatoria{k + 1}", rng.uniform(JOINT_LIMITS_RAD[:, 0], JOINT_LIMITS_RAD[:, 1])))
    return lista


def clasificar(cand, e_p, e_R, kappa, ambiguedad_limite):
    if not cand.real:
        return "sin solución: inexistente en el modelo (|cos θ3| > 1: pose fuera del alcance de la rama)"
    if cand.singular_wrist or kappa > KAPPA_SINGULAR:
        return "numéricamente singular (q4 y q6 solo determinados en suma)"
    if e_p > TOL_RESIDUO["e_p_m"] or e_R > TOL_RESIDUO["e_R_rad"]:
        return "no válida (residuo FK excede el cribado exploratorio)"
    if cand.q is None:
        # fuera de límites: ¿por cuánto?
        return "no válida (viola límites de junta " + ",".join(f"J{j}" for j in cand.out_of_limits) + ")"
    q = np.array(cand.q)
    margen = np.minimum(q - JOINT_LIMITS_RAD[:, 0], JOINT_LIMITS_RAD[:, 1] - q).min()
    if margen < ambiguedad_limite:
        return "indeterminada por datos (límite de junta: las fuentes difieren en %.1e rad)" % ambiguedad_limite
    return "válida en modelo"


POSES = {}


def definir_poses():
    n1, n2 = D.cargar_postura("N1"), D.cargar_postura("N2")
    q_n1 = D.q_rad(FK._fila_modal(n1))
    q_n2 = D.q_rad(FK._fila_modal(n2))
    d2r = np.deg2rad
    return {
        "IK-1": {"q_doc": q_n1, "fuente": "FK propia de q de FK-N1 (postura real S1 de la sesión 1)", "tipo": "regular"},
        "IK-2": {"q_doc": q_n2, "fuente": "FK propia de q de FK-N2 (postura real S1 de la sesión 2, q5≈89.7°)", "tipo": "regular"},
        "IK-3": {"q_doc": d2r([10.0, 30.0, -10.0, 20.0, 0.5, 40.0]), "fuente": "FK propia de q sintética con q5 = 0.5° (cerca de singularidad de muñeca)", "tipo": "cerca singularidad"},
        "IK-4": {"q_doc": d2r([10.0, 30.0, -10.0, 20.0, 0.0, 40.0]), "fuente": "FK propia de q sintética con q5 = 0 exacto (singularidad de muñeca)", "tipo": "singular"},
        "IK-5": {"q_doc": d2r([10.0, 30.0, -10.0, 20.0, 30.0, 40.0]), "fuente": "FK propia de q sintética desplazada +0.8 m en x_base (fuera del alcance)", "tipo": "inalcanzable", "desplazar_x_m": 0.8},
    }


def resolver_pose(pid, info, ambiguedad_limite):
    q_doc = info["q_doc"]
    T_d = forward_kinematics(q_doc)
    if "desplazar_x_m" in info:
        T_d = T_d.copy()
        T_d[0, 3] += info["desplazar_x_m"]
    cands = enumerate_candidates(T_d, q_doc)
    filas, ramas = [], []
    for c in cands:
        if c.real:
            q_eval = np.array(c.q if c.q is not None else c.q_raw)
            T_own, T_ref = forward_kinematics(q_eval), rosi_forward_kinematics(q_eval)
            e_own, e_ref = M.error_pose(T_own, T_d), M.error_pose(T_ref, T_d)
            Js = M.escalar_jacobiano(geometric_jacobian(q_eval, "tool0"), L_ESCALA)
            kappa = M.rango_numerico(Js)["kappa"]
            dentro = c.q is not None
            marg = float(np.minimum(q_eval - JOINT_LIMITS_RAD[:, 0], JOINT_LIMITS_RAD[:, 1] - q_eval).min())
            igual_doc = bool(np.allclose(M.diferencia_angular_envuelta(q_eval, q_doc), 0, atol=1e-6)) if "desplazar_x_m" not in info else False
        else:
            q_eval, e_own, e_ref, kappa, dentro, marg, igual_doc = None, {"e_p_m": float("nan"), "e_R_rad": float("nan"), "e_R_atan2_rad": float("nan")}, {"e_p_m": float("nan"), "e_R_rad": float("nan"), "e_R_atan2_rad": float("nan")}, float("nan"), False, float("nan"), False
        estado = clasificar(c, e_own["e_p_m"] if c.real else 0, e_own["e_R_rad"] if c.real else 0, kappa if c.real else 0, ambiguedad_limite)
        # el residuo exigido en la clasificación es el MAYOR entre FK propia y de referencia
        if c.real:
            peor_p, peor_R = max(e_own["e_p_m"], e_ref["e_p_m"]), max(e_own["e_R_rad"], e_ref["e_R_rad"])
            estado = clasificar(c, peor_p, peor_R, kappa, ambiguedad_limite)
        ramas.append({"pose": pid, "rama": c.branch, "brazo": c.arm, "codo": c.elbow, "muneca": c.wrist, "real": c.real,
                      "q_rad": q_eval, "q_raw_rad": c.q_raw, "dentro_limites": dentro, "fuera_de_limites": list(c.out_of_limits),
                      "margen_limite_rad": marg, "cos_codo": c.cos_elbow, "muneca_singular": c.singular_wrist,
                      "e_p_propia_m": e_own["e_p_m"], "e_R_propia_rad": e_own["e_R_rad"], "e_p_ref_m": e_ref["e_p_m"], "e_R_ref_rad": e_ref["e_R_rad"],
                      "kappa_Js": kappa, "estado": estado, "es_q_doc": igual_doc})
        filas.append(ramas[-1])
    # IK numérica de referencia
    intentos = []
    for nombre, q0 in semillas(cands, q_doc):
        r = ik_dls(T_d, q0)
        r["semilla"] = nombre
        r["q0"] = q0
        intentos.append(r)
    conv = [r for r in intentos if r["estado"] == "convergido"]
    unicas = []
    for r in conv:
        qw = envolver(r["q"])
        for u in unicas:
            if np.abs(M.diferencia_angular_envuelta(qw, u["qw"])).max() < 1e-5:
                u["n"] += 1
                break
        else:
            unicas.append({"qw": qw, "n": 1, "r": r})
    # emparejar con ramas reales propias (módulo 2π). En q5 = 0 (muñeca singular) q4 y q6 no son únicos: se compara
    # la suma q4+q6 (mod 2π) y el resto de las juntas (familia de soluciones).
    def _coincide(qw, b):
        if b["q_raw_rad"] is None:
            return False
        if b["muneca_singular"]:
            d = M.diferencia_angular_envuelta(qw, b["q_raw_rad"])
            return bool(np.abs(d[[0, 1, 2, 4]]).max() < 1e-5 and abs(M.diferencia_angular_envuelta(qw[3] + qw[5], b["q_raw_rad"][3] + b["q_raw_rad"][5])) < 1e-5)
        return bool(np.abs(M.diferencia_angular_envuelta(qw, b["q_raw_rad"])).max() < 1e-5)

    no_emp, emparejadas = [], 0
    for u in unicas:
        if any(b["real"] and _coincide(u["qw"], b) for b in ramas):
            emparejadas += 1
        else:
            no_emp.append(u)
    ramas_cubiertas = []
    for b in ramas:
        b["encontrada_por_DLS"] = bool(b["real"] and any(_coincide(u["qw"], b) for u in unicas))
        if b["real"]:
            ramas_cubiertas.append(b["encontrada_por_DLS"])
    resumen = {"pose": pid, "n_intentos": len(intentos), "n_convergidos": len(conv), "n_soluciones_distintas": len(unicas),
               "n_emparejadas_con_ramas_propias": emparejadas, "n_sin_rama_propia": len(no_emp),
               "ramas_propias_reales": int(sum(b["real"] for b in ramas)), "ramas_reales_halladas_por_DLS": int(sum(ramas_cubiertas)),
               "mejor_residuo_sin_convergencia": float(min((r["e_p_m"] for r in intentos), default=float("nan"))) if not conv else None,
               "iteraciones_mediana": float(np.median([r["iteraciones"] for r in conv])) if conv else None,
               "tiempo_total_s": float(sum(r["tiempo_s"] for r in intentos)),
               "sin_rama_propia_q_wrapped": [u["qw"] for u in no_emp],
               "sumas_q4_q6_familia": sorted({round(float(envolver(u["qw"][3] + u["qw"][5])), 6) for u in unicas if abs(u["qw"][4]) < 1e-6}) if info["tipo"] == "singular" else None,
               "n_familia_singular_q4_distintos": int(sum(1 for u in unicas if abs(u["qw"][4]) < 1e-6)) if info["tipo"] == "singular" else None,
               "estado_numerico": ("sin solución encontrada por DLS (no demuestra inexistencia)" if not conv else "soluciones numéricas halladas")}
    return T_d, ramas, intentos, resumen


def ejecutar():
    graficos.estilo()
    lim = FK.limites_documentados()
    ambig = lim["max_dif_dh_rosi_rad"]
    res = {"tol_residuo": TOL_RESIDUO, "dls": DLS, "ambiguedad_limite_rad": ambig, "kappa_singular": KAPPA_SINGULAR, "poses": {}}
    filas_ramas, filas_dls = [], []
    for pid, info in definir_poses().items():
        T_d, ramas, intentos, resumen = resolver_pose(pid, info, ambig)
        res["poses"][pid] = {"fuente": info["fuente"], "tipo": info["tipo"], "q_doc_rad": info["q_doc"], "T_d": T_d, "ramas": ramas, "resumen_dls": resumen}
        for b in ramas:
            filas_ramas.append([pid, b["rama"], b["brazo"], b["codo"], b["muneca"], b["real"], b["q_rad"] if b["q_rad"] is not None else "",
                                b["dentro_limites"], ",".join(map(str, b["fuera_de_limites"])), b["margen_limite_rad"], b["e_p_propia_m"], b["e_R_propia_rad"],
                                b["e_p_ref_m"], b["e_R_ref_rad"], b["kappa_Js"], b["encontrada_por_DLS"], b["es_q_doc"], b["estado"]])
        for r in intentos:
            filas_dls.append([pid, r["semilla"], r["q0"], r["estado"], r["iteraciones"], r["tiempo_s"], r["e_p_m"], r["e_R_rad"], r["q"]])
    util.escribir_csv(rutas.RESULTADOS / "ik_ramas.csv",
                      ["pose", "rama", "brazo", "codo", "muneca", "real", "q_rad", "dentro_limites", "juntas_fuera_de_limites", "margen_limite_rad",
                       "e_p_propia_m", "e_R_propia_rad", "e_p_ref_rosi_m", "e_R_ref_rosi_rad", "kappa_Js", "encontrada_por_DLS", "es_q_documentada", "estado"], filas_ramas)
    util.escribir_csv(rutas.RESULTADOS / "ik_dls_intentos.csv", ["pose", "semilla", "q0_rad", "estado", "iteraciones", "tiempo_s", "e_p_m", "e_R_rad", "q_final_rad"], filas_dls)
    res["figuras"] = graficar(res)
    return res


def graficar(res):
    import matplotlib.pyplot as plt
    graficos.estilo()
    poses = [p for p in res["poses"] if res["poses"][p]["tipo"] != "inalcanzable"]
    fig, axs = plt.subplots(1, len(poses), figsize=(3.6 * len(poses), 3.8), sharey=True)
    colores = {"válida": "#4f8a3c", "no válida": "#c0504d", "numéricamente": "#e08a00", "indeterminada": "#7b4f9d", "sin solución": "#999999"}
    for ax, pid in zip(np.atleast_1d(axs), poses):
        ramas = res["poses"][pid]["ramas"]
        for b in ramas:
            c = next((v for k, v in colores.items() if b["estado"].startswith(k)), "#555")
            if b["real"]:
                ax.bar(b["rama"] - 0.2, max(b["e_p_propia_m"], 1e-18), 0.4, color=c)
                ax.bar(b["rama"] + 0.2, max(b["e_p_ref_m"], 1e-18), 0.4, color=c, alpha=0.45, hatch="//")
            else:
                ax.text(b["rama"], 1e-17, "×", ha="center", color="#999")
        ax.set_yscale("log")
        ax.set(title=f"{pid} ({res['poses'][pid]['tipo']})", xlabel="rama k (1..8)")
        ax.axhline(1e-6, color="k", ls="--", lw=0.8)
        ax.set_xticks(range(1, 9))
    np.atleast_1d(axs)[0].set_ylabel("e_p [m]  (sólido: FK propia; rayado: FK rosi)")
    handles = [plt.Rectangle((0, 0), 1, 1, color=v) for v in colores.values()]
    fig.legend(handles, list(colores.keys()), loc="outside lower center", ncol=5, fontsize=7)
    return {"ik_ramas": graficos.guardar(fig, "ik_ramas_residuos.png")}
