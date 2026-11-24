"""Bloque C: validación de cinemática directa (FK-N1, FK-N2, FK-N3, FK-L, FK-D-TCP, FK-D-ORD) y diagnóstico de FUERA.

Convenciones (declaradas, ver manifiestos):
  * FK propia: hito2/irb120/dh.py, DH clásica, base_link -> tool0 (brida). q en rad, longitudes en m.
  * Referencia FÍSICA: pose del IRC5 en `Base`, `tool0`, `wobj0` leída por RWS (nivel S1).
    posición mm -> m; cuaternión (w, x, y, z) -> R. NUNCA se compara brida contra TCP salvo en FK-D-TCP (intencional).
  * Referencia OFFLINE independiente: hito2/irb120/rosi_model.py (xacro oficial de ROS-Industrial; traslaciones +
    ejes, sin DH). Independiente de la TABLA DH, pero no de la geometría nominal ABB: no demuestra exactitud física.
"""

import json
import math
from collections import Counter

import numpy as np

from . import datos_irc5 as D
from . import graficos, metricas as M, rutas, util
from irb120.dh import (DH_PARAMETERS, JOINT_LIMITS_DEG, JOINT_LIMITS_RAD, TCP_Z_M, forward_kinematics,  # noqa: E402
                       tcp_transform)
from irb120.jacobian import geometric_jacobian  # noqa: E402
from irb120.rosi_model import ROSI_LIMITS_RAD, rosi_forward_kinematics  # noqa: E402
from irb120.urdf_chain import chain_transform  # noqa: E402

CRITERIO_ESTRICTO_PROYECTO = {"e_p_m": 1.0e-6, "e_R_rad": 1.0e-6,
                              "estado": "criterio numérico estricto del proyecto (nodo validacion_fk); propuesto, NO aprobado"}
CRIBADO_SINTETICO = {"e_p_m": 1.0e-6, "e_R_rad": 1.0e-5, "estado": "cribado exploratorio sintético del documento W14-S02; solo modelo artificial, pendiente de aprobación"}


def T_controlador(fila):
    p, qwxyz = D.pose_controlador(fila)
    T = np.eye(4)
    T[:3, :3] = M.cuaternion_wxyz_a_R(qwxyz)
    T[:3, 3] = p
    return T


def semi_resolucion_xyz_m(xyz_mm):
    """Semi-resolución por eje [m] si la posición se reporta con 7 cifras significativas (observado en los registros S1)."""
    v = np.abs(np.asarray(xyz_mm, float))
    v = np.where(v == 0, 1.0, v)
    return 0.5 * 10.0 ** (np.floor(np.log10(v)) - 6) / 1000.0


def cuantizacion(q_rad_vec, xyz_mm):
    """Cotas de redondeo de los datos del IRC5 propagadas a la pose (declaradas, ver tolerancias.py).

    q: RWS entrega float32 -> semi-ulp float32 de cada q_i. xyz: 7 cifras significativas (4 decimales en mm para |v|>=100 mm; 6 decimales si |v|<10 mm).
    cuaternión: 7 cifras significativas -> ±5e-8 por componente (cota).
    """
    q_deg = np.rad2deg(q_rad_vec)
    semi = np.array([np.spacing(np.float32(abs(v))) / 2.0 for v in q_deg])  # grados
    semi_rad = np.deg2rad(semi)
    J = geometric_jacobian(q_rad_vec, "tool0")
    cota_xyz = float(np.linalg.norm(semi_resolucion_xyz_m(xyz_mm)))
    cota_p = float(np.sum(np.linalg.norm(J[:3], axis=0) * semi_rad) + cota_xyz)
    cota_R = float(np.sum(np.linalg.norm(J[3:], axis=0) * semi_rad) + 2.0 * math.sqrt(4) * 5.0e-8)
    return {"semi_ulp_q_deg": semi.tolist(), "cota_e_p_m": cota_p, "cota_e_R_rad": cota_R,
            "cota_e_p_solo_xyz_m": cota_xyz}


