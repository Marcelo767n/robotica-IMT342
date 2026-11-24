"""Pestaña Reglas: veredicto, tolerancias y, por tramo, las dos opciones con cada regla en verde/ámbar/rojo."""
import customtkinter as ctk

from irb120_control.estudio.formato import n
from irb120_control.estudio.tema import COLORES, fuente
from irb120_control.estudio.vistas import Vista
from irb120_control.estudio.widgets import Tarjeta, insignia
from irb120_control.trayectorias import TOLERANCIAS as T

ESTADO_REGLA = {'ok': 'ok', 'aviso': 'aviso', 'falla': 'falla'}


def filas_tolerancias(t=T):
    """(regla, aviso, bloqueo) tal como en la tabla del contrato; separado para poder probarlo."""
    p = lambda x: f'{x * 100:.0f} %'
    return [('σ_min(J) a lo largo del tramo', f'< {n(t.sigma_aviso, 2)}', f'< {n(t.sigma_bloqueo, 2)}'),
            ('Número de condición κ(J)', f'> {n(t.cond_aviso, 0)}', f'> {n(t.cond_bloqueo, 0)}'),
            ('Margen a los límites articulares', f'< {n(t.margen_aviso_deg, 0)}°', f'< {n(t.margen_bloqueo_deg, 0)}°'),
            ('Velocidad articular (de la máx.)', f'> {p(t.vel_aviso)}', f'> {p(t.vel_bloqueo)}'),
            ('Aceleración articular (del perfil)', f'> {p(t.acc_aviso)}', f'> {p(t.acc_bloqueo)}'),
            ('Par articular (de τ_ref)', f'> {p(t.par_aviso)}', f'> {p(t.par_bloqueo)}'),
            ('Salto de rama en tramo lineal', '—', f'> {n(t.salto_rama_deg, 0)}°'),
            ('Altura z del TCP', f'< {n(t.z_aviso_mm, 0)} mm', f'< {n(t.z_bloqueo_mm, 0)} mm'),
            ('Precisión IK → FK', '—', f'> {t.ik_mm} mm / {t.ik_deg}°')]


