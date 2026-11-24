"""Sesión RWS con el controlador para el panel (o robot simulado)."""
from datetime import datetime, timezone
import getpass

from irb120_control.rws_mover import Mover, logout
from irb120_control.panel.simulado import SimulatedMover


def abrir(base, user, log_dir, simulated=False, modulo='v5'):
    """Devuelve (mover, session). Pide la contraseña en la terminal; no se guarda."""
    if simulated:
        print('MODO SIMULADO: no se conecta a ningún robot.', flush=True)
        return SimulatedMover(), None
    import requests
    from requests.auth import HTTPDigestAuth
    password = getpass.getpass(f'Contraseña RWS de "{user}" (no se guarda): ')
    session = requests.Session()
    session.trust_env = False
    session.auth = HTTPDigestAuth(user, password)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%fZ')
    mover = Mover(session, base, session_factory=requests.Session, log=log_dir / f'panel_{stamp}.jsonl',
                  modulo=modulo)
    try:
        identity = mover.connect()
    except BaseException:
        session.close()
        raise
    print(f"Controlador {identity['name']} | RobotWare {identity['rwversionname']} | "
          f"módulo {mover.module_version}", flush=True)
    return mover, session


def cerrar(mover, session):
    """Suelta RMMP y cierra la sesión RWS (RW6 admite pocas sesiones simultáneas)."""
    if session is None:
        return
    try:
        mover.rmmp.close()
    finally:
        logout(mover)
        session.close()
