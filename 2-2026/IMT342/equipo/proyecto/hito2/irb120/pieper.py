"""Cinematica inversa analitica del ABB IRB 120 por el metodo de Pieper.

El IRB 120 tiene muneca esferica: los ejes 4, 5 y 6 se cortan en un punto, el
centro de muneca (origen de los marcos 4 y 5, pues a4 = a5 = d5 = 0). Pieper
desacopla el problema:

1. Posicion: p_wc = p_tool0 - d6 * z6 depende solo de q1, q2, q3.
   - q1 = atan2(y, x) (brazo "frente") o atan2(y, x) + pi (brazo "atras").
   - En el plano vertical del brazo, hombro S = (0, d1), brazo L2 y antebrazo
     L3 = sqrt(d4^2 + a3^2) desplazado delta = atan2(a3, d4). La ley de cosenos
     da dos soluciones de codo ("arriba" / "abajo").
2. Orientacion: R_3^6 = R_0^3^T R_0^6 = Rz(q4) Ry(-q5) Rz(q6 + pi), una
   descomposicion de Euler ZYZ que da dos soluciones de muneca (q5 > 0 / < 0).

Son 2 x 2 x 2 = 8 ramas. `enumerate_candidates` devuelve SIEMPRE las 8, marcando
cuales existen (real) y cuales respetan los limites articulares; `analyze_pose`
las verifica ademas por FK y decide si la pose es alcanzable. Sin MoveIt ni
resolvedores numericos.
"""

from dataclasses import dataclass
from math import asin, atan2, hypot, pi, sqrt

import numpy as np
from numpy.typing import NDArray

from irb120.dh import (
    DH_PARAMETERS,
    JOINT_LIMITS_RAD,
    dh_transform,
    tcp_transform,
)
from irb120.transforms import assert_rigid_transform
from irb120.validation import FKCheck, fk_check

Matrix4 = NDArray[np.float64]

D1 = DH_PARAMETERS[0].d_m
L2 = DH_PARAMETERS[1].a_m
A3 = DH_PARAMETERS[2].a_m
D4 = DH_PARAMETERS[3].d_m
D6 = DH_PARAMETERS[5].d_m
L3 = sqrt(D4 * D4 + A3 * A3)
DELTA = atan2(A3, D4)
REACH_MIN_M = abs(L2 - L3)  # distancia hombro-muneca minima (codo plegado)
REACH_MAX_M = L2 + L3  # distancia hombro-muneca maxima (codo extendido)

LIMITS_RAD = JOINT_LIMITS_RAD
SINGULARITY_EPS = 1.0e-9
FK_TOLERANCE_M = 1.0e-6

ARM_BRANCHES = ("frente", "atras")
ELBOW_BRANCHES = ("arriba", "abajo")
WRIST_BRANCHES = ("q5+", "q5-")


@dataclass(frozen=True)
class IKSolution:
    """Una solucion articular [rad] con su configuracion (brazo, codo, muneca)."""

    q: tuple[float, ...]
    arm: str  # "frente" o "atras"
    elbow: str  # "arriba" o "abajo"
    wrist: str  # "q5+" o "q5-"
    singular_wrist: bool = False


@dataclass(frozen=True)
class Candidate:
    """Una de las 8 ramas de Pieper, exista o no.

    real            la rama existe geometricamente (|cos| <= 1 en la ley de cosenos).
    q_raw           angulos envueltos a (-pi, pi]; None si la rama no es real.
    q               representante dentro de limites (q + 2 pi k); None si alguna junta no cabe.
    out_of_limits   juntas (1..6) que no tienen representante dentro de sus limites.
    """

    branch: int
    arm: str
    elbow: str
    wrist: str
    real: bool
    q_raw: tuple[float, ...] | None
    q: tuple[float, ...] | None
    out_of_limits: tuple[int, ...]
    singular_wrist: bool = False
    cos_elbow: float = float("nan")

    @property
    def within_limits(self) -> bool:
        return self.real and self.q is not None


def _wrap_pi(angle: float) -> float:
    return (angle + pi) % (2.0 * pi) - pi