def _fila_modal(filas):
    claves = Counter((tuple(f[f"qa{i}_deg"] for i in range(1, 7)), f["x_mm"], f["y_mm"], f["z_mm"], f["qw"], f["qx"], f["qy"], f["qz"]) for f in filas)
    mejor, _ = claves.most_common(1)[0]
    for f in filas:
        if (tuple(f[f"qa{i}_deg"] for i in range(1, 7)), f["x_mm"], f["y_mm"], f["z_mm"], f["qw"], f["qx"], f["qy"], f["qz"]) == mejor:
            return f


def _evaluar_fila(f):
    q = D.q_rad(f)
    T_own = forward_kinematics(q)
    T_ref = T_controlador(f)
    T_rosi = rosi_forward_kinematics(q)
    e = M.error_pose(T_own, T_ref)
    e_rc = M.error_pose(T_rosi, T_ref)
    e_or = M.error_pose(T_own, T_rosi)
    return q, T_own, T_ref, T_rosi, e, e_rc, e_or


def comparar_real(nombre, filas):
    """FK-N1/FK-N2 con datos reales S1: todas las muestras estacionarias de una postura."""
    modal = _fila_modal(filas)
    ep, eR, eRa, ep_rc, eR_rc, ep_or, ortho_o, ortho_r, det_o, det_r = ([] for _ in range(10))
    detalle = []
    for f in filas:
        q, T_own, T_ref, T_rosi, e, e_rc, e_or = _evaluar_fila(f)
        ep.append(e["e_p_m"]); eR.append(e["e_R_rad"]); eRa.append(e["e_R_atan2_rad"])
        ep_rc.append(e_rc["e_p_m"]); eR_rc.append(e_rc["e_R_atan2_rad"]); ep_or.append(e_or["e_p_m"])
        co, cr = M.comprobar_rotacion(T_own[:3, :3]), M.comprobar_rotacion(T_ref[:3, :3])
        ortho_o.append(co["ortogonalidad_max"]); det_o.append(abs(co["det_menos_1"]))
        ortho_r.append(cr["ortogonalidad_max"]); det_r.append(abs(cr["det_menos_1"]))
        detalle.append([nombre, f["archivo"], f["linea"], f["seq"], f["received_at_utc"], f["status_registro"], f["window_ms"],
                        *[f[f"qa{i}_deg"] for i in range(1, 7)], e["e_p_m"], e["e_R_rad"], e["e_R_atan2_rad"],
                        e_rc["e_p_m"], e_rc["e_R_atan2_rad"], e_or["e_p_m"],
                        abs(e["e_p_m"] * 1000.0 - f["e_p_mm_registro"])])
    q, T_own, T_ref, T_rosi, e, e_rc, e_or = _evaluar_fila(modal)
    cuant = cuantizacion(q, [modal['x_mm'], modal['y_mm'], modal['z_mm']])
    ep_a, eR_a = np.array(ep), np.array(eR)
    pasa = lambda c: int(np.sum((ep_a <= c["e_p_m"]) & (np.array(eRa) <= c["e_R_rad"])))  # noqa: E731
    resultado = {
        "caso": f"FK-{nombre}", "n_muestras": len(filas),
        "sesion_archivo": filas[0]["archivo"], "linea_representativa": modal["linea"], "seq_representativa": modal["seq"],
        "t_representativa_utc": modal["received_at_utc"], "stamp_representativo": [modal["stamp_sec"], modal["stamp_nanosec"]],
        "q_deg": [modal[f"qa{i}_deg"] for i in range(1, 7)], "q_rad": q,
        "p_own_m": T_own[:3, 3], "p_ref_m": T_ref[:3, 3],
        "R_own": T_own[:3, :3], "R_ref": T_ref[:3, :3],
        "quat_own_wxyz": M.R_a_cuaternion_wxyz(T_own[:3, :3]), "quat_ref_wxyz_registrado": [modal["qw"], modal["qx"], modal["qy"], modal["qz"]],
        "e_p_m_rep": e["e_p_m"], "e_R_rad_rep": e["e_R_rad"], "e_R_atan2_rad_rep": e["e_R_atan2_rad"],
        "estadistica_e_p_m": M.resumen_estadistico(ep), "estadistica_e_R_rad": M.resumen_estadistico(eR),
        "estadistica_e_R_atan2_rad": M.resumen_estadistico(eRa),
        "rosi_vs_controlador": {"e_p_m": M.resumen_estadistico(ep_rc), "e_R_atan2_rad": M.resumen_estadistico(eR_rc)},
        "propia_vs_rosi_e_p_m": M.resumen_estadistico(ep_or),
        "ortogonalidad_max_R_own": float(max(ortho_o)), "ortogonalidad_max_R_ref": float(max(ortho_r)),
        "det_dev_max_R_own": float(max(det_o)), "det_dev_max_R_ref": float(max(det_r)),
        "n_poses_controlador_distintas": len({(f["x_mm"], f["y_mm"], f["z_mm"], f["qw"], f["qx"], f["qy"], f["qz"]) for f in filas}),
        "n_estados_registro": dict(Counter(f["status_registro"] for f in filas)),
        "n_dentro_criterio_estricto_proyecto": pasa(CRITERIO_ESTRICTO_PROYECTO),
        "cuantizacion": cuant,
        "razon_e_p_max_sobre_cota_cuantizacion": float(ep_a.max() / cuant["cota_e_p_m"]),
        "razon_e_R_mediana_sobre_cota_cuantizacion": float(np.median(eRa) / cuant["cota_e_R_rad"]),
        "max_dif_vs_registro_hito1_mm": float(max(r[-1] for r in detalle)),
        "ventana_ms": M.resumen_estadistico([f["window_ms"] for f in filas]),
        "t_primera_utc": min(f["received_at_utc"] for f in filas), "t_ultima_utc": max(f["received_at_utc"] for f in filas),
    }
    return resultado, detalle


