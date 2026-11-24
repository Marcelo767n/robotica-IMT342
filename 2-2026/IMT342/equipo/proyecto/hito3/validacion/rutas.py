"""Rutas del proyecto y acceso al paquete `irb120` del Hito 2 (solo lectura, sin modificarlo)."""

import hashlib
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]  # .../proyecto
HITO3 = RAIZ / "hito3"
DATOS = HITO3 / "datos"
RESULTADOS = HITO3 / "resultados"
FIGURAS = RESULTADOS / "figuras"
LATEX = RESULTADOS / "latex"
MANIFIESTOS = HITO3 / "manifiestos"
EVIDENCIAS = RAIZ / "docs" / "conexion_abb" / "evidencias"
URDF = RAIZ / "hito2" / "datos" / "irb120.urdf"

# Checkout principal con los registros crudos (SOLO LECTURA). Solo hace falta para re-extraer datos.
RAIZ_M = Path(os.environ.get("HITO3_M", "/home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto"))
ORIGEN_CRUDO = RAIZ_M / "salidas" / "prueba_comunicacion"

_hito2 = str(RAIZ / "hito2")
if _hito2 not in sys.path:
    sys.path.insert(0, _hito2)


def asegurar_directorios():
    for ruta in (DATOS, RESULTADOS, FIGURAS, LATEX, MANIFIESTOS):
        ruta.mkdir(parents=True, exist_ok=True)


def sha256_archivo(ruta) -> str:
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def commit_git() -> dict:
    """Commit HEAD del repositorio y si hay cambios sin versionar en hito3/."""
    def _git(*args):
        try:
            return subprocess.run(["git", "-C", str(RAIZ), *args], capture_output=True, text=True, timeout=20, check=True).stdout.strip()
        except Exception:  # noqa: BLE001 - git puede no estar disponible
            return None
    commit = _git("rev-parse", "HEAD")
    sucio = _git("status", "--porcelain", "--", "hito3")
    return {
        "commit": commit or "no disponible",
        "hito3_sin_versionar": bool(sucio) if sucio is not None else None,
    }
