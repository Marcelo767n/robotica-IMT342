"""Pestaña Validación: resultados del Hito 3 (estados P5, evidencia S0–S3, tablas por bloque, detalle y figuras)."""
from tkinter import filedialog, ttk

import customtkinter as ctk
from PIL import Image

from irb120_control.estudio import validacion_datos as vd
from irb120_control.estudio.tema import COLORES, es_oscuro, fuente
from irb120_control.estudio.vistas import Vista
from irb120_control.estudio.widgets import estilo_tabla

# (texto, fondo) por estado; los cuatro primeros reutilizan la paleta del Estudio.
CHIP = {'verificado': (COLORES['ok'], COLORES['ok_fondo']), 'parcial': (COLORES['aviso'], COLORES['aviso_fondo']),
        'fallido': (COLORES['falla'], COLORES['falla_fondo']), 'no ejecutado': (COLORES['nada'], COLORES['nada_fondo']),
        'bloqueado': (('#6d28d9', '#a78bfa'), ('#ede9fe', '#4c1d95'))}
HEX = {'verificado': ('#15803d', '#22c55e'), 'parcial': ('#b45309', '#f59e0b'), 'fallido': ('#b91c1c', '#ef4444'),
       'no ejecutado': ('#6b7280', '#9ca3af'), 'bloqueado': ('#6d28d9', '#a78bfa')}