COLS_DETALLE = (["caso", "archivo", "linea", "seq", "received_at_utc", "status_registro", "window_ms"]
                + [f"q{i}_deg" for i in range(1, 7)]
                + ["e_p_m", "e_R_rad_arccos", "e_R_rad_atan2", "e_p_rosi_vs_irc5_m", "e_R_rosi_vs_irc5_rad", "e_p_propia_vs_rosi_m",
                   "dif_vs_registro_hito1_mm"])


def comparar_g2():
    """FK-N3 (complementario): postura única del 29/10/2026, pose leída de foto de pantalla FlexPendant (S1 limitado)."""
    ruta = rutas.EVIDENCIAS / "g2_fk_vs_controlador_pose1_2026-10-29.json"
    g = json.loads(ruta.read_text(encoding="utf-8"))
    q = np.deg2rad(g["ejes_deg_rws"])
    T_own = forward_kinematics(q)
    p_ref = np.array(g["flexpendant"]["xyz_mm"]) / 1000.0
    R_ref = M.cuaternion_wxyz_a_R(g["flexpendant"]["cuaternion_q1_q4"])
    e_p = M.error_posicion(T_own[:3, 3], p_ref)
    e_R = M.error_rotacion(T_own[:3, :3], R_ref)
    return {"caso": "FK-N3", "q_deg": g["ejes_deg_rws"], "p_own_m": T_own[:3, 3], "p_ref_m": p_ref, "R_own": T_own[:3, :3], "R_ref": R_ref,
            "e_p_m": e_p, "e_R_rad": e_R, "e_R_atan2_rad": M.error_rotacion_atan2(T_own[:3, :3], R_ref),
            "resolucion_pantalla": "0.01 mm en posición; 5 decimales en cuaternión (FlexPendant, transcrito de foto)",
            "cota_cuantizacion_e_p_m": math.sqrt(3) * 0.5e-5, "archivo": str(ruta.relative_to(rutas.RAIZ)),
            "limitacion": "una postura; sin marca temporal simultánea q-pose; lectura humana de una foto"}


# ----------------------------------------------------------------------------------------------- offline
def fk_offline_n(nombre, q_rad):
    T_own, T_ref = forward_kinematics(q_rad), rosi_forward_kinematics(q_rad)
    e = M.error_pose(T_own, T_ref)
    uq = chain_transform(rutas.URDF, {f"joint_{i + 1}": float(q_rad[i]) for i in range(6)}, "base_link", "tool0")
    e_u = M.error_pose(T_own, uq)
    return {"caso": nombre, "q_rad": q_rad, "p_own_m": T_own[:3, 3], "p_ref_m": T_ref[:3, 3], "R_own": T_own[:3, :3], "R_ref": T_ref[:3, :3],
            "e_p_m": e["e_p_m"], "e_R_rad": e["e_R_rad"], "e_R_atan2_rad": e["e_R_atan2_rad"],
            "e_p_urdf_m": e_u["e_p_m"], "e_R_urdf_atan2_rad": e_u["e_R_atan2_rad"],
            "ortogonalidad_own": M.comprobar_rotacion(T_own[:3, :3])["ortogonalidad_max"], "ortogonalidad_ref": M.comprobar_rotacion(T_ref[:3, :3])["ortogonalidad_max"],
            "det_dev_own": abs(M.comprobar_rotacion(T_own[:3, :3])["det_menos_1"]), "det_dev_ref": abs(M.comprobar_rotacion(T_ref[:3, :3])["det_menos_1"])}


