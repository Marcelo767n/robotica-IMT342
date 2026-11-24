"""Piezas reutilizables: tarjeta, indicador de estado, tabla con tema y diálogos modales."""
import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

from irb120_control.estudio import tema
from irb120_control.estudio.tema import COLORES, fuente


class Tarjeta(ctk.CTkFrame):
    """Panel con borde y título; el contenido va en `.cuerpo`."""

    def __init__(self, master, titulo, **kw):
        super().__init__(master, fg_color=COLORES['tarjeta'], border_color=COLORES['borde'], border_width=1,
                         corner_radius=12, **kw)
        self.titulo = ctk.CTkLabel(self, text=titulo, font=fuente(2, True), text_color=COLORES['acento'], anchor='w')
        self.titulo.pack(fill='x', padx=14, pady=(10, 4))
        self.cuerpo = ctk.CTkFrame(self, fg_color='transparent')
        self.cuerpo.pack(fill='both', expand=True, padx=14, pady=(0, 12))


class Indicador(ctk.CTkFrame):
    """Punto de color (verde/ámbar/rojo/gris) con una etiqueta y un texto de valor."""

    def __init__(self, master, etiqueta, ancho_etiqueta=None):
        super().__init__(master, fg_color='transparent')
        self.punto = ctk.CTkLabel(self, text='●', font=fuente(6), width=26, text_color=COLORES['nada'])
        self.punto.pack(side='left')
        self.etiqueta = ctk.CTkLabel(self, text=etiqueta, font=fuente(0, True), anchor='w',
                                     width=ancho_etiqueta or 0)
        self.etiqueta.pack(side='left', padx=(0, 8))
        self.valor = ctk.CTkLabel(self, text='—', font=fuente(), anchor='w', text_color=COLORES['suave'])
        self.valor.pack(side='left', fill='x', expand=True)

    def poner(self, estado, texto):
        self.punto.configure(text_color=COLORES[estado if estado in tema.ESTADOS else 'nada'])
        self.valor.configure(text=texto)


def insignia(master, texto, estado):
    """Etiqueta redondeada con fondo del color del estado."""
    return ctk.CTkLabel(master, text=f' {texto} ', font=fuente(0, True), corner_radius=8,
                        text_color=COLORES[estado], fg_color=COLORES[f'{estado}_fondo'])


def estilo_tabla(raiz, oscuro, escala=1.0):
    """Estilo ttk de la tabla (Treeview) acorde al tema."""
    st = ttk.Style(raiz)
    st.theme_use('clam')
    fondo, texto = ('#1f2937', '#f3f4f6') if oscuro else ('#ffffff', '#111827')
    cab = '#374151' if oscuro else '#e5e7eb'
    st.configure('Estudio.Treeview', background=fondo, fieldbackground=fondo, foreground=texto,
                 rowheight=int(34 * escala), font=('DejaVu Sans', 13), borderwidth=0)
    st.configure('Estudio.Treeview.Heading', background=cab, foreground=texto, font=('DejaVu Sans', 13, 'bold'),
                 relief='flat')
    st.configure('Estudio.Treeview', bordercolor=fondo, lightcolor=fondo, darkcolor=fondo)
    st.configure('Estudio.Vertical.TScrollbar', background=cab, troughcolor=fondo, bordercolor=fondo,
                 arrowcolor=texto, lightcolor=cab, darkcolor=cab)
    st.map('Estudio.Treeview', background=[('selected', '#2563eb')], foreground=[('selected', '#ffffff')])
    st.map('Estudio.Treeview.Heading', background=[('active', cab)])


