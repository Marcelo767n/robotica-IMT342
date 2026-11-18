"""Panel del IRB 120 en RViz: ángulos, pose con cinemática inversa y envío al robot real por RWS.

  ./iniciar.sh panel              robot real (pide la contraseña RWS en la terminal)
  ./iniciar.sh panel --simulado   sin robot
  ./iniciar.sh panel --web        además, la página local http://127.0.0.1:8770/

No arranca RAPID ni motores: el operador arranca ServidorPC en el FlexPendant.
Cerrar el panel NO detiene el robot: habilitador, Stop o paro de emergencia.
"""
import argparse
import fcntl
from pathlib import Path
import signal
import tempfile
import threading
import time
import webbrowser

from irb120_conexion.rutas import PROJECT
from irb120_conexion.nodos.lectura_articular.puente_rws import build_base_url
from irb120_control.rws_j6 import Refused
from irb120_control.rws_mover import MAX_STEP_DEG
from irb120_control.panel import conexion, vista
from irb120_control.panel.estado import Panel

LOCK = PROJECT / 'salidas/control_articular/instancia.lock'


def argumentos(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--host', default='192.168.125.1')
    parser.add_argument('--user', default='Default User')
    parser.add_argument('--http-port', type=int, default=80, help='Puerto RWS; distinto de 80 solo en 127.0.0.1')
    parser.add_argument('--paso', type=float, default=40., help='Máximo cambio por eje en cada orden (≤40°)')
    parser.add_argument('--timeout', type=float, default=120., help='Segundos de espera por orden')
    parser.add_argument('--simulado', action='store_true', help='Sin robot: practicar con un robot ficticio')
    parser.add_argument('--web', action='store_true', help='Abrir también la página local')
    parser.add_argument('--panel-port', type=int, default=8770, help='Puerto de la página local (--web)')
    parser.add_argument('--no-rviz', action='store_true')
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--duration', type=float, default=0, help=argparse.SUPPRESS)
    parser.add_argument('--log-dir', type=Path, default=PROJECT / 'salidas/control_articular/rws_mover')
    args = parser.parse_args(argv)
    if not 0 < args.paso <= MAX_STEP_DEG:
        parser.error(f'--paso debe estar entre 0 y {MAX_STEP_DEG:g}')
    if not 1024 <= args.panel_port <= 65535:
        parser.error('--panel-port debe estar entre 1024 y 65535')
    try:
        args.base = build_base_url(args.host, args.http_port)
    except ValueError as exc:
        parser.error(str(exc))
    return parser, args


def bloquear(parser):
    """Mismos tópicos que control_*: nunca dos sesiones a la vez."""
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    handle = LOCK.open('a')
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        parser.error('Ya hay una sesión de control o de panel abierta. Cerrarla antes de iniciar otra.')
    return handle


def leer_en_segundo_plano(panel, stop):
    def reader():
        count = 0
        while not stop.wait(.3):
            panel.poll(full=count % 5 == 0)   # postura cada 0,3 s; estado completo cada 1,5 s
            count += 1
    threading.Thread(target=reader, daemon=True, name='panel-lectura').start()


def instrucciones(con_panel, url):
    lines = ['', 'RViz: robot sólido = postura medida; naranja = objetivo.']
    if con_panel:
        lines.append('Panel «IRB 120» (a la izquierda): ángulos, pose + cinemática inversa, Enviar al robot.')
    else:
        lines.append('AVISO: panel C++ sin compilar (./brazo.sh compilar). Quedan los controles 3D y --web.')
    lines += ['Control 3D: herramienta «Interact», arrastrar la pose; clic derecho = ajustar ejes o enviar.']
    if url:
        lines.append(f'Página local: {url}')
    lines += ['Cerrar el panel NO detiene el robot: habilitador, Stop o paro de emergencia.',
              'Ctrl+C aquí cierra panel y RViz.', '']
    print('\n'.join(lines), flush=True)


def main(argv=None):
    parser, args = argumentos(argv)
    from irb120_control.rviz_control import model_joints
    model_joints()  # no se inicia si modelo/URDF discrepan
    args.log_dir.mkdir(parents=True, exist_ok=True)
    lock = bloquear(parser)
    import rclpy
    from irb120_control.panel.puente_ros import PuenteRos, crear_nodo
    from irb120_control.panel.rviz_controles import RvizControls
    mover = session = keeper = server = node = None
    children, stop = [], threading.Event()
    try:
        mover, session = conexion.abrir(args.base, args.user, args.log_dir, args.simulado)
        panel = Panel(mover, step=args.paso, timeout=args.timeout, simulated=args.simulado)
        panel.poll()
        if panel.state is not None:
            try:  # pedir RMMP ahora, con el robot quieto, y no en medio del primer envío
                mover.ensure_rmmp(panel.state)
            except Refused as exc:
                print('AVISO:', exc, '— se volverá a pedir en el primer envío.', flush=True)
        keeper = mover.start_keeper()
        leer_en_segundo_plano(panel, stop)
        url = None
        if args.web:
            from irb120_control.panel.web import serve
            server, _ = serve(panel, args.panel_port)
            url = f'http://127.0.0.1:{server.server_address[1]}/'
            if not args.no_browser:
                threading.Thread(target=lambda: webbrowser.open(url), daemon=True).start()
        rclpy.init(args=[])
        node = crear_nodo()
        bridge = PuenteRos(node, panel)         # noqa: F841 (los temporizadores guardan la referencia)
        controls = RvizControls(node, panel)    # noqa: F841
        con_panel = vista.panel_disponible()
        with tempfile.TemporaryDirectory(prefix='irb120_panel_') as directory:
            children = vista.lanzar(vista.preparar(directory, con_panel), rviz=not args.no_rviz)
            instrucciones(con_panel, url)

            def interrupt(*_):
                raise KeyboardInterrupt
            signal.signal(signal.SIGTERM, interrupt)
            started = time.monotonic()
            while rclpy.ok():
                rclpy.spin_once(node, timeout_sec=.05)
                if any(child.poll() is not None for child in children):
                    break
                if args.duration and time.monotonic() - started >= args.duration:
                    break
    except KeyboardInterrupt:
        pass
    except Refused as exc:
        print('DETENIDO:', exc, flush=True)
        return 2
    except OSError as exc:  # incluye errores de red de requests y puerto ocupado
        print('No se pudo iniciar el panel:', exc, flush=True)
        return 2
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        stop.set()
        if keeper is not None:
            keeper.set()
        if server is not None:
            server.shutdown()
        if mover is not None:
            conexion.cerrar(mover, session)
        vista.detener(children)
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        lock.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
