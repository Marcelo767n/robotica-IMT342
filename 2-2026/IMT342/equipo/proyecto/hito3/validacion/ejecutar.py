"""Ejecuta toda la validación cinemática del Hito 3, offline y reproducible.

    python3 -m hito3.validacion            (desde la carpeta proyecto/)
    python3 hito3/validacion/ejecutar.py   (idem)

Entradas: hito3/datos/ (subconjunto compacto S1 con procedencia) y el código de hito2/irb120 (solo lectura).
Opción --reextraer: regenera hito3/datos/ desde los registros crudos del checkout principal (variable HITO3_M).
Salidas: hito3/resultados/ (CSV, JSON, figuras, fragmentos LaTeX) y hito3/manifiestos/*.yaml.
"""

import argparse
import sys
import time
from pathlib import Path

if __package__ in (None, ""):  # ejecución como script
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hito3.validacion import casos, datos_irc5, fk, ik, jacobiano, rutas, singularidad, sinteticos, tablas, tolerancias, util  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--reextraer", action="store_true", help="regenerar hito3/datos desde los registros crudos (requiere el checkout principal)")
    args = ap.parse_args(argv)
    t0 = time.time()
    rutas.asegurar_directorios()
    if args.reextraer or not (rutas.DATOS / "fk_real_N1_estacionarias.csv").exists():
        print("Extrayendo subconjunto S1 desde", rutas.ORIGEN_CRUDO)
        datos_irc5.extraer()
    res = {}
    print("[1/8] verificación de métricas con ejemplos sintéticos"); res["sint"] = sinteticos.ejecutar()
    print("[2/8] Bloque C: FK (real S1, offline, diagnósticos)"); res["fk"] = fk.ejecutar()
    print("[3/8] Bloque D: IK (8 ramas, DLS independiente)"); res["ik"] = ik.ejecutar()
    print("[4/8] Bloque E: Jacobiano y curva FD"); res["jac"] = jacobiano.ejecutar()
    print("[5/8] Bloque F: singularidad"); res["sing"] = singularidad.ejecutar()
    print("[6/8] Bloques G/H: tolerancias"); res["tol"] = tolerancias.ejecutar(res["fk"])
    print("[7/8] validation_cases.csv, manifiestos y tablas P1-P5")
    ctx = casos.contexto()
    filas, meta = casos.construir(res, ctx)
    casos.escribir(filas, meta)
    n_man = casos.escribir_manifiestos(filas, meta, ctx)
    tablas.p1(res, meta, ctx); tablas.p2(res, meta, ctx); tablas.p3(res, meta, ctx); tablas.p4(res, meta, ctx)
    cuentas = tablas.p5_y_otros(res, meta, ctx, filas)
    print("[8/8] resultados.json")
    util.escribir_json(rutas.RESULTADOS / "resultados.json", {"contexto": {k: v for k, v in ctx.items() if k != "proc"}, "estados": cuentas, "casos": meta, **{k: v for k, v in res.items()}})
    print(f"\nListo en {time.time() - t0:.1f} s. Casos: {len(filas)}; manifiestos: {n_man}; estados: {cuentas}")
    print(f"{'caso':<11}{'nivel':<18}{'estado':<22}")
    for cid, m in meta.items():
        print(f"{cid:<11}{m['nivel']:<18}{m['estado']:<22}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
