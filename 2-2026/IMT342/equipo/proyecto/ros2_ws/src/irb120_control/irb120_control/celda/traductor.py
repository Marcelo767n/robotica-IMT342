"""Traductor PLC ↔ brazo (docs/PLC_S7_1200.md §5). PURO: sin ROS ni red; el reloj se inyecta.

Entradas:  entrada_plc(d)  JSON de /irb120/plc/entrada · estado_brazo(d)  JSON de /irb120/panel/estado · tic().
Salidas:   tomar_ordenes()  órdenes {"id","accion",...} para /irb120/panel/orden · salida()  JSON de /irb120/plc/salida.

Cada orden del PLC es un bit de nivel (`ordenes`): se ejecuta una vez en su flanco de subida y el saludo
`aceptada`/`rechazada` (código positivo en `valor`) se mantiene mientras el bit siga a 1. Las órdenes se atienden
de una en una (FIFO), salvo pausar y cancelar, que salen al panel al instante. Ejecutar trayectoria planifica (~1,5 s): no se hace aquí sino en un hilo
del nodo con tomar_trabajo() → trabajo.calcular() → completar(trabajo, resultado) (planificar_pendiente() lo
hace todo seguido, para pruebas). El panel vuelve a verificar el plan: aquí solo se filtra pronto.
"""
import collections
import math
import time

from irb120_control.trayectorias import Trayectoria, a_ordenes, planificar

GUARDIAN_PLC_S = 1.0       # sin entrada del PLC durante este tiempo → enlace perdido
EDAD_BRAZO_S = 2.0         # estado del panel más viejo → sin enlace con el brazo
ESPERA_VEL_S = 5.0
ESPERA_RESP_S = 10.0       # 'trayectoria' re-planifica en el panel (~1,5 s)
MAX_REGISTRO = 200
ID_BASE = 900000           # ids propios, lejos de los del panel de RViz

FASES = {'lista': 0, 'ejecutando': 1, 'pausada': 2, 'terminada': 3, 'cancelada': 4, 'error': 5}
ORDENES = ('ejecutar', 'pausar', 'reanudar', 'cancelar', 'reposo', 'acusar', 'velocidad', 'punto')
MOVIMIENTO = ('ejecutar', 'reposo', 'velocidad')   # sin `habilitar` → 2
URGENTES = ('pausar', 'cancelar')                  # al panel al instante, fuera de la cola
REPOSO = [0., 0., 0., 0., 30., 0.]


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _entero(d, clave, defecto=0):
    v = d.get(clave, defecto)
    return int(v) if _num(v) and math.isfinite(v) else defecto


def _vector(v, n):
    if isinstance(v, (list, tuple)) and len(v) == n and all(_num(x) and math.isfinite(x) for x in v):
        return [float(x) for x in v]
    return None


class Trabajo:
    """Planificación pendiente: calcular() no toca el Traductor (se llama fuera de cualquier cerrojo)."""

    def __init__(self, ruta, q, velocidad, repeticiones, cargar, plan, ordenes):
        self.ruta, self.q, self.velocidad, self.repeticiones = ruta, q, velocidad, repeticiones
        self._cargar, self._plan, self._ordenes = cargar, plan, ordenes

    def calcular(self):
        """('ok', tray, ordenes) · ('archivo', motivo) → -5 · ('plan', motivo) → -6. Nunca lanza."""
        try:
            tray = self._cargar(self.ruta)
        except (OSError, ValueError) as exc:
            return ('archivo', f'{self.ruta}: {exc}')
        except Exception as exc:
            return ('archivo', f'{self.ruta}: fallo inesperado: {exc}')
        try:
            if self.repeticiones:
                tray.repeticiones = self.repeticiones
            plan = self._plan(tray, self.q, self.velocidad)
            if not plan.ok:
                return ('plan', plan.resumen)
            return ('ok', tray, self._ordenes(plan))
        except Exception as exc:
            return ('plan', f'no se pudo planificar: {exc}')