class Dialogo(ctk.CTkToplevel):
    """Ventana modal sencilla: título, cuerpo y botones; `resultado` queda en None si se cierra."""

    def __init__(self, master, titulo, ancho=560, alto=None):
        super().__init__(master)
        self.title(titulo)
        self.resultado = None
        self.transient(master.winfo_toplevel())
        self.configure(fg_color=COLORES['fondo'])
        self.geometry(f'{ancho}x{alto}' if alto else f'{ancho}x1')
        self.protocol('WM_DELETE_WINDOW', self.destroy)
        self.bind('<Escape>', lambda _e: self.destroy())

    def mostrar(self):
        """Centra, bloquea la ventana madre y espera a que se cierre."""
        self.update_idletasks()
        madre = self.master.winfo_toplevel()
        w, h = max(self.winfo_reqwidth(), 480), self.winfo_reqheight()
        x = madre.winfo_rootx() + (madre.winfo_width() - w) // 2
        y = madre.winfo_rooty() + max(20, (madre.winfo_height() - h) // 3)
        self.geometry(f'{w}x{h}+{max(0, x)}+{max(0, y)}')
        try:
            self.wait_visibility()
            self.grab_set()
            self.focus_force()
        except tk.TclError:
            pass
        self.wait_window()
        return self.resultado


def confirmar(master, titulo, lineas, aceptar='Confirmar', peligro=False):
    """Diálogo Sí/No con un resumen en líneas; devuelve True si se acepta."""
    d = Dialogo(master, titulo, 600)
    ctk.CTkLabel(d, text=titulo, font=fuente(4, True), anchor='w').pack(fill='x', padx=24, pady=(20, 8))
    caja = ctk.CTkFrame(d, fg_color=COLORES['tarjeta'], corner_radius=10)
    caja.pack(fill='both', expand=True, padx=24, pady=6)
    for linea in lineas:
        ctk.CTkLabel(caja, text=linea, font=fuente(), anchor='w', justify='left', wraplength=540).pack(
            fill='x', padx=14, pady=3)
    fila = ctk.CTkFrame(d, fg_color='transparent')
    fila.pack(fill='x', padx=24, pady=(10, 20))

    def si():
        d.resultado = True
        d.destroy()
    ctk.CTkButton(fila, text=aceptar, font=fuente(0, True), height=44, command=si,
                  fg_color=COLORES['falla'] if peligro else COLORES['ok']).pack(side='right', padx=(10, 0))
    ctk.CTkButton(fila, text='Cancelar', font=fuente(), height=44, command=d.destroy,
                  fg_color=COLORES['nada']).pack(side='right')
    return bool(d.mostrar())


def decidir(master, titulo, lineas, opciones, peligro=None):
    """Diálogo con varios botones: `opciones` = [(clave, texto)], la primera es la principal.

    Devuelve la clave elegida o None si se cancela/cierra. Cancelar se añade siempre.
    """
    d = Dialogo(master, titulo, 620)
    ctk.CTkLabel(d, text=titulo, font=fuente(4, True), anchor='w').pack(fill='x', padx=24, pady=(20, 8))
    caja = ctk.CTkFrame(d, fg_color=COLORES['tarjeta'], corner_radius=10)
    caja.pack(fill='both', expand=True, padx=24, pady=6)
    for linea in lineas:
        ctk.CTkLabel(caja, text=linea, font=fuente(), anchor='w', justify='left', wraplength=560).pack(
            fill='x', padx=14, pady=3)
    fila = ctk.CTkFrame(d, fg_color='transparent')
    fila.pack(fill='x', padx=24, pady=(10, 20))

    def elegir(clave):
        d.resultado = clave
        d.destroy()
    ctk.CTkButton(fila, text='Cancelar', font=fuente(), height=44, command=d.destroy,
                  fg_color=COLORES['nada']).pack(side='right')
    for k, (clave, texto) in reversed(list(enumerate(opciones))):
        color = COLORES['falla'] if clave == peligro else COLORES['acento'] if k == 0 else COLORES['nada']
        ctk.CTkButton(fila, text=texto, font=fuente(0, k == 0), height=44, fg_color=color,
                      command=lambda c=clave: elegir(c)).pack(side='right', padx=(0, 10))
    return d.mostrar()


def pedir_nombre_numero(master, titulo, nombre, numero, nota=''):
    """Pide nombre y Nº PLC (vacío = sin número). Devuelve (nombre, numero|None) o None."""
    d = Dialogo(master, titulo, 560)
    ctk.CTkLabel(d, text=titulo, font=fuente(4, True), anchor='w').pack(fill='x', padx=24, pady=(18, 6))
    f = ctk.CTkFrame(d, fg_color=COLORES['tarjeta'], corner_radius=10)
    f.pack(fill='x', padx=24, pady=6)
    f.columnconfigure(1, weight=1)
    ctk.CTkLabel(f, text='Nombre', font=fuente(0, True)).grid(row=0, column=0, padx=12, pady=8, sticky='w')
    e_nom = ctk.CTkEntry(f, font=fuente(), height=38)
    e_nom.insert(0, nombre)
    e_nom.grid(row=0, column=1, padx=12, pady=8, sticky='ew')
    ctk.CTkLabel(f, text='Nº PLC (1–99)', font=fuente(0, True)).grid(row=1, column=0, padx=12, pady=8, sticky='w')
    e_num = ctk.CTkEntry(f, font=fuente(), height=38, width=90)
    e_num.insert(0, '' if numero is None else str(numero))
    e_num.grid(row=1, column=1, padx=12, pady=8, sticky='w')
    if nota:
        ctk.CTkLabel(f, text=nota, font=fuente(-1), text_color=COLORES['suave'], wraplength=500, justify='left',
                     anchor='w').grid(row=2, column=0, columnspan=2, padx=12, pady=(0, 8), sticky='w')
    error = ctk.CTkLabel(d, text='', font=fuente(), text_color=COLORES['falla'], anchor='w', wraplength=500)
    error.pack(fill='x', padx=24)

    def aceptar():
        nom = e_nom.get().strip()
        txt = e_num.get().strip()
        if not nom:
            error.configure(text='Escribe un nombre.')
            return
        try:
            num = int(txt) if txt else None
            if num is not None and not 1 <= num <= 99:
                raise ValueError
        except ValueError:
            error.configure(text='El número de PLC debe ser un entero de 1 a 99 (o vacío).')
            return
        d.resultado = (nom, num)
        d.destroy()
    fila = ctk.CTkFrame(d, fg_color='transparent')
    fila.pack(fill='x', padx=24, pady=(8, 18))
    ctk.CTkButton(fila, text='Aceptar', font=fuente(0, True), height=42, command=aceptar,
                  fg_color=COLORES['ok']).pack(side='right', padx=(10, 0))
    ctk.CTkButton(fila, text='Cancelar', font=fuente(), height=42, command=d.destroy,
                  fg_color=COLORES['nada']).pack(side='right')
    d.bind('<Return>', lambda _e: aceptar())
    return d.mostrar()
