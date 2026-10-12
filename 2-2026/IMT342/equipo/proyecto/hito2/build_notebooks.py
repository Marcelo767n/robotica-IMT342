"""Genera y ejecuta los tres notebooks del Hito 2.  Uso (desde hito2/):  python build_notebooks.py"""
import runpy
from pathlib import Path

import nbformat as nbf

md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
OUT = Path(__file__).parent / "notebooks"
OUT.mkdir(exist_ok=True)

SETUP = """import sys
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore", message="Unable to import Axes3D")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path.cwd().resolve().parent))   # carpeta hito2/ (paquete irb120)
np.set_printoptions(precision=4, suppress=True)
"""


def save(name, cells):
    notebook = nbf.v4.new_notebook(cells=cells)
    notebook.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nbf.write(notebook, OUT / name)
    print("escrito", OUT / name)


# --------------------------------------------------------------------------- 01 Pieper
save("01_cinematica_inversa_pieper.ipynb", [
md("""# Notebook 1 · Cinemática inversa del ABB IRB 120 por el método de Pieper

**IMT-342 Robótica · Hito 2.** Dada la pose deseada del efector, calcular los seis ángulos articulares **de forma analítica**
(sin MoveIt ni resolvedores numéricos).

**Idea.** Los ejes 4, 5 y 6 se cortan en un punto, el *centro de muñeca* $p_{wc}=p_{tool0}-d_6\\,z_6$, que solo depende de $q_1,q_2,q_3$.

1. **Posición** ($q_1,q_2,q_3$): $q_1=\\operatorname{atan2}(y,x)$ (o $+\\pi$) y, en el plano del brazo, ley de cosenos con $L_2=0.270$, $L_3=\\sqrt{d_4^2+a_3^2}$.
2. **Orientación** ($q_4,q_5,q_6$): $R_3^6=R_0^{3\\,T}R=R_z(q_4)R_y(-q_5)R_z(q_6+\\pi)$, un Euler ZYZ.
3. Resultan **hasta 8 soluciones** (2 brazo × 2 codo × 2 muñeca); se filtran por límites articulares y se comprueban con la cinemática directa."""),
code(SETUP + """
from irb120.dh import forward_kinematics, forward_kinematics_tcp, position_error_m, rotation_error_rad, DH_PARAMETERS
from irb120.pieper import inverse_kinematics, inverse_kinematics_tcp, LIMITS_RAD
from irb120.transforms import rpy_to_matrix, pose_matrix
from irb120.jacobian import joint_frames

print("Tabla DH (d, a, alpha, offset):")
for i, p in enumerate(DH_PARAMETERS, 1):
    print(f"  eje {i}: d={p.d_m:.3f}  a={p.a_m:.3f}  alpha={np.rad2deg(p.alpha_rad):7.1f} deg  offset={np.rad2deg(p.theta_offset_rad):6.1f} deg")"""),
md("## 1. Ida y vuelta: FK → IK\nSe parte de una postura conocida, se calcula la pose del TCP y se resuelve la IK tomando la postura original como referencia."),
code("""q = np.deg2rad([30, -20, 15, 40, -35, 60])
T = forward_kinematics_tcp(q)
print("Pose del TCP:\\n", T)
solutions = inverse_kinematics_tcp(T, q)
print(f"\\n{len(solutions)} soluciones validas:")
for s in solutions:
    reached = forward_kinematics_tcp(np.array(s.q))
    print(f"  {s.arm:6s}/{s.elbow:6s}/{s.wrist}  q [deg] = {np.rad2deg(s.q).round(2)}  error pos = {position_error_m(T, reached):.1e} m")
assert np.allclose(solutions[0].q, q, atol=1e-6)"""),
md("## 2. Las configuraciones alcanzan la misma pose\nVista lateral (x–z) del brazo en cada solución: configuraciones distintas, mismo efector."),
code("""def skeleton(q):
    frames = joint_frames(q)
    pts = [f[:3, 3] for f in frames]
    flange = frames[6]
    tcp = (flange @ np.array([0, 0, 0.100, 1]))[:3]
    return np.array(pts + [tcp])

fig, axes = plt.subplots(1, len(solutions), figsize=(3.2 * len(solutions), 3.6), sharey=True)
for axis, s in zip(np.atleast_1d(axes), solutions):
    pts = skeleton(np.array(s.q))
    axis.plot(pts[:, 0], pts[:, 2], "o-", lw=2)
    axis.plot(*pts[-1][[0, 2]], "r*", ms=12)
    axis.set_title(f"{s.arm}/{s.elbow}/{s.wrist}", fontsize=9); axis.set_aspect("equal"); axis.grid(alpha=.3)
    axis.set_xlabel("x [m]")
plt.tight_layout(); plt.show()"""),
md("## 3. Pose objetivo con la pinza hacia abajo\nCaso típico de pick & place: TCP en $(0.25,-0.15,0.30)$ m con el eje Z de la pinza apuntando a la mesa."),
code("""target = pose_matrix((0.25, -0.15, 0.30), rpy_to_matrix(0, np.pi, 0))
sols = inverse_kinematics_tcp(target, np.zeros(6))
best = sols[0]
print("soluciones:", len(sols), "| elegida:", best.arm, best.elbow, best.wrist)
print("q [deg] =", np.rad2deg(best.q).round(2))
print("TCP alcanzado [m] =", forward_kinematics_tcp(np.array(best.q))[:3, 3])
assert position_error_m(target, forward_kinematics_tcp(np.array(best.q))) < 1e-9"""),
md("## 4. Poses fuera del alcance\nSi la ley de cosenos da un valor fuera de $[-1,1]$ o ninguna solución respeta los límites, la lista queda vacía."),
code("""far = np.eye(4); far[:3, 3] = [2.0, 0.0, 0.5]
print("Pose a 2 m de la base ->", inverse_kinematics(far), "(sin solucion)")
near = np.eye(4); near[:3, 3] = [0.05, 0.0, 0.2]
print("Pose pegada a la base  ->", len(inverse_kinematics(near)), "soluciones")"""),
md("## 5. Validación estadística\n1000 posturas aleatorias dentro de los límites del robot: la IK debe devolver la original y todas las soluciones deben reproducir la pose."),
code("""rng = np.random.default_rng(342)
worst_pos = worst_rot = 0.0
counts, recovered = [], 0
for _ in range(1000):
    qr = rng.uniform(LIMITS_RAD[:, 0], LIMITS_RAD[:, 1])
    Tr = forward_kinematics(qr)
    sols = inverse_kinematics(Tr, qr)
    counts.append(len(sols))
    recovered += bool(sols) and np.allclose(sols[0].q, qr, atol=1e-6)
    for s in sols:
        reached = forward_kinematics(np.array(s.q))
        worst_pos = max(worst_pos, position_error_m(Tr, reached))
        worst_rot = max(worst_rot, rotation_error_rad(Tr, reached))
print(f"postura original recuperada: {recovered}/1000")
print(f"peor error de posicion:    {worst_pos:.2e} m   (limite del proyecto: 1e-6 m)")
print(f"peor error de orientacion: {worst_rot:.2e} rad")
assert recovered == 1000 and worst_pos < 1e-6

plt.figure(figsize=(5, 3)); plt.hist(counts, bins=np.arange(0.5, 9.5, 1), rwidth=.8)
plt.xlabel("soluciones validas por pose"); plt.ylabel("posturas"); plt.title("Cuantas soluciones hay por pose"); plt.show()"""),
md("""## Conclusión
- La IK analítica recupera la postura original en las 1000 pruebas, con errores del orden de $10^{-16}$ m, muy por debajo del límite de $10^{-6}$ m.
- Hay hasta 8 soluciones; menos cuando los límites articulares descartan algunas. En el robot se elige la más cercana a la postura actual.
- Los puntos fuera del alcance se detectan sin excepciones: lista vacía."""),
])