def _fit_to_limits(angle: float, lower: float, upper: float, reference: float) -> float | None:
    """Representante angle + 2*pi*k dentro de limites, el mas cercano a reference."""
    best = None
    for turns in range(-3, 4):
        candidate = angle + 2.0 * pi * turns
        if lower - 1e-9 <= candidate <= upper + 1e-9:
            if best is None or abs(candidate - reference) < abs(best - reference):
                best = candidate
    return best


def wrist_center(target_tool0: Matrix4) -> NDArray[np.float64]:
    """p_wc = p_tool0 - d6 * z6 (paso 0 de Pieper)."""
    target = np.asarray(target_tool0, dtype=float)
    return target[:3, 3] - D6 * target[:3, 2]


def _arm_branches(center: NDArray[np.float64]):
    """Las 4 ramas de brazo (arm, elbow, real, cos_term, q1, q2, q3); q = nan si no es real."""
    x, y, z = center
    planar = hypot(x, y)
    height = z - D1
    results = []
    for arm, q1, radial in (
        ("frente", atan2(y, x), planar),
        ("atras", atan2(y, x) + pi, -planar),
    ):
        reach_sq = radial * radial + height * height
        cos_term = (reach_sq - L2 * L2 - L3 * L3) / (2.0 * L2 * L3)
        if abs(cos_term) > 1.0 + 1e-12:  # fuera del espacio de trabajo
            for elbow in ELBOW_BRANCHES:
                results.append((arm, elbow, False, cos_term, np.nan, np.nan, np.nan))
            continue
        clipped = max(-1.0, min(1.0, cos_term))
        # -sin(q3 - delta) = cos_term  ->  dos soluciones de codo
        base = asin(-clipped)
        alpha = atan2(radial, height)  # angulo de S->W medido desde la vertical
        for elbow, q3_minus_delta in (("arriba", base), ("abajo", pi - base)):
            q3 = _wrap_pi(q3_minus_delta + DELTA)
            eta = pi / 2.0 + q3 - DELTA
            q2 = _wrap_pi(alpha - atan2(L3 * np.sin(eta), L2 + L3 * np.cos(eta)))
            results.append((arm, elbow, True, cos_term, _wrap_pi(q1), q2, q3))
    return results


def _rotation_0_3(q1: float, q2: float, q3: float) -> NDArray[np.float64]:
    transform = np.eye(4)
    for angle, parameter in zip((q1, q2, q3), DH_PARAMETERS[:3], strict=True):
        transform = transform @ dh_transform(angle, parameter)
    return transform[:3, :3]


def _wrist_solutions(rotation_3_6: NDArray[np.float64], q4_reference: float):
    """Las 2 soluciones (wrist, q4, q5, q6, singular) de R36 = Rz(q4) Ry(-q5) Rz(q6+pi).

    En q5 = 0 solo q4 + q6 esta determinado: se fija q4 = q4_reference (rama q5+) y
    q4 = q4_reference + pi (rama q5-), que es la misma orientacion con otra eleccion.
    """
    sin_beta = hypot(rotation_3_6[0, 2], rotation_3_6[1, 2])
    if sin_beta < SINGULARITY_EPS:
        if rotation_3_6[2, 2] < 0.0:
            # q5 = -pi: Rz(q4) Ry(pi) Rz(q6+pi) = Rz(q4 - q6 - pi) Ry(pi). Siempre fuera de |q5| <= 120 deg.
            difference = atan2(-rotation_3_6[1, 0], -rotation_3_6[0, 0])
            q6 = _wrap_pi(q4_reference - difference - pi)
            return [
                ("q5+", q4_reference, -pi, q6, True),
                ("q5-", q4_reference, -pi, q6, True),
            ]
        total = atan2(rotation_3_6[1, 0], rotation_3_6[0, 0])  # = q4 + q6 + pi (cos_beta = 1)
        return [
            ("q5+", q4_reference, 0.0, _wrap_pi(total - q4_reference - pi), True),
            ("q5-", _wrap_pi(q4_reference + pi), 0.0, _wrap_pi(total - q4_reference - 2.0 * pi), True),
        ]
    cos_beta = float(rotation_3_6[2, 2])
    solutions = []
    # beta = -q5 (por la Ry(-q5) del modelo), asi que el signo de sin(beta) es el OPUESTO al de q5:
    # sign = -1 da q5 > 0 (rama "q5+") y sign = +1 da q5 < 0 (rama "q5-").
    for wrist, sign in (("q5+", -1.0), ("q5-", 1.0)):
        beta = atan2(sign * sin_beta, cos_beta)
        alpha = atan2(sign * rotation_3_6[1, 2], sign * rotation_3_6[0, 2])
        gamma = atan2(sign * rotation_3_6[2, 1], -sign * rotation_3_6[2, 0])
        solutions.append((wrist, alpha, -beta, _wrap_pi(gamma - pi), False))
    return solutions