class VistaValidacion(Vista):
    titulo = 'Validación'

    def __init__(self, master, ctx, carpeta=None):
        self.ctx = ctx
        self.carpeta = vd.descubrir_carpeta(carpeta)
        self.modelo = None
        self.bloque = 'fk'
        self.ejecutando = False
        self.fila_sel = None
        self.imagen = None
        self._figura = None              # ruta de la figura mostrada
        self._tam_img = (0, 0)
        self._job_img = None
        self.frame = f = ctk.CTkFrame(master, fg_color='transparent')
        f.columnconfigure(0, weight=1)
        f.rowconfigure(3, weight=1)
        self._cabecera(f)
        self.selector = ctk.CTkSegmentedButton(f, values=[vd.BLOQUES[c][0] for c in vd.ORDEN], font=fuente(1, True),
                                               height=38, command=self._elegir_bloque)
        self.selector.set(vd.BLOQUES[self.bloque][0])
        self.selector.grid(row=1, column=0, sticky='w', padx=6, pady=(4, 6))
        self._vacio(f)
        self._cuerpo(f)
        self.recargar()

    # ------------------------------------------------------------ construcción
    def _cabecera(self, f):
        t = ctk.CTkFrame(f, fg_color=COLORES['tarjeta'], corner_radius=12, border_width=1,
                         border_color=COLORES['borde'])
        t.grid(row=0, column=0, sticky='ew', padx=6, pady=6)
        fila = ctk.CTkFrame(t, fg_color='transparent')
        fila.pack(fill='x', padx=14, pady=(10, 2))
        ctk.CTkLabel(fila, text='Validación del Hito 3', font=fuente(4, True), text_color=COLORES['acento']
                     ).pack(side='left')
        self.b_ejecutar = ctk.CTkButton(fila, text='Volver a ejecutar la validación', font=fuente(0, True), height=36,
                                        width=250, command=self.ejecutar)
        self.b_ejecutar.pack(side='right')
        self.l_ruta = ctk.CTkLabel(t, text='', font=fuente(-2), anchor='w', text_color=COLORES['suave'])
        self.l_ruta.pack(fill='x', padx=14)
        self.f_estados = ctk.CTkFrame(t, fg_color='transparent')
        self.f_estados.pack(fill='x', padx=14, pady=(6, 2))
        self.f_niveles = ctk.CTkFrame(t, fg_color='transparent')
        self.f_niveles.pack(fill='x', padx=14, pady=(2, 4))
        self.l_estado = ctk.CTkLabel(t, text='Datos leídos de hito3/resultados/*.csv  ·  clic en la figura para ampliarla', font=fuente(-1), anchor='w', text_color=COLORES['suave'])
        self.l_estado.pack(fill='x', padx=14, pady=(0, 8))
        self.chips_estado, self.chips_nivel = {}, {}
        for e in vd.ESTADOS:
            c = ctk.CTkLabel(self.f_estados, text='', font=fuente(1, True), corner_radius=8, text_color=CHIP[e][0],
                             fg_color=CHIP[e][1])
            c.pack(side='left', padx=(0, 8))
            self.chips_estado[e] = c
        ctk.CTkLabel(self.f_niveles, text='Evidencia por caso:', font=fuente(0, True)).pack(side='left', padx=(0, 8))
        for n in vd.NIVELES:
            c = ctk.CTkLabel(self.f_niveles, text='', font=fuente(0, True), corner_radius=8,
                             text_color=COLORES['acento'], fg_color=COLORES['borde'])
            c.pack(side='left', padx=(0, 8))
            self.chips_nivel[n] = c

    def _vacio(self, f):
        self.f_vacio = ctk.CTkFrame(f, fg_color=COLORES['tarjeta'], corner_radius=12, border_width=1,
                                    border_color=COLORES['borde'])
        self.l_vacio = ctk.CTkLabel(self.f_vacio, text='', font=fuente(3), justify='center', wraplength=900)
        self.l_vacio.pack(pady=(60, 16), padx=20)
        ctk.CTkButton(self.f_vacio, text='Ejecutar la validación', font=fuente(1, True), height=42, width=240,
                      command=self.ejecutar).pack()
        ctk.CTkButton(self.f_vacio, text='Elegir otra carpeta…', font=fuente(), height=34, width=240,
                      fg_color=COLORES['nada'], command=self.elegir_carpeta).pack(pady=10)

    def _cuerpo(self, f):
        self.f_cuerpo = c = ctk.CTkFrame(f, fg_color='transparent')
        c.columnconfigure(0, weight=3, uniform='v')
        c.columnconfigure(1, weight=2, uniform='v')
        c.rowconfigure(0, weight=3)
        c.rowconfigure(1, weight=2)
        izq = ctk.CTkFrame(c, fg_color=COLORES['tarjeta'], corner_radius=12, border_width=1,
                           border_color=COLORES['borde'])
        izq.grid(row=0, column=0, sticky='nsew', padx=6, pady=(0, 6))
        estilo_tabla(self.frame, es_oscuro())
        self.tabla = ttk.Treeview(izq, show='headings', selectmode='browse', style='Estudio.Treeview', height=8)
        sb = ttk.Scrollbar(izq, command=self.tabla.yview, style='Estudio.Vertical.TScrollbar')
        self.tabla.configure(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y', padx=(0, 4), pady=6)
        self.tabla.pack(side='left', fill='both', expand=True, padx=(8, 0), pady=8)
        self.tabla.bind('<<TreeviewSelect>>', lambda _e: self._seleccionar())
        self._colorear_tags()
        det = ctk.CTkFrame(c, fg_color=COLORES['tarjeta'], corner_radius=12, border_width=1,
                           border_color=COLORES['borde'])
        det.grid(row=1, column=0, sticky='nsew', padx=6, pady=(0, 6))
        self.detalle = ctk.CTkTextbox(det, font=fuente(-1, mono=True), fg_color='transparent', wrap='word',
                                      text_color=COLORES['texto'])
        self.detalle.pack(fill='both', expand=True, padx=8, pady=8)
        self._poner_detalle('Selecciona un caso de la tabla para ver su motivo, evidencia y manifiesto.')
        der = ctk.CTkFrame(c, fg_color=COLORES['tarjeta'], corner_radius=12, border_width=1,
                           border_color=COLORES['borde'])
        der.grid(row=0, column=1, rowspan=2, sticky='nsew', padx=6, pady=(0, 6))
        self.sel_fig = ctk.CTkSegmentedButton(der, values=['—'], font=fuente(-2), command=self._elegir_figura)
        self.f_fig = ctk.CTkFrame(der, fg_color='transparent')
        self.f_fig.pack_propagate(False)
        self.f_fig.pack(side='bottom', fill='both', expand=True, padx=8, pady=8)
        self.l_fig = ctk.CTkLabel(self.f_fig, text='', font=fuente(), text_color=COLORES['suave'])
        self.l_fig.place(relx=.5, rely=.5, anchor='center')
        self.f_fig.bind('<Configure>', self._redimensionada)
        self.l_fig.bind('<Button-1>', lambda _e: self.ampliar())
        self.l_fig.configure(cursor='hand2')

    # ------------------------------------------------------------ carga
    def recargar(self):
        """Relee los CSV de la carpeta y repinta todo (nunca lanza)."""
        try:
            self.modelo = vd.Modelo(self.carpeta)
        except Exception as exc:
            self.modelo = None
            self.ctx.mensaje(f'Validación: no se pudieron leer los resultados ({exc})', 'falla')
        self.l_ruta.configure(text=f'Carpeta: {self._ruta_corta()}')
        hay = bool(self.modelo and self.modelo.hay_datos)
        if hay:
            self.f_vacio.grid_remove()
            self.f_cuerpo.grid(row=3, column=0, sticky='nsew')
            self.selector.grid()
            est, niv = self.modelo.resumen()
            for e, c in self.chips_estado.items():
                c.configure(text=f' {est[e]} {e} ')
            for n, c in self.chips_nivel.items():
                c.configure(text=f' {n}: {niv[n]} ')
            self._pintar_bloque()
        else:
            self.f_cuerpo.grid_remove()
            self.selector.grid_remove()
            self.f_vacio.grid(row=3, column=0, sticky='nsew', padx=6, pady=6)
            self.l_vacio.configure(text=f'No hay resultados de validación en\n{self.carpeta / "resultados"}\n\n'
                                        'Ejecuta la validación para generarlos (tarda unos segundos).')
            for c in (*self.chips_estado.values(), *self.chips_nivel.values()):
                c.configure(text='')

    def _ruta_corta(self):
        try:
            return str(self.carpeta.resolve().relative_to(vd.Path(vd.PROJECT).resolve().parent))
        except (ValueError, OSError):
            return str(self.carpeta)

    def _colorear_tags(self):
        i = 1 if es_oscuro() else 0
        for e, (hexa) in HEX.items():
            self.tabla.tag_configure(e, foreground=hexa[i])

    def _pintar_bloque(self):
        tab = self.modelo.tablas.get(self.bloque) if self.modelo else None
        self.tabla.delete(*self.tabla.get_children())
        self.fila_sel = None
        self._poner_detalle('Selecciona un caso de la tabla para ver su motivo, evidencia y manifiesto.')
        if tab is None:
            return
        cols = [f'c{i}' for i in range(len(tab.columnas))]
        self.tabla.configure(columns=cols)
        for c, (tit, ancho) in zip(cols, tab.columnas):
            self.tabla.heading(c, text=tit)
            self.tabla.column(c, width=ancho, minwidth=40, anchor='w', stretch=c == cols[-1])
        for i, fila in enumerate(tab.filas):
            self.tabla.insert('', 'end', iid=str(i), values=fila.celdas, tags=(fila.estado,) if fila.estado else ())
        if not tab.filas:
            self._poner_detalle(f'No hay datos de «{tab.titulo}» en la carpeta de resultados.')
        elif self.tabla.get_children():
            self.tabla.selection_set('0')
        self._figuras(tab)

    def _seleccionar(self):
        sel = self.tabla.selection()
        tab = self.modelo.tablas.get(self.bloque) if self.modelo else None
        if not sel or tab is None:
            return
        try:
            self.fila_sel = tab.filas[int(sel[0])]
            self._poner_detalle(self.modelo.detalle(self.fila_sel))
        except Exception as exc:
            self._poner_detalle(f'No se pudo mostrar el detalle: {exc}')

    def _poner_detalle(self, texto):
        self.detalle.configure(state='normal')
        self.detalle.delete('1.0', 'end')
        self.detalle.insert('1.0', texto)
        self.detalle.configure(state='disabled')

    # ------------------------------------------------------------ figuras
    def _figuras(self, tab):
        self.sel_fig.pack_forget()
        figs = tab.figuras
        if not figs:
            self._figura = None
            self.imagen = None
            self.l_fig.configure(image='', text='Este bloque no tiene figura.' if self.bloque == 'todos'
                                 else 'Figura no disponible: vuelve a ejecutar la validación.')
            return
        self._nombres = {p.stem: p for p in figs}
        if len(figs) > 1:
            self.sel_fig.configure(values=list(self._nombres))
            self.sel_fig.set(figs[0].stem)
            self.sel_fig.pack(side='top', fill='x', padx=8, pady=(8, 0))
        self._figura = figs[0]
        self._dibujar_figura()

    def _elegir_figura(self, nombre):
        self._figura = self._nombres.get(nombre, self._figura)
        self._dibujar_figura()

    def _redimensionada(self, ev):
        if self._job_img is not None:
            self.f_fig.after_cancel(self._job_img)
        self._job_img = self.f_fig.after(150, self._dibujar_figura)

    def _dibujar_figura(self):
        self._job_img = None
        if self._figura is None:
            return
        try:
            w, h = max(self.f_fig.winfo_width() - 4, 50), max(self.f_fig.winfo_height() - 4, 50)
            img = Image.open(self._figura)
            img.load()
            k = min(w / img.width, h / img.height)
            tam = (max(int(img.width * k), 1), max(int(img.height * k), 1))
            self.imagen = ctk.CTkImage(light_image=img, dark_image=img, size=tam)
            self.l_fig.configure(image=self.imagen, text='')
        except Exception as exc:
            self.imagen = None
            self.l_fig.configure(image='', text=f'No se pudo abrir la figura ({exc})')

    def ampliar(self):
        """Figura a pantalla casi completa (para proyectar); se cierra con clic o Escape."""
        if self._figura is None:
            return
        try:
            win = ctk.CTkToplevel(self.frame)
            win.title(self._figura.stem)
            win.configure(fg_color=COLORES['tarjeta'])
            w, h = int(win.winfo_screenwidth() * .9), int(win.winfo_screenheight() * .85)
            win.geometry(f'{w}x{h}+{int(w * .055)}+30')
            img = Image.open(self._figura)
            img.load()
            k = min((w - 20) / img.width, (h - 20) / img.height)
            self._grande = ctk.CTkImage(light_image=img, dark_image=img,
                                        size=(max(int(img.width * k), 1), max(int(img.height * k), 1)))
            lb = ctk.CTkLabel(win, text='', image=self._grande)
            lb.pack(expand=True)
            for w_ in (win, lb):
                w_.bind('<Button-1>', lambda _e: win.destroy())
            win.bind('<Escape>', lambda _e: win.destroy())
            win.after(100, win.focus_force)
        except Exception as exc:
            self.ctx.mensaje(f'No se pudo ampliar la figura: {exc}', 'falla')

    def _elegir_bloque(self, texto):
        self.bloque = next((c for c in vd.ORDEN if vd.BLOQUES[c][0] == texto), self.bloque)
        self._pintar_bloque()

    # ------------------------------------------------------------ ejecución
    def ejecutar(self):
        if self.ejecutando:
            return
        self.ejecutando = True
        self.b_ejecutar.configure(state='disabled', text='Ejecutando… (hasta 120 s)')
        self.l_estado.configure(text='Ejecutando python3 -m hito3.validacion …', text_color=COLORES['aviso'])
        carpeta = self.carpeta
        self.ctx.en_hilo(lambda: vd.ejecutar_validacion(carpeta), self._termino)

    def _termino(self, res, err):
        self.ejecutando = False
        self.b_ejecutar.configure(state='normal', text='Volver a ejecutar la validación')
        ok, salida = res if res else (False, str(err))
        self.l_estado.configure(text=('Validación ejecutada y recargada.' if ok else
                                      f'La validación falló: {salida[-300:]}').replace('\n', ' '),
                                text_color=COLORES['ok' if ok else 'falla'])
        self.recargar()

    def elegir_carpeta(self):
        ruta = filedialog.askdirectory(title='Carpeta hito3/ (con resultados/ dentro)', initialdir=str(self.carpeta))
        if ruta:
            self.carpeta = vd.descubrir_carpeta(ruta)
            self.recargar()

    def al_cambiar(self, evento):
        if evento == 'tema':
            estilo_tabla(self.frame, es_oscuro())
            self._colorear_tags()
