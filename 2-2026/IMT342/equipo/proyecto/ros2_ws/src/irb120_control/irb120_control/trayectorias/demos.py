"""Trayectorias de exhibición para la demo en vivo: se regeneran y verifican con
`python -m irb120_control.trayectorias.demos [--sin-escribir] [carpeta]`.

Todas: puntos dados en ÁNGULOS (q), tipo «articular» en cada punto (valen también con un módulo antiguo que solo
hace MoveAbsJ), ciclo cerrado y repetición en bucle (repeticiones = 0). Volumen seguro (se comprueba en las muestras
de cada plan, no solo en los puntos): márgenes ≥ 15° a los límites de dh.py, |q5| ≥ 20° (lejos de la singularidad
de muñeca), TCP a z ≥ 200 mm sobre la base, |q1| ≤ 90° (nunca por detrás), J2 en [−30°, 40°], J3 en [−60°, 30°].
Duración de una vuelta de 6 a 20 s a velocidad del 25 %. Se verifica desde el reposo del panel
(q = [0, 0, 0, 0, 30, 0]) y desde el primer punto (vueltas siguientes del bucle).
"""
import math
from pathlib import Path
import sys

import numpy as np

from irb120_control.analisis.modelo import hito2
from irb120_control.panel.cinematica import pose_of
from irb120_control.trayectorias import Punto, Trayectoria, planificar

try:
    from irb120_conexion.rutas import PROJECT
except Exception:  # fuera del árbol del proyecto
    PROJECT = Path(__file__).resolve().parents[5]
CARPETA = Path(PROJECT) / 'salidas' / 'trayectorias'

REPOSO = [0., 0., 0., 0., 30., 0.]
VELOCIDAD_PCT = 25.
DURACION_S = (6., 20.)
Q1_MAX, J2_RANGO, J3_RANGO, Q5_MIN, Z_MIN_MM, MARGEN_MIN = 90., (-30., 40.), (-60., 30.), 20., 200., 15.

ARRIBA = [0, 10, -20, 0, 45, 0]      # brazo levantado al frente (TCP ≈ 514, 0, 550 mm)


# ------------------------------------------------------------------ definiciones

def _saludo():
    alto = [0, 5, -40, 0, 50, 0]
    der, izq = [0, 5, -40, 50, 50, -30], [0, 5, -40, -50, 50, 30]
    nombres = ['Reposo arriba', 'Brazo alto'] + [f'Saludo {i}{l}' for i in (1, 2, 3) for l in 'ab'] + ['Baja']
    qs = [ARRIBA, alto, der, izq, der, izq, der, izq, ARRIBA[:1] + [8, -30, 0, 45, 0]]
    return 'Saludo', nombres, qs


def _reverencia():
    nombres = ['Erguido', 'Inclina un poco', 'Inclina', 'Giro a', 'Giro b', 'Giro c', 'Giro d', 'Centra',
               'Se alza a medias', 'Se incorpora']
    h = [0, 24, -28, 0, 46]       # inclinada: el brazo se adelanta y el antebrazo queda casi vertical
    qs = [[0, 0, -10, 0, 40, 0], [0, 14, -22, 0, 43, 0], h + [0], h + [60], h + [-60], h + [60], h + [-60],
          h + [0], [0, 12, -22, 0, 43, 0], [0, 4, -15, 0, 41, 0]]
    return 'Reverencia', nombres, qs


def _mirar_alrededor():
    nombres = ['Frente', 'Mira izquierda', 'Izquierda arriba', 'Mira derecha', 'Derecha arriba', 'Vuelve']
    qs = [ARRIBA, [-75, 10, -20, -30, 35, 0], [-75, 5, -35, -30, 60, 0], [75, 10, -20, 30, 35, 0],
          [75, 5, -35, 30, 60, 0], [30, 10, -20, 0, 45, 0]]
    return 'Mirar alrededor', nombres, qs