def enumerate_candidates(
    target_tool0: Matrix4,
    reference_q: np.ndarray | None = None,
) -> list[Candidate]:
    """Las 8 ramas de Pieper para la pose de tool0, en orden fijo (brazo, codo, muneca)."""
    target = assert_rigid_transform(target_tool0)  # rechaza matrices que no son poses rigidas
    reference = np.zeros(6) if reference_q is None else np.asarray(reference_q, dtype=float)
    rotation = target[:3, :3]

    candidates: list[Candidate] = []
    for arm, elbow, real, cos_term, q1, q2, q3 in _arm_branches(wrist_center(target)):
        if not real:
            for wrist in WRIST_BRANCHES:
                candidates.append(
                    Candidate(len(candidates) + 1, arm, elbow, wrist, False, None, None, (), False, cos_term)
                )
            continue
        rotation_3_6 = _rotation_0_3(q1, q2, q3).T @ rotation
        for wrist, q4, q5, q6, singular in _wrist_solutions(rotation_3_6, reference[3]):
            raw = (q1, q2, q3, q4, q5, q6)
            fitted = [
                _fit_to_limits(angle, lower, upper, reference[index])
                for index, (angle, (lower, upper)) in enumerate(zip(raw, LIMITS_RAD, strict=True))
            ]
            out = tuple(index + 1 for index, value in enumerate(fitted) if value is None)
            q = None if out else tuple(float(value) for value in fitted)
            candidates.append(
                Candidate(
                    len(candidates) + 1,
                    arm,
                    elbow,
                    wrist,
                    True,
                    tuple(float(value) for value in raw),
                    q,
                    out,
                    singular,
                    cos_term,
                )
            )
    return candidates


def inverse_kinematics(
    target_tool0: Matrix4,
    reference_q: np.ndarray | None = None,
) -> list[IKSolution]:
    """Solo las soluciones admisibles (reales, en limites y verificadas por FK), ordenadas por cercania.

    `target_tool0` es base_link -> tool0 (4x4). Si no hay solucion devuelve una lista vacia.
    """
    target = np.asarray(target_tool0, dtype=float)
    reference = np.zeros(6) if reference_q is None else np.asarray(reference_q, dtype=float)
    found: list[IKSolution] = []
    for candidate in enumerate_candidates(target, reference):
        if not candidate.within_limits:
            continue
        if not fk_check(target, candidate.q, tcp=False).accepted:
            continue
        found.append(
            IKSolution(candidate.q, candidate.arm, candidate.elbow, candidate.wrist, candidate.singular_wrist)
        )

    found.sort(key=lambda solution: float(np.linalg.norm(np.array(solution.q) - reference)))
    unique: list[IKSolution] = []
    for solution in found:
        if not any(np.allclose(solution.q, other.q, atol=1e-9) for other in unique):
            unique.append(solution)
    return unique


def tool0_from_tcp(target_tcp: Matrix4) -> Matrix4:
    """T_tool0 = T_tcp * Tz(TCP_Z_M)^-1."""
    return np.asarray(target_tcp, dtype=float) @ np.linalg.inv(tcp_transform())


def inverse_kinematics_tcp(
    target_tcp: Matrix4,
    reference_q: np.ndarray | None = None,
) -> list[IKSolution]:
    """Igual que inverse_kinematics pero para la pose del TCP."""
    return inverse_kinematics(tool0_from_tcp(target_tcp), reference_q)


