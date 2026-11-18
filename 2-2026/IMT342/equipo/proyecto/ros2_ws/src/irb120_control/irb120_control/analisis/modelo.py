"""Acceso al paquete del Hito 2 (hito2/irb120): el mismo código que se presentó y se probó."""
import sys

from irb120_conexion.rutas import PROJECT


def hito2():
    path = str(PROJECT / 'hito2')
    if path not in sys.path:
        sys.path.insert(0, path)
    from irb120 import dh, dynamics, dynamics_1r, jacobian, lspb, pieper, transforms, validation
    return {'dh': dh, 'dynamics': dynamics, 'dynamics_1r': dynamics_1r, 'jacobian': jacobian,
            'lspb': lspb, 'pieper': pieper, 'transforms': transforms, 'validation': validation}