def limites_documentados():
    import xml.etree.ElementTree as ET
    raiz = ET.parse(rutas.URDF).getroot()
    urdf = np.array([[float(j.find("limit").attrib["lower"]), float(j.find("limit").attrib["upper"])] for j in raiz.findall("joint") if j.attrib["type"] == "revolute"])
    return {"dh_deg": JOINT_LIMITS_DEG, "dh_rad": JOINT_LIMITS_RAD, "rosi_rad": ROSI_LIMITS_RAD, "urdf_rad": urdf,
            "max_dif_dh_rosi_rad": float(np.abs(JOINT_LIMITS_RAD - ROSI_LIMITS_RAD).max()),
            "max_dif_dh_urdf_rad": float(np.abs(JOINT_LIMITS_RAD - urdf).max()),
            "fuente_dh": "ABB, Product specification IRB 120 (según hito2/irb120/dh.py); no verificado contra el controlador (límites de software del IRC5 sin leer)"}


def fk_limites():
    L = JOINT_LIMITS_RAD
    margen = np.deg2rad(1.0)
    casos = {
        "FK-L1 (todas a 1° del límite superior)": L[:, 1] - margen,
        "FK-L2 (todas a 1° del límite inferior)": L[:, 0] + margen,
        "FK-L3 (alternadas sup/inf a 1°)": np.where(np.arange(6) % 2 == 0, L[:, 1] - margen, L[:, 0] + margen),
        "FK-L4 (exactamente en el límite superior)": L[:, 1].copy(),
    }
    return [fk_offline_n(n, q) for n, q in casos.items()]


def fk_d_tcp(filas_n1):
    """FK-D-TCP: N1 con TCP 150 mm de la FK propia contra la brida del controlador (discrepancia intencional)."""
    barrido = []
    for d in (0.0, 0.025, 0.05, 0.10, TCP_Z_M, 0.20):
        eps, cosz = [], []
        for f in filas_n1[:300]:
            q = D.q_rad(f)
            T = forward_kinematics(q) @ tcp_transform(d)
            Tc = T_controlador(f)
            dp = T[:3, 3] - Tc[:3, 3]
            eps.append(np.linalg.norm(dp))
            if d > 0:
                cosz.append(float(dp @ Tc[:3, 2] / np.linalg.norm(dp)))
        barrido.append({"tcp_z_m": d, "e_p_mediana_m": float(np.median(eps)), "e_p_max_m": float(np.max(eps)),
                        "cos_angulo_con_z6": float(np.median(cosz)) if cosz else None})
    # discrepancia: TCP propio 0.150 contra brida del IRC5 (todas las muestras N1)
    ep, eR = [], []
    ep_corr = []
    for f in filas_n1:
        q = D.q_rad(f)
        T = forward_kinematics(q) @ tcp_transform(TCP_Z_M)
        Tc = T_controlador(f)
        e = M.error_pose(T, Tc)
        ep.append(e["e_p_m"]); eR.append(e["e_R_atan2_rad"])
        ep_corr.append(M.error_posicion(T[:3, 3], (Tc @ tcp_transform(TCP_Z_M))[:3, 3]))  # misma herramienta en ambos lados
    return {"caso": "FK-D-TCP", "tcp_simulado_m": TCP_Z_M, "estadistica_e_p_m": M.resumen_estadistico(ep),
            "estadistica_e_R_atan2_rad": M.resumen_estadistico(eR), "estadistica_e_p_corregido_m": M.resumen_estadistico(ep_corr),
            "barrido": barrido, "n_muestras": len(filas_n1),
            "explicacion": ("p_TCP = p_brida + d·z6: con d = 0.150 m la FK propia al TCP queda 0.150 m a lo largo del eje z de la brida respecto a la pose de tool0 "
                            "del controlador; la orientación no cambia porque tool0->TCP es una traslación pura. Corrección: aplicar la misma transformación "
                            "tool0->TCP a ambos lados (o comparar brida contra brida).")}


