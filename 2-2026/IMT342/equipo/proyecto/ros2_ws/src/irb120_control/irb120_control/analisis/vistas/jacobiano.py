"""Pestaña 4: Jacobiano geométrico en el objetivo y σ_min a lo largo de la trayectoria."""
from tkinter import ttk

from irb120_control.analisis.calculos import SINGULAR_SIGMA
from irb120_control.analisis.vistas.comun import figura, indicador, matriz, pintar, texto_matriz


class VistaJacobiano:
    titulo = 'Jacobiano y singularidad'

    def __init__(self, parent):
        self.frame = ttk.Frame(parent, padding=8)
        top = ttk.Frame(self.frame)
        top.pack(fill='x')
        f, self.j = matriz(top, 'J(q_objetivo) 6×6 · filas v (m/s) y ω (rad/s) por rad/s de cada eje')
        f.pack(side='left', fill='x', expand=True)
        self.metricas = ttk.Label(top, font=('DejaVu Sans', 12), justify='left')
        self.metricas.pack(side='left', padx=16, anchor='n')
        self.ind = indicador(self.frame, '')
        self.ind.pack(fill='x', pady=6)
        self.fig, self.axes, self.canvas = figura(self.frame, alto=3.6)

    def actualizar(self, r):
        j = r['jacobiano']
        self.j.configure(text=texto_matriz(j['J'], 4))
        self.metricas.configure(text=f"det J = {j['det']:+.3e}\nσ_min = {j['sigma_min']:.4f}\n"
                                     f"número de condición = {j['condicion']:.1f}\nrango = {j['rango']} de 6\n"
                                     f"σ = {', '.join(f'{s:.3f}' for s in j['sigma'])}")
        pintar(self.ind, not j['singular'], f"σ_min a lo largo de la LSPB: mínimo {j['sigma_t'].min():.4f} "
               f"({'lejos de' if not j['singular'] else 'CERCA DE'} singularidad; umbral {SINGULAR_SIGMA})")
        ax = self.axes[0][0]
        ax.clear()
        ax.plot(j['t_sigma'], j['sigma_t'], color='#1f77b4', label='σ_min(J(q(t)))')
        ax.axhline(SINGULAR_SIGMA, color='#b91c1c', ls='--', label='umbral de singularidad')
        ax.set_xlabel('t (s)'); ax.set_ylabel('σ_min'); ax.grid(alpha=.3); ax.legend()
        self.canvas.draw_idle()
