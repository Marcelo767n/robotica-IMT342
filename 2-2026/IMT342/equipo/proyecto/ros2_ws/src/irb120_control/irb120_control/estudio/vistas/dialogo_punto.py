"""Diálogo para crear o editar un punto: pose (mm/°) o ángulos, tipo de movimiento y nombre."""
import customtkinter as ctk

from irb120_control.estudio.formato import n
from irb120_control.estudio.tema import COLORES, fuente
from irb120_control.estudio.vistas.estado import pose_tcp
from irb120_control.estudio.widgets import Dialogo
from irb120_control.trayectorias import Punto

POSE = ('X [mm]', 'Y [mm]', 'Z [mm]', 'roll [°]', 'pitch [°]', 'yaw [°]')
ANG = tuple(f'J{i} [°]' for i in range(1, 7))
MODOS = ('Pose (mm / °)', 'Ángulos (°)')


def _num(texto):
    return float(texto.strip().replace(',', '.'))


def pedir_punto(master, punto=None, nombre_sugerido='A', q_medido=None, herramienta='tcp'):
    """Devuelve el Punto aceptado o None."""
    d = Dialogo(master, 'Editar punto' if punto else 'Nuevo punto', 640)
    ctk.CTkLabel(d, text='Editar punto' if punto else 'Nuevo punto', font=fuente(4, True), anchor='w').pack(
        fill='x', padx=24, pady=(18, 6))
    f = ctk.CTkFrame(d, fg_color=COLORES['tarjeta'], corner_radius=10)
    f.pack(fill='x', padx=24, pady=6)
    f.columnconfigure(1, weight=1)
    f.columnconfigure(3, weight=1)
    nombre = ctk.CTkEntry(f, font=fuente(), height=38)
    nombre.insert(0, punto.nombre if punto else nombre_sugerido)
    ctk.CTkLabel(f, text='Nombre', font=fuente(0, True)).grid(row=0, column=0, padx=12, pady=8, sticky='w')
    nombre.grid(row=0, column=1, columnspan=3, padx=12, pady=8, sticky='ew')
    modo_ini = MODOS[1] if punto is not None and punto.q is not None else MODOS[0]
    modo = ctk.CTkSegmentedButton(f, values=list(MODOS), font=fuente(), height=38)
    modo.set(modo_ini)
    modo.grid(row=1, column=0, columnspan=4, padx=12, pady=6, sticky='ew')
    etiquetas, campos = [], []
    for i in range(6):
        lb = ctk.CTkLabel(f, text='', font=fuente(0, True), anchor='w')
        e = ctk.CTkEntry(f, font=fuente(), height=38)
        lb.grid(row=2 + i // 2, column=(i % 2) * 2, padx=12, pady=6, sticky='w')
        e.grid(row=2 + i // 2, column=(i % 2) * 2 + 1, padx=12, pady=6, sticky='ew')
        etiquetas.append(lb)
        campos.append(e)
    tipo = ctk.CTkOptionMenu(f, values=['auto', 'articular', 'lineal'], font=fuente(), height=38,
                             dropdown_font=fuente())
    tipo.set(punto.tipo if punto else 'auto')
    ctk.CTkLabel(f, text='Movimiento para llegar', font=fuente(0, True)).grid(row=5, column=0, padx=12, pady=8, sticky='w')
    tipo.grid(row=5, column=1, padx=12, pady=8, sticky='ew')
    error = ctk.CTkLabel(d, text='', font=fuente(), text_color=COLORES['falla'], wraplength=580, justify='left',
                         anchor='w')
    error.pack(fill='x', padx=24)

    def llenar(valores, fmt):
        for e, v in zip(campos, valores):
            e.delete(0, 'end')
            e.insert(0, '' if v is None else fmt(v))

    def etiquetar():
        for lb, t in zip(etiquetas, ANG if modo.get() == MODOS[1] else POSE):
            lb.configure(text=t)

    def inicial():
        etiquetar()
        if punto is None:
            llenar([''] * 6, str)
        elif punto.q is not None:
            llenar(punto.q, lambda v: n(v, 3))
        else:
            llenar(punto.pose, lambda v: n(v, 3))
    inicial()

    def cambio_modo(valor):
        """Convierte ángulos → pose al pasar de uno a otro cuando hay valores válidos."""
        etiquetar()
        try:
            v = [_num(e.get()) for e in campos]
        except ValueError:
            return
        if valor == MODOS[0]:
            p = pose_tcp(v, herramienta)
            if p:
                llenar(p, lambda x: n(x, 3))
    modo.configure(command=cambio_modo)

    def rellenar_medido():
        if q_medido is None:
            error.configure(text='No hay postura medida disponible.')
            return
        if modo.get() == MODOS[1]:
            llenar(q_medido, lambda v: n(v, 3))
        else:
            p = pose_tcp(q_medido, herramienta)
            if p:
                llenar(p, lambda x: n(x, 3))
        error.configure(text='')

    def aceptar():
        try:
            v = [_num(e.get()) for e in campos]
        except ValueError:
            error.configure(text='Escribe seis números (se admite coma o punto decimal).')
            return
        try:
            en_ang = modo.get() == MODOS[1]
            origen = punto.origen if punto is not None and (punto.q is not None) == en_ang else (
                'angulos' if en_ang else 'manual')
            d.resultado = Punto(nombre.get().strip(), pose=None if en_ang else v, q=v if en_ang else None,
                                origen=origen, tipo=tipo.get())
        except ValueError as exc:
            error.configure(text=str(exc))
            return
        d.destroy()

    fila = ctk.CTkFrame(d, fg_color='transparent')
    fila.pack(fill='x', padx=24, pady=(8, 18))
    ctk.CTkButton(fila, text='Rellenar con la postura medida', font=fuente(), height=42, command=rellenar_medido,
                  fg_color=COLORES['acento']).pack(side='left')
    ctk.CTkButton(fila, text='Aceptar', font=fuente(0, True), height=42, command=aceptar,
                  fg_color=COLORES['ok']).pack(side='right', padx=(10, 0))
    ctk.CTkButton(fila, text='Cancelar', font=fuente(), height=42, command=d.destroy,
                  fg_color=COLORES['nada']).pack(side='right')
    d.bind('<Return>', lambda _e: aceptar())
    return d.mostrar()