PERMUTACIONES = {
    "intercambio q4<->q6": [0, 1, 2, 5, 4, 3],
    "intercambio q1<->q2": [1, 0, 2, 3, 4, 5],
    "orden invertido": [5, 4, 3, 2, 1, 0],
    "rotación cíclica": [1, 2, 3, 4, 5, 0],
}


def fk_d_ord(filas_n2):
    salida = []
    for nombre, perm in PERMUTACIONES.items():
        ep, eR, ep_c, eR_c = [], [], [], []
        inv = np.argsort(perm)
        for f in filas_n2[::10]:
            q = D.q_rad(f)
            Tc = T_controlador(f)
            qp = q[perm]
            e = M.error_pose(forward_kinematics(qp), Tc)
            ec = M.error_pose(forward_kinematics(qp[inv]), Tc)  # corrección: aplicar la permutación inversa
            ep.append(e["e_p_m"]); eR.append(e["e_R_atan2_rad"]); ep_c.append(ec["e_p_m"]); eR_c.append(ec["e_R_atan2_rad"])
        salida.append({"permutacion": nombre, "indices": perm, "n": len(ep), "e_p_mediana_m": float(np.median(ep)), "e_p_max_m": float(np.max(ep)),
                       "e_R_mediana_rad": float(np.median(eR)), "e_R_max_rad": float(np.max(eR)),
                       "e_p_corregido_max_m": float(np.max(ep_c)), "e_R_corregido_max_rad": float(np.max(eR_c))})
    # error de unidades (grados interpretados como radianes) como diagnóstico adicional
    ep_u = []
    for f in filas_n2[::10]:
        qd = np.array([f[f"qa{i}_deg"] for i in range(1, 7)])
        ep_u.append(M.error_posicion(forward_kinematics(qd)[:3, 3], T_controlador(f)[:3, 3]))
    return {"caso": "FK-D-ORD", "permutaciones": salida, "error_unidades_grados_como_rad_e_p_mediana_m": float(np.median(ep_u))}


# ----------------------------------------------------------------------------------------------- diagnóstico FUERA
def _paso_ulp_deg(q_deg):
    return float(max(np.spacing(np.float32(abs(v))) / 2.0 for v in q_deg))


