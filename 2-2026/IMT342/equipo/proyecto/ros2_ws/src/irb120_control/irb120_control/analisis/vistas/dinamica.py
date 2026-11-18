"""Pestaña 5: pares articulares a lo largo de la LSPB (modelo completo y modelo 1R del hombro)."""
from tkinter import ttk

from irb120_control.analisis.vistas.comun import COLORES_EJES, figura, llenar, tabla


class VistaDinamica:
    titulo = 'Dinámica'

    def __init__(self, parent):
        self.frame = ttk.Frame(parent, padding=8)
        self.info = ttk.Label(self.frame, font=('DejaVu Sans', 12, 'bold'))
        self.info.pack(anchor='w')
        ttk.Label(self.frame, text='τ = M(q)·(d²q/dt²) + c(q, dq/dt) + g(q) con los parámetros de Truc y Lam (2020) + pinza; '
                  'modelo 1R del Hito 2: τ = J·(d²θ/dt²) + m·g·lc·sin θ con J3–J6 congeladas en la postura inicial.',
                  wraplength=1250).pack(anchor='w')
        self.tabla = tabla(self.frame, ('', 'J1', 'J2', 'J3', 'J4', 'J5', 'J6'), alto=1,
                           anchos=(170, 95, 95, 95, 95, 95, 95))
        self.tabla.pack(anchor='w', pady=4)
        self.fig, self.axes, self.canvas = figura(self.frame, 1, 2, alto=5.6)

    def actualizar(self, r):
        d = r['dinamica']
        m = d['modelo_1r']
        self.info.configure(text=f"Hombro J2 · 1R: máx {d['j2_1r_max']:.2f} N·m · completo: máx {d['j2_completo_max']:.2f} N·m"
                                 f" · m = {m['m_kg']:.2f} kg, lc = {m['lc_m'] * 1000:.0f} mm, J = {m['J_kg_m2']:.3f} kg·m²")
        llenar(self.tabla, [(('|τ| máx (N·m)', *[f'{v:.2f}' for v in d['tau_max']]), '')])
        a, b = self.axes[0]
        a.clear(); b.clear()
        for i in range(6):
            a.plot(d['t'], d['tau'][:, i], color=COLORES_EJES[i], label=f'J{i + 1}')
        a.set_title('Modelo completo: τ(t) de los 6 ejes'); a.set_xlabel('t (s)'); a.set_ylabel('τ (N·m)')
        a.grid(alpha=.3); a.legend(ncol=3, fontsize=8)
        j2 = d['j2_1r']
        b.plot(d['t'], d['tau'][:, 1], color='#111827', lw=2, label='completo')
        b.plot(d['t'], j2['total'], color='#ff7f0e', ls='--', label='1R total')
        b.plot(d['t'], j2['gravedad'], color='#2ca02c', ls=':', label='1R gravedad')
        b.plot(d['t'], j2['inercial'], color='#9467bd', ls=':', label='1R inercial')
        b.set_title('Hombro J2: modelo 1R frente al completo'); b.set_xlabel('t (s)'); b.set_ylabel('τ (N·m)')
        b.grid(alpha=.3); b.legend(fontsize=8)
        self.canvas.draw_idle()