def _ocho(n=14, x=450., zc=550., ay=110., az=70.):
    """Lemniscata de Gerono en el plano vertical x = const: y = ay·sin t, z = zc + az·sin t·cos t, con la
    orientación de la herramienta fija (la de ARRIBA). Cinemática inversa de Pieper vía el planificador."""
    roll, pitch, yaw = pose_of(ARRIBA)[3:]
    puntos = []
    for k in range(n):
        t = 2 * math.pi * k / n
        pose = [x, ay * math.sin(t), zc + az * 2 * math.sin(t) * math.cos(t), roll, pitch, yaw]
        puntos.append(Punto(f'Ocho {k + 1}', pose=pose))
    plan = planificar(Trayectoria('Ocho', puntos, cerrar=False), ARRIBA, VELOCIDAD_PCT)
    qs = [[round(v, 2) for v in q] for q in plan.q_puntos]
    if any(not q for q in qs):
        raise ValueError('Algún punto del ocho no tiene solución de IK: ' + plan.resumen)
    return 'Ocho', [p.nombre for p in puntos], qs


def _baile():
    nombres = ['Inicio', 'Balanceo der', 'Balanceo izq', 'Balanceo der 2', 'Inclina', 'Giro der', 'Giro izq',
               'Brazo alto', 'Saludo der', 'Saludo izq', 'Final']
    qs = [ARRIBA, [25, 15, -30, 40, 45, -40], [-25, 15, -30, -40, 45, 40], [25, 15, -30, 40, 45, -40],
          [0, 20, -26, 0, 44, 0], [0, 20, -26, 0, 44, 60], [0, 20, -26, 0, 44, -60], [0, 0, -38, 0, 48, 0],
          [0, 5, -40, 45, 50, -30], [0, 5, -40, -45, 50, 30], [0, 10, -25, 0, 45, 0]]
    return 'Baile', nombres, qs


DEMOS = (('10_saludo', _saludo), ('11_reverencia', _reverencia), ('12_mirar_alrededor', _mirar_alrededor),
         ('13_ocho', _ocho), ('14_baile', _baile))


def construir(fabrica):
    nombre, nombres, qs = fabrica()
    puntos = [Punto(nom, pose=[round(v, 3) for v in pose_of(q, 'tcp')], q=[float(v) for v in q],
                    origen='angulos', tipo='articular') for nom, q in zip(nombres, qs)]
    return Trayectoria(nombre, puntos, cerrar=True, repeticiones=0, herramienta='tcp')


# ------------------------------------------------------------------ verificación

def _evaluar(tray, q0):
    """Plan desde q0 y métricas sobre las muestras elegidas: (plan, dict, problemas)."""
    plan = planificar(tray, q0, VELOCIDAD_PCT)
    problemas = []
    if not plan.ok:
        return plan, {}, [f'plan no apto: {plan.resumen}']
    lim = hito2()['dh'].JOINT_LIMITS_DEG
    sig, marg, z, q5 = [], [], [], []
    q_todo = []
    for tramo in plan.tramos:
        ev = tramo.opciones.get(tramo.tipo)
        if tramo.tipo != 'articular':
            problemas.append(f'tramo {tramo.indice + 1} no articular')
        for r in (ev.avisos() if ev else []):
            problemas.append(f'aviso en tramo {tramo.indice + 1}: {r.nombre}: {r.detalle}')
        m = ev.muestras if ev else None
        if m is None:
            continue
        sig.append(float(np.min(m.sigma)))
        z.append(float(np.min(m.tcp[:, 2])))
        marg.append(float(np.min(np.minimum(m.q - lim[:, 0], lim[:, 1] - m.q))))
        q_todo.append(np.asarray(m.q))
    if q_todo:
        q = np.vstack(q_todo)
        if np.max(np.abs(q[:, 0])) > Q1_MAX:
            problemas.append(f'|q1| llega a {np.max(np.abs(q[:, 0])):.1f}°')
        if q[:, 1].min() < J2_RANGO[0] or q[:, 1].max() > J2_RANGO[1]:
            problemas.append(f'J2 fuera de {J2_RANGO}: {q[:, 1].min():.1f}…{q[:, 1].max():.1f}°')
        if q[:, 2].min() < J3_RANGO[0] or q[:, 2].max() > J3_RANGO[1]:
            problemas.append(f'J3 fuera de {J3_RANGO}: {q[:, 2].min():.1f}…{q[:, 2].max():.1f}°')
        q5 = float(np.min(np.abs(q[:, 4])))
        if q5 < Q5_MIN:
            problemas.append(f'|q5| baja a {q5:.1f}°')
    res = {'duracion_s': plan.duracion_s, 'sigma_min': min(sig, default=float('nan')),
           'margen_min': min(marg, default=float('nan')), 'z_min': min(z, default=float('nan'))}
    if min(marg, default=99.) < MARGEN_MIN:
        problemas.append(f'margen a límites {res["margen_min"]:.1f}° < {MARGEN_MIN:g}°')
    if min(z, default=999.) < Z_MIN_MM:
        problemas.append(f'z mínima {res["z_min"]:.0f} mm < {Z_MIN_MM:g} mm')
    return plan, res, problemas


