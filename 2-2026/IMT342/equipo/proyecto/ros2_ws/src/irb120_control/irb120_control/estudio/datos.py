"""Muestras de todo el plan concatenadas para las gráficas (puro, sin Tk ni matplotlib)."""
import numpy as np


def muestras_tramo(tramo):
    """Muestras del tipo elegido (o, si faltan, de la otra opción); None si ninguna las tiene."""
    ev = tramo.opciones.get(tramo.tipo)
    if ev is not None and ev.muestras is not None:
        return ev.muestras
    return next((e.muestras for e in tramo.opciones.values() if e.muestras is not None), None)


def concatenar(plan):
    """dict t, q, qd, qdd, tau (N×6), sigma, cond (N,), cortes [(t, 'A→B')]; None si no hay muestras."""
    partes, cortes, t0 = [], [], 0.
    for tr in plan.tramos:
        m = muestras_tramo(tr)
        if m is None:
            continue
        cortes.append((t0, f'{tr.desde}→{tr.hasta}'))
        partes.append((m, t0))
        t0 += float(m.t[-1])
    if not partes:
        return None
    cat = lambda f: np.concatenate([f(m) for m, _ in partes])
    t = np.concatenate([m.t + o for m, o in partes])
    return {'t': t, 'q': cat(lambda m: m.q), 'qd': cat(lambda m: m.qd), 'qdd': cat(lambda m: m.qdd),
            'tau': cat(lambda m: m.tau), 'sigma': cat(lambda m: m.sigma), 'cond': cat(lambda m: m.cond),
            'cortes': cortes, 'duracion': t0}
