"""python3 -m irb120_control.estudio [--puerto 8770] [--demo] [--tema oscuro|claro] [--escala 1.0]"""
import argparse
from pathlib import Path
import subprocess
import time

from irb120_control.estudio.cliente import PUERTO, Cliente


def _biblioteca_demo(app):
    """Biblioteca de ejemplo en una carpeta temporal y una trayectoria de 5 puntos con tipos mezclados abierta."""
    from irb120_control.trayectorias import Punto
    c = app.ctx
    puntos = [('A', [20, 10, -10, 0, 40, 0], 'auto'), ('B', [-20, 15, -5, 0, 45, 10], 'articular'),
              ('C', [0, -10, 10, 0, 60, 0], 'lineal'), ('D', [15, 20, -15, 0, 50, -10], 'auto'),
              ('E', [-10, 5, 0, 0, 35, 0], 'articular')]
    for nombre, numero, n in (('Inspección', 1, 2), ('Paletizado', 3, 5), ('Prueba suelta', None, 3)):
        c.nueva()
        c.editor.puntos = [Punto(a, q=q, origen='angulos', tipo=t) for a, q, t in puntos[:n]]
        c.nombre, c.numero, c.cerrar = nombre, numero, nombre == 'Inspección'
        c.guardar()
    c.abrir(next(e.ruta for e in __import__('irb120_control.estudio.biblioteca', fromlist=['x']).listar(c.carpeta)
                 if e.numero == 3))
    app.vistas[1].poner_parametros()
    app.vistas[1].refrescar_biblioteca()


def capturar(app, carpeta, espera_latex=True):
    """Modo oculto: recorre las pestañas y guarda una captura de cada una."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    _biblioteca_demo(app)
    app.ctx.planificar()
    app.esperar_plan()
    for i, v in enumerate(app.vistas):
        if v.titulo == 'Validación':
            v.recargar()
        app.tabs.set(v.titulo)
        app.refrescar()
        fin = time.monotonic() + (14 if v.titulo == 'Matemática' and espera_latex else 1.2)
        while time.monotonic() < fin:
            app.ctx.drenar()
            app.update()
            time.sleep(.03)
        app.update_idletasks()
        ruta = carpeta / f'{i + 1}_{v.titulo.lower().replace("á", "a").replace("í", "i").replace("ó", "o")}.png'
        subprocess.run(['import', '-window', hex(app.winfo_id()), str(ruta)], check=False)
        print(ruta)
    app.destruir()


def main(argv=None):
    p = argparse.ArgumentParser(description='Estudio de trayectorias del IRB 120 (CustomTkinter).')
    p.add_argument('--puerto', type=int, default=PUERTO, help='Puerto del panel local (8770)')
    p.add_argument('--demo', action='store_true', help='Sin panel: postura de ejemplo; se puede planificar, no enviar')
    p.add_argument('--tema', choices=('oscuro', 'claro'), default='oscuro')
    p.add_argument('--escala', type=float, default=1.0, help='Factor de tamaño para el proyector (p. ej. 1.3)')
    p.add_argument('--captura', metavar='DIR', help=argparse.SUPPRESS)
    p.add_argument('--cerrar', type=float, default=0, help=argparse.SUPPRESS)
    a = p.parse_args(argv)
    if not 0.5 <= a.escala <= 3:
        p.error('--escala debe estar entre 0.5 y 3')
    from irb120_control.estudio.app import App
    cliente = Cliente(a.puerto, demo=a.demo)
    cliente.iniciar()
    carpeta = None
    if a.captura:
        import tempfile
        carpeta = tempfile.mkdtemp(prefix='estudio_bib_')
    app = App(cliente, oscuro=a.tema == 'oscuro', escala=a.escala, carpeta=carpeta)
    app.protocol('WM_DELETE_WINDOW', app.destruir)
    if a.demo and not a.captura:
        app.cargar_demo()
    if a.cerrar:
        app.after(int(a.cerrar * 1000), app.destruir)
    if a.captura:
        app.after(600, lambda: capturar(app, a.captura))
    try:
        app.mainloop()
    finally:
        cliente.detener()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