def diagnosticar_fuera(filas_fuera, procedencia):
    filas_csv, categorias = [], Counter()
    pos_fail = rot_fail = 0
    for f in filas_fuera:
        q = D.q_rad(f)
        T_own = forward_kinematics(q)
        T_c = T_controlador(f)
        e = M.error_pose(T_own, T_c)
        modal = np.array([f["modal_x_mm"], f["modal_y_mm"], f["modal_z_mm"]]) / 1000.0
        Tm = np.eye(4)
        Tm[:3, :3] = M.cuaternion_wxyz_a_R([f["modal_qw"], f["modal_qx"], f["modal_qy"], f["modal_qz"]])
        Tm[:3, 3] = modal
        dp = float(np.linalg.norm(T_c[:3, 3] - modal))
        dR = M.error_rotacion_atan2(T_c[:3, :3], Tm[:3, :3])
        e_modal = M.error_pose(T_own, Tm)
        twist = np.concatenate([T_c[:3, 3] - modal, M.logaritmo_rotacion(T_c[:3, :3] @ Tm[:3, :3].T)])
        dq_eq = np.rad2deg(np.linalg.solve(geometric_jacobian(q, "tool0"), twist))
        dq_eq_max = float(np.abs(dq_eq).max())
        ulp = _paso_ulp_deg([f[f"qa{i}_deg"] for i in range(1, 7)])
        # árbol del Bloque C (paso 1: ¿mismo q y t estático?; pasos 2-6 se descartan por la evidencia de las demás muestras de esa q)
        n_misma_q = f["n_estacionarias_misma_q"]
        if f["dq_max_deg"] > D.UMBRAL_ESTACIONARIO_DEG:
            cat = "A: movimiento entre lecturas (Δq > umbral)"
        elif f["window_ms"] > D.VENTANA_MAX_MS:
            cat = "B: ventana q-pose-q excesiva"
        elif n_misma_q < 3:
            cat = "E: q con <3 lecturas estacionarias: sin pose modal con que contrastar (indeterminada por datos)"
        elif dp > 0.0 or dR > 0.0:
            cat = "C: q idéntico y pose del IRC5 distinta a la pose modal de esa q (indeterminada por datos)"
        else:
            cat = "D: pose modal repetida de esa q queda fuera de criterio (error reproducible; revisar pasos 2-6)"
        categorias[cat] += 1
        pos_fail += e["e_p_m"] > 1e-6
        rot_fail += e["e_R_rad"] > 1e-6
        filas_csv.append([f["archivo"], f["linea"], f["seq"], f["received_at_utc"], f["window_ms"], f["dq_max_deg"],
                          e["e_p_m"], e["e_R_rad"], e["e_p_m"] > 1e-6, e["e_R_rad"] > 1e-6,
                          dp, dR, e_modal["e_p_m"], e_modal["e_R_rad"], dq_eq_max, ulp, dq_eq_max / ulp,
                          f["n_modal_misma_q"], f["n_estacionarias_misma_q"], cat])
    col = ["archivo", "linea", "seq", "received_at_utc", "window_ms", "dq_max_deg", "e_p_m", "e_R_rad", "falla_posicion_1e-6m", "falla_orientacion_1e-6rad",
           "dist_pose_ctrl_a_modal_m", "ang_pose_ctrl_a_modal_rad", "e_p_modal_m", "e_R_modal_rad", "dq_equivalente_max_deg", "semi_ulp_float32_q_deg",
           "razon_dq_equiv_sobre_semi_ulp", "n_poses_modales_misma_q", "n_estacionarias_misma_q", "categoria"]
    arr = np.array([r[col.index("e_p_m")] for r in filas_csv])
    inv = procedencia["lecturas_invalidas"]
    rango = procedencia.get("lecturas_invalidas_rango_utc", {})
    por_sesion = Counter(r[0] for r in filas_csv)
    return {
        "n_fuera": len(filas_csv), "por_archivo": dict(por_sesion), "categorias": dict(categorias),
        "n_falla_posicion": int(pos_fail), "n_falla_orientacion": int(rot_fail),
        "estadistica_e_p_m": M.resumen_estadistico(arr),
        "estadistica_e_R_rad": M.resumen_estadistico([r[col.index("e_R_rad")] for r in filas_csv]),
        "estadistica_dq_equivalente_deg": M.resumen_estadistico([r[col.index("dq_equivalente_max_deg")] for r in filas_csv]),
        "estadistica_razon_dq_sobre_semi_ulp": M.resumen_estadistico([r[col.index("razon_dq_equiv_sobre_semi_ulp")] for r in filas_csv]),
        "estadistica_ventana_ms": M.resumen_estadistico([r[col.index("window_ms")] for r in filas_csv]),
        "lecturas_invalidas": inv, "lecturas_invalidas_rango_utc": rango,
        "lecturas_invalidas_total": int(sum(sum(v.values()) for v in inv.values())),
    }, col, filas_csv


