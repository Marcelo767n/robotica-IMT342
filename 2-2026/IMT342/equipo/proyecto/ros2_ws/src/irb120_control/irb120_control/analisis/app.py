"""Ventana principal: lee el estado del panel, calcula en segundo plano y refresca las pestañas."""
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk

from irb120_control.analisis import calculos, fuente
from irb120_control.analisis.vistas.cinematica import VistaCinematica
from irb120_control.analisis.vistas.dinamica import VistaDinamica
from irb120_control.analisis.vistas.jacobiano import VistaJacobiano
from irb120_control.analisis.vistas.ramas import VistaRamas
from irb120_control.analisis.vistas.trayectoria import VistaTrayectoria

VISTAS = (VistaCinematica, VistaRamas, VistaTrayectoria, VistaJacobiano, VistaDinamica)


class App(tk.Tk):
    def __init__(self, source, pestana=0):
        super().__init__()
        self.title('IRB 120 · Análisis Hito 2 en vivo (solo lectura)')
        self.geometry('1320x880')
        style = ttk.Style(self)
        style.configure('Treeview', rowheight=24, font=('DejaVu Sans', 11))
        style.configure('Treeview.Heading', font=('DejaVu Sans', 11, 'bold'))
        style.configure('TNotebook.Tab', font=('DejaVu Sans', 12), padding=(12, 6))
        self.source = source
        self.estado = tk.Label(self, font=('DejaVu Sans', 12), anchor='w', padx=10, pady=6)
        self.estado.pack(fill='x')
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True)
        self.vistas = []
        for cls in VISTAS:
            vista = cls(self.notebook)
            self.notebook.add(vista.frame, text=cls.titulo)
            self.vistas.append(vista)
        self.notebook.select(pestana)
        self.resultados = queue.Queue()
        self.pedido = None          # Entrada pendiente de calcular
        self.mostrado = None        # Entrada del último resultado dibujado
        self.ocupado = False
        self.after(100, self.ciclo)

    def ciclo(self):
        data, error = self.source.instantanea()
        e = None if data is None else fuente.entrada(data)
        if error:
            self.estado.configure(text=error, fg='#b91c1c')
        elif e is None:
            self.estado.configure(text='Esperando medida y objetivo del panel…', fg='#6b7280')
        else:
            modo = data.get('modo') or '—'
            mov = ' · MOVIENDO' if data.get('ocupado') else ''
            self.estado.configure(fg='#111827', text=f"Panel: {modo}{mov} · punto {e.herramienta} · velocidad "
                                  f"{e.velocidad_pct:.0f} % · medido {', '.join(f'{v:.2f}' for v in e.medido)} · "
                                  f"objetivo {', '.join(f'{v:.2f}' for v in e.objetivo)}")
            key = calculos.redondear(e)
            if key != self.mostrado and not self.ocupado:
                self.ocupado = True
                threading.Thread(target=self.calcular, args=(key, e), daemon=True).start()
        try:
            while True:
                key, result, failure = self.resultados.get_nowait()
                self.ocupado = False
                if failure:
                    self.estado.configure(text=f'Error en el cálculo: {failure}', fg='#b91c1c')
                    self.mostrado = key
                    continue
                for vista in self.vistas:
                    vista.actualizar(result)
                self.mostrado = key
        except queue.Empty:
            pass
        self.after(300, self.ciclo)

    def calcular(self, key, exacta):
        try:
            self.resultados.put((key, calculos.analizar(exacta), None))
        except Exception as exc:  # una pose rara no debe cerrar la ventana
            self.resultados.put((key, None, str(exc)))
