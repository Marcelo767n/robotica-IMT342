#!/usr/bin/env python3
"""Compatibilidad: la implementación está organizada en ros2_ws/src/irb120_conexion/."""
from pathlib import Path as _Path
import sys as _sys
_package_root = _Path(__file__).resolve().parents[1] / "ros2_ws/src/irb120_conexion"
_sys.path.insert(0, str(_package_root))
__file__ = str(_package_root / 'irb120_conexion/comunicacion/lectura_rws.py')
exec(compile(_Path(__file__).read_text(encoding="utf-8"), __file__, "exec"), globals())
