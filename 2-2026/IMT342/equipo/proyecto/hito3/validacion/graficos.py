"""Estilo común de figuras (matplotlib, backend Agg, etiquetas en español)."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from . import rutas  # noqa: E402

COLORES = ["#1f4e79", "#c0504d", "#4f8a3c", "#e08a00", "#7b4f9d", "#2a9d9d", "#555555"]


def estilo():
    plt.rcParams.update({
        "figure.dpi": 110, "savefig.dpi": 150, "font.size": 9, "axes.grid": True, "grid.alpha": 0.3,
        "axes.spines.top": False, "axes.spines.right": False, "axes.prop_cycle": matplotlib.cycler(color=COLORES),
        "legend.frameon": False, "figure.constrained_layout.use": True,
    })


def guardar(fig, nombre):
    rutas.FIGURAS.mkdir(parents=True, exist_ok=True)
    ruta = rutas.FIGURAS / nombre
    fig.savefig(ruta)
    plt.close(fig)
    return str(ruta.relative_to(rutas.RAIZ))