def verificar(tray):
    """Verifica desde el reposo y desde el primer punto. Devuelve (resumen, problemas)."""
    problemas = []
    _, desde_reposo, p = _evaluar(tray, REPOSO)
    problemas += [f'[desde el reposo] {x}' for x in p]
    _, ciclo, p = _evaluar(tray, tray.puntos[0].q)
    problemas += [f'[vuelta en bucle] {x}' for x in p]
    if ciclo and not DURACION_S[0] <= ciclo['duracion_s'] <= DURACION_S[1]:
        problemas.append(f'duración {ciclo["duracion_s"]:.1f} s fuera de {DURACION_S}')
    if tray.repeticiones != 0 or not tray.cerrar or any(pt.tipo != 'articular' for pt in tray.puntos):
        problemas.append('debe ser cerrada, en bucle y con tipo articular en todos los puntos')
    resumen = dict(ciclo) if ciclo else {}
    resumen['ok'] = not problemas
    for k in ('sigma_min', 'margen_min', 'z_min'):   # el peor de las dos evaluaciones
        if ciclo and desde_reposo:
            resumen[k] = min(ciclo[k], desde_reposo[k])
    resumen['duracion_reposo_s'] = desde_reposo.get('duracion_s')
    return resumen, problemas


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    escribir = '--sin-escribir' not in args
    args = [a for a in args if not a.startswith('--')]
    carpeta = Path(args[0]) if args else CARPETA
    if escribir:
        carpeta.mkdir(parents=True, exist_ok=True)
    fallos = 0
    print(f'{"archivo":<22}{"ok":<4}{"vuelta s":>9}{"1ª s":>7}{"σ_min":>8}{"margen°":>9}{"z mín mm":>10}')
    for archivo, fabrica in DEMOS:
        tray = construir(fabrica)
        if escribir:
            tray.guardar(carpeta / f'{archivo}.json')
            tray = Trayectoria.cargar(carpeta / f'{archivo}.json')   # se verifica lo que quedó en disco
        res, problemas = verificar(tray)
        print(f'{archivo:<22}{"sí" if res["ok"] else "NO":<4}{res.get("duracion_s", float("nan")):>9.1f}'
              f'{res.get("duracion_reposo_s") or float("nan"):>7.1f}{res.get("sigma_min", float("nan")):>8.3f}'
              f'{res.get("margen_min", float("nan")):>9.1f}{res.get("z_min", float("nan")):>10.0f}')
        for x in problemas:
            print('   ·', x)
        fallos += bool(problemas)
    return 1 if fallos else 0


if __name__ == '__main__':
    raise SystemExit(main())
