"""Pestaña 2: las 8 ramas de Pieper con el criterio de selección del proyecto."""
from tkinter import ttk

from irb120_control.analisis.vistas.comun import fmt, llenar, sci, tabla


class VistaRamas:
    titulo = 'Ramas IK (Pieper)'

    def __init__(self, parent):
        self.frame = ttk.Frame(parent, padding=8)
        self.veredicto = ttk.Label(self.frame, font=('DejaVu Sans', 13, 'bold'))
        self.veredicto.pack(anchor='w', pady=(0, 6))
        ttk.Label(self.frame, text='Brazo frente/atrás × codo arriba/abajo × muñeca q5+/q5−; e_p y e_R = FK de la rama '
                  'frente a la pose pedida. Orden: admisible → σ_min ≥ 0,01 → margen ≥ 5° → menor ‖W(q − q_medido)‖.',
                  wraplength=1200).pack(anchor='w')
        cols = ('Rama', 'Brazo', 'Codo', 'Muñeca', 'J1', 'J2', 'J3', 'J4', 'J5', 'J6', 'e_p (mm)', 'e_R (°)', 'σ_min', 'Estado')
        anchos = (55, 70, 70, 70, 75, 75, 75, 75, 75, 75, 95, 95, 75, 290)
        self.tabla = tabla(self.frame, cols, alto=9, anchos=anchos)
        self.tabla.pack(fill='both', expand=True, pady=6)

    def actualizar(self, r):
        data = r['ramas']
        self.veredicto.configure(text=data['veredicto'])
        filas = []
        for x in data['filas']:
            q = x['q'] or [None] * 6
            tag = 'elegida' if x['rama'] == data['elegida'] else ('gris' if x['puesto'] is None else '')
            filas.append(((x['rama'], x['brazo'], x['codo'], x['muneca'], *[fmt(v, 2) for v in q],
                           sci(x['e_p_mm']), sci(x['e_R_deg']), fmt(x['sigma_min'], 3), x['estado']), tag))
        llenar(self.tabla, filas)
