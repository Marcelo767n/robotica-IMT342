"""Datos reales S1 del IRC5: extracción desde los registros crudos (solo lectura) y carga del subconjunto compacto.

Fuente: registros JSONL de la sesión del 04/11/2026 (RWS, http://192.168.125.1), pose del controlador en
`Base`, herramienta `tool0` (brida), `wobj0`; q en grados (orden de ejes ABB 1..6 = joint_1..joint_6);
posición en mm; cuaternión en orden (w, x, y, z).

`extraer()` necesita el checkout principal M (solo lectura) y escribe en hito3/datos/.
`cargar_*()` lee únicamente hito3/datos/, de modo que el resto del paquete corre offline sin M.
"""

import collections
import csv
import json
from pathlib import Path

import numpy as np

from . import rutas

ARCHIVOS = {
    "S1": "comunicacion_20261104_223936_186467Z_fk.jsonl",
    "S2": "comunicacion_20261104_225612_309539Z_fk.jsonl",
}
UMBRAL_ESTACIONARIO_DEG = 1.0e-3   # max|q_despues - q_antes| declarado para "estacionaria"
VENTANA_MAX_MS = 500.0             # ventana q->pose->q máxima aceptada (igual que el nodo de registro)
REDONDEO_POSTURA_DEG = 2           # agrupa lecturas de una misma postura (0.01 deg)
MIN_MUESTRAS_POSTURA = 20

# postura elegida para cada caso nominal: (sesión, q aproximada en grados)
POSTURAS_NOMINALES = {
    "N1": ("S1", (-73.21, -12.15, 9.91, 91.88, 31.75, -134.5)),
    "N2": ("S2", (2.95, -1.93, 2.59, -13.06, 89.66, -133.98)),
}

COLUMNAS = (
    ["archivo", "linea", "seq", "received_at_utc", "stamp_sec", "stamp_nanosec", "status_registro", "window_ms"]
    + [f"qb{i}_deg" for i in range(1, 7)] + [f"qa{i}_deg" for i in range(1, 7)]
    + ["x_mm", "y_mm", "z_mm", "qw", "qx", "qy", "qz", "tool", "wobj", "coordinate", "e_p_mm_registro", "e_R_rad_registro"]
)


def _fila(archivo, linea, d):
    s, r = d["sample"], d["result"]
    pose = s["controller_pose"]
    return [archivo, linea, s.get("seq"), d["received_at_utc"], s["stamp"]["sec"], s["stamp"]["nanosec"],
            r["status"], s["window_ms"], *s["q_before_deg"], *s["q_after_deg"], *pose["xyz_mm"],
            *pose["quaternion_wxyz"], s["context"]["tool"], s["context"]["wobj"], s["context"]["coordinate"],
            r.get("position_error_mm"), r.get("orientation_error_rad")]


def _leer(clave):
    ruta = rutas.ORIGEN_CRUDO / ARCHIVOS[clave]
    with open(ruta, encoding="utf-8") as fh:
        for n, linea in enumerate(fh, 1):
            if linea.strip():
                yield n, json.loads(linea)


def _estacionaria(d):
    s = d["sample"]
    dq = np.abs(np.array(s["q_after_deg"]) - np.array(s["q_before_deg"])).max()
    return dq <= UMBRAL_ESTACIONARIO_DEG and s["window_ms"] <= VENTANA_MAX_MS, float(dq)


