"""Modelo de datos de una trayectoria: puntos de paso y secuencia con nombre (JSON)."""
from dataclasses import dataclass, field
import json
import math
from pathlib import Path

ORIGENES = ('manual', 'captura', 'rviz', 'vision', 'angulos')
TIPOS = ('auto', 'articular', 'lineal')
HERRAMIENTAS = ('tcp', 'brida')


def _numeros(valor, n, que):
    """Lista de n números finitos (sin bool) o ValueError con mensaje claro."""
    if not isinstance(valor, (list, tuple)) or len(valor) != n:
        raise ValueError(f'{que}: se esperan {n} números.')
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in valor):
        raise ValueError(f'{que}: todos los valores deben ser números finitos.')
    return [float(v) for v in valor]


@dataclass
class Punto:
    nombre: str
    pose: list | None = None     # [x, y, z mm, roll, pitch, yaw °] de la herramienta, en base_link
    q: list | None = None        # ángulos [°]; si está, tiene prioridad sobre la pose
    origen: str = 'manual'       # manual | captura | rviz | vision | angulos
    tipo: str = 'auto'           # movimiento PARA LLEGAR a este punto: auto | articular | lineal

    def __post_init__(self):
        if not isinstance(self.nombre, str) or not self.nombre.strip():
            raise ValueError('El punto necesita un nombre no vacío.')
        if self.pose is None and self.q is None:
            raise ValueError(f'Punto «{self.nombre}»: hace falta una pose o los ángulos q.')
        if self.pose is not None:
            self.pose = _numeros(self.pose, 6, f'Punto «{self.nombre}», pose [x, y, z, roll, pitch, yaw]')
        if self.q is not None:
            self.q = _numeros(self.q, 6, f'Punto «{self.nombre}», q')
        if self.origen not in ORIGENES:
            raise ValueError(f'Punto «{self.nombre}»: origen «{self.origen}» desconocido ({", ".join(ORIGENES)}).')
        if self.tipo not in TIPOS:
            raise ValueError(f'Punto «{self.nombre}»: tipo «{self.tipo}» desconocido ({", ".join(TIPOS)}).')

    def to_dict(self):
        return {'nombre': self.nombre, 'pose': self.pose, 'q': self.q, 'origen': self.origen,
                'tipo': self.tipo}

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            raise ValueError('Un punto debe ser un objeto JSON.')
        return cls(nombre=d.get('nombre'), pose=d.get('pose'), q=d.get('q'),
                   origen=d.get('origen', 'manual'), tipo=d.get('tipo', 'auto'))


@dataclass
class Trayectoria:
    nombre: str
    puntos: list = field(default_factory=list)
    cerrar: bool = True          # A→B→C→A
    repeticiones: int = 1
    herramienta: str = 'tcp'     # tcp | brida

    def __post_init__(self):
        if not isinstance(self.nombre, str) or not self.nombre.strip():
            raise ValueError('La trayectoria necesita un nombre no vacío.')
        if not isinstance(self.puntos, list) or not all(isinstance(p, Punto) for p in self.puntos):
            raise ValueError('«puntos» debe ser una lista de Punto.')
        nombres = [p.nombre for p in self.puntos]
        repetidos = sorted({n for n in nombres if nombres.count(n) > 1})
        if repetidos:
            raise ValueError(f'Nombres de punto repetidos: {", ".join(repetidos)}.')
        if isinstance(self.repeticiones, bool) or not isinstance(self.repeticiones, int) or not 1 <= self.repeticiones <= 1000:
            raise ValueError('«repeticiones» debe ser un entero entre 1 y 1000.')
        if self.herramienta not in HERRAMIENTAS:
            raise ValueError(f'Herramienta «{self.herramienta}» desconocida: usar «tcp» o «brida».')
        self.cerrar = bool(self.cerrar)

    def to_dict(self):
        return {'nombre': self.nombre, 'puntos': [p.to_dict() for p in self.puntos], 'cerrar': self.cerrar,
                'repeticiones': self.repeticiones, 'herramienta': self.herramienta}

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            raise ValueError('La trayectoria debe ser un objeto JSON.')
        puntos = d.get('puntos')
        if not isinstance(puntos, list):
            raise ValueError('Falta la lista «puntos».')
        return cls(nombre=d.get('nombre'), puntos=[Punto.from_dict(p) for p in puntos],
                   cerrar=d.get('cerrar', True), repeticiones=d.get('repeticiones', 1),
                   herramienta=d.get('herramienta', 'tcp'))

    def guardar(self, path):
        Path(path).write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    @classmethod
    def cargar(cls, path):
        try:
            datos = json.loads(Path(path).read_text(encoding='utf-8'))
        except json.JSONDecodeError as exc:
            raise ValueError(f'El archivo {path} no es un JSON válido: {exc}') from exc
        return cls.from_dict(datos)
