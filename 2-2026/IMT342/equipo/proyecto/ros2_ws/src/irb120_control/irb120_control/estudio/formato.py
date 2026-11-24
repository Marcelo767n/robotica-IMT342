"""Formato de números para mostrar (coma decimal, «—» si falta)."""


def n(x, dec=2, signo=False):
    if x is None:
        return '—'
    try:
        return f'{float(x):{"+" if signo else ""}.{dec}f}'.replace('.', ',')
    except (TypeError, ValueError):
        return '—'


def lista(v, dec=2):
    try:
        return '  '.join(n(x, dec) for x in v)
    except TypeError:
        return '—'


def texto_vuelta(tr):
    """«vuelta 7 (bucle)», «vuelta 2/3» o None si no hay vuelta en curso (tr = estado de la trayectoria)."""
    if not isinstance(tr, dict) or not tr.get('vuelta'):
        return None
    if tr.get('bucle') or tr.get('vueltas') in (None, 0):
        return f"vuelta {n(tr['vuelta'], 0)} (bucle)"
    return f"vuelta {n(tr['vuelta'], 0)}/{n(tr['vueltas'], 0)}"


def seis(v):
    """Lista de 6 números o None."""
    try:
        if len(v) == 6:
            return [float(x) for x in v]
    except (TypeError, ValueError):
        pass
    return None