def extraer() -> dict:
    """Lee M (solo lectura) y escribe el subconjunto compacto con procedencia en hito3/datos/."""
    rutas.asegurar_directorios()
    info = {"umbral_estacionario_deg": UMBRAL_ESTACIONARIO_DEG, "ventana_max_ms": VENTANA_MAX_MS,
            "redondeo_postura_deg": REDONDEO_POSTURA_DEG, "archivos": {}}
    filas_n = {"N1": [], "N2": []}
    filas_fuera, posturas, invalidas = [], [], collections.defaultdict(lambda: collections.Counter())
    rangos_inv = {}
    for clave in ARCHIVOS:
        ruta = rutas.ORIGEN_CRUDO / ARCHIVOS[clave]
        registros = list(_leer(clave))
        estados = collections.Counter(d["result"]["status"] for _, d in registros)
        info["archivos"][clave] = {
            "archivo": f"salidas/prueba_comunicacion/{ARCHIVOS[clave]}", "sha256": rutas.sha256_archivo(ruta),
            "bytes": ruta.stat().st_size, "lineas": len(registros), "estados": dict(estados),
            "primera_recepcion_utc": registros[0][1]["received_at_utc"], "ultima_recepcion_utc": registros[-1][1]["received_at_utc"]}
        # lecturas inválidas: causa agrupada (sin la cadena completa, que varía por dirección/tiempo)
        for n, d in registros:
            if d["result"]["status"] == "LECTURA_INVALIDA":
                texto = d["result"].get("reason", "")
                causa = texto.split(":")[0] if ":" in texto else texto
                if "timed out" in texto:
                    causa += " (timed out)"
                invalidas[clave][causa] += 1
                rango = rangos_inv.setdefault(clave, {}).setdefault(causa, [d["received_at_utc"], d["received_at_utc"]])
                rango[1] = d["received_at_utc"]
        # agrupación por postura (solo muestras con datos de q y pose, estacionarias)
        grupos = collections.defaultdict(list)
        modal = collections.defaultdict(collections.Counter)  # q exacta -> pose más repetida
        for n, d in registros:
            if d["result"]["status"] == "LECTURA_INVALIDA":
                continue
            ok, dq = _estacionaria(d)
            if ok:
                clave_q = tuple(np.round(d["sample"]["q_after_deg"], REDONDEO_POSTURA_DEG))
                grupos[clave_q].append((n, d))
                p = d["sample"]["controller_pose"]
                modal[tuple(d["sample"]["q_after_deg"])][(tuple(p["xyz_mm"]), tuple(p["quaternion_wxyz"]))] += 1
        for q, lista in grupos.items():
            if len(lista) >= MIN_MUESTRAS_POSTURA:
                poses = {(tuple(d["sample"]["controller_pose"]["xyz_mm"]), tuple(d["sample"]["controller_pose"]["quaternion_wxyz"])) for _, d in lista}
                posturas.append([clave, *q, len(lista), len(poses), collections.Counter(d["result"]["status"] for _, d in lista).get("FUERA", 0),
                                 lista[0][1]["received_at_utc"], lista[-1][1]["received_at_utc"]])
        for nombre, (ses, qn) in POSTURAS_NOMINALES.items():
            if ses == clave:
                k = tuple(np.round(qn, REDONDEO_POSTURA_DEG))
                filas_n[nombre] = [_fila(ARCHIVOS[clave], n, d) for n, d in grupos[k]]
        for n, d in registros:
            if d["result"]["status"] == "FUERA":
                ok, dq = _estacionaria(d)
                qa = tuple(d["sample"]["q_after_deg"])
                (mxyz, mq), cnt = modal[qa].most_common(1)[0] if modal[qa] else (((np.nan,) * 3, (np.nan,) * 4), 0)
                filas_fuera.append(_fila(ARCHIVOS[clave], n, d) + [dq, mxyz[0], mxyz[1], mxyz[2], *mq, cnt, sum(modal[qa].values())])
    for nombre, filas in filas_n.items():
        _escribir(rutas.DATOS / f"fk_real_{nombre}_estacionarias.csv", COLUMNAS, filas)
    extra = ["dq_max_deg", "modal_x_mm", "modal_y_mm", "modal_z_mm", "modal_qw", "modal_qx", "modal_qy", "modal_qz",
             "n_modal_misma_q", "n_estacionarias_misma_q"]
    _escribir(rutas.DATOS / "fk_real_fuera.csv", COLUMNAS + extra, filas_fuera)
    _escribir(rutas.DATOS / "fk_real_posturas.csv",
              ["sesion", *[f"q{i}_deg" for i in range(1, 7)], "n_estacionarias", "n_poses_controlador_distintas", "n_fuera", "primera_utc", "ultima_utc"],
              sorted(posturas, key=lambda f: (f[0], -f[7])))
    info["lecturas_invalidas"] = {k: dict(v) for k, v in invalidas.items()}
    info["lecturas_invalidas_rango_utc"] = rangos_inv
    info["n_fuera_total"] = len(filas_fuera)
    info["n_filas_N1"], info["n_filas_N2"] = len(filas_n["N1"]), len(filas_n["N2"])
    with open(rutas.DATOS / "fk_real_procedencia.json", "w", encoding="utf-8") as fh:
        json.dump(info, fh, indent=2, ensure_ascii=False)
    return info


def _escribir(ruta, columnas, filas):
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(columnas)
        w.writerows(filas)


def _cargar_csv(nombre):
    with open(rutas.DATOS / nombre, newline="", encoding="utf-8") as fh:
        filas = list(csv.DictReader(fh))
    numericas = {c for c in filas[0] if c not in ("archivo", "received_at_utc", "status_registro", "tool", "wobj", "coordinate", "sesion", "primera_utc", "ultima_utc")} if filas else set()
    for f in filas:
        for c in numericas:
            f[c] = float(f[c]) if f[c] not in ("", "nan") else float("nan")
        for c in ("linea", "seq", "stamp_sec", "stamp_nanosec"):
            if c in f and f[c] == f[c]:
                f[c] = int(f[c])
    return filas


def cargar_postura(nombre):
    return _cargar_csv(f"fk_real_{nombre}_estacionarias.csv")


def cargar_fuera():
    return _cargar_csv("fk_real_fuera.csv")


def cargar_posturas():
    return _cargar_csv("fk_real_posturas.csv")


def cargar_procedencia():
    with open(rutas.DATOS / "fk_real_procedencia.json", encoding="utf-8") as fh:
        return json.load(fh)


def q_rad(fila, prefijo="qa"):
    return np.deg2rad([fila[f"{prefijo}{i}_deg"] for i in range(1, 7)])


def pose_controlador(fila):
    """(p [m], cuaternión wxyz) del controlador para una fila."""
    return np.array([fila["x_mm"], fila["y_mm"], fila["z_mm"]]) / 1000.0, np.array([fila["qw"], fila["qx"], fila["qy"], fila["qz"]])


if __name__ == "__main__":
    print(json.dumps(extraer(), indent=2, ensure_ascii=False))
