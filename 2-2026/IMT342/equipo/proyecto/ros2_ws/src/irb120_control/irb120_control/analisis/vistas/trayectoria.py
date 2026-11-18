"""Pestaña 3: perfil LSPB del Hito 2 de la postura medida al objetivo."""
from tkinter import ttk

from irb120_control.analisis.vistas.comun import COLORES_EJES, figura, fmt


class VistaTrayectoria:
    titulo = 'Trayectoria LSPB'

    def __init__(self, parent):
        self.frame = ttk.Frame(parent, padding=8)
        self.info = ttk.Label(self.frame, font=('DejaVu Sans', 12, 'bold'))
        self.info.pack(anchor='w')
        ttk.Label(self.frame, text='Perfil planificado con plan_lspb del Hito 2 (tramos parabólicos + crucero, '
                  'ejes sincronizados). vmax = % de velocidad del panel × velocidad máxima ABB; amax = vmax / 0,25 s. '
                  'El robot real ejecuta MoveAbsJ con el planificador propio de ABB: esto es el modelo teórico.',
                  wraplength=1250).pack(anchor='w', pady=(0, 4))
        self.fig, self.axes, self.canvas = figura(self.frame, 1, 3, alto=6.2)

    def actualizar(self, r):
        tr = r['trayectoria']
        ck = tr['check']
        self.info.configure(text=f"tf = {tr['tf']:.3f} s · tb = {tr['tb']:.3f} s · velocidad {r['entrada'].velocidad_pct:.0f} % · "
                                 f"comprobación {'OK' if ck['paso'] else 'FALLA'} (error final {fmt(ck['error_final_deg'], 6, '°')})")
        for ax, key, label in zip(self.axes[0], ('q', 'qd', 'qdd'), ('q (°)', 'dq/dt (°/s)', 'd²q/dt² (°/s²)')):
            ax.clear()
            for i in range(6):
                ax.plot(tr['t'], tr[key][:, i], color=COLORES_EJES[i], label=f'J{i + 1}')
            for x in (tr['tb'], tr['tf'] - tr['tb']):
                ax.axvline(x, color='#9ca3af', lw=.8, ls='--')
            ax.set_xlabel('t (s)'); ax.set_ylabel(label); ax.grid(alpha=.3)
        self.axes[0][0].legend(ncol=3, fontsize=8)
        self.axes[0][0].set_title('Posición'); self.axes[0][1].set_title('Velocidad'); self.axes[0][2].set_title('Aceleración')
        self.canvas.draw_idle()
