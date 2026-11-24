"""Ventana principal del Estudio: pestañas, tema oscuro/claro, barra de estado y sondeo del panel."""
import time
import tkinter as tk

import customtkinter as ctk

from irb120_control.estudio import tema
from irb120_control.estudio.contexto import Contexto
from irb120_control.estudio.tema import COLORES, fuente
from irb120_control.estudio.vistas.estado import VistaEstado
from irb120_control.estudio.vistas.graficas import VistaGraficas
from irb120_control.estudio.vistas.matematica import VistaMatematica
from irb120_control.estudio.vistas.reglas import VistaReglas
from irb120_control.estudio.vistas.trayectoria import VistaTrayectoria
from irb120_control.estudio.vistas.validacion import VistaValidacion
from irb120_control.trayectorias import Punto

VISTAS = (VistaEstado, VistaTrayectoria, VistaReglas, VistaGraficas, VistaMatematica, VistaValidacion)
DEMO_PUNTOS = (('A', [20, 10, -10, 0, 40, 0]), ('B', [-20, 15, -5, 0, 45, 10]), ('C', [0, -10, 10, 0, 60, 0]))
PERIODO_MS = 500


class App(ctk.CTk):
    def __init__(self, cliente, oscuro=True, escala=1.0, carpeta=None):
        tema.parchear_scrollbar()
        ctk.set_appearance_mode('dark' if oscuro else 'light')
        ctk.set_widget_scaling(escala)
        ctk.set_window_scaling(escala)
        super().__init__(fg_color=COLORES['fondo'])
        self.title('IRB 120 · Estudio de trayectorias')
        self.geometry(f'{int(1400 * escala)}x{int(900 * escala)}')
        self.minsize(int(1100 * escala), int(700 * escala))
        self.cliente = cliente
        self.ctx = Contexto(cliente, carpeta)
        self.ctx.oscuro = oscuro
        self.ctx.mensaje_cb = self.mensaje
        self.report_callback_exception = self._excepcion
        self._barra()
        self.tabs = ctk.CTkTabview(self, fg_color='transparent', command=self._pestana, text_color=COLORES['texto'],
                                   segmented_button_unselected_color=COLORES['borde'],
                                   segmented_button_selected_color=COLORES['acento'],
                                   segmented_button_fg_color=COLORES['borde'])
        self.tabs._segmented_button.configure(font=fuente(2, True), height=44)
        self.tabs.pack(fill='both', expand=True, padx=12, pady=(0, 4))
        self.vistas = []
        for cls in VISTAS:
            self.tabs.add(cls.titulo)
            v = cls(self.tabs.tab(cls.titulo), self.ctx)
            v.frame.pack(fill='both', expand=True)
            self.vistas.append(v)
        self.ctx.escuchas.append(self._avisos)
        self.tabs.set(VistaTrayectoria.titulo)   # la demo en vivo empieza aquí
        self.bind('<F2>', lambda _e: self.vistas[1].capturar())   # capturar postura actual
        self._ult_msg = 0.
        self.ciclo()

    # ------------------------------------------------------------ construcción
    def _barra(self):
        b = ctk.CTkFrame(self, fg_color='transparent')
        b.pack(fill='x', padx=16, pady=(10, 6))
        ctk.CTkLabel(b, text='IRB 120 · Estudio de trayectorias', font=fuente(8, True)).pack(side='left')
        self.sw = ctk.CTkSwitch(b, text='Tema oscuro', font=fuente(), command=self.cambiar_tema)
        if self.ctx.oscuro:
            self.sw.select()
        self.sw.pack(side='right')
        self.conexion = ctk.CTkLabel(b, text='', font=fuente(0, True), corner_radius=8)
        self.conexion.pack(side='right', padx=20)
        self.estado_barra = ctk.CTkLabel(self, text='Listo.', font=fuente(), anchor='w', corner_radius=8,
                                         text_color=COLORES['texto'], fg_color=COLORES['tarjeta'], height=38)
        self.estado_barra.pack(side='bottom', fill='x', padx=12, pady=(0, 10))

    # ------------------------------------------------------------ mensajes y errores
    def mensaje(self, texto, nivel='info'):
        color = {'falla': 'falla', 'aviso': 'aviso'}.get(nivel, 'texto')
        self.estado_barra.configure(text='  ' + str(texto).replace('\n', ' '), text_color=COLORES[color])
        self._ult_msg = time.monotonic()

    def _excepcion(self, exc, val, tb):
        self.mensaje(f'Error interno: {val}', 'falla')

    # ------------------------------------------------------------ eventos
    def cambiar_tema(self):
        self.ctx.oscuro = bool(self.sw.get())
        ctk.set_appearance_mode('dark' if self.ctx.oscuro else 'light')
        self.ctx.avisar('tema')

    def _avisos(self, evento):
        for v in self.vistas:
            try:
                v.al_cambiar(evento)
            except Exception as exc:
                self.mensaje(f'Error en la pestaña {v.titulo}: {exc}', 'falla')

    def _pestana(self):
        self.refrescar()

    def refrescar(self):
        estado, error = self.cliente.instantanea()
        c = self.cliente
        if c.demo:
            self.conexion.configure(text=' DEMO ', text_color=COLORES['aviso'], fg_color=COLORES['aviso_fondo'])
        elif error:
            self.conexion.configure(text=' SIN PANEL ', text_color=COLORES['falla'], fg_color=COLORES['falla_fondo'])
        else:
            self.conexion.configure(text=' PANEL CONECTADO ', text_color=COLORES['ok'], fg_color=COLORES['ok_fondo'])
        for v in self.vistas:
            if v.frame.winfo_ismapped() or isinstance(v, (VistaEstado, VistaTrayectoria)):
                try:
                    v.actualizar(estado, error)
                except Exception as exc:
                    self.mensaje(f'Error en la pestaña {v.titulo}: {exc}', 'falla')

    def ciclo(self):
        try:
            self.ctx.drenar()
            if time.monotonic() - getattr(self, '_ult_poll', 0) >= PERIODO_MS / 1000. - .01:
                self._ult_poll = time.monotonic()
                self.refrescar()
        except Exception as exc:
            self.mensaje(f'Error: {exc}', 'falla')
        self.after(60, self.ciclo)

    # ------------------------------------------------------------ utilidades (demo, capturas, pruebas)
    def cargar_demo(self):
        """Trayectoria de ejemplo A→B→C→A (cerrada) para --demo y las capturas."""
        self.ctx.editor.puntos = [Punto(n, q=q, origen='angulos') for n, q in DEMO_PUNTOS]
        self.ctx.nombre, self.ctx.cerrar = 'Demostración ABC', True
        self.vistas[1].poner_parametros()
        self.ctx.marcar_guardado()
        self.ctx.cambio('lista')

    def esperar_plan(self, limite=60.):
        """Bombea eventos hasta que termine la planificación (pruebas y capturas)."""
        t0 = time.monotonic()
        while self.ctx.planificando and time.monotonic() - t0 < limite:
            self.ctx.drenar()
            self.update()
            time.sleep(.02)
        self.ctx.drenar()
        self.update()

    def destruir(self):
        self.cliente.detener()
        try:
            self.destroy()
        except tk.TclError:
            pass
