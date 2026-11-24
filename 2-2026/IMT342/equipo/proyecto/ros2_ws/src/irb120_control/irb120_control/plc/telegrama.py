"""Telegramas PLC → PC (orden) y PC → PLC (estado), núcleo de 2 palabras + parte extendida. Puro: sin ROS ni red.

Big-endian, desplazamientos de docs/PLC_S7_1200.md §3. Formato `nucleo` = 4 B en cada sentido;
`completo` = 36 B (orden) y 68 B (estado). JSON de los tópicos: §4."""
import math
import struct
from dataclasses import dataclass, field
from typing import List, Optional

NUCLEO, COMPLETO = 'nucleo', 'completo'
FORMATOS = (NUCLEO, COMPLETO)
LARGO_NUCLEO = 4
LARGO_ORDEN_COMPLETA = 36
LARGO_ESTADO_COMPLETO = 68

# Bits de `mando` (§3.1); el bit 15 es `vida`
MANDO_HABILITAR = 1 << 0
BITS_ORDEN = ('ejecutar', 'pausar', 'reanudar', 'cancelar', 'reposo', 'acusar', 'velocidad', 'punto')  # bits 1…8
MASCARA_ORDENES = sum(1 << (i + 1) for i in range(len(BITS_ORDEN)))
BIT_VIDA = 1 << 15

# Bits de `estado` (§3.2), bit i = nombre i; el bit 15 es `vida`
BITS_ESTADO = ('enlace', 'listo', 'moviendo', 'terminado', 'error', 'pausada', 'motores_on', 'servidor_activo',
               'auto', 'simulado', 'aceptada', 'rechazada', 'habilitar_recibido')

# Fases (§3.2)
FASE_LISTA, FASE_EJECUTANDO, FASE_PAUSADA, FASE_TERMINADA, FASE_CANCELADA, FASE_ERROR = range(6)

# Códigos de rechazo / error (§3.3, positivos)
RECHAZO_NO_VALIDA, RECHAZO_SIN_HABILITAR, RECHAZO_SIN_BRAZO, RECHAZO_NO_LISTO, RECHAZO_TRAYECTORIA = 1, 2, 3, 4, 5
RECHAZO_PLAN, RECHAZO_BRAZO, RECHAZO_OCUPADO, RECHAZO_ENLACE = 6, 7, 8, 9
ERROR_SIN_BRAZO = 3

_NUCLEO = struct.Struct('>HH')
_ORDEN = struct.Struct('>HHHHHH6f')
_ESTADO = struct.Struct('>HHHHHHHHHH6f6f')
assert (_ORDEN.size, _ESTADO.size) == (LARGO_ORDEN_COMPLETA, LARGO_ESTADO_COMPLETO)


def largo_orden(formato):
    return LARGO_ORDEN_COMPLETA if formato == COMPLETO else LARGO_NUCLEO


def largo_estado(formato):
    return LARGO_ESTADO_COMPLETO if formato == COMPLETO else LARGO_NUCLEO


def _u16(valor):
    return max(0, min(0xFFFF, int(valor)))


def _real(valor):
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return 0.
    return valor if math.isfinite(valor) else 0.


def _f32(valor):
    """Valor tal como viaja en un Real de 32 bits (los desbordes de float32 no son finitos)."""
    try:
        return struct.unpack('>f', struct.pack('>f', _real(valor)))[0]
    except OverflowError:
        return 0.


def _seis(valores):
    valores = list(valores or [])[:6]
    return [_f32(v) for v in valores] + [0.] * (6 - len(valores))


@dataclass
class Orden:
    """PLC → PC. `mando` incluye el bit de vida (bit 15)."""
    mando: int = 0
    valor: int = 0
    velocidad_pct: int = 0
    repeticiones: int = 0
    pose: Optional[List[float]] = None       # None en formato núcleo

    @property
    def habilitar(self):
        return bool(self.mando & MANDO_HABILITAR)

    @property
    def vida(self):
        return bool(self.mando & BIT_VIDA)

    @property
    def ordenes(self):
        return {n: bool(self.mando & (1 << (i + 1))) for i, n in enumerate(BITS_ORDEN)}

    def pack(self, completo=True):
        if not completo:
            return _NUCLEO.pack(_u16(self.mando), _u16(self.valor))
        return _ORDEN.pack(_u16(self.mando), _u16(self.valor), _u16(self.velocidad_pct),
                           _u16(self.repeticiones), 0, 0, *_seis(self.pose))

    @classmethod
    def unpack(cls, datos):
        datos = bytes(datos)
        if len(datos) == LARGO_NUCLEO:
            return cls(*_NUCLEO.unpack(datos))
        if len(datos) != LARGO_ORDEN_COMPLETA:
            raise ValueError(f'La orden mide {LARGO_NUCLEO} o {LARGO_ORDEN_COMPLETA} bytes, no {len(datos)}')
        v = _ORDEN.unpack(datos)
        return cls(v[0], v[1], v[2], v[3], list(v[6:]))


