"""Pestaña Gráficas: q, q̇, q̈, τ, σ_min y κ de toda la trayectoria concatenada (matplotlib embebido)."""
import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from irb120_control.estudio.datos import concatenar
from irb120_control.estudio.tema import COLORES, color, fuente
from irb120_control.estudio.vistas import Vista
from irb120_control.trayectorias import TOLERANCIAS

COLORES_J = ('#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#a855f7', '#06b6d4')
PANELES = (('q', 'q(t)  [°]'), ('qd', 'q̇(t)  [°/s]'), ('qdd', 'q̈(t)  [°/s²]'), ('tau', 'τ(t)  [N·m]'))


def construir_figura(datos, oscuro, tol=TOLERANCIAS, tam=11, fig=None):
    """Dibuja el plan en una Figure (sin pyplot). datos = datos.concatenar(plan) o None."""
    fig = fig or Figure(figsize=(12, 7.5), dpi=100)
    fig.clear()
    fondo, texto, rejilla = color('tarjeta', oscuro), color('texto', oscuro), color('borde', oscuro)
    fig.set_facecolor(fondo)
    if datos is None:
        fig.text(.5, .5, 'Planifica una trayectoria para ver las gráficas', ha='center', va='center',
                 color=texto, fontsize=tam + 4)
        return fig
    gs = fig.add_gridspec(3, 2, left=.065, right=.985, top=.9, bottom=.07, hspace=.42, wspace=.17)
    ejes = [fig.add_subplot(gs[i // 2, i % 2]) for i in range(6)]
    t = datos['t']
    for ax, (clave, etiqueta) in zip(ejes, PANELES):
        for j in range(6):
            ax.plot(t, datos[clave][:, j], color=COLORES_J[j], lw=1.8, label=f'J{j + 1}')
        ax.set_ylabel(etiqueta, color=texto, fontsize=tam + 1)
    ax = ejes[4]
    ax.plot(t, datos['sigma'], color='#38bdf8' if oscuro else '#0369a1', lw=2)
    ax.axhspan(0, tol.sigma_bloqueo, color=color('falla', oscuro), alpha=.25)
    ax.axhspan(tol.sigma_bloqueo, tol.sigma_aviso, color=color('aviso', oscuro), alpha=.25)
    ax.axhline(tol.sigma_bloqueo, color=color('falla', oscuro), lw=1, ls='--')
    ax.axhline(tol.sigma_aviso, color=color('aviso', oscuro), lw=1, ls='--')
    ax.set_ylim(0, max(float(datos['sigma'].max()) * 1.1, tol.sigma_aviso * 2))
    ax.set_ylabel('σ_min(J)', color=texto, fontsize=tam + 1)
    ax = ejes[5]
    ax.plot(t, datos['cond'], color='#fb7185' if oscuro else '#be123c', lw=2)
    ax.axhline(tol.cond_aviso, color=color('aviso', oscuro), lw=1, ls='--')
    ax.axhline(tol.cond_bloqueo, color=color('falla', oscuro), lw=1, ls='--')
    ax.set_yscale('log')
    ax.set_ylabel('κ(J)', color=texto, fontsize=tam + 1)
    for k, ax in enumerate(ejes):
        ax.set_facecolor(fondo)
        ax.grid(True, color=rejilla, lw=.6, alpha=.8)
        ax.tick_params(colors=texto, labelsize=tam - 1)
        for s in ax.spines.values():
            s.set_color(rejilla)
        if k >= 4:
            ax.set_xlabel('t [s]', color=texto, fontsize=tam)
        ax.set_xlim(0, datos['duracion'])
        for tc, etq in datos['cortes']:
            if tc > 0:
                ax.axvline(tc, color=color('suave', oscuro), lw=1, ls=':')
            if k < 2:
                ax.text(tc, 1.02, etq, transform=ax.get_xaxis_transform(), color=texto, fontsize=tam - 1,
                        ha='left', va='bottom')
    h, l = ejes[0].get_legend_handles_labels()
    fig.legend(h, l, loc='upper center', ncol=6, frameon=False, labelcolor=texto, fontsize=tam + 1,
               bbox_to_anchor=(.5, 1.0))
    return fig


class VistaGraficas(Vista):
    titulo = 'Gráficas'

    def __init__(self, master, ctx):
        self.ctx = ctx
        self.frame = ctk.CTkFrame(master, fg_color=COLORES['tarjeta'], corner_radius=12, border_width=1,
                                  border_color=COLORES['borde'])
        self.fig = Figure(figsize=(12, 7.5), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.widget = self.canvas.get_tk_widget()
        self.widget.pack(fill='both', expand=True, padx=8, pady=8)
        self.sucio = True
        self.dibujar()

    def dibujar(self):
        plan = self.ctx.plan
        datos = concatenar(plan) if plan is not None else None
        construir_figura(datos, self.ctx.oscuro, plan.tolerancias if plan is not None else TOLERANCIAS, fig=self.fig)
        self.frame.configure(fg_color=COLORES['tarjeta'])
        self.canvas.draw_idle()
        self.sucio = False

    def al_cambiar(self, evento):
        if evento in ('plan', 'tema'):
            self.dibujar()

    def exportar(self, ruta):
        self.fig.savefig(ruta, dpi=150, facecolor=self.fig.get_facecolor())
