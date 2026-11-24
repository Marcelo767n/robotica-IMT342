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


def seis(v):
    """Lista de 6 números o None."""
    try:
        if len(v) == 6:
            return [float(x) for x in v]
    except (TypeError, ValueError):
        pass
    return None
