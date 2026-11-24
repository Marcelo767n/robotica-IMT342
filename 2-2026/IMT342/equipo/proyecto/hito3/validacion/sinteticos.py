"""Verificación del código de métricas con los ejemplos sintéticos resueltos del documento W14-S02 (no ABB, S0)."""

import numpy as np

from . import metricas as M, rutas, util

REF_2R = {"p": [1.34898832, 0.37059048], "Jp": [[-0.37059048, 0.12940952], [1.34898832, 0.48296291]], "pdot": [-0.06294095, 0.03830625], "det": -0.35355339}
REF_FD = {1e-2: 2.33e-5, 1e-3: 2.33e-7, 1e-4: 2.33e-9}  # valores de la Visual 4 (coordenadas del documento)


def ejecutar():
    q = np.deg2rad([30.0, -45.0])
    qd = np.array([0.10, -0.20])
    J = M.jac_2r(q)
    filas = []

    def reg(nombre, esperado, obtenido, tol):
        e, o = np.asarray(esperado, float), np.asarray(obtenido, float)
        err = float(np.abs(e - o).max())
        filas.append([nombre, util.vec(e, 9), util.vec(o, 9), err, tol, err <= tol])

    reg("Ejemplo 1: p(q) [m]", REF_2R["p"], M.fk_2r(q), 5e-9)
    reg("Ejemplo 1: Jp(q) [m/rad]", REF_2R["Jp"], J, 5e-9)
    reg("Ejemplo 1: ṗ = Jp q̇ [m/s]", REF_2R["pdot"], J @ qd, 5e-9)
    reg("Ejemplo 1: det Jp = a1 a2 sin q2", [REF_2R["det"]], [np.linalg.det(J)], 5e-9)
    reg("Ejemplo 1: det Jp (fórmula cerrada)", [M.A1_2R * M.A2_2R * np.sin(q[1])], [np.linalg.det(J)], 1e-14)
    fd = M.curva_fd_2r(q, list(REF_FD))
    for (h, esp), obt in zip(REF_FD.items(), fd):
        reg(f"Ejemplo 1: E(h={h:.0e}) Visual 4", [esp], [obt], 0.01 * esp)
    # Ejemplo 2: e_R = pi/18
    Rz10 = M.Rz(np.deg2rad(10.0))
    reg("Ejemplo 2: e_R arccos [rad]", [np.pi / 18], [M.error_rotacion(Rz10, np.eye(3))], 1e-12)
    reg("Ejemplo 2: e_R atan2 [rad]", [np.pi / 18], [M.error_rotacion_atan2(Rz10, np.eye(3))], 1e-15)
    reg("Ejemplo 2: tr(R_err) = 1 + 2 cos 10°", [1 + 2 * np.cos(np.deg2rad(10))], [np.trace(np.eye(3).T @ Rz10)], 1e-15)
    # clip: argumento ligeramente fuera de [-1, 1] no debe producir NaN
    R_ruido = np.eye(3) * (1.0 + 1e-15)
    reg("Clip: e_R con tr/3 ligeramente > 1 no es NaN", [0.0], [M.error_rotacion(R_ruido, np.eye(3))], 1e-7)
    # Ejemplo 3: rango 1 y dirección perdida
    Jp = np.array([[1.0, 2.0], [2.0, 4.0]])
    r = M.rango_numerico(Jp)
    reg("Ejemplo 3: rank_num(Jp) = 1", [1], [r["rango"]], 0)
    u, s, vt = np.linalg.svd(Jp)
    perdida = u[:, -1] * np.sign(u[0, -1])
    esperada = np.array([-2.0, 1.0]) / np.sqrt(5.0)
    reg("Ejemplo 3: dirección perdida ±[-2,1]/√5", np.abs(esperada), np.abs(perdida), 1e-12)
    F = np.array([3.0, -7.0])
    reg("Ejemplo 3: Jpᵀ F finito (= [-11, -22])", [-11.0, -22.0], Jp.T @ F, 1e-12)
    reg("Ejemplo 3: τ_num = max(m,n) ε σ_max", [2 * M.EPS * s[0]], [r["tau_num"]], 1e-30)
    # logaritmo de rotación
    ang = 0.3
    reg("log(Rz(0.3)) = [0,0,0.3]", [0, 0, ang], M.logaritmo_rotacion(M.Rz(ang)), 1e-14)
    # cuaternión wxyz <-> R
    Rq = M.cuaternion_wxyz_a_R([np.cos(0.15), 0, 0, np.sin(0.15)])
    reg("cuaternión (w,x,y,z) de Rz(0.3) -> R", M.Rz(0.3), Rq, 1e-15)
    reg("R -> cuaternión canónico w>=0", [np.cos(0.15), 0, 0, np.sin(0.15)], M.R_a_cuaternion_wxyz(M.Rz(0.3)), 1e-14)
    util.escribir_csv(rutas.RESULTADOS / "verificacion_metricas_sinteticas.csv", ["verificacion", "esperado", "obtenido", "error_max", "tolerancia", "ok"], filas)
    return {"filas": filas, "todas_ok": all(f[-1] for f in filas), "n": len(filas)}
