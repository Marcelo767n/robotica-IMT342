"""Puesta en marcha guiada en AUTO para «./brazo.sh sesion» (una sola contraseña).

Lee el estado del robot y pide al operador solo lo que falta, en orden:
  llave en AUTO → módulo v4 (si hace falta: motores OFF, vaciar objetivo e instalar) →
  Motors On → PP a ServidorPC y arranque por RWS → «Iniciar» en el FlexPendant.
Mientras espera solo lee (GET). No pulsa nada por el operador: Motors On e «Iniciar» siguen
siendo suyos. Ctrl+C sale sin cambiar nada más.
"""
import time

from irb120_control.rws_j6 import EMPTY, Refused

POLL_S = .5
ATTEMPTS = 3


def esperar(mover, condition, message, echo, timeout=600., sleep=time.sleep):
    """Muestra el mensaje una vez y espera hasta que condition(estado) sea verdadera."""
    state = mover.status()
    if condition(state):
        return state
    echo('>>> ' + message)
    started = time.monotonic()
    while time.monotonic() - started < timeout:
        sleep(POLL_S)
        state = mover.status()
        if condition(state):
            return state
    raise Refused('Tiempo de espera agotado: ' + message)


def preparar_auto(mover, log_dir, echo=print, sleep=time.sleep, timeout=600.):
    """Deja ServidorPC (v4, variante AUTO) en ejecución y aceptando órdenes."""
    with mover.lock:
        state = mover.status()
        if state['module'] == 'servidor_v4_auto' and state['execution'] == 'running' and state.get('rbActivo') == 1:
            echo('ServidorPC ya está activo en el robot.')
            return state
        state = esperar(mover, lambda s: s['opmode'] == 'AUTO',
                        'Girar la llave a AUTO y confirmar el diálogo del FlexPendant.', echo, timeout, sleep)
        if state['module'] != 'servidor_v4_auto':
            echo(f"El robot tiene el módulo {state['module']}: se instalará la v4 (variante AUTO).")
            esperar(mover, lambda s: s['execution'] == 'stopped' and s['ctrlstate'] != 'motoron',
                    'Pulsar Stop en el FlexPendant y el botón Motors Off del controlador.', echo, timeout, sleep)
            # AUTO_CH = cambio de modo sin confirmar en el FlexPendant: esperar a AUTO firme.
            esperar(mover, lambda s: s['ctrlstate'] == 'motoroff' and s['opmode'] == 'AUTO',
                    'Esperando motores OFF y modo AUTO confirmado (aceptar el diálogo del FlexPendant)…',
                    echo, timeout, sleep)
            if mover.get_target() != EMPTY:
                echo('Vaciando un objetivo pendiente de la sesión anterior (no mueve el robot).')
                mover.set_target(EMPTY)
            report = mover.install(log_dir, auto=True)
            if not report.get('passed'):
                raise Refused('La instalación del módulo v4 no pasó la verificación; ver ' + str(log_dir))
            echo('Módulo v4 instalado y verificado.')
            mover.connect()
        for attempt in range(1, ATTEMPTS + 1):
            esperar(mover, lambda s: s['ctrlstate'] == 'motoron',
                    'Pulsar el botón blanco Motors On del controlador (sin pulsar Start).', echo, timeout, sleep)
            state = mover.status()
            if state['execution'] == 'running':
                _, where = mover.pointer()
                if 'ServidorPC' not in where:
                    # Otro programa (p. ej. main de otro grupo) en marcha: no lo tocamos desde la PC.
                    esperar(mover, lambda s: s['execution'] == 'stopped',
                            'Hay otro programa en ejecución en el robot: pulsar Stop en el FlexPendant.',
                            echo, timeout, sleep)
            if mover.status()['execution'] != 'running':
                mover.start_server(echo=lambda line: echo(line))
            state = esperar(mover, lambda s: (s.get('rbActivo') == 1 and s['execution'] == 'running')
                            or s['execution'] == 'stopped',
                            'En el FlexPendant: icono «Ventana del operador» (barra superior, junto al Menú ABB) → '
                            '«¿Aceptar objetivos enviados por la PC?» → pulsar «Iniciar». Hay 2 minutos.',
                            echo, 150., sleep)
            if state.get('rbActivo') == 1 and state['execution'] == 'running':
                echo('ServidorPC activo: el robot acepta órdenes desde RViz.')
                return mover.status()
            echo(f'No se confirmó «Iniciar» a tiempo o se pulsó Cancelar/Stop (intento {attempt}/{ATTEMPTS}): '
                 'se vuelve a arrancar ServidorPC.')
        raise Refused(f'No se confirmó «Iniciar» en {ATTEMPTS} intentos. Ejecutar de nuevo ./brazo.sh sesion.')