# --------------------------------------------------------------------------- 02 LSPB
save("02_trayectorias_lspb.ipynb", [
md("""# Notebook 2 · Perfiles de trayectoria LSPB (Linear Segment with Parabolic Blends)

**IMT-342 Robótica · Hito 2.** Dada la postura actual $q_0$ y la meta $q_f$ (salida de Pieper), generar una trayectoria **suave**: arranque parabólico a aceleración constante, tramo lineal a velocidad constante y frenado simétrico.

Todas las juntas comparten el tiempo total $t_f$ y el tiempo de mezcla $t_b$, así que llegan a la vez:

$$V_i=\\frac{\\Delta_i}{t_f-t_b},\\qquad a_i=\\frac{V_i}{t_b}$$

El menor $t_f$ factible respeta $|V_i|\\le v_{max,i}$ y $|a_i|\\le a_{max,i}$ y se halla por bisección."""),
code(SETUP + """
from irb120.lspb import plan_lspb
from irb120.dh import forward_kinematics_tcp

VMAX = np.deg2rad([250, 250, 250, 320, 320, 420])     # limites ABB IRB 120 [rad/s]
q0 = np.zeros(6)
qf = np.deg2rad([60, -40, 20, 90, 30, -120])"""),
md("## 1. Planificación con el 30 % de la velocidad máxima y 3 rad/s²"),
code("""traj = plan_lspb(q0, qf, VMAX * 0.3, 3.0)
print(f"tf = {traj.tf:.3f} s   tb = {traj.tb:.3f} s")
print("velocidad de crucero [deg/s]:", np.rad2deg(traj.cruise_velocity).round(1))
print("aceleracion de mezcla [rad/s2]:", traj.blend_acceleration.round(3))
print("junta que satura la aceleracion:", int(np.argmax(np.abs(traj.blend_acceleration))) + 1)"""),
md("## 2. Perfiles de posición, velocidad y aceleración"),
code("""t = np.linspace(0, traj.tf, 500)
q, v, a = (np.degrees(np.array([traj.sample(x)[i] for x in t])) for i in range(3))
fig, ax = plt.subplots(1, 3, figsize=(14, 3.8))
for axis, data, title in zip(ax, (q, v, a), ("Posicion [deg]", "Velocidad [deg/s]", "Aceleracion [deg/s²]")):
    axis.plot(t, data); axis.axvline(traj.tb, c="gray", ls=":"); axis.axvline(traj.tf - traj.tb, c="gray", ls=":")
    axis.set(xlabel="t [s]", title=title); axis.grid(alpha=.3)
ax[0].legend([f"J{i+1}" for i in range(6)], ncol=2, fontsize=8)
plt.tight_layout(); plt.show()"""),
md("## 3. Comprobaciones: extremos en reposo, continuidad y sincronía"),
code("""start, end = traj.sample(0.0), traj.sample(traj.tf)
assert np.allclose(start[0], q0) and np.allclose(end[0], qf)
assert np.allclose(start[1], 0) and np.allclose(end[1], 0)
for instant in (traj.tb, traj.tf - traj.tb):
    before, after = traj.sample(instant - 1e-9), traj.sample(instant + 1e-9)
    assert np.allclose(before[0], after[0], atol=1e-6) and np.allclose(before[1], after[1], atol=1e-6)
assert np.allclose(traj.sample(traj.tf / 2)[0], (q0 + qf) / 2)           # todas llegan a la vez
times = np.linspace(0, traj.tf, 4001)
vel = np.array([traj.sample(x)[1] for x in times])
integral = np.sum(0.5 * (vel[1:] + vel[:-1]) * np.diff(times)[:, None], axis=0)
assert np.allclose(integral, qf - q0, atol=1e-5)
assert np.all(np.abs(traj.cruise_velocity) <= VMAX * 0.3 + 1e-9) and np.all(np.abs(traj.blend_acceleration) <= 3.0 + 1e-9)
print("OK: reposo en los extremos, continuidad C1, sincronia, integral de v = Delta q y limites respetados")"""),
md("## 4. Efecto de la velocidad y de la aceleración máximas"),
code("""print(f"{'speed_scale':>12} {'amax':>6} {'tf [s]':>8} {'tb [s]':>8}")
rows = []
for scale in (0.1, 0.3, 0.6, 1.0):
    for amax in (1.0, 3.0, 8.0):
        tr = plan_lspb(q0, qf, VMAX * scale, amax)
        rows.append((scale, amax, tr.tf)); print(f"{scale:12.1f} {amax:6.1f} {tr.tf:8.3f} {tr.tb:8.3f}")
plt.figure(figsize=(5, 3.4))
for amax in (1.0, 3.0, 8.0):
    plt.plot([r[0] for r in rows if r[1] == amax], [r[2] for r in rows if r[1] == amax], "o-", label=f"amax={amax}")
plt.xlabel("fraccion de la velocidad maxima"); plt.ylabel("tf [s]"); plt.legend(); plt.grid(alpha=.3); plt.show()"""),
md("## 5. Trayectoria del TCP resultante\nAl interpolar en el espacio articular el TCP describe una curva suave (no una recta); aquí se proyecta sobre x–z y x–y."),
code("""tcp = np.array([forward_kinematics_tcp(traj.sample(x)[0])[:3, 3] for x in t])
fig, ax = plt.subplots(1, 2, figsize=(9, 3.6))
ax[0].plot(tcp[:, 0], tcp[:, 2]); ax[0].plot(*tcp[0, [0, 2]], "go"); ax[0].plot(*tcp[-1, [0, 2]], "r*", ms=11); ax[0].set(xlabel="x [m]", ylabel="z [m]", title="Vista x-z"); ax[0].grid(alpha=.3)
ax[1].plot(tcp[:, 0], tcp[:, 1]); ax[1].plot(*tcp[0, :2], "go"); ax[1].plot(*tcp[-1, :2], "r*", ms=11); ax[1].set(xlabel="x [m]", ylabel="y [m]", title="Vista x-y"); ax[1].grid(alpha=.3)
plt.tight_layout(); plt.show()
print("TCP inicial [m]:", tcp[0], " final [m]:", tcp[-1])"""),
md("""## Conclusión
- El LSPB parte y termina en reposo, es continuo en posición y velocidad y mantiene todas las juntas sincronizadas.
- El tiempo total lo fija la junta más exigente (la 6 en este ejemplo); las demás reducen velocidad y aceleración para llegar a la vez.
- Subir la velocidad máxima solo acorta $t_f$ hasta que la aceleración pasa a ser el límite."""),
])

# --------------------------------------------------------------------------- 03 singularidad
runpy.run_path(str(Path(__file__).parent / "build_notebook_03.py"))
