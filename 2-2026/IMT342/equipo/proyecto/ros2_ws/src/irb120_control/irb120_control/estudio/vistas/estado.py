"""Pestaña Estado: conexión, velocidad, postura medida, verificaciones, trayectoria en curso y registro."""
import customtkinter as ctk

from irb120_control.estudio.formato import n, seis
from irb120_control.estudio.tema import COLORES, fuente
from irb120_control.estudio.vistas import Vista
from irb120_control.estudio.widgets import Indicador, Tarjeta, insignia


def pose_tcp(q, herramienta):
    try:
        from irb120_control.panel.cinematica import pose_of
        return pose_of(q, herramienta if herramienta in ('tcp', 'brida') else 'tcp')
    except Exception:
        return None


class VistaEstado(Vista):
    titulo = 'Estado'

    def __init__(self, master, ctx):
        self.ctx = ctx
        self.frame = f = ctk.CTkFrame(master, fg_color='transparent')
        for c in range(3):
            f.columnconfigure(c, weight=1, uniform='c')
        f.rowconfigure(0, weight=0)
        f.rowconfigure(1, weight=1)
        # Conexión
        t = self.t_con = Tarjeta(f, 'Conexión con el panel')
        t.grid(row=0, column=0, sticky='nsew', padx=6, pady=6)
        self.i_con = Indicador(t.cuerpo, 'Panel')
        self.i_modo = Indicador(t.cuerpo, 'Modo')
        self.i_mot = Indicador(t.cuerpo, 'Motores')
        self.i_srv = Indicador(t.cuerpo, 'Servidor RAPID')
        self.i_listo = Indicador(t.cuerpo, 'Listo')
        for w in (self.i_con, self.i_modo, self.i_mot, self.i_srv, self.i_listo):
            w.pack(fill='x', pady=2)
        # Velocidad
        t = Tarjeta(f, 'Velocidad y herramienta')
        t.grid(row=0, column=1, sticky='nsew', padx=6, pady=6)
        self.l_vel = ctk.CTkLabel(t.cuerpo, text='—', font=fuente(22, True), anchor='w')
        self.l_vel.pack(fill='x')
        self.l_vel_det = ctk.CTkLabel(t.cuerpo, text='', font=fuente(), anchor='w', text_color=COLORES['suave'])
        self.l_vel_det.pack(fill='x')
        self.l_herr = ctk.CTkLabel(t.cuerpo, text='', font=fuente(2, True), anchor='w')
        self.l_herr.pack(fill='x', pady=(10, 0))
        # Postura
        t = Tarjeta(f, 'Postura medida')
        t.grid(row=0, column=2, sticky='nsew', padx=6, pady=6)
        malla = ctk.CTkFrame(t.cuerpo, fg_color='transparent')
        malla.pack(fill='x')
        self.l_j = []
        for i in range(6):
            malla.columnconfigure(i % 2, weight=1)
            lb = ctk.CTkLabel(malla, text=f'J{i + 1}  —', font=fuente(2, mono=True), anchor='w')
            lb.grid(row=i // 2, column=i % 2, sticky='w', padx=4)
            self.l_j.append(lb)
        self.l_pose = ctk.CTkLabel(t.cuerpo, text='TCP —', font=fuente(0, mono=True), anchor='w', justify='left',
                                   text_color=COLORES['suave'])
        self.l_pose.pack(fill='x', pady=(8, 0))
        # Verificaciones
        t = Tarjeta(f, 'Verificaciones del objetivo')
        t.grid(row=1, column=0, sticky='nsew', padx=6, pady=6)
        self.v = [Indicador(t.cuerpo, x) for x in
                  ('1 · IK → FK', '2 · Ida y vuelta', '3 · Modelo / ABB', '4 · Robot real')]
        for w in self.v:
            w.pack(fill='x', pady=3)
        ctk.CTkLabel(t.cuerpo, text='Tolerancias: 1 y 2 ≤ 0,001 mm / 0,001° · 3 ≤ 0,5 mm / 0,1° (robot quieto) · '
                     '4 muestra el error de llegada. El envío se bloquea si falla 1, 2 o 3.',
                     font=fuente(-2), text_color=COLORES['suave'], wraplength=400, justify='left', anchor='w').pack(
            fill='x', pady=(12, 0))
        # Trayectoria
        t = Tarjeta(f, 'Trayectoria en curso')
        t.grid(row=1, column=1, sticky='nsew', padx=6, pady=6)
        self.fase = insignia(t.cuerpo, 'sin trayectoria', 'nada')
        self.fase.pack(anchor='w')
        self.l_tr = ctk.CTkLabel(t.cuerpo, text='', font=fuente(2, True), anchor='w')
        self.l_tr.pack(fill='x', pady=(8, 2))
        self.barra = ctk.CTkProgressBar(t.cuerpo, height=16, progress_color=COLORES['acento'])
        self.barra.set(0)
        self.barra.pack(fill='x', pady=4)
        self.l_msg = ctk.CTkLabel(t.cuerpo, text='', font=fuente(), anchor='nw', justify='left', wraplength=360,
                                  text_color=COLORES['suave'])
        self.l_msg.pack(fill='x')
        # Registro
        t = Tarjeta(f, 'Registro del panel')
        t.grid(row=1, column=2, sticky='nsew', padx=6, pady=6)
        self.log = ctk.CTkTextbox(t.cuerpo, font=fuente(-2, mono=True), wrap='none', activate_scrollbars=True)
        self.log.pack(fill='both', expand=True)
        self.log.configure(state='disabled')
        self._ult_log = None

    # ------------------------------------------------------------
    def actualizar(self, estado, error):
        e = estado if isinstance(estado, dict) else {}
        c = self.ctx.cliente
        if c.demo:
            self.i_con.poner('aviso', 'DEMO: sin panel ni robot')
        elif error:
            self.i_con.poner('falla', 'sin conexión (' + str(error).split(':')[0] + ')')
        else:
            self.i_con.poner('ok', f'conectado · puerto {c.puerto}')
        modo = e.get('modo')
        self.i_modo.poner('nada' if modo is None else 'ok' if modo in ('AUTO', 'DEMO') else 'aviso', str(modo or '—'))
        mot = e.get('motores')
        self.i_mot.poner('nada' if mot is None else 'ok' if 'on' in str(mot).lower() else 'aviso', str(mot or '—'))
        srv = e.get('servidor_activo')
        self.i_srv.poner('nada' if srv is None else 'ok' if srv else 'falla',
                         '—' if srv is None else 'activo' if srv else 'inactivo')
        listo, ocup, faltas = e.get('listo'), e.get('ocupado'), e.get('faltas') or []
        if ocup:
            self.i_listo.poner('aviso', 'moviéndose…')
        elif listo is None:
            self.i_listo.poner('nada', '—')
        else:
            self.i_listo.poner('ok' if listo else 'falla', 'sí' if listo else '; '.join(map(str, faltas)) or 'no')
        v = e.get('velocidad_pct')
        self.l_vel.configure(text=f'{n(v, 0)} %')
        self.l_vel_det.configure(text='' if e.get('velocidad_mm_s') is None else
                                 f"{n(e.get('velocidad_mm_s'), 0)} mm/s · {n(e.get('velocidad_deg_s'), 0)} °/s")
        h = e.get('herramienta')
        self.l_herr.configure(text='Punto: ' + {'tcp': 'TCP (150 mm sobre la brida)', 'brida': 'brida (tool0)'}.get(h, '—'))
        q = seis(e.get('medido'))
        for i, lb in enumerate(self.l_j):
            lb.configure(text=f'J{i + 1} {n(q[i], 2, True):>8}°' if q else f'J{i + 1}      —')
        p = pose_tcp(q, h) if q else None
        self.l_pose.configure(text=('XYZ  ' + '  '.join(n(x, 1) for x in p[:3]) + ' mm\nRPY  ' +
                                    '  '.join(n(x, 1) for x in p[3:]) + ' °') if p else 'pose —')
        self._verificaciones(e.get('verificacion'))
        self._trayectoria(e.get('trayectoria'))
        reg = e.get('registro')
        if isinstance(reg, list) and reg != self._ult_log:
            self._ult_log = list(reg)
            self.log.configure(state='normal')
            self.log.delete('1.0', 'end')
            self.log.insert('end', '\n'.join(map(str, reg[-14:])))
            self.log.see('end')
            self.log.configure(state='disabled')

    def _verificaciones(self, vf):
        v = self.v
        if not isinstance(vf, dict):
            for w in v:
                w.poner('nada', 'sin objetivo verificado')
            return
        ik = vf.get('ik_fk')
        v[0].poner('nada' if not ik else 'ok' if ik.get('ok') else 'falla',
                   '—' if not ik else f"{n(ik.get('pos_mm'), 4)} mm · {n(ik.get('rot_deg'), 4)}°")
        iv = vf.get('ida_vuelta_ok')
        v[1].poner('nada' if iv is None else 'ok' if iv else 'falla', '—' if iv is None else 'recupera los ángulos' if iv else 'no recupera')
        co = vf.get('controlador')
        if not co:
            v[2].poner('nada', '—')
        elif not co.get('valida', True):
            v[2].poner('aviso', 'sin lectura reciente del ABB')
        else:
            v[2].poner('ok' if co.get('ok') else 'falla', f"{n(co.get('pos_mm'), 4)} mm · {n(co.get('rot_deg'), 4)}°")
        ro = vf.get('robot')
        v[3].poner('nada' if not ro else 'ok' if ro.get('ok') else 'aviso',
                   '—' if not ro else f"{n(ro.get('pos_mm'), 3)} mm · máx {n(ro.get('max_eje_deg'), 3)}° por eje")

    def _trayectoria(self, tr):
        tr = tr if isinstance(tr, dict) else {}
        fase = tr.get('fase') or 'lista'
        estado = {'ejecutando': 'ok', 'pausada': 'aviso', 'error': 'falla', 'cancelada': 'aviso'}.get(fase, 'nada')
        self.fase.configure(text=f' {fase} ', text_color=COLORES[estado], fg_color=COLORES[f'{estado}_fondo'])
        total, tramo = tr.get('total'), tr.get('tramo')
        if total:
            self.l_tr.configure(text=f"Vuelta {n(tr.get('vuelta'), 0)}/{n(tr.get('vueltas'), 0)} · tramo {n(tramo, 0)}/{n(total, 0)}")
            try:
                self.barra.set(max(0., min(1., float(tramo) / float(total))))
            except (TypeError, ValueError):
                self.barra.set(0)
        else:
            self.l_tr.configure(text='—')
            self.barra.set(0)
        self.l_msg.configure(text=str(tr.get('mensaje') or ''))