# --------------------------------------------------------------------------- analisis de una pose


@dataclass(frozen=True)
class PoseReport:
    """Todo lo que Pieper + FK dicen sobre una pose objetivo del TCP."""

    target_tcp: Matrix4
    target_tool0: Matrix4
    wrist_center: NDArray[np.float64]
    shoulder_to_wrist_m: float
    candidates: tuple[Candidate, ...]
    checks: tuple[FKCheck | None, ...]  # FK de q_raw (o de q si existe); None si la rama no es real

    def accepted(self, candidate: Candidate) -> bool:
        check = self.checks[candidate.branch - 1]
        return candidate.within_limits and check is not None and check.accepted

    @property
    def admissible(self) -> list[Candidate]:
        return [candidate for candidate in self.candidates if self.accepted(candidate)]

    @property
    def geometrically_reachable(self) -> bool:
        return any(candidate.real for candidate in self.candidates)

    @property
    def reachable(self) -> bool:
        return bool(self.admissible)

    @property
    def verdict(self) -> str:
        if self.reachable:
            return f"ALCANZABLE: {len(self.admissible)} de 8 ramas son admisibles."
        if not self.geometrically_reachable:
            return (
                "NO ALCANZABLE: la distancia hombro-muneca "
                f"{self.shoulder_to_wrist_m:.4f} m esta fuera de "
                f"[{REACH_MIN_M:.4f}, {REACH_MAX_M:.4f}] m."
            )
        blocked = sorted({joint for c in self.candidates if c.real for joint in c.out_of_limits})
        return (
            "NO ALCANZABLE: existe geometricamente, pero todas las ramas violan limites "
            f"articulares (juntas {blocked})."
        )

    def table(self) -> list[dict]:
        """Filas listas para imprimir: una por rama."""
        rows = []
        for candidate in self.candidates:
            check = self.checks[candidate.branch - 1]
            q = candidate.q if candidate.q is not None else candidate.q_raw
            rows.append(
                {
                    "rama": candidate.branch,
                    "brazo": candidate.arm,
                    "codo": candidate.elbow,
                    "muneca": candidate.wrist,
                    "real": candidate.real,
                    "en_limites": candidate.within_limits,
                    "fuera_de_limites": candidate.out_of_limits,
                    "q_deg": None if q is None else tuple(np.rad2deg(q)),
                    "e_p_m": None if check is None else check.position_error_m,
                    "e_R_rad": None if check is None else check.rotation_error_rad,
                    "aceptada": self.accepted(candidate),
                    "muneca_singular": candidate.singular_wrist,
                }
            )
        return rows


def analyze_pose(target_tcp: Matrix4, reference_q: np.ndarray | None = None) -> PoseReport:
    """Enumera las 8 ramas para una pose del TCP, las verifica por FK y decide si es alcanzable."""
    target_tcp = assert_rigid_transform(target_tcp)
    target_tool0 = tool0_from_tcp(target_tcp)
    candidates = enumerate_candidates(target_tool0, reference_q)
    checks = tuple(
        None
        if not candidate.real
        else fk_check(target_tcp, candidate.q if candidate.q is not None else candidate.q_raw)
        for candidate in candidates
    )
    center = wrist_center(target_tool0)
    distance = float(hypot(hypot(center[0], center[1]), center[2] - D1))
    return PoseReport(target_tcp, target_tool0, center, distance, tuple(candidates), checks)


@dataclass(frozen=True)
class BranchDecision:
    """Las metricas de una rama para decidir cual se usa en la trayectoria."""

    candidate: Candidate
    admissible: bool
    sigma_min: float  # sigma_min(J) en la rama (nan si no es admisible)
    limit_margin_deg: float  # menor distancia de alguna junta a su limite [deg]
    weighted_cost: float  # ||W (q - q_ref)||
    lspb_tf: float  # duracion del LSPB desde q_ref con los limites por defecto [s]
    status: str  # "ELEGIDA", "apta", o el motivo de descarte
    rank: int | None  # 1 = la elegida; None si se descarta