@dataclass
class Estado:
    """PC → PLC. `estado` incluye el bit de vida (bit 15)."""
    estado: int = 0
    valor: int = 0
    fase: int = 0
    tramo: int = 0
    tramos: int = 0
    vuelta: int = 0
    velocidad_pct: int = 0
    codigo: int = 0
    q: List[float] = field(default_factory=lambda: [0.] * 6)
    pose: List[float] = field(default_factory=lambda: [0.] * 6)

    def bit(self, nombre):
        return bool(self.estado & (1 << BITS_ESTADO.index(nombre)))

    @property
    def vida(self):
        return bool(self.estado & BIT_VIDA)

    def pack(self, completo=True):
        if not completo:
            return _NUCLEO.pack(_u16(self.estado), _u16(self.valor))
        return _ESTADO.pack(_u16(self.estado), _u16(self.valor), _u16(self.fase), _u16(self.tramo),
                            _u16(self.tramos), _u16(self.vuelta), _u16(self.velocidad_pct),
                            _u16(self.codigo), 0, 0, *_seis(self.q), *_seis(self.pose))

    @classmethod
    def unpack(cls, datos):
        datos = bytes(datos)
        if len(datos) == LARGO_NUCLEO:
            return cls(*_NUCLEO.unpack(datos))
        if len(datos) != LARGO_ESTADO_COMPLETO:
            raise ValueError(f'El estado mide {LARGO_NUCLEO} o {LARGO_ESTADO_COMPLETO} bytes, no {len(datos)}')
        v = _ESTADO.unpack(datos)
        return cls(*v[:8], q=list(v[10:16]), pose=list(v[16:22]))


def orden_a_dict(orden, enlace, t, errores, formato=COMPLETO):
    """JSON de /irb120/plc/entrada (§4). Sin trama válida `orden` puede ser None (todo a 0)."""
    o = orden or Orden()
    completo = formato == COMPLETO
    return {'enlace': bool(enlace), 't': float(t), 'errores_trama': int(errores), 'formato': formato,
            'mando': o.mando & ~BIT_VIDA, 'habilitar': o.habilitar, 'ordenes': o.ordenes, 'valor': o.valor,
            'velocidad_pct': o.velocidad_pct if completo else 0,
            'repeticiones': o.repeticiones if completo else 0,
            'pose': [float(v) for v in _seis(o.pose)] if completo and o.pose is not None else None}


def estado_sin_brazo(vida):
    """Estado cuando el panel no responde: enlace=0, error=1, valor=3 (§3.2)."""
    return Estado(estado=(1 << BITS_ESTADO.index('error')) | (BIT_VIDA if vida else 0), valor=ERROR_SIN_BRAZO,
                  codigo=ERROR_SIN_BRAZO)


def estado_desde_dict(d, vida):
    """JSON de /irb120/plc/salida (§4) → Estado. Tolerante: ausente → 0/False, fuera de rango → recortado."""
    d = d if isinstance(d, dict) else {}
    bits = d.get('estado')
    bits = bits if isinstance(bits, dict) else {}
    palabra = sum(1 << i for i, n in enumerate(BITS_ESTADO) if bits.get(n))
    if vida:
        palabra |= BIT_VIDA

    def entero(clave):
        try:
            valor = float(d.get(clave, 0))
            return max(0, min(0xFFFF, int(valor))) if math.isfinite(valor) else 0
        except (TypeError, ValueError):
            return 0

    return Estado(estado=palabra, valor=entero('valor'), fase=entero('fase'), tramo=entero('tramo'),
                  tramos=entero('tramos'), vuelta=entero('vuelta'), velocidad_pct=entero('velocidad_pct'),
                  codigo=entero('codigo'), q=_seis(d.get('q')), pose=_seis(d.get('pose')))


def describir_estado(e):
    """Una línea legible del estado (la usa el simulador)."""
    activos = ','.join(n for n in BITS_ESTADO if e.bit(n)) + (',vida' if e.vida else '')
    return (f'estado=16#{e.estado:04X} [{activos.strip(",") or "-"}] valor={e.valor} fase={e.fase} '
            f'tramo={e.tramo}/{e.tramos} vuelta={e.vuelta} vel={e.velocidad_pct}% cod={e.codigo} '
            f'q={[round(v, 1) for v in e.q]} pose={[round(v, 1) for v in e.pose]}')
