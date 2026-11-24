"""Biblioteca de trayectorias en disco (sin Tk): `NN_<nombre>.json` con número de PLC, o `<nombre>.json` sin él."""
from dataclasses import dataclass
from pathlib import Path
import re
import time
import unicodedata

from irb120_control.trayectorias import Trayectoria

MAX_NUMERO = 99
PAPELERA = 'papelera'
_PREFIJO = re.compile(r'^(\d{1,2})_(.+)$')


@dataclass
class Entrada:
    ruta: Path
    numero: int | None
    nombre: str
    puntos: int = 0


class Ocupado(ValueError):
    """El archivo o el número de destino ya lo usa otra trayectoria (`.entrada`)."""

    def __init__(self, entrada, numero):
        self.entrada, self.numero = entrada, numero
        quien = f'el número {numero}' if numero is not None and entrada.numero == numero else 'ese archivo'
        super().__init__(f'{quien.capitalize()} ya lo usa «{entrada.nombre}».')


def sanear(nombre):
    """Nombre seguro para archivo: minúsculas, sin acentos, guiones."""
    t = unicodedata.normalize('NFKD', str(nombre)).encode('ascii', 'ignore').decode().lower()
    t = re.sub(r'[^a-z0-9]+', '-', t).strip('-')
    return t or 'trayectoria'


def validar_numero(numero):
    if numero is None:
        return None
    if isinstance(numero, bool) or not isinstance(numero, int) or not 1 <= numero <= MAX_NUMERO:
        raise ValueError(f'El número de PLC debe ser un entero entre 1 y {MAX_NUMERO}.')
    return numero


def nombre_archivo(nombre, numero=None):
    numero = validar_numero(numero)
    base = sanear(nombre)
    return f'{numero:02d}_{base}.json' if numero is not None else f'{base}.json'


def numero_de(ruta):
    m = _PREFIJO.match(Path(ruta).stem)
    return int(m.group(1)) if m and 1 <= int(m.group(1)) <= MAX_NUMERO else None


def listar(carpeta):
    """Entradas ordenadas: primero las numeradas por número, luego las demás por nombre. Ignora JSON rotos."""
    carpeta = Path(carpeta)
    if not carpeta.is_dir():
        return []
    salida = []
    for ruta in carpeta.glob('*.json'):
        try:
            t = Trayectoria.cargar(ruta)
        except (ValueError, OSError):
            continue
        salida.append(Entrada(ruta, numero_de(ruta), t.nombre, len(t.puntos)))
    return sorted(salida, key=lambda e: (e.numero is None, e.numero or 0, e.nombre.lower()))


def etiqueta(e):
    num = f'{e.numero:02d}' if e.numero is not None else '——'
    return f'{num} · {e.nombre}  ({e.puntos} pts)'


def entrada_con_numero(carpeta, numero, ignorar=None):
    for e in listar(carpeta):
        if e.numero == numero and (ignorar is None or Path(e.ruta) != Path(ignorar)):
            return e
    return None


def numero_libre(carpeta, desde=1):
    usados = {e.numero for e in listar(carpeta) if e.numero is not None}
    for n in list(range(desde, MAX_NUMERO + 1)) + list(range(1, desde)):
        if n not in usados:
            return n
    raise ValueError('Los 99 números de PLC están ocupados.')


def nombre_unico(carpeta, base):
    usados = {e.nombre for e in listar(carpeta)}
    if base not in usados:
        return base
    k = 2
    while f'{base} {k}' in usados:
        k += 1
    return f'{base} {k}'


def a_papelera(ruta):
    """Mueve el archivo a salidas/trayectorias/papelera/ (nunca lo borra). Devuelve la nueva ruta."""
    ruta = Path(ruta)
    dest = ruta.parent / PAPELERA
    dest.mkdir(parents=True, exist_ok=True)
    nuevo = dest / ruta.name
    if nuevo.exists():
        nuevo = dest / f'{ruta.stem}_{time.strftime("%Y%m%d-%H%M%S")}{ruta.suffix}'
    ruta.rename(nuevo)
    return nuevo


def guardar(tray, carpeta, numero=None, ruta_previa=None, reemplazar=False):
    """Guarda `tray` como NN_nombre.json. Si `ruta_previa` es otro archivo, se renombra (se retira el viejo).

    Lanza `Ocupado` si el número o el archivo lo usa OTRA trayectoria y no se pidió `reemplazar`
    (en ese caso la otra va a la papelera).
    """
    carpeta = Path(carpeta)
    numero = validar_numero(numero)
    destino = carpeta / nombre_archivo(tray.nombre, numero)
    previa = Path(ruta_previa) if ruta_previa else None
    otras = []
    if numero is not None:
        e = entrada_con_numero(carpeta, numero, ignorar=previa)
        if e is not None and e.ruta != destino:
            otras.append(e)
    if destino.exists() and destino != previa:
        otras.append(next((e for e in listar(carpeta) if e.ruta == destino), Entrada(destino, numero_de(destino),
                                                                                   destino.stem)))
    if otras and not reemplazar:
        raise Ocupado(otras[0], numero)
    carpeta.mkdir(parents=True, exist_ok=True)
    for e in otras:
        if e.ruta.exists():
            a_papelera(e.ruta)
    tray.guardar(destino)
    if previa is not None and previa != destino and previa.exists():
        previa.unlink()
    return destino


def duplicar(ruta, carpeta, nombre_nuevo, numero=None, reemplazar=False):
    t = Trayectoria.cargar(ruta)
    t.nombre = nombre_nuevo.strip()
    return guardar(Trayectoria.from_dict(t.to_dict()), carpeta, numero, None, reemplazar)


def renombrar(ruta, nombre_nuevo, numero=None, reemplazar=False):
    t = Trayectoria.cargar(ruta)
    t.nombre = nombre_nuevo.strip()
    return guardar(Trayectoria.from_dict(t.to_dict()), Path(ruta).parent, numero, ruta, reemplazar)
