"""Pestaña Matemática: bloques LaTeX con los valores del punto, de la postura medida o de un instante de un tramo."""
import io
import time

import customtkinter as ctk
import numpy as np
from PIL import Image

from irb120_control.estudio import contexto as cx
from irb120_control.estudio import matematica as mat
from irb120_control.estudio.datos import muestras_tramo
from irb120_control.estudio.formato import n
from irb120_control.estudio.tema import COLORES, fuente
from irb120_control.estudio.vistas import Vista
from irb120_control.estudio.widgets import Tarjeta

CONTEXTOS = ('Punto de la trayectoria', 'Postura medida', 'Instante de un tramo')
GRUPOS = ('Cinemática DH y T', 'Jacobiano', 'LSPB del tramo', 'Dinámica τ')
TAM_BASE, TAM_PROY = 18, 25
SIN_PLAN = 'Planifica la trayectoria (pestaña Trayectoria) para elegir un punto o un instante.'


def seleccion_q(ctx, contexto, i_punto, i_tramo, frac):
    """(q, qd, qdd, descripcion) del contexto elegido, o (None, …, motivo)."""
    z = [0.] * 6
    plan = ctx.plan
    if contexto == CONTEXTOS[1]:
        q = ctx.q_medido()
        return (q, z, z, 'postura medida del robot, en reposo') if q else (None, None, None, 'No hay postura medida.')
    if contexto == CONTEXTOS[0]:
        puntos = ctx.editor.puntos
        if not 0 <= i_punto < len(puntos):
            return None, None, None, 'No hay puntos en la trayectoria.'
        q = (plan.q_puntos[i_punto] if plan is not None and i_punto < len(plan.q_puntos) else puntos[i_punto].q)
        if q is None:
            return None, None, None, SIN_PLAN
        return list(q), z, z, f'punto «{puntos[i_punto].nombre}», en reposo'
    if plan is None or not 0 <= i_tramo < len(plan.tramos):
        return None, None, None, SIN_PLAN
    tr = plan.tramos[i_tramo]
    m = muestras_tramo(tr)
    if m is None:
        return None, None, None, 'Este tramo no tiene muestras (no es alcanzable).'
    k = int(round(min(1., max(0., frac)) * (len(m.t) - 1)))
    return (list(m.q[k]), list(m.qd[k]), list(m.qdd[k]),
            f'tramo {tr.desde}→{tr.hasta} ({tr.tipo}), t = {n(m.t[k], 2)} s')


def bloques_para(ctx, contexto, grupo, i_punto, i_tramo, frac):
    """(bloques, descripcion). Lanza ValueError con un texto para el usuario si no se puede."""
    q, qd, qdd, desc = seleccion_q(ctx, contexto, i_punto, i_tramo, frac)
    if grupo == GRUPOS[2]:
        plan = ctx.plan
        if plan is None or not 0 <= i_tramo < len(plan.tramos):
            raise ValueError(SIN_PLAN)
        tr = plan.tramos[i_tramo]
        return (mat.bloques_lspb(tr.q0, tr.qf, ctx.plan_velocidad or ctx.velocidad_efectiva()),
                f'tramo {tr.desde}→{tr.hasta}, velocidad {n(ctx.plan_velocidad, 0)} %')
    if q is None:
        raise ValueError(desc)
    if grupo == GRUPOS[0]:
        return mat.bloques_cinematica(q, 'tcp' if ctx.herramienta == 'tcp' else 'tool0'), desc
    if grupo == GRUPOS[1]:
        return mat.bloques_jacobiano(q), desc
    return mat.bloques_dinamica(q, qd, qdd), desc


