"""python3 -m irb120_control.analisis [--url URL] [--demo]"""
import argparse

from irb120_control.analisis import fuente
from irb120_control.analisis.app import App, VISTAS


def main(argv=None):
    parser = argparse.ArgumentParser(description='Análisis Hito 2 en vivo del IRB 120 (solo lectura).')
    parser.add_argument('--url', default=fuente.DEFAULT_URL, help='Estado del panel (GET, solo local)')
    parser.add_argument('--demo', action='store_true', help='Sin panel: postura y objetivo de ejemplo')
    parser.add_argument('--pestana', type=int, default=0, choices=range(len(VISTAS)), help=argparse.SUPPRESS)
    parser.add_argument('--cerrar', type=float, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if not args.url.startswith(('http://127.0.0.1:', 'http://localhost:')):
        parser.error('--url debe ser local (127.0.0.1 o localhost)')
    source = fuente.Fuente(args.url, demo=args.demo)
    source.iniciar()
    app = App(source, pestana=args.pestana)
    if args.cerrar:
        app.after(int(args.cerrar * 1000), app.destroy)
    try:
        app.mainloop()
    finally:
        source.detener()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
