"""Pestaña 1: IK → FK (matrices homogéneas) e ida y vuelta eje por eje, y el robot real."""
from tkinter import ttk

from irb120_control.analisis.calculos import TOL_DEG, TOL_MM
from irb120_control.analisis.vistas.comun import fmt, indicador, llenar, matriz, pintar, sci, tabla, texto_matriz


class VistaCinematica:
    titulo = 'Cinemática (ida y vuelta)'

    def __init__(self, parent):
        self.frame = ttk.Frame(parent, padding=8)
        top = ttk.Frame(self.frame)
        top.pack(fill='x')
        f1, self.t_pedida = matriz(top, 'T pedida (base → punto), m')
        f2, self.t_fk = matriz(top, 'T = FK(q_IK) con la FK del Hito 2, m')
        f1.pack(side='left', fill='x', expand=True, padx=4)
        f2.pack(side='left', fill='x', expand=True, padx=4)
        self.ind_fk = indicador(self.frame, '')
        self.ind_fk.pack(fill='x', pady=(8, 2))
        self.ind_vuelta = indicador(self.frame, '')
        self.ind_vuelta.pack(fill='x', pady=2)
        cols = ('Eje', 'q_IK (°)', 'IK(FK(q_IK)) (°)', 'Error (°)', f'≤ {TOL_DEG}°')
        ttk.Label(self.frame, text='Ida y vuelta: q_IK → FK → IK de Pieper (rama más cercana) → q recuperado',
                  font=('DejaVu Sans', 11, 'bold')).pack(anchor='w', pady=(8, 2))
        self.tabla_vuelta = tabla(self.frame, cols, alto=6, anchos=(60, 140, 170, 140, 90))
        self.tabla_vuelta.pack(fill='x')
        self.ind_robot = indicador(self.frame, '')
        self.ind_robot.pack(fill='x', pady=(10, 2))
        cols = ('Eje', 'q_IK (°)', 'q medido (°)', 'Error (°)', 'Error (% del recorrido)', '≤ 0,1°')
        self.tabla_robot = tabla(self.frame, cols, alto=6, anchos=(60, 140, 140, 120, 180, 90))
        self.tabla_robot.pack(fill='x')

    def actualizar(self, r):
        c = r['cinematica']
        self.t_pedida.configure(text=texto_matriz(c['T_pedida']))
        self.t_fk.configure(text=texto_matriz(c['T_fk']))
        fk = c['fk']
        pintar(self.ind_fk, fk['ok'], f"1 · FK(q_IK) frente a T pedida (origen: {c['origen']}): posición "
               f"{sci(fk['pos_mm'], ' mm')} · orientación {sci(fk['rot_deg'], '°')}  (criterio ≤ {TOL_MM} mm / {TOL_DEG}°)")
        rows = c['ida_vuelta']
        worst = max((abs(x['error_deg']) for x in rows if x['error_deg'] is not None), default=None)
        pintar(self.ind_vuelta, all(x['ok'] for x in rows),
               f"2 · Ida y vuelta IK(FK(q_IK)): error máximo {sci(worst, '°')} (rama {c['rama_recuperada']})")
        llenar(self.tabla_vuelta, [((x['eje'], fmt(x['q_ik']), fmt(x['q_recuperado']), sci(x['error_deg']),
                                     'sí' if x['ok'] else 'NO'), 'ok' if x['ok'] else 'mal') for x in rows])
        rp = c['robot_pose']
        pintar(self.ind_robot, rp['ok'], f"3 · Robot real: FK(q_medido) frente a T pedida {fmt(rp['pos_mm'], 3, ' mm')}"
               f" · {fmt(rp['rot_deg'], 3, '°')}  (llegada ≤ 0,5 mm / 0,1°)")
        llenar(self.tabla_robot, [((x['eje'], fmt(x['q_ik'], 3), fmt(x['q_medido'], 3), f"{x['error_deg']:+.3f}",
                                    fmt(x['error_pct'], 2, ' %'), 'sí' if x['ok'] else 'NO'),
                                   'ok' if x['ok'] else 'mal') for x in c['robot']])