# ----------------------------------------------------------------------------------------------- orquestación
def ejecutar():
    estilo_ok = graficos.estilo()  # noqa: F841
    proc = D.cargar_procedencia()
    res = {"criterios": {"estricto_proyecto": CRITERIO_ESTRICTO_PROYECTO, "cribado_sintetico": CRIBADO_SINTETICO}}
    filas_det = []
    datos = {}
    for n in ("N1", "N2"):
        filas = D.cargar_postura(n)
        datos[n] = filas
        r, det = comparar_real(n, filas)
        res[f"FK-{n}"] = r
        filas_det += det
        res[f"FK-{n}-S0"] = fk_offline_n(f"FK-{n}-S0", r["q_rad"])
    util.escribir_csv(rutas.RESULTADOS / "fk_real_errores_por_muestra.csv", COLS_DETALLE, filas_det)
    res["FK-N3"] = comparar_g2()
    res["FK-N3-S0"] = fk_offline_n("FK-N3-S0", np.deg2rad(res["FK-N3"]["q_deg"]))
    res["limites"] = limites_documentados()
    res["FK-L"] = fk_limites()
    res["FK-D-TCP"] = fk_d_tcp(datos["N1"])
    res["FK-D-ORD"] = fk_d_ord(datos["N2"])
    diag, col, filas_f = diagnosticar_fuera(D.cargar_fuera(), proc)
    res["FUERA"] = diag
    util.escribir_csv(rutas.RESULTADOS / "fk_fuera_diagnostico.csv", col, filas_f)
    # cobertura de las demás posturas estacionarias (todas las de >=20 muestras)
    cob = []
    for p in D.cargar_posturas():
        cob.append([p["sesion"], *[p[f"q{i}_deg"] for i in range(1, 7)], int(p["n_estacionarias"]), int(p["n_poses_controlador_distintas"]), int(p["n_fuera"])])
    res["cobertura_posturas"] = cob
    util.escribir_csv(rutas.RESULTADOS / "fk_cobertura_posturas.csv", ["sesion", *[f"q{i}_deg" for i in range(1, 7)], "n_estacionarias", "n_poses_distintas", "n_fuera"], cob)
    # CSV de casos offline
    off = [res["FK-N1-S0"], res["FK-N2-S0"], res["FK-N3-S0"], *res["FK-L"]]
    util.escribir_csv(rutas.RESULTADOS / "fk_offline_propia_vs_rosi.csv",
                      ["caso", "q_rad", "e_p_m", "e_R_rad_arccos", "e_R_rad_atan2", "e_p_urdf_vs_propia_m", "e_R_urdf_atan2_rad", "ortogonalidad_own", "ortogonalidad_ref", "det_dev_own", "det_dev_ref"],
                      [[c["caso"], list(c["q_rad"]), c["e_p_m"], c["e_R_rad"], c["e_R_atan2_rad"], c["e_p_urdf_m"], c["e_R_urdf_atan2_rad"], c["ortogonalidad_own"], c["ortogonalidad_ref"], c["det_dev_own"], c["det_dev_ref"]] for c in off])
    util.escribir_csv(rutas.RESULTADOS / "fk_d_tcp.csv", ["tcp_z_m", "e_p_mediana_m", "e_p_max_m", "cos_angulo_con_z6"],
                      [[b["tcp_z_m"], b["e_p_mediana_m"], b["e_p_max_m"], b["cos_angulo_con_z6"]] for b in res["FK-D-TCP"]["barrido"]])
    util.escribir_csv(rutas.RESULTADOS / "fk_d_ord.csv", ["permutacion", "indices", "n", "e_p_mediana_m", "e_p_max_m", "e_R_mediana_rad", "e_R_max_rad", "e_p_corregido_max_m", "e_R_corregido_max_rad"],
                      [[p["permutacion"], p["indices"], p["n"], p["e_p_mediana_m"], p["e_p_max_m"], p["e_R_mediana_rad"], p["e_R_max_rad"], p["e_p_corregido_max_m"], p["e_R_corregido_max_rad"]] for p in res["FK-D-ORD"]["permutaciones"]])
    res["figuras"] = graficar(res, datos, filas_f, col)
    return res


