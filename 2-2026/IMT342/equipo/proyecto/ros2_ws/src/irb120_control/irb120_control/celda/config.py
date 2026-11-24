"""Configuración de la celda (`config/celda.yaml`, sección `celda:`). Sin ROS; si falta el archivo, valores por defecto."""
from collections.abc import Mapping
from pathlib import Path
import re

import yaml

CARPETA = 'salidas/trayectorias'
REPOSO = [0., 0., 0., 0., 30., 0.]
YAML = Path(__file__).resolve().parents[2] / 'config/celda.yaml'


NUMERADO = re.compile(r'^(\d{1,2})_.+\.json$')   # 03_paletizado.json → trayectoria nº 3 del PLC


class Catalogo(Mapping):
    """{número: Path} que se relee en cada consulta: una trayectoria guardada en el Estudio como
    `NN_nombre.json` está disponible para el PLC sin reiniciar el nodo. Las entradas del YAML mandan;
    un número repetido en la carpeta (dos archivos NN_*) no se usa (ambiguo)."""

    def __init__(self, fijas, carpeta):
        self.fijas, self.carpeta = dict(fijas), Path(carpeta)

    def _todas(self):
        vistas, repetidos = {}, set()
        if self.carpeta.is_dir():
            for archivo in sorted(self.carpeta.glob('*.json')):
                m = NUMERADO.match(archivo.name)
                n = int(m.group(1)) if m else 0
                if 1 <= n <= 99:
                    if n in vistas:
                        repetidos.add(n)
                    vistas[n] = archivo
        for n in repetidos:
            vistas.pop(n)
        return {**vistas, **self.fijas}

    def __getitem__(self, n):
        return self._todas()[n]

    def __iter__(self):
        return iter(sorted(self._todas()))

    def __len__(self):
        return len(self._todas())


def rutas(trayectorias, carpeta, base):
    """Catálogo {número: Path absoluto}: entradas del YAML (1…99) + archivos `NN_nombre.json` de la carpeta."""
    carpeta = Path(carpeta)
    if not carpeta.is_absolute():
        carpeta = Path(base) / carpeta
    salida = {}
    for clave, nombre in (trayectorias or {}).items():
        try:
            n = int(clave)
        except (TypeError, ValueError):
            continue
        if 1 <= n <= 99 and isinstance(nombre, str) and nombre.strip():
            salida[n] = carpeta / nombre.strip()
    return Catalogo(salida, carpeta)


def cargar(base, yaml_path=None, carpeta=None):
    """(rutas, reposo). `carpeta` de la línea de comandos manda sobre el YAML."""
    datos = {}
    path = Path(yaml_path) if yaml_path else YAML
    if path.is_file():
        try:
            datos = (yaml.safe_load(path.read_text(encoding='utf-8')) or {}).get('celda') or {}
        except (yaml.YAMLError, AttributeError, OSError):
            datos = {}
    reposo = datos.get('reposo')
    if not (isinstance(reposo, list) and len(reposo) == 6):
        reposo = REPOSO
    return rutas(datos.get('trayectorias'), carpeta or datos.get('carpeta') or CARPETA, base), [float(v) for v in reposo]
