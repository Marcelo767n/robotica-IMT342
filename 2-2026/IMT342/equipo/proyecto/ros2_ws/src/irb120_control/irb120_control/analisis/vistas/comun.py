"""Piezas compartidas por las pestañas: tablas, matrices y figuras."""
import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

VERDE, ROJO, GRIS = '#15803d', '#b91c1c', '#6b7280'
COLORES_EJES = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
MONO = ('DejaVu Sans Mono', 11)


def fmt(value, decimals=4, unit=''):
    if value is None:
        return '—'
    return f'{value:.{decimals}f}{unit}'


def sci(value, unit=''):
    return '—' if value is None else f'{value:.2e}{unit}'


def tabla(parent, columnas, alto=8, anchos=None):
    tree = ttk.Treeview(parent, columns=columnas, show='headings', height=alto)
    for i, col in enumerate(columnas):
        tree.heading(col, text=col)
        tree.column(col, width=(anchos[i] if anchos else 95), anchor='center')
    tree.tag_configure('ok', foreground=VERDE)
    tree.tag_configure('mal', foreground=ROJO)
    tree.tag_configure('elegida', background='#fde68a')
    tree.tag_configure('gris', foreground=GRIS)
    return tree


def llenar(tree, filas):
    """filas: lista de (valores, tag)."""
    tree.delete(*tree.get_children())
    for valores, tag in filas:
        tree.insert('', 'end', values=valores, tags=(tag,) if tag else ())


def matriz(parent, titulo):
    frame = ttk.LabelFrame(parent, text=titulo, padding=6)
    label = tk.Label(frame, font=MONO, justify='left', anchor='w')
    label.pack(fill='x')
    return frame, label


def texto_matriz(T, decimales=6):
    return '\n'.join('  '.join(f'{v:+{decimales + 4}.{decimales}f}' for v in row) for row in T)


def indicador(parent, texto):
    label = tk.Label(parent, text=texto, font=('DejaVu Sans', 13, 'bold'), anchor='w')
    return label


def pintar(label, ok, texto):
    label.configure(text=('●  ' if ok else '✖  ') + texto, fg=VERDE if ok else ROJO)


def figura(parent, filas=1, columnas=1, alto=7.):
    fig = Figure(figsize=(12., alto), dpi=90, constrained_layout=True)
    axes = fig.subplots(filas, columnas, squeeze=False)
    canvas = FigureCanvasTkAgg(fig, master=parent)
    canvas.get_tk_widget().pack(fill='both', expand=True)
    return fig, axes, canvas