def graficar(res, datos, filas_f, col):
    import matplotlib.pyplot as plt
    graficos.estilo()
    figs = {}
    # 1) errores reales N1/N2 por muestra + piso de cuantización
    fig, ax = plt.subplots(2, 2, figsize=(10, 6))
    for j, n in enumerate(("N1", "N2")):
        filas = datos[n]
        t = np.array([(np.datetime64(f["received_at_utc"][:26]) - np.datetime64(filas[0]["received_at_utc"][:26])) / np.timedelta64(1, "s") for f in filas])
        ep = np.array([M.error_posicion(forward_kinematics(D.q_rad(f))[:3, 3], T_controlador(f)[:3, 3]) for f in filas])
        eR = np.array([M.error_rotacion_atan2(forward_kinematics(D.q_rad(f))[:3, :3], T_controlador(f)[:3, :3]) for f in filas])
        c = res[f"FK-{n}"]["cuantizacion"]
        ax[0, j].semilogy(t, np.maximum(ep, 1e-12), ".", ms=3, label="e_p por muestra")
        ax[0, j].axhline(1e-6, color="#c0504d", ls="--", lw=1, label="1e-6 m (criterio estricto, no aprobado)")
        ax[0, j].axhline(c["cota_e_p_m"], color="#4f8a3c", ls=":", lw=1.4, label="cota de cuantización de los datos")
        ax[0, j].set(title=f"FK-{n} — e_p (tool0, Base) n={len(filas)}", xlabel="t [s]", ylabel="e_p [m]")
        ax[0, j].set_ylim(top=max(ep.max(), 1e-6) * 40)
        ax[0, j].legend(fontsize=7, loc="upper right")
        ax[1, j].semilogy(t, np.maximum(eR, 1e-12), ".", ms=3, label="e_R (atan2)")
        ax[1, j].axhline(1e-6, color="#c0504d", ls="--", lw=1, label="1e-6 rad (criterio estricto, no aprobado)")
        ax[1, j].axhline(c["cota_e_R_rad"], color="#4f8a3c", ls=":", lw=1.4, label="cota de cuantización de los datos")
        ax[1, j].set(xlabel="t [s]", ylabel="e_R [rad]")
        ax[1, j].set_ylim(top=max(eR.max(), 1e-6) * 40)
        ax[1, j].legend(fontsize=7, loc="upper right")
    figs["fk_real_errores"] = graficos.guardar(fig, "fk_real_errores_N1_N2.png")
    # 2) diagnóstico FUERA
    ep = np.array([r[col.index("e_p_m")] for r in filas_f])
    dq = np.array([r[col.index("dq_equivalente_max_deg")] for r in filas_f])
    ul = np.array([r[col.index("semi_ulp_float32_q_deg")] for r in filas_f])
    win = np.array([r[col.index("window_ms")] for r in filas_f])
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.8))
    ax[0].hist(ep * 1e6, bins=30)
    ax[0].axvline(1.0, color="#c0504d", ls="--")
    ax[0].set(title="FUERA: e_p [µm]", xlabel="e_p [µm]", ylabel="muestras")
    ax[1].loglog(ul, dq, "o", ms=4, alpha=0.6)
    lim = [min(ul.min(), dq.min()) * 0.5, dq.max() * 2]
    ax[1].plot(lim, lim, "k--", lw=1, label="Δq equiv. = semi-ulp float32")
    ax[1].set(title="Δq equivalente de la pose vs resolución de q", xlabel="semi-ulp float32 de q [°]", ylabel="Δq equivalente máx [°]")
    ax[1].legend(fontsize=7)
    ax[2].plot(win, ep * 1e6, ".", ms=4)
    ax[2].set(title="FUERA: e_p vs ventana q-pose-q", xlabel="window_ms [ms]", ylabel="e_p [µm]")
    figs["fk_fuera"] = graficos.guardar(fig, "fk_fuera_diagnostico.png")
    # 3) FK-D-TCP y FK-D-ORD
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    b = res["FK-D-TCP"]["barrido"]
    x = [r["tcp_z_m"] for r in b]
    ax[0].plot(x, [r["e_p_mediana_m"] for r in b], "o-", label="e_p medido (mediana)")
    ax[0].plot(x, x, "k--", lw=1, label="e_p = d (teoría)")
    ax[0].set(title="FK-D-TCP: TCP propio vs brida del IRC5", xlabel="d = TCP_z simulado [m]", ylabel="e_p [m]")
    ax[0].legend(fontsize=8)
    pr = res["FK-D-ORD"]["permutaciones"]
    idx = np.arange(len(pr))
    ax[1].bar(idx - 0.2, [p["e_p_mediana_m"] for p in pr], 0.4, label="con permutación")
    ax[1].bar(idx + 0.2, [max(p["e_p_corregido_max_m"], 1e-9) for p in pr], 0.4, label="corregida (permutación inversa)")
    ax[1].set_yscale("log")
    ax[1].set_xticks(idx, [p["permutacion"] for p in pr], rotation=15, fontsize=7)
    ax[1].set(title="FK-D-ORD: error por orden articular (N2)", ylabel="e_p [m]")
    ax[1].legend(fontsize=8)
    figs["fk_diagnosticos"] = graficos.guardar(fig, "fk_d_tcp_d_ord.png")
    return figs
