"""Métricas de comparación del protocolo (Bloques C, D, E, F). Unidades SI: m, rad.

Todas las funciones son puras y se verifican con los ejemplos sintéticos del documento
(2R planar, Ejemplo 2 de error de orientación, Ejemplo 3 de rango) en tests/test_validacion.py.
"""

import numpy as np

EPS = float(np.finfo(float).eps)


# ----------------------------------------------------------------------------- rotaciones / poses
def comprobar_rotacion(R) -> dict:
    """R^T R ≈ I y det(R) ≈ +1 (precondición de e_R)."""
    R = np.asarray(R, dtype=float)
    return {
        "ortogonalidad_max": float(np.abs(R.T @ R - np.eye(3)).max()),
        "det_menos_1": float(np.linalg.det(R) - 1.0),
    }


def error_posicion(p_propia, p_ref) -> float:
    """e_p = ||p_propia - p_ref||_2 [m]."""
    return float(np.linalg.norm(np.asarray(p_propia, float) - np.asarray(p_ref, float)))


def error_rotacion(R_propia, R_ref) -> float:
    """e_R = arccos(clip((tr(R_ref^T R_propia) - 1)/2, -1, 1)) [rad], fórmula exacta del protocolo."""
    R_err = np.asarray(R_ref, float).T @ np.asarray(R_propia, float)
    c = float(np.clip((np.trace(R_err) - 1.0) / 2.0, -1.0, 1.0))
    return float(np.arccos(c))


def error_rotacion_atan2(R_propia, R_ref) -> float:
    """Mismo ángulo geodésico vía atan2(|vee(R-R^T)|/2, (tr-1)/2): sin el piso ~sqrt(2 eps) del arccos."""
    R_err = np.asarray(R_ref, float).T @ np.asarray(R_propia, float)
    v = np.array([R_err[2, 1] - R_err[1, 2], R_err[0, 2] - R_err[2, 0], R_err[1, 0] - R_err[0, 1]])
    return float(np.arctan2(np.linalg.norm(v) / 2.0, np.clip((np.trace(R_err) - 1.0) / 2.0, -1.0, 1.0)))


def error_pose(T_propia, T_ref) -> dict:
    return {
        "e_p_m": error_posicion(T_propia[:3, 3], T_ref[:3, 3]),
        "e_R_rad": error_rotacion(T_propia[:3, :3], T_ref[:3, :3]),
        "e_R_atan2_rad": error_rotacion_atan2(T_propia[:3, :3], T_ref[:3, :3]),
    }


def cuaternion_wxyz_a_R(q_wxyz) -> np.ndarray:
    """Matriz de rotación del cuaternión en orden (w, x, y, z) (orden de RWS/RAPID). Se normaliza."""
    w, x, y, z = np.asarray(q_wxyz, float) / np.linalg.norm(q_wxyz)
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def R_a_cuaternion_wxyz(R) -> np.ndarray:
    """Cuaternión (w, x, y, z) con w >= 0 (signo canónico) de una rotación."""
    R = np.asarray(R, float)
    tr = np.trace(R)
    if tr > 0:
        s = 2.0 * np.sqrt(tr + 1.0)
        q = np.array([0.25 * s, (R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s])
    else:
        i = int(np.argmax(np.diag(R)))
        j, k = (i + 1) % 3, (i + 2) % 3
        s = 2.0 * np.sqrt(1.0 + R[i, i] - R[j, j] - R[k, k])
        v = np.zeros(3)
        v[i] = 0.25 * s
        v[j] = (R[j, i] + R[i, j]) / s
        v[k] = (R[k, i] + R[i, k]) / s
        q = np.array([(R[k, j] - R[j, k]) / s, *v])
    q = q / np.linalg.norm(q)
    return -q if q[0] < 0 else q


def logaritmo_rotacion(R) -> np.ndarray:
    """Vector de rotación (eje·ángulo) de R, estable para ángulos pequeños y cercanos a pi."""
    R = np.asarray(R, float)
    v = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]]) / 2.0
    s = np.linalg.norm(v)
    c = (np.trace(R) - 1.0) / 2.0
    ang = np.arctan2(s, c)
    if s < 1e-12:
        if c > 0:
            return v
        # ángulo ~ pi: eje desde la diagonal
        eje = np.sqrt(np.maximum((np.diag(R) + 1.0) / 2.0, 0.0))
        eje = eje * np.where(np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]]) >= 0, 1.0, -1.0)
        return ang * eje / max(np.linalg.norm(eje), 1e-300)
    return v * (ang / s)