class VistaReglas(Vista):
    titulo = 'Reglas'

    def __init__(self, master, ctx):
        self.ctx = ctx
        self.frame = ctk.CTkScrollableFrame(master, fg_color='transparent')
        self.cab = ctk.CTkFrame(self.frame, fg_color='transparent')
        self.cab.pack(fill='x')
        self.cuerpo = ctk.CTkFrame(self.frame, fg_color='transparent')
        self.cuerpo.pack(fill='x')
        self.al_cambiar('plan')

    def al_cambiar(self, evento):
        if evento != 'plan':
            return
        for w in (*self.cab.winfo_children(), *self.cuerpo.winfo_children()):
            w.destroy()
        self.frame._parent_canvas.yview_moveto(0)
        self._cabecera()
        plan = self.ctx.plan
        if plan is None:
            return
        for tr in plan.tramos:
            self._tramo(tr)

    # ------------------------------------------------------------
    def _cabecera(self):
        c, plan = self.ctx, self.ctx.plan
        v = Tarjeta(self.cab, 'Veredicto')
        v.pack(side='left', fill='both', padx=(0, 8), pady=6)
        if c.planificando:
            insignia(v.cuerpo, 'PLANIFICANDO…', 'aviso').pack(anchor='w')
        elif plan is None:
            insignia(v.cuerpo, 'SIN PLAN', 'nada').pack(anchor='w')
            texto = c.plan_error or 'Planifica la trayectoria en la pestaña Trayectoria.'
            ctk.CTkLabel(v.cuerpo, text=texto, font=fuente(), wraplength=420, justify='left', anchor='w').pack(
                fill='x', pady=8)
        else:
            sev = 'ok' if plan.ok else 'falla'
            insignia(v.cuerpo, 'APTA PARA ENVIAR' if plan.ok else 'BLOQUEADA', sev).pack(anchor='w')
            ctk.CTkLabel(v.cuerpo, text=plan.resumen, font=fuente(), wraplength=420, justify='left',
                         anchor='w').pack(fill='x', pady=8)
            ctk.CTkLabel(v.cuerpo, text=f'Duración de una vuelta: {n(plan.duracion_s, 1)} s', font=fuente(0, True),
                         anchor='w').pack(fill='x')
        t = Tarjeta(self.cab, 'Tolerancias (más estrictas que el Hito 2)')
        t.pack(side='left', fill='both', expand=True, pady=6)
        filas = filas_tolerancias(plan.tolerancias if plan is not None else T)
        for j, tit in enumerate(('Regla', 'Aviso', 'Bloqueo')):
            ctk.CTkLabel(t.cuerpo, text=tit, font=fuente(-2, True), text_color=COLORES['suave'], anchor='w').grid(
                row=0, column=j, sticky='w', padx=6)
        for i, (nom, av, bl) in enumerate(filas, 1):
            ctk.CTkLabel(t.cuerpo, text=nom, font=fuente(-2), anchor='w').grid(row=i, column=0, sticky='w', padx=6)
            ctk.CTkLabel(t.cuerpo, text=av, font=fuente(-2, True), text_color=COLORES['aviso'], anchor='w').grid(
                row=i, column=1, sticky='w', padx=6)
            ctk.CTkLabel(t.cuerpo, text=bl, font=fuente(-2, True), text_color=COLORES['falla'], anchor='w').grid(
                row=i, column=2, sticky='w', padx=6)
        t.cuerpo.columnconfigure(0, weight=1)
        ctk.CTkLabel(t.cuerpo, text='τ_ref = 1,5 × el par de gravedad máximo de cada eje (ABB no publica el par '
                     'de los motores).', font=fuente(-3), text_color=COLORES['suave'], anchor='w').grid(
            row=len(filas) + 1, column=0, columnspan=3, sticky='w', padx=6, pady=(4, 0))

    def _tramo(self, tr):
        t = Tarjeta(self.cuerpo, f'Tramo {tr.indice + 1} · {tr.desde} → {tr.hasta}')
        t.pack(fill='x', pady=6)
        fila = ctk.CTkFrame(t.cuerpo, fg_color='transparent')
        fila.pack(fill='x')
        insignia(fila, f'elegido: {tr.tipo}', 'ok' if tr.ok else 'falla').pack(side='left')
        insignia(fila, 'apto' if tr.ok else 'bloqueado', 'ok' if tr.ok else 'falla').pack(side='left', padx=8)
        ctk.CTkLabel(t.cuerpo, text=tr.motivo, font=fuente(), wraplength=1150, justify='left', anchor='w').pack(
            fill='x', pady=(6, 6))
        cols = ctk.CTkFrame(t.cuerpo, fg_color='transparent')
        cols.pack(fill='x')
        for k, (nombre, ev) in enumerate(tr.opciones.items()):
            cols.columnconfigure(k, weight=1, uniform='o')
            caja = ctk.CTkFrame(cols, fg_color=COLORES['fondo'], corner_radius=10)
            caja.grid(row=0, column=k, sticky='nsew', padx=4)
            peor = 'falla' if ev.fallas() else 'aviso' if ev.avisos() else 'ok'
            cab = ctk.CTkFrame(caja, fg_color='transparent')
            cab.pack(fill='x', padx=10, pady=(8, 2))
            ctk.CTkLabel(cab, text=nombre.capitalize() + (' ✔' if nombre == tr.tipo else ''), font=fuente(2, True),
                         anchor='w').pack(side='left')
            insignia(cab, ('factible · ' if ev.factible else 'no factible · ') + f'{n(ev.duracion_s, 1)} s',
                     peor).pack(side='right')
            for r in ev.reglas:
                self._regla(caja, r)
        if tr.sugerencias:
            s = ctk.CTkFrame(t.cuerpo, fg_color=COLORES['aviso_fondo'], corner_radius=10)
            s.pack(fill='x', pady=(8, 0))
            ctk.CTkLabel(s, text='Sugerencias', font=fuente(0, True), text_color=COLORES['aviso'], anchor='w').pack(
                fill='x', padx=12, pady=(8, 0))
            for txt in tr.sugerencias:
                ctk.CTkLabel(s, text='• ' + txt, font=fuente(), wraplength=1100, justify='left', anchor='w').pack(
                    fill='x', padx=12, pady=(2, 6))

    @staticmethod
    def _regla(caja, r):
        fila = ctk.CTkFrame(caja, fg_color='transparent')
        fila.pack(fill='x', padx=10, pady=1)
        ctk.CTkLabel(fila, text='●', font=fuente(4), width=22, text_color=COLORES[ESTADO_REGLA.get(r.estado, 'nada')]
                     ).pack(side='left', anchor='n')
        ctk.CTkLabel(fila, text=f'{r.nombre}: {r.detalle}' if r.detalle else r.nombre, font=fuente(-1), anchor='w',
                     justify='left', wraplength=520).pack(side='left', fill='x', expand=True)