def limit_margin_deg(q) -> float:
    """Menor margen articular de la configuracion: min_i min(q_i - lo_i, hi_i - q_i), en grados."""
    q = np.asarray(q, dtype=float)
    return float(np.rad2deg(np.min(np.minimum(q - LIMITS_RAD[:, 0], LIMITS_RAD[:, 1] - q))))


DEFAULT_WEIGHTS = np.array([1.0, 1.0, 1.0, 0.5, 0.5, 0.5])


def rank_candidates(
    report: PoseReport,
    reference_q: np.ndarray,
    weights: np.ndarray | None = None,
    min_sigma: float = 1.0e-2,
    min_margin_deg: float = 5.0,
) -> list[BranchDecision]:
    """Evalua las 8 ramas y las ordena segun el criterio de seleccion del proyecto.

    Criterio (filtros en orden, luego costo):
      1. Admisible: real, dentro de limites y verificada por FK (obligatorio).
      2. Lejos de singularidad: sigma_min(J) >= min_sigma.
      3. Lejos de los topes: margen articular >= min_margin_deg en las 6 juntas.
      4. Entre las que pasan 1-3: menor desplazamiento ponderado ||W (q - q_ref)||;
         desempate por mayor sigma_min.
    Si ninguna rama admisible pasa 2 y 3, se relaja primero el margen y luego sigma_min
    (y el estado lo indica), para no quedarse sin solucion cuando la pose si es alcanzable.
    """
    from irb120.jacobian import smallest_singular_value  # evita import circular
    from irb120.lspb import default_limits, plan_lspb

    reference = np.asarray(reference_q, dtype=float)
    w = DEFAULT_WEIGHTS if weights is None else np.asarray(weights, dtype=float)
    vmax, amax = default_limits()
    rows = []
    for candidate in report.candidates:
        if not report.accepted(candidate):
            if not candidate.real:
                reason = "descartada: no existe (|c| > 1)"
            elif not candidate.within_limits:
                reason = "descartada: fuera de limites J" + ",".join(map(str, candidate.out_of_limits))
            else:
                reason = "descartada: no pasa la FK"
            rows.append([candidate, False, np.nan, np.nan, np.nan, np.nan, reason])
            continue
        q = np.array(candidate.q)
        rows.append([
            candidate, True, smallest_singular_value(q), limit_margin_deg(q),
            float(np.linalg.norm(w * (q - reference))), plan_lspb(reference, q, vmax, amax).tf, "",
        ])

    admissible = [r for r in rows if r[1]]
    for relax_margin, relax_sigma, note in ((False, False, ""), (True, False, " (margen relajado)"),
                                            (True, True, " (margen y sigma relajados)")):
        pool = [r for r in admissible
                if (relax_sigma or r[2] >= min_sigma) and (relax_margin or r[3] >= min_margin_deg)]
        if pool or not admissible:
            break
    for r in admissible:
        if r not in pool:
            r[6] = ("descartada: cerca de singularidad (sigma_min < %.3g)" % min_sigma if r[2] < min_sigma
                    else "descartada: a menos de %.0f deg de un limite" % min_margin_deg)
    pool.sort(key=lambda r: (r[4], -r[2]))
    decisions, rank_of = [], {id(r): i + 1 for i, r in enumerate(pool)}
    for r in rows:
        rank = rank_of.get(id(r))
        status = r[6] or ("ELEGIDA" + note if rank == 1 else f"apta (puesto {rank})")
        decisions.append(BranchDecision(r[0], r[1], r[2], r[3], r[4], r[5], status, rank))
    return decisions


def select_solution(
    report: PoseReport,
    reference_q: np.ndarray,
    weights: np.ndarray | None = None,
    min_sigma: float = 1.0e-2,
    min_margin_deg: float = 5.0,
) -> Candidate | None:
    """La rama elegida por `rank_candidates` (puesto 1), o None si la pose no es alcanzable."""
    for decision in rank_candidates(report, reference_q, weights, min_sigma, min_margin_deg):
        if decision.rank == 1:
            return decision.candidate
    return None