def Rz(angulo: float) -> np.ndarray:
    c, s = np.cos(angulo), np.sin(angulo)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def diferencia_angular_envuelta(a, b) -> np.ndarray:
    """a - b envuelto a (-pi, pi]."""
    return (np.asarray(a, float) - np.asarray(b, float) + np.pi) % (2.0 * np.pi) - np.pi


# ----------------------------------------------------------------------------- Jacobiano
def error_jacobiano(J_propio, J_ref) -> dict:
    """Errores separados (el protocolo prohíbe la norma mezclada): Jv [m/rad], Jw [rad/rad]."""
    d = np.asarray(J_propio, float) - np.asarray(J_ref, float)
    return {"eJv_fro": float(np.linalg.norm(d[:3], "fro")), "eJw_fro": float(np.linalg.norm(d[3:], "fro"))}


def jacobiano_fd(f_pose, q, h: float):
    """J por diferencias centrales de una FK f_pose(q)->T 4x4 (Jv: columna dp/dq; Jw: log(R+ R-^T)/2h)."""
    q = np.asarray(q, float)
    J = np.zeros((6, q.size))
    for i in range(q.size):
        e = np.zeros(q.size)
        e[i] = h
        Tp, Tm = f_pose(q + e), f_pose(q - e)
        J[:3, i] = (Tp[:3, 3] - Tm[:3, 3]) / (2.0 * h)
        J[3:, i] = logaritmo_rotacion(Tp[:3, :3] @ Tm[:3, :3].T) / (2.0 * h)
    return J


def umbral_rango(J) -> float:
    """tau_num = max(m, n) * eps * sigma_max."""
    J = np.asarray(J, float)
    return float(max(J.shape) * EPS * np.linalg.svd(J, compute_uv=False)[0])


def rango_numerico(J) -> dict:
    J = np.asarray(J, float)
    sigma = np.linalg.svd(J, compute_uv=False)
    tau = max(J.shape) * EPS * sigma[0]
    rango = int(np.sum(sigma > tau))
    return {"sigma": sigma, "tau_num": float(tau), "rango": rango,
            "kappa": float(sigma[0] / sigma[-1]) if sigma[-1] > 0 else float("inf"),
            "sigma_min": float(sigma[-1]), "sigma_max": float(sigma[0])}


def escalar_jacobiano(J, L: float) -> np.ndarray:
    """J_s = [Jv / L; Jw] (homogeneiza unidades con la longitud característica L > 0 [m])."""
    if L <= 0:
        raise ValueError("L debe ser > 0")
    J = np.asarray(J, float).copy()
    J[:3] /= L
    return J


# ----------------------------------------------------------------------------- banco sintético 2R (NO ABB)
A1_2R, A2_2R = 1.0, 0.5


def fk_2r(q):
    q1, q2 = q
    return np.array([A1_2R * np.cos(q1) + A2_2R * np.cos(q1 + q2), A1_2R * np.sin(q1) + A2_2R * np.sin(q1 + q2)])


def jac_2r(q):
    q1, q2 = q
    s1, s12, c1, c12 = np.sin(q1), np.sin(q1 + q2), np.cos(q1), np.cos(q1 + q2)
    return np.array([[-A1_2R * s1 - A2_2R * s12, -A2_2R * s12], [A1_2R * c1 + A2_2R * c12, A2_2R * c12]])


def curva_fd_2r(q, pasos):
    """E(h) = ||J[:,0] - J_FD(h)[:,0]|| para el 2R (Visual 4 del documento)."""
    q = np.asarray(q, float)
    J = jac_2r(q)
    salida = []
    for h in pasos:
        e0 = np.array([h, 0.0])
        col = (fk_2r(q + e0) - fk_2r(q - e0)) / (2 * h)
        salida.append(float(np.linalg.norm(J[:, 0] - col)))
    return salida


# ----------------------------------------------------------------------------- estadística
def resumen_estadistico(valores) -> dict:
    v = np.asarray(valores, float)
    if v.size == 0:
        return {"n": 0, "min": None, "mediana": None, "p95": None, "max": None, "media": None, "desv": None}
    return {"n": int(v.size), "min": float(v.min()), "mediana": float(np.median(v)),
            "p95": float(np.percentile(v, 95)), "max": float(v.max()), "media": float(v.mean()),
            "desv": float(v.std(ddof=1)) if v.size > 1 else 0.0}