class VistaMatematica(Vista):
    titulo = 'Matemática'

    def __init__(self, master, ctx):
        self.ctx = ctx
        self.gen = 0
        self.pendiente = None
        self.bloques, self.rotulos, self.cajas = [], [], []
        self.frame = f = ctk.CTkFrame(master, fg_color='transparent')
        t = Tarjeta(f, 'Qué mostrar')
        t.pack(fill='x', padx=6, pady=(4, 6))
        fila = ctk.CTkFrame(t.cuerpo, fg_color='transparent')
        fila.pack(fill='x')
        ctk.CTkLabel(fila, text='Contexto', font=fuente(0, True), width=90, anchor='w').pack(side='left')
        self.s_ctx = ctk.CTkSegmentedButton(fila, values=list(CONTEXTOS), font=fuente(), height=38,
                                            command=lambda _v: self._selectores())
        self.s_ctx.set(CONTEXTOS[0])
        self.s_ctx.pack(side='left', padx=8)
        self.o_punto = ctk.CTkOptionMenu(fila, values=['—'], font=fuente(), width=130, height=38, dropdown_font=fuente(),
                                         command=lambda _v: self.pedir())
        self.o_tramo = ctk.CTkOptionMenu(fila, values=['—'], font=fuente(), width=200, height=38, dropdown_font=fuente(),
                                         command=lambda _v: self.pedir())
        fila2 = ctk.CTkFrame(t.cuerpo, fg_color='transparent')
        fila2.pack(fill='x', pady=(8, 0))
        ctk.CTkLabel(fila2, text='Grupo', font=fuente(0, True), width=90, anchor='w').pack(side='left')
        self.s_grp = ctk.CTkSegmentedButton(fila2, values=list(GRUPOS), font=fuente(), height=38,
                                            command=lambda _v: self._selectores())
        self.s_grp.set(GRUPOS[0])
        self.s_grp.pack(side='left', padx=8)
        self.b_proy = ctk.CTkButton(fila2, text='Modo proyección', font=fuente(), height=38, width=170,
                                    command=self.alternar_proyeccion)
        self.b_exp = ctk.CTkButton(fila2, text='Exportar PNG', font=fuente(), height=38, width=140,
                                   fg_color=COLORES['nada'], command=self.exportar)
        self.b_exp.pack(side='right')
        self.b_proy.pack(side='right', padx=8)
        self.fila_t = ctk.CTkFrame(t.cuerpo, fg_color='transparent')
        ctk.CTkLabel(self.fila_t, text='Instante', font=fuente(0, True), width=90, anchor='w').pack(side='left')
        self.s_t = ctk.CTkSlider(self.fila_t, from_=0, to=1, number_of_steps=100, width=520,
                                 command=lambda _v: self.pedir(.35))
        self.s_t.set(.5)
        self.s_t.pack(side='left', padx=8)
        self.l_t = ctk.CTkLabel(self.fila_t, text='', font=fuente(0, True))
        self.l_t.pack(side='left')
        self.l_desc = ctk.CTkLabel(t.cuerpo, text='', font=fuente(), text_color=COLORES['suave'], anchor='w')
        self.l_desc.pack(fill='x', pady=(8, 0))
        self.zona = ctk.CTkScrollableFrame(f, fg_color='transparent')
        self.zona.pack(fill='both', expand=True, padx=6, pady=4)
        self._opciones()
        self._selectores()

    # ------------------------------------------------------------ selectores
    def _opciones(self):
        c = self.ctx
        nombres = c.editor.nombres() or ['—']
        actual = self.o_punto.get()
        self.o_punto.configure(values=nombres)
        self.o_punto.set(actual if actual in nombres else nombres[0])
        tramos = [f'{t.indice + 1} · {t.desde}→{t.hasta}' for t in c.plan.tramos] if c.plan else ['—']
        actual = self.o_tramo.get()
        self.o_tramo.configure(values=tramos)
        self.o_tramo.set(actual if actual in tramos else tramos[0])

    def _selectores(self):
        ctx_, grp = self.s_ctx.get(), self.s_grp.get()
        for w in (self.o_punto, self.o_tramo):
            w.pack_forget()
        if ctx_ == CONTEXTOS[0]:
            self.o_punto.pack(side='left', padx=8)
        if ctx_ == CONTEXTOS[2] or grp == GRUPOS[2]:
            self.o_tramo.pack(side='left', padx=8)
        if ctx_ == CONTEXTOS[2] and grp != GRUPOS[2]:
            self.fila_t.pack(fill='x', pady=(8, 0), after=self.s_grp.master)
        else:
            self.fila_t.pack_forget()
        self.pedir()

    def _indices(self):
        c = self.ctx
        try:
            ip = c.editor.nombres().index(self.o_punto.get())
        except ValueError:
            ip = -1
        txt = self.o_tramo.get()
        it = int(txt.split(' ')[0]) - 1 if txt[:1].isdigit() else -1
        return ip, it

    # ------------------------------------------------------------ render
    def pedir(self, espera=0.0):
        """Reconstruye los bloques (con pequeña espera si viene de un deslizador)."""
        if self.pendiente is not None:
            self.frame.after_cancel(self.pendiente)
        self.pendiente = self.frame.after(int(espera * 1000) + 1, self.renderizar)

    def alternar_proyeccion(self):
        self.ctx.proyeccion = not self.ctx.proyeccion
        self.b_proy.configure(fg_color=COLORES['ok'] if self.ctx.proyeccion else COLORES['acento'],
                              text='Salir de proyección' if self.ctx.proyeccion else 'Modo proyección')
        self.renderizar()

    def renderizar(self):
        self.pendiente = None
        c = self.ctx
        self.gen += 1
        self.zona._parent_canvas.yview_moveto(0)
        gen = self.gen
        for w in self.zona.winfo_children():
            w.destroy()
        self.rotulos, self.bloques = [], []
        ip, it = self._indices()
        frac = float(self.s_t.get())
        try:
            self.bloques, desc = bloques_para(c, self.s_ctx.get(), self.s_grp.get(), ip, it, frac)
        except ValueError as exc:
            self.l_desc.configure(text='')
            ctk.CTkLabel(self.zona, text=str(exc), font=fuente(2), text_color=COLORES['suave'], wraplength=900,
                         justify='left').pack(padx=20, pady=40)
            return
        except Exception as exc:
            c.mensaje(f'Matemática: {exc}', 'falla')
            return
        self.l_desc.configure(text=f'Valores de: {desc}')
        if c.plan and self.s_ctx.get() == CONTEXTOS[2]:
            self.l_t.configure(text=desc.split('t = ')[-1])
        proy = c.proyeccion
        for b in self.bloques:
            caja = Tarjeta(self.zona, b.titulo)
            caja.titulo.configure(font=fuente(8 if proy else 4, True))
            caja.pack(fill='x', pady=6)
            img = ctk.CTkLabel(caja.cuerpo, text='Renderizando…', font=fuente(), text_color=COLORES['suave'])
            img.pack(anchor='w', pady=4)
            ctk.CTkLabel(caja.cuerpo, text=b.explicacion, font=fuente(4 if proy else 0), anchor='w', justify='left',
                         wraplength=1150, text_color=COLORES['suave']).pack(fill='x', pady=(2, 0))
            self.rotulos.append(img)
        tam = TAM_PROY if proy else TAM_BASE
        oscuro = c.oscuro
        bloques = list(self.bloques)

        def trabajo():
            etapas = [False] + ([True] if mat.usar_latex() else [])
            for usetex in etapas:
                for k, b in enumerate(bloques):
                    if gen != self.gen:
                        return
                    png = mat.png_bytes_bloque(b, tam, oscuro, usetex)
                    c.cola.put(lambda k=k, png=png: self._poner(gen, k, png))
        c.en_hilo(trabajo, lambda r, e: c.mensaje(f'Matemática: {e}', 'falla') if e else None)

    def _poner(self, gen, k, png):
        if gen != self.gen or k >= len(self.rotulos):
            return
        try:
            im = Image.open(io.BytesIO(png))
            im.load()
            w, h = im.size
            disp = max(500, self.zona.winfo_width() - 90)
            e = min(1., disp / w)
            self.rotulos[k].configure(image=ctk.CTkImage(light_image=im, dark_image=im, size=(int(w * e), int(h * e))),
                                      text='')
        except Exception as exc:
            self.ctx.mensaje(f'Imagen: {exc}', 'falla')

    # ------------------------------------------------------------ ganchos
    def al_cambiar(self, evento):
        if evento in ('plan', 'lista'):
            self._opciones()
            self.pedir()
        elif evento == 'tema':
            self.pedir()

    def exportar(self):
        c = self.ctx
        if not self.bloques:
            c.mensaje('No hay bloques que exportar.', 'falla')
            return
        bloques, tam, oscuro = list(self.bloques), TAM_PROY if c.proyeccion else TAM_BASE, c.oscuro
        base = f'{self.s_grp.get().split()[0].lower()}_{time.strftime("%H%M%S")}'

        def trabajo():
            cx.CARPETA_MATEMATICA.mkdir(parents=True, exist_ok=True)
            for k, b in enumerate(bloques, 1):
                (cx.CARPETA_MATEMATICA / f'{base}_{k:02d}.png').write_bytes(mat.png_bytes_bloque(b, tam, oscuro))
            return cx.CARPETA_MATEMATICA
        c.en_hilo(trabajo, lambda r, e: c.mensaje(f'Exportados {len(bloques)} PNG en {r}' if e is None
                                                  else f'No se pudo exportar: {e}', 'info' if e is None else 'falla'))