class Traductor:
    def __init__(self, rutas=None, reloj=time.monotonic, cargar=Trayectoria.cargar, plan=planificar,
                 ordenes=a_ordenes, reposo=REPOSO):
        self.rutas, self.reloj, self.reposo = (rutas if rutas is not None else {}), reloj, [float(v) for v in reposo]
        self._cargar, self._plan, self._ordenes = cargar, plan, ordenes
        self._id = ID_BASE
        self._salida = []                                # órdenes por publicar al panel
        self.registro_ = collections.deque(maxlen=MAX_REGISTRO)
        self.n_registro = 0                              # líneas escritas en total (el registro es acotado)
        # PLC
        self.t_plc = None
        self.enlace = False
        self.habilitar = False
        self.formato = 'completo'
        self.niveles = {n: False for n in ORDENES}       # niveles de los bits en el último mensaje
        self.base_pendiente = True                       # los bits a 1 en el primer mensaje no cuentan
        self.perdido = False                             # enlace PLC perdido (episodio en curso)
        self.pausa_enviada = False                       # 'pausar' ya enviada en este episodio
        # brazo
        self.brazo = None
        self.t_brazo = None
        # órdenes en curso y saludo
        self.cola = collections.deque(maxlen=8)
        self.actual = None
        self.urgentes = []
        self.saludo = None                               # {'codigo': 0 aceptada | >0 rechazada, 'bits': [...]}
        self.error = 0                                   # error con memoria (9) hasta «acusar»
        self.ultimo_codigo = 0

    # ---------- entradas ----------
    def entrada_plc(self, d, ahora=None):
        ahora = self.reloj() if ahora is None else ahora
        if not isinstance(d, dict):
            return
        self.t_plc = ahora
        self.enlace = d.get('enlace') is True
        if not self.enlace:
            self._perder(ahora)
            return
        self.perdido = False
        self.habilitar = d.get('habilitar') is True
        self.formato = d.get('formato') if d.get('formato') in ('nucleo', 'completo') else 'completo'
        bits = d.get('ordenes') if isinstance(d.get('ordenes'), dict) else {}
        niveles = {n: bits.get(n) is True for n in ORDENES}
        previos, self.niveles = self.niveles, niveles
        if self.saludo and not any(niveles[b] for b in self.saludo['bits']):
            self.saludo = None                           # el PLC bajó el bit: se baja el saludo
        if self.base_pendiente:
            self.base_pendiente = False
            self._log('Línea base de órdenes: los bits ya a 1 no cuentan como flanco.')
        else:
            subidas = [n for n in ORDENES if niveles[n] and not previos[n]]
            activos = [n for n in ORDENES if niveles[n]]
            if subidas and len(activos) > 1:
                self._rechazo_directo(1, activos, f"dos bits de orden a la vez ({', '.join(activos)}).")
            elif subidas:
                self._nueva(subidas[0], d, ahora)
        self._avanzar(ahora)

    def estado_brazo(self, d, ahora=None):
        ahora = self.reloj() if ahora is None else ahora
        if isinstance(d, dict):
            self.brazo, self.t_brazo = d, ahora
        self._avanzar(ahora)

    def tic(self, ahora=None):
        self._avanzar(self.reloj() if ahora is None else ahora)

    def tomar_ordenes(self):
        ordenes, self._salida = self._salida, []
        return ordenes

    # ---------- planificación fuera del hilo principal ----------
    def tomar_trabajo(self):
        a = self.actual
        if a and a['fase'] == 'planificar' and a.get('trabajo') is None:
            a['trabajo'] = Trabajo(a['ruta'], a['q'], a['velocidad'], a['reps'], self._cargar, self._plan,
                                   self._ordenes)
            return a['trabajo']
        return None

    def completar(self, trabajo, res, ahora=None):
        ahora = self.reloj() if ahora is None else ahora
        a = self.actual
        if not a or a.get('trabajo') is not trabajo:
            return                                       # la orden se abortó mientras se planificaba
        if res[0] == 'archivo':
            self._cerrar(a, 5, f'trayectoria no válida: {res[1]}')
        elif res[0] == 'plan':
            self._cerrar(a, 6, f'plan NO apto: {res[1]}')
        else:
            _, tray, ordenes = res
            self._publicar(a, 'trayectoria', trayectoria=tray.to_dict(), ordenes=ordenes,
                           velocidad_pct=a['velocidad'])
            a['fase'], a['t'] = 'resp', ahora
            self._log(f'Plan apto ({len(ordenes)} tramos): orden «trayectoria» enviada al brazo.')
        self._avanzar(ahora)

    def planificar_pendiente(self):
        t = self.tomar_trabajo()
        if t is not None:
            self.completar(t, t.calcular())

    # ---------- máquina de órdenes ----------
    def _nueva(self, nombre, d, ahora):
        o = {'orden': nombre, 'valor': _entero(d, 'valor'), 'vel': _entero(d, 'velocidad_pct'),
             'reps': _entero(d, 'repeticiones'), 'pose': d.get('pose'), 'fase': None, 't': ahora}
        if nombre in URGENTES:
            self._iniciar_urgente(o, ahora)
        else:
            self.cola.append(o)

    def _avanzar(self, ahora):
        self._vigilar(ahora)
        for o in list(self.urgentes):
            self._seguir(o, ahora)
        for _ in range(len(self.cola) + 2):
            if self.actual is None:
                if not self.cola:
                    return
                self.actual = self.cola.popleft()
                self._iniciar(self.actual, ahora)
            elif not self._seguir(self.actual, ahora):
                return

    def _vivo(self, ahora):
        return self.brazo is not None and self.t_brazo is not None and ahora - self.t_brazo <= EDAD_BRAZO_S

    def _tray(self):
        t = (self.brazo or {}).get('trayectoria')
        return t if isinstance(t, dict) else {}

    def _publicar(self, a, accion, **campos):
        self._id += 1
        a['id'] = self._id
        self._salida.append({'id': self._id, 'accion': accion, **campos})

    def _cerrar(self, a, codigo, motivo):
        """Termina una orden: codigo 0 = aceptada, >0 = rechazada. Deja el saludo mientras el bit siga a 1."""
        if a is self.actual:
            self.actual = None
        if a in self.urgentes:
            self.urgentes.remove(a)
        if codigo:
            self.ultimo_codigo = codigo
        self.saludo = {'codigo': codigo, 'bits': [a['orden']]} if self.niveles.get(a['orden']) else None
        self._log(f"Orden «{a['orden']}»: {'aceptada' if not codigo else f'rechazada, código {codigo}'}. "
                  f"{motivo}".rstrip())

    def _rechazo_directo(self, codigo, bits, motivo):
        self.ultimo_codigo = codigo
        self.saludo = {'codigo': codigo, 'bits': list(bits)}
        self._log(f'Orden rechazada, código {codigo}. {motivo}')

    def _rechazar_orden(self, o, codigo, motivo):
        self._cerrar(o, codigo, motivo)

    def _iniciar_urgente(self, o, ahora):
        self.urgentes.append(o)
        self._publicar(o, o['orden'])
        o['fase'] = 'resp'
        if not self._vivo(ahora):                        # por seguridad se envía igualmente
            self._cerrar(o, 3, 'estado del brazo viejo; la orden se envió igualmente sin confirmación.')

    def _iniciar(self, o, ahora):
        nombre, brazo = o['orden'], self.brazo or {}
        if nombre in MOVIMIENTO and not self.habilitar:
            return self._cerrar(o, 2, 'habilitar = 0.')
        if nombre == 'acusar':
            self.error = self.ultimo_codigo = 0
            return self._cerrar(o, 0, 'error borrado.')
        pose = None
        if nombre == 'velocidad':
            o['vel'] = o['vel'] if o['vel'] > 0 else o['valor']
            if not 1 <= o['vel'] <= 100:
                return self._cerrar(o, 1, f"velocidad {o['vel']} fuera de 1…100.")
        elif nombre == 'ejecutar':
            if not 1 <= o['valor'] <= 99 or o['vel'] > 100 or not 0 <= o['reps'] <= 1000:
                return self._cerrar(o, 1, 'trayectoria, velocidad o repeticiones fuera de rango.')
        elif nombre == 'punto':
            pose = _vector(o['pose'], 6)
            if self.formato == 'nucleo' or pose is None:
                return self._cerrar(o, 1, 'punto solo en formato completo y con pose de 6 números.')
        if not self._vivo(ahora):
            return self._cerrar(o, 3, 'sin estado reciente del brazo.')
        if nombre in ('ejecutar', 'reposo') and brazo.get('ocupado'):
            return self._cerrar(o, 8, 'el brazo está ocupado.')
        if nombre in MOVIMIENTO and (brazo.get('faltas') or []):
            return self._cerrar(o, 4, 'robot no listo: ' + '; '.join(map(str, brazo['faltas'])))
        if nombre == 'ejecutar':
            ruta = self.rutas.get(o['valor'])
            if ruta is None:
                return self._cerrar(o, 5, f"trayectoria {o['valor']} sin archivo en la configuración.")
            if not _vector(brazo.get('medido'), 6) or not _num(brazo.get('velocidad_pct')):
                return self._cerrar(o, 4, 'sin postura medida o velocidad del panel.')
            o['ruta'] = ruta
            if 1 <= o['vel'] <= 100 and o['vel'] != brazo['velocidad_pct']:
                self._publicar(o, 'velocidad', valor=o['vel'])
                o['fase'] = 'vel'
                self._log(f"Trayectoria {o['valor']}: primero velocidad {o['vel']} %.")
            else:
                self._planear(o, brazo)
            return None
        if nombre == 'reanudar':
            self._publicar(o, 'reanudar')
        elif nombre == 'reposo':
            self._publicar(o, 'posicion', valor='reposo')
            o['fase'] = 'pos'
            return None
        elif nombre == 'velocidad':
            self._publicar(o, 'velocidad', valor=o['vel'])
        elif nombre == 'punto':
            self._publicar(o, 'punto_externo', pose=pose, nombre=f'plc{int(ahora)}')
        o['fase'] = 'resp'
        return None

    def _planear(self, o, brazo):
        o['q'], o['velocidad'], o['fase'], o['trabajo'] = [float(v) for v in brazo['medido']], \
            float(brazo['velocidad_pct']), 'planificar', None

    def _seguir(self, a, ahora):
        """Avanza una orden en curso; True si terminó."""
        brazo = self.brazo or {}
        if a['fase'] == 'planificar':
            return False
        if not self._vivo(ahora) and ahora - a['t'] > EDAD_BRAZO_S:
            self._cerrar(a, 3, 'se perdió el estado del brazo esperando respuesta.')
            return True
        resp = brazo.get('respuesta')
        resp = resp if isinstance(resp, dict) and resp.get('id') == a.get('id') else None
        if a['fase'] == 'vel':
            if resp and not resp.get('ok'):
                self._cerrar(a, 7, f"el brazo rechazó la velocidad: {resp.get('error')}")
                return True
            if resp and brazo.get('velocidad_pct') == a['vel']:
                self._planear(a, brazo)
                return False
            if ahora - a['t'] > ESPERA_VEL_S:
                self._cerrar(a, 7, 'el brazo no confirmó la velocidad.')
                return True
            return False
        if resp:
            if not resp.get('ok'):
                error = str(resp.get('error'))
                ocupado = any(p in error.lower() for p in ('ocupad', 'en curso'))
                self._cerrar(a, 8 if ocupado else 7, f'el brazo rechazó: {error}')
                return True
            if a['fase'] == 'pos':                       # reposo: objetivo fijado → ahora se envía (el panel verifica)
                self._publicar(a, 'enviar', q=list(self.reposo))
                a['fase'], a['t'] = 'resp', ahora
                return False
            self._cerrar(a, 0, '')
            return True
        if ahora - a['t'] > ESPERA_RESP_S:
            self._cerrar(a, 7, 'el brazo no respondió.')
            return True
        return False

    # ---------- seguridad ----------
    def _perder(self, ahora):
        if not self.perdido:
            self.perdido, self.pausa_enviada = True, False
            self.base_pendiente = True                   # al volver, los bits a 1 no son flancos
            self.saludo = None
            self.cola.clear()
            self._log('Enlace con el PLC perdido.')
            a = self.actual
            if a and a['fase'] in ('vel', 'planificar', 'pos'):
                self._cerrar(a, 9, 'enlace con el PLC perdido antes de enviar al brazo.')
        if self._vivo(ahora) and self._tray().get('fase') == 'ejecutando' and not self.pausa_enviada:
            self.pausa_enviada = True
            self.error = self.ultimo_codigo = 9
            self._publicar({}, 'pausar')
            self._log('Enlace con el PLC perdido con trayectoria en ejecución: pausar y error 9.')

    def _vigilar(self, ahora):
        if self.t_plc is not None and ahora - self.t_plc > GUARDIAN_PLC_S:
            self.enlace = False
            self._perder(ahora)

    # ---------- salida al PLC ----------
    def salida(self, ahora=None):
        ahora = self.reloj() if ahora is None else ahora
        vivo, b, t = self._vivo(ahora), self.brazo or {}, self._tray()
        fase = t.get('fase') if vivo else None
        en_curso = FASES.get(t.get('fase'), 0) in (1, 2)
        n = lambda k: _entero(t, k) if vivo else 0
        error = self.error or (7 if fase == 'error' else 0) or (3 if not vivo and en_curso else 0)
        motores = str(b.get('motores') or '').lower()
        rechazada = bool(self.saludo and self.saludo['codigo'])
        estado = {'enlace': vivo, 'listo': vivo and b.get('listo') is True,
                  'moviendo': vivo and b.get('ocupado') is True, 'terminado': fase == 'terminada',
                  'error': error != 0, 'pausada': fase == 'pausada',
                  'motores_on': vivo and motores == 'motoron',
                  'servidor_activo': vivo and b.get('servidor_activo') is True,
                  'auto': vivo and str(b.get('modo') or '').upper() == 'AUTO',
                  'simulado': vivo and b.get('simulado') is True,
                  'aceptada': bool(self.saludo) and not rechazada, 'rechazada': rechazada,
                  'habilitar_recibido': self.habilitar and self.enlace}
        valor = self.saludo['codigo'] if rechazada else error or (n('tramo') if en_curso else 0)
        vel = b.get('velocidad_pct')
        return {'estado': estado, 'valor': valor,
                'fase': 5 if (not vivo and en_curso) else FASES.get(fase, 0),
                'tramo': n('tramo'), 'tramos': n('total'), 'vuelta': n('vuelta'),
                'velocidad_pct': int(vel) if _num(vel) else 0, 'codigo': error or self.ultimo_codigo,
                'q': _vector(b.get('medido'), 6) or [0.] * 6,
                'pose': _vector(b.get('pose_medida'), 6) or [0.] * 6}

    # ---------- registro ----------
    def _log(self, texto):
        self.registro_.append(f'[{self.reloj():.1f}] {texto}')
        self.n_registro += 1

    def registro(self):
        return list(self.registro_)
