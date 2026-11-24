"""Pestaña Trayectoria: editor de puntos, captura, buzón, guardar/cargar, planificar y enviar al panel."""
import time
from tkinter import ttk

import customtkinter as ctk

from irb120_control.estudio import biblioteca
from irb120_control.estudio.formato import n, seis
from irb120_control.estudio.tema import COLORES, es_oscuro, fuente
from irb120_control.estudio.vistas import Vista
from irb120_control.estudio.vistas.dialogo_punto import pedir_punto
from irb120_control.estudio.vistas.estado import pose_tcp
from irb120_control.estudio.widgets import (confirmar, decidir, estilo_tabla, pedir_nombre_numero, Tarjeta)
from irb120_control.trayectorias import Punto

COLUMNAS = (('n', '#', 36), ('nombre', 'Nombre', 90), ('origen', 'Origen', 96), ('tipo', 'Tipo', 90),
            ('x', 'X mm', 64), ('y', 'Y mm', 64), ('z', 'Z mm', 64), ('r', 'Roll °', 62), ('p', 'Pitch °', 84),
            ('w', 'Yaw °', 66), ('q', 'q [°] J1 … J6', 290))


class VistaTrayectoria(Vista):
    titulo = 'Trayectoria'

    def __init__(self, master, ctx):
        self.ctx = ctx
        self.enviada = False
        self.b = {}
        self.rutas = {}
        self.t_plan0 = 0.
        self.frame = f = ctk.CTkFrame(master, fg_color='transparent')
        self._biblioteca(f)
        self._datos(f)
        self._acciones(f)
        self._tabla(f)
        self.refrescar_biblioteca()
        self.refrescar_tabla()
        self.refrescar_botones()

    # ------------------------------------------------------------ construcción
    def _biblioteca(self, f):
        t = Tarjeta(f, 'Biblioteca de trayectorias')
        t.pack(fill='x', padx=6, pady=(4, 4))
        fila = ctk.CTkFrame(t.cuerpo, fg_color='transparent')
        fila.pack(fill='x')
        # Dos filas: en una sola (≈1100 px de anchos fijos) Tk la encogía, CustomTkinter la redibujaba a su
        # ancho fijo y el ciclo de geometría no terminaba (la ventana se congelaba).
        self.o_lib = ctk.CTkOptionMenu(fila, values=['(vacía)'], font=fuente(), height=38, dropdown_font=fuente())
        self.o_lib.pack(side='left', fill='x', expand=True)
        fila = ctk.CTkFrame(t.cuerpo, fg_color='transparent')
        fila.pack(fill='x', pady=(6, 0))
        self.bl = {}
        for clave, texto, cmd, ancho in (('abrir', 'Abrir', self.abrir, 80), ('nueva', 'Nueva', self.nueva, 80),
                                         ('guardar', 'Guardar', self.guardar, 90),
                                         ('como', 'Guardar como…', self.guardar_como, 150),
                                         ('dup', 'Duplicar', self.duplicar_tray, 100),
                                         ('ren', 'Renombrar', self.renombrar, 110),
                                         ('del', 'Borrar', self.borrar_tray, 90)):
            self.bl[clave] = ctk.CTkButton(fila, text=texto, font=fuente(), height=38, width=ancho, command=cmd,
                                           fg_color=COLORES['acento'] if clave in ('guardar',) else COLORES['nada'])
            self.bl[clave].pack(side='left', padx=3)
        self.bl['del'].configure(fg_color=COLORES['falla'])
        self.l_arch = ctk.CTkLabel(t.cuerpo, text='', font=fuente(-1), anchor='w', text_color=COLORES['suave'])
        self.l_arch.pack(fill='x', pady=(6, 0))

    def _datos(self, f):
        t = Tarjeta(f, 'Trayectoria')
        t.pack(fill='x', padx=6, pady=(4, 6))
        fila = ctk.CTkFrame(t.cuerpo, fg_color='transparent')
        fila.pack(fill='x')
        ctk.CTkLabel(fila, text='Nombre', font=fuente(0, True)).pack(side='left')
        self.e_nombre = ctk.CTkEntry(fila, font=fuente(), width=240, height=38)
        self.e_nombre.insert(0, self.ctx.nombre)
        self.e_nombre.pack(side='left', padx=(8, 20))
        self.e_nombre.bind('<KeyRelease>', lambda _e: self._nombre())
        ctk.CTkLabel(fila, text='Nº PLC (1–99)', font=fuente(0, True)).pack(side='left')
        self.e_num = ctk.CTkEntry(fila, font=fuente(), width=60, height=38, justify='center')
        if self.ctx.numero is not None:
            self.e_num.insert(0, str(self.ctx.numero))
        self.e_num.pack(side='left', padx=(8, 20))
        self.e_num.bind('<KeyRelease>', lambda _e: self._numero())
        self.v_cerrar = ctk.BooleanVar(value=self.ctx.cerrar)
        ctk.CTkCheckBox(fila, text='Cerrar ciclo (volver a A)', font=fuente(), variable=self.v_cerrar,
                        command=self._parametros).pack(side='left', padx=(0, 20))
        ctk.CTkLabel(fila, text='Repeticiones', font=fuente(0, True)).pack(side='left')
        self.e_rep = ctk.CTkEntry(fila, font=fuente(), width=64, height=38, justify='center')
        self.e_rep.insert(0, str(self.ctx.repeticiones))
        self.e_rep.pack(side='left', padx=(8, 20))
        self.e_rep.bind('<KeyRelease>', lambda _e: self._parametros())
        ctk.CTkLabel(fila, text='Punto', font=fuente(0, True)).pack(side='left')
        self.o_herr = ctk.CTkOptionMenu(fila, values=['tcp', 'brida'], font=fuente(), width=100, height=38,
                                        command=lambda _v: self._parametros(), dropdown_font=fuente())
        self.o_herr.pack(side='left', padx=8)
        fila2 = ctk.CTkFrame(t.cuerpo, fg_color='transparent')
        fila2.pack(fill='x', pady=(8, 0))
        ctk.CTkLabel(fila2, text='Velocidad', font=fuente(0, True)).pack(side='left')
        self.s_vel = ctk.CTkSlider(fila2, from_=1, to=100, number_of_steps=99, width=360, command=self._velocidad)
        self.s_vel.set(self.ctx.velocidad_efectiva())
        self.s_vel.pack(side='left', padx=12)
        self.l_vel = ctk.CTkLabel(fila2, text='', font=fuente(0, True), width=220, anchor='w')
        self.l_vel.pack(side='left')
        self._etiqueta_vel()
        self.b_panel_vel = ctk.CTkButton(fila2, text='Usar la del panel', font=fuente(-1), height=32, width=150,
                                         fg_color=COLORES['nada'], command=self._vel_panel)
        self.b_panel_vel.pack(side='left')
        self.l_plc = ctk.CTkLabel(fila2, text='', font=fuente(-1, True), anchor='w')
        self.l_plc.pack(side='left', padx=20)

    def _tabla(self, f):
        cont = ctk.CTkFrame(f, fg_color='transparent')
        cont.pack(fill='both', expand=True, padx=6, pady=4)
        der = ctk.CTkFrame(cont, fg_color='transparent')
        der.pack(side='right', fill='y', padx=(8, 0))
        izq = ctk.CTkFrame(cont, fg_color=COLORES['tarjeta'], corner_radius=12, border_width=1,
                           border_color=COLORES['borde'])
        izq.pack(side='left', fill='both', expand=True)
        estilo_tabla(self.frame, es_oscuro())
        self.tabla = ttk.Treeview(izq, columns=[c[0] for c in COLUMNAS], show='headings', selectmode='browse',
                                  style='Estudio.Treeview', height=7)
        for c, tit, ancho in COLUMNAS:
            self.tabla.heading(c, text=tit)
            self.tabla.column(c, width=ancho, minwidth=40, anchor='w' if c in ('nombre', 'q') else 'center',
                              stretch=(c == 'q'))
        self.tabla.tag_configure('falla', foreground='#ef4444')
        sb = ttk.Scrollbar(izq, command=self.tabla.yview, style='Estudio.Vertical.TScrollbar')
        self.tabla.configure(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y', padx=(0, 4), pady=6)
        self.tabla.pack(side='left', fill='both', expand=True, padx=(8, 0), pady=8)
        self.tabla.bind('<Double-1>', lambda _e: self.editar())
        self.tabla.bind('<<TreeviewSelect>>', lambda _e: self.refrescar_botones())
        pos = {'add': (0, 0, 1), 'ins': (0, 1, 1), 'dupp': (1, 0, 1), 'edit': (1, 1, 1), 'up': (2, 0, 1),
               'down': (2, 1, 1), 'del': (3, 0, 2), 'cap': (4, 0, 2), 'buz': (5, 0, 2)}
        for clave, texto, cmd in (('add', 'Añadir al final', self.agregar), ('ins', 'Insertar tras…', self.insertar),
                                  ('dupp', 'Duplicar punto', self.duplicar_punto), ('edit', 'Editar', self.editar),
                                  ('up', 'Subir', self.subir), ('down', 'Bajar', self.bajar),
                                  ('del', 'Borrar', self.borrar),
                                  ('cap', 'Capturar postura actual', self.capturar),
                                  ('buz', 'Traer del buzón', self.traer_buzon)):
            self.b[clave] = ctk.CTkButton(der, text=texto, font=fuente(), height=38, width=150, command=cmd,
                                          fg_color=COLORES['acento'] if clave in ('add', 'ins', 'cap', 'buz') else COLORES['nada'])
            r, col, span = pos[clave]
            self.b[clave].grid(row=r, column=col, columnspan=span, padx=3, pady=3, sticky='ew')
        self.b['del'].configure(fg_color=COLORES['falla'])
        self.l_buzon = ctk.CTkLabel(der, text='', font=fuente(-1, True), text_color=COLORES['aviso'],
                                    wraplength=240, justify='left')
        self.l_buzon.grid(row=6, column=0, columnspan=2, pady=4)

    def _acciones(self, f):
        t = Tarjeta(f, 'Verificar y enviar')
        t.pack(side='bottom', fill='x', padx=6, pady=(4, 4))
        fila = ctk.CTkFrame(t.cuerpo, fg_color='transparent')
        fila.pack(fill='x')
        self.b['plan'] = ctk.CTkButton(fila, text='Planificar y verificar', font=fuente(0, True), height=44, width=240,
                                       command=self.ctx.planificar)
        self.b['prev'] = ctk.CTkButton(fila, text='Vista previa en RViz', font=fuente(), height=44, width=200,
                                       command=self.vista_previa)
        self.o_factor = ctk.CTkOptionMenu(fila, values=['×1', '×2', '×4'], width=76, height=44, font=fuente(),
                                          dropdown_font=fuente())
        self.b['send'] = ctk.CTkButton(fila, text='Enviar al panel', font=fuente(0, True), height=44, width=200,
                                       fg_color=COLORES['ok'], command=self.enviar)
        self.b['plan'].pack(side='left', padx=(0, 18))
        self.b['prev'].pack(side='left', padx=(0, 4))
        self.o_factor.pack(side='left', padx=(0, 18))
        self.b['send'].pack(side='left')
        self.l_plan = ctk.CTkLabel(t.cuerpo, text='', font=fuente(), anchor='w', justify='left', wraplength=1150)
        self.l_plan.pack(fill='x', pady=(8, 0))
        self.barra = ctk.CTkProgressBar(t.cuerpo, mode='indeterminate', height=10)
        self.fila_ej = ctk.CTkFrame(t.cuerpo, fg_color='transparent')
        for clave, texto, color in (('pausar', 'Pausar', 'aviso'), ('reanudar', 'Reanudar', 'ok'),
                                    ('cancelar', 'Cancelar', 'falla')):
            self.b[clave] = ctk.CTkButton(self.fila_ej, text=texto, font=fuente(0, True), height=42, width=150,
                                          fg_color=COLORES[color], command=lambda a=clave: self.control(a))
            self.b[clave].pack(side='left', padx=(0, 10))

    # ------------------------------------------------------------ parámetros
    def _nombre(self):
        nombre = self.e_nombre.get().strip()
        if nombre:
            self.ctx.nombre = nombre
            if self.ctx.plan_tray is not None:
                self.ctx.plan_tray.nombre = nombre

    def _numero(self):
        txt = self.e_num.get().strip()
        try:
            self.ctx.numero = int(txt) if txt else None
            if self.ctx.numero is not None and not 1 <= self.ctx.numero <= 99:
                raise ValueError
        except ValueError:
            self.ctx.mensaje('El número de PLC debe estar entre 1 y 99.', 'aviso')
            return
        self._etiqueta_archivo()

    def _parametros(self):
        c = self.ctx
        c.cerrar = bool(self.v_cerrar.get())
        c.herramienta = self.o_herr.get()
        try:
            c.repeticiones = int(self.e_rep.get())
        except ValueError:
            pass
        c.cambio('lista')

    def _etiqueta_vel(self):
        v = self.ctx.velocidad_efectiva()
        self.l_vel.configure(text=f'{n(v, 0)} %' + ('  (la del panel)' if self.ctx.velocidad is None else ''))

    def _velocidad(self, valor):
        self.ctx.velocidad = float(round(valor))
        self._etiqueta_vel()
        self.ctx.cambio('lista')

    def _vel_panel(self):
        self.ctx.velocidad = None
        self.s_vel.set(self.ctx.velocidad_efectiva())
        self._etiqueta_vel()
        self.ctx.cambio('lista')

    # ------------------------------------------------------------ tabla
    def seleccion(self):
        s = self.tabla.selection()
        return int(s[0]) if s else None

    def refrescar_tabla(self):
        c = self.ctx
        sel = self.seleccion()
        malos = set()
        if c.plan is not None:
            malos = {t.hasta for t in c.plan.tramos if not t.ok}
        self.tabla.delete(*self.tabla.get_children())
        for i, p in enumerate(c.editor.puntos):
            pose = p.pose
            if p.q is not None:
                pose = pose_tcp(p.q, c.herramienta) or p.pose
            q = p.q
            if q is None and c.plan is not None and i < len(c.plan.q_puntos):
                q = c.plan.q_puntos[i]
            vals = [i + 1, p.nombre, p.origen, p.tipo,
                    *[(n(v, 1) if pose else '—') for v in (pose or [None] * 6)],
                    '—' if q is None else '  '.join(n(v, 1) for v in q)]
            self.tabla.insert('', 'end', iid=str(i), values=vals, tags=('falla',) if p.nombre in malos else ())
        if sel is not None and sel < len(c.editor):
            self.tabla.selection_set(str(sel))

    def seleccionar(self, i):
        if i is not None and 0 <= i < len(self.ctx.editor):
            self.tabla.selection_set(str(i))
            self.tabla.see(str(i))

    def refrescar_botones(self):
        c, sel = self.ctx, self.seleccion()
        tiene = sel is not None
        st = lambda ok: 'normal' if ok else 'disabled'
        self.b['edit'].configure(state=st(tiene))
        self.b['ins'].configure(state=st(tiene))
        self.b['dupp'].configure(state=st(tiene))
        self.b['del'].configure(state=st(tiene))
        self.b['up'].configure(state=st(tiene and sel > 0))
        self.b['down'].configure(state=st(tiene and sel < len(c.editor) - 1))
        self.b['cap'].configure(state=st(c.q_medido() is not None))
        self.b['buz'].configure(state=st(c.hay_panel))
        self.b['plan'].configure(state=st(len(c.editor) > 0 and not c.planificando))
        puede = c.puede_enviar()
        self.b['prev'].configure(state=st(puede))
        self.b['send'].configure(state=st(puede))
        if not c.planificando:
            self.t_plan0 = 0.
        if c.planificando:
            self.barra.pack(fill='x', pady=4)
            self.barra.start()
        else:
            self.barra.stop()
            self.barra.pack_forget()
        # Texto del plan
        if c.planificando:
            self.t_plan0 = self.t_plan0 or time.monotonic()
            self.l_plan.configure(text=f'Planificando y verificando todas las reglas… {time.monotonic() - self.t_plan0:.0f} s',
                                  text_color=COLORES['suave'])
        elif c.plan_error:
            self.l_plan.configure(text=c.plan_error, text_color=COLORES['falla'])
        elif c.plan is not None:
            extra = '' if c.hay_panel else '  Sin panel: solo se puede estudiar, no enviar.'
            self.l_plan.configure(text=c.plan.resumen + extra,
                                  text_color=COLORES['ok'] if c.plan.ok else COLORES['falla'])
        else:
            self.l_plan.configure(text='Sin planificar: pulsa «Planificar y verificar».', text_color=COLORES['suave'])

    # ------------------------------------------------------------ puntos
    def agregar(self):
        c = self.ctx
        p = pedir_punto(self.frame, None, c.editor.nombre_nuevo(), c.q_medido(), c.herramienta)
        if p is not None:
            self._con_error(lambda: self.seleccionar(c.editor.agregar(p)))

    def insertar(self):
        c = self.ctx
        i = self.seleccion()
        p = pedir_punto(self.frame, None, c.editor.nombre_nuevo(), c.q_medido(), c.herramienta)
        if p is not None:
            self._con_error(lambda: self.seleccionar(c.editor.insertar(i, p)))

    def duplicar_punto(self):
        i = self.seleccion()
        if i is not None:
            j = self.ctx.editor.duplicar(i)
            self.ctx.cambio('lista')
            self.seleccionar(j)

    def editar(self):
        i = self.seleccion()
        if i is None:
            return
        c = self.ctx
        p = pedir_punto(self.frame, c.editor.puntos[i], c.editor.puntos[i].nombre, c.q_medido(), c.herramienta)
        if p is not None:
            self._con_error(lambda: c.editor.editar(i, p))
            self.seleccionar(i)

    def _con_error(self, f):
        try:
            f()
        except ValueError as exc:
            self.ctx.mensaje(str(exc), 'falla')
        self.ctx.cambio('lista')

    def subir(self):
        i = self.seleccion()
        if i is not None:
            j = self.ctx.editor.subir(i)
            self.ctx.cambio('lista')
            self.seleccionar(j)

    def bajar(self):
        i = self.seleccion()
        if i is not None:
            j = self.ctx.editor.bajar(i)
            self.ctx.cambio('lista')
            self.seleccionar(j)

    def borrar(self):
        i = self.seleccion()
        if i is not None:
            j = self.ctx.editor.borrar(i)
            self.ctx.cambio('lista')
            self.seleccionar(j)

    def capturar(self):
        c = self.ctx
        q = c.q_medido()
        if q is None:
            c.mensaje('No hay postura medida del robot.', 'falla')
            return
        p = Punto(c.editor.nombre_nuevo(), pose=pose_tcp(q, c.herramienta), q=q, origen='captura')
        self.seleccionar(c.editor.insertar(self.seleccion(), p))
        c.cambio('lista')
        c.mensaje(f'Punto «{p.nombre}» capturado de la postura actual.')

    # ------------------------------------------------------------ buzón
    def _nuevas(self):
        b = self.ctx.estado().get('buzon')
        if not isinstance(b, list):
            return 0
        return sum(1 for e in b if isinstance(e, dict) and isinstance(e.get('id'), int) and e['id'] > self.ctx.ultimo_buzon)

    def traer_buzon(self):
        c = self.ctx
        despues = self.seleccion()
        self.b['buz'].configure(state='disabled')

        def listo(res, err):
            if err is not None or not res or not res.get('ok'):
                c.mensaje((res or {}).get('error') or f'Buzón: {err}', 'falla')
                return
            ent = res.get('entradas') or []
            cuantas, ultimo = c.editor.desde_buzon(ent, despues)
            c.ultimo_buzon = max(c.ultimo_buzon, ultimo)
            if cuantas:
                c.cambio('lista')
                self.seleccionar(despues + cuantas if despues is not None else len(c.editor) - 1)
            c.mensaje(f'Buzón: {cuantas} punto(s) traído(s).' if cuantas else 'El buzón no tiene puntos nuevos.')
        c.en_hilo(lambda: c.cliente.accion('buzon_tomar', {'desde_id': c.ultimo_buzon}), listo)

    # ------------------------------------------------------------ biblioteca
    def refrescar_biblioteca(self, elegir=None):
        c = self.ctx
        ents = biblioteca.listar(c.carpeta)
        self.rutas = {biblioteca.etiqueta(e): e.ruta for e in ents}
        vals = list(self.rutas) or ['(sin trayectorias guardadas)']
        self.o_lib.configure(values=vals)
        ruta = elegir or c.ruta
        sel = next((k for k, r in self.rutas.items() if r == ruta), None)
        self.o_lib.set(sel or vals[0])
        self._etiqueta_archivo()

    def _etiqueta_archivo(self):
        c = self.ctx
        arch = c.ruta.name if c.ruta else 'sin guardar'
        marca = '  ● cambios sin guardar' if c.sucio() else ''
        plc = (f'Nº PLC {c.numero}: el PLC la pide con valor = {c.numero}' if c.numero is not None
               else 'Sin número: no es visible para el PLC')
        self.l_arch.configure(text=f'Archivo: {arch}{marca}   ·   {plc}',
                              text_color=COLORES['aviso'] if marca else COLORES['suave'])
        self.l_plc.configure(text=(f'el PLC la pide con valor = {c.numero}' if c.numero is not None
                                   else 'sin número: no visible para el PLC'),
                             text_color=COLORES['ok'] if c.numero is not None else COLORES['suave'])

    def _seleccion_lib(self):
        return self.rutas.get(self.o_lib.get())

    def _resolver_ocupado(self, exc, accion):
        """Pregunta qué hacer si el número/archivo está ocupado; accion(reemplazar) reintenta. True si se guardó."""
        c = self.ctx
        libre = biblioteca.numero_libre(c.carpeta, (c.numero or 0) + 1)
        op = decidir(self.frame, 'Número o archivo ocupado',
                     [str(exc), f'Puedes usar el siguiente número libre ({libre}) o reemplazar: la otra '
                                'trayectoria se mueve a la papelera.'],
                     [('libre', f'Usar el Nº {libre}'), ('reemplazar', 'Reemplazar')], peligro='reemplazar')
        if op is None:
            return False
        if op == 'libre':
            c.numero = libre
            self.e_num.delete(0, 'end')
            self.e_num.insert(0, str(libre))
        accion(op == 'reemplazar')
        return True

    def _intentar(self, accion):
        """Ejecuta accion(reemplazar) gestionando errores y números ocupados. True si terminó bien."""
        try:
            try:
                accion(False)
            except biblioteca.Ocupado as exc:
                if not self._resolver_ocupado(exc, accion):
                    return False
        except (ValueError, OSError) as exc:
            self.ctx.mensaje(f'No se pudo guardar: {exc}', 'falla')
            return False
        return True

    def guardar(self):
        c = self.ctx
        if not self._intentar(lambda r: c.guardar(r)):
            return False
        c.mensaje(f'Guardada en {c.ruta}')
        self.refrescar_biblioteca()
        return True

    def guardar_como(self):
        c = self.ctx
        r = pedir_nombre_numero(self.frame, 'Guardar como…', biblioteca.nombre_unico(c.carpeta, c.nombre),
                                biblioteca.numero_libre(c.carpeta) if c.numero is not None else None,
                                'Con número, el PLC puede pedirla; sin número solo se usa desde el Estudio.')
        if r is None:
            return False
        nombre, num = r
        if not self._intentar(lambda rep: c.guardar_como(nombre, num, rep)):
            return False
        self.poner_parametros()
        c.mensaje(f'Guardada como {c.ruta.name}')
        self.refrescar_biblioteca()
        return True

    def renombrar(self):
        c = self.ctx
        r = pedir_nombre_numero(self.frame, 'Renombrar trayectoria', c.nombre, c.numero)
        if r is None:
            return
        antes = (c.nombre, c.numero)
        c.nombre, c.numero = r
        if c.ruta is not None and not self._intentar(lambda rep: c.guardar(rep)):
            c.nombre, c.numero = antes
        self.poner_parametros()
        self.refrescar_biblioteca()

    def duplicar_tray(self):
        c = self.ctx
        ruta = self._seleccion_lib()
        if ruta is None:
            return
        base = next((e for e in biblioteca.listar(c.carpeta) if e.ruta == ruta), None)
        r = pedir_nombre_numero(self.frame, 'Duplicar trayectoria',
                                biblioteca.nombre_unico(c.carpeta, base.nombre + ' copia'),
                                biblioteca.numero_libre(c.carpeta) if base and base.numero is not None else None)
        if r is None:
            return
        nuevo = []
        if self._intentar(lambda rep: nuevo.append(biblioteca.duplicar(ruta, c.carpeta, r[0], r[1], rep))):
            c.mensaje(f'Duplicada como {nuevo[-1].name}')
            self.refrescar_biblioteca(nuevo[-1])

    def borrar_tray(self):
        c = self.ctx
        ruta = self._seleccion_lib()
        if ruta is None:
            return
        if not confirmar(self.frame, 'Mover a la papelera', [f'«{self.o_lib.get()}» se moverá a la carpeta '
                                                           f'papelera/ (no se borra del disco).'],
                         'Mover a la papelera', True):
            return
        try:
            c.borrar_archivo(ruta)
            c.mensaje('Movida a la papelera.')
        except OSError as exc:
            c.mensaje(f'No se pudo borrar: {exc}', 'falla')
        self.refrescar_biblioteca()

    def _proteger_cambios(self):
        """True si se puede continuar (sin cambios, guardados o descartados)."""
        c = self.ctx
        if not c.sucio():
            return True
        op = decidir(self.frame, 'Cambios sin guardar', [f'«{c.nombre}» tiene cambios sin guardar.'],
                     [('guardar', 'Guardar y seguir'), ('descartar', 'Descartar')], peligro='descartar')
        if op == 'guardar':
            return self.guardar()
        return op == 'descartar'

    def nueva(self):
        if self._proteger_cambios():
            self.ctx.nueva()
            self.poner_parametros()
            self.refrescar_biblioteca()
            self.ctx.mensaje('Trayectoria nueva y vacía (ciclo abierto): añade puntos.')

    def abrir(self):
        c = self.ctx
        ruta = self._seleccion_lib()
        if ruta is None:
            c.mensaje('No hay trayectorias guardadas.', 'aviso')
            return
        if not self._proteger_cambios():
            return
        try:
            c.abrir(ruta)
        except (ValueError, OSError) as exc:
            c.mensaje(f'No se pudo abrir: {exc}', 'falla')
            return
        self.poner_parametros()
        self.refrescar_biblioteca()
        c.mensaje(f'Abierta «{c.nombre}» ({len(c.editor)} puntos).')

    def poner_parametros(self):
        c = self.ctx
        self.e_nombre.delete(0, 'end')
        self.e_nombre.insert(0, c.nombre)
        self.e_rep.delete(0, 'end')
        self.e_rep.insert(0, str(c.repeticiones))
        self.v_cerrar.set(c.cerrar)
        self.o_herr.set(c.herramienta)
        self.e_num.delete(0, 'end')
        if c.numero is not None:
            self.e_num.insert(0, str(c.numero))
        self._etiqueta_archivo()

    # ------------------------------------------------------------ panel
    def vista_previa(self):
        c = self.ctx
        cuerpo = c.cuerpo_envio(factor=float(self.o_factor.get()[1:]))
        if cuerpo is None:
            return
        c.mensaje('Pidiendo la vista previa al panel…')
        c.en_hilo(lambda: c.cliente.accion('vista_previa', cuerpo, timeout=10.),
                  lambda r, e: c.mensaje('Vista previa en marcha en RViz.' if r and r.get('ok')
                                         else (r or {}).get('error') or f'Vista previa: {e}',
                                         'info' if r and r.get('ok') else 'falla'))

    def resumen_envio(self):
        c, plan = self.ctx, self.ctx.plan
        t = c.plan_tray
        lineas = [f'Trayectoria «{t.nombre}»: {len(t.puntos)} puntos, {len(plan.tramos)} tramos'
                  f'{" (cierra el ciclo)" if t.cerrar else ""}.']
        for tr in plan.tramos:
            ev = tr.opciones.get(tr.tipo)
            lineas.append(f'  {tr.indice + 1}. {tr.desde} → {tr.hasta}: {tr.tipo}'
                          + (f', {n(ev.duracion_s, 1)} s' if ev else ''))
        lineas.append(f'Duración de una vuelta: {n(plan.duracion_s, 1)} s · velocidad {n(c.plan_velocidad, 0)} % · '
                      f'{t.repeticiones} repetición(es).')
        lineas.append('El robot REAL se moverá. El panel volverá a verificar con la postura medida y se detiene en '
                      'cada punto. Ten el paro de emergencia a mano.')
        return lineas

    def enviar(self):
        c = self.ctx
        if not c.puede_enviar():
            return
        if not confirmar(self.frame, '¿Enviar la trayectoria al panel?', self.resumen_envio(), 'Enviar y ejecutar', True):
            return
        cuerpo = c.cuerpo_envio()

        def listo(r, e):
            if r and r.get('ok'):
                self.enviada = True
                c.mensaje('Trayectoria aceptada por el panel.')
            else:
                c.mensaje((r or {}).get('error') or f'Envío: {e}', 'falla')
            self.refrescar_control()
        c.mensaje('Enviando al panel…')
        c.en_hilo(lambda: c.cliente.accion('trayectoria', cuerpo, timeout=20.), listo)

    def control(self, accion):
        c = self.ctx
        c.en_hilo(lambda: c.cliente.accion(accion, {}, timeout=5.),
                  lambda r, e: c.mensaje(f'{accion.capitalize()}: ' + ('hecho.' if r and r.get('ok')
                                                                       else (r or {}).get('error') or str(e)),
                                         'info' if r and r.get('ok') else 'falla'))

    def refrescar_control(self):
        fase = (self.ctx.estado().get('trayectoria') or {}).get('fase')
        activa = fase in ('ejecutando', 'pausada')
        if activa or (self.enviada and fase in (None, 'lista')):
            self.fila_ej.pack(fill='x', pady=(8, 0))
        else:
            self.enviada = False
            self.fila_ej.pack_forget()
        self.b['pausar'].configure(state='normal' if fase == 'ejecutando' else 'disabled')
        self.b['reanudar'].configure(state='normal' if fase == 'pausada' else 'disabled')
        self.b['cancelar'].configure(state='normal' if activa else 'disabled')

    # ------------------------------------------------------------ ganchos
    def actualizar(self, estado, error):
        n_nuevas = self._nuevas()
        self.l_buzon.configure(text=f'{n_nuevas} punto(s) nuevo(s) en el buzón (RViz / visión)' if n_nuevas else '')
        self.b['buz'].configure(fg_color=COLORES['aviso'] if n_nuevas else COLORES['acento'])
        if self.ctx.velocidad is None:
            self.s_vel.set(self.ctx.velocidad_efectiva())
            self._etiqueta_vel()
        self.refrescar_botones()
        self.refrescar_control()
        self._etiqueta_archivo()

    def al_cambiar(self, evento):
        if evento in ('lista', 'plan'):
            self.refrescar_tabla()
            self.refrescar_botones()
        elif evento == 'tema':
            estilo_tabla(self.frame, es_oscuro())
