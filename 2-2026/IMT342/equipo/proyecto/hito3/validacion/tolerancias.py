"""Bloques G y H: presupuesto de tolerancia numérico offline e incertidumbres de la comparación con el IRC5.

NO se declara ningún umbral aprobado: el presupuesto offline es una propuesta (estado «pendiente de aprobación») y para el
IRC5 solo se enumeran y, cuando hay datos, se acotan las fuentes de incertidumbre (estado «pendiente y bloqueada por datos»).
"""

import csv
import math
import re

import numpy as np

from . import datos_irc5 as D, metricas as M, rutas, util
from irb120.pieper import D1, D6, L2, L3  # noqa: E402

K_PRESUPUESTO = 10.0       # factor de acumulación declarado (no derivado): cubre error de trig. y propagación
N_OPS = 700                # operaciones de punto flotante estimadas de una FK DH de 6 ejes (ver desglose)
DESGLOSE_N_OPS = {"matrices DH (6 x ~16 operaciones + 12 trig. contadas como 1)": 6 * 16 + 12, "productos 4x4x4 (5 x 112)": 5 * 112, "margen declarado": 700 - (6 * 16 + 12) - 5 * 112}
L_REF = D1 + L2 + L3 + D6  # cota superior (desigualdad triangular) de ||p_tool0|| desde la base: 0.942 m


def presupuesto():
    eps = M.EPS
    return {"eps_mach": eps, "K": K_PRESUPUESTO, "N_ops": N_OPS, "desglose_N_ops": DESGLOSE_N_OPS, "L_ref_m": L_REF,
            "tau_p_m": K_PRESUPUESTO * eps * L_REF * N_OPS, "tau_R_rad": K_PRESUPUESTO * eps * N_OPS,
            "piso_arccos_rad": math.sqrt(2.0 * eps),
            "nota_arccos": "e_R por arccos tiene piso ≈ sqrt(2 eps) ≈ 2.1e-8 rad: para comparar con tau_R se usa la forma atan2.",
            "cribado_exploratorio_sintetico": {"e_p_m": 1e-6, "e_R_rad": 1e-5, "estado": "pendiente de aprobación"},
            "estado": "pendiente de aprobación",
            "L_justificacion": "L_ref = d1 + a2 + sqrt(d4²+a3²) + d6 = 0.942 m, cota del alcance de tool0 (declarada)."}


def _decimales_observados():
    mx_xyz, mx_sig = 0, 0
    for n in ("N1", "N2"):
        with open(rutas.DATOS / f"fk_real_{n}_estacionarias.csv", newline="", encoding="utf-8") as fh:
            for f in csv.DictReader(fh):
                for k in ("x_mm", "y_mm", "z_mm"):
                    s = f[k]
                    mx_xyz = max(mx_xyz, len(s.split(".")[1]) if "." in s else 0)
                for k in ("qw", "qx", "qy", "qz"):
                    digs = re.sub(r"^[-0.]+", "", f[k]).replace(".", "").rstrip("0")
                    mx_sig = max(mx_sig, len(digs))
    return mx_xyz, mx_sig


def incertidumbres_irc5(fk_res, fuera):
    dec_xyz, sig_q = _decimales_observados()
    n1, n2 = fk_res["FK-N1"], fk_res["FK-N2"]
    ventana = {n: fk_res[f"FK-{n}"]["ventana_ms"] for n in ("N1", "N2")}
    filas = [
        {"fuente": "Resolución de la posición del robtarget (xyz)", "valor": f"7 cifras significativas: 4 decimales en mm (1e-4 mm = 1e-7 m) si |v| ≥ 100 mm; hasta {dec_xyz} decimales si |v| < 10 mm",
         "efecto_e_p_m": n1["cuantizacion"]["cota_e_p_solo_xyz_m"], "origen": "observado en los registros S1 (FK-N1; cota de FK-N2: %.1e m)" % n2["cuantizacion"]["cota_e_p_solo_xyz_m"], "estado": "cota derivada; umbral pendiente"},
        {"fuente": "Resolución del cuaternión (w,x,y,z)", "valor": f"≤ {sig_q} cifras significativas observadas (componentes ≤ 1)",
         "efecto_e_R_rad": 2.0 * 2.0 * 5e-8, "origen": "observado; cota 2·||δq||, |δq_i| ≤ 5e-8", "estado": "cota derivada; umbral pendiente"},
        {"fuente": "Resolución de q (RWS entrega float32)", "valor": f"semi-ulp float32 hasta {max(n1['cuantizacion']['semi_ulp_q_deg']):.1e} ° en FK-N1",
         "efecto_e_p_m": n1["cuantizacion"]["cota_e_p_m"] - n1["cuantizacion"]["cota_e_p_solo_xyz_m"], "origen": "derivado: Σ‖Jv_i‖·semi-ulp (FK-N1)", "estado": "cota derivada; umbral pendiente"},
        {"fuente": "Cota total de cuantización de los datos (FK-N1 / FK-N2)", "valor": f"e_p ≤ {n1['cuantizacion']['cota_e_p_m']:.2e} / {n2['cuantizacion']['cota_e_p_m']:.2e} m; e_R ≤ {n1['cuantizacion']['cota_e_R_rad']:.2e} / {n2['cuantizacion']['cota_e_R_rad']:.2e} rad",
         "origen": "suma de las tres fuentes anteriores", "estado": "piso de resolución, no tolerancia"},
        {"fuente": "TCP / herramienta activa", "valor": "tooldata del IRC5 NO leído; se compara tool0 (brida) ⇒ TCP no interviene; TCP de 0.150 m es convención del modelo (tcp_verified_on_robot: false)",
         "origen": "no medido", "estado": "bloqueado por datos"},
        {"fuente": "Sincronía q ↔ pose", "valor": f"ventana q→pose→q: mediana {ventana['N1']['mediana']:.1f} / {ventana['N2']['mediana']:.1f} ms, máx {ventana['N1']['max']:.1f} / {ventana['N2']['max']:.1f} ms (N1/N2); sin reloj común, robot estacionario",
         "origen": "observado (window_ms)", "estado": "mitigada con q_antes ≈ q_después; no medible por debajo de la ventana"},
        {"fuente": "Fluctuación de la pose del IRC5 con q constante", "valor": f"hasta e_p = {fuera['estadistica_e_p_m']['max']:.2e} m y e_R = {fuera['estadistica_e_R_rad']['max']:.2e} rad en las {fuera['n_fuera']} muestras FUERA",
         "origen": "observado (diagnóstico FUERA)", "estado": "causa indeterminada por datos"},
        {"fuente": "Base y ceros mecánicos del controlador frente al modelo", "valor": "coincidencia empírica en 2 posturas distintas (error ≤ ~1e-6 m); calibración de fábrica del robot no consultada",
         "origen": "no medido directamente", "estado": "parcial"},
        {"fuente": "Repetibilidad / exactitud absoluta del IRB 120", "valor": "no medida en este trabajo; el repositorio cita 0.01 mm de repetibilidad (hito2/irb120/validation.py, de la hoja ABB) sin verificación local",
         "origen": "cita no verificada", "estado": "bloqueada por datos"},
    ]
    return {"filas": filas, "estado_global": "pendiente de aprobación; sin umbral numérico aprobado para FK propia vs IRC5",
            "tau_real_propuesto": None, "decimales_xyz_observados": dec_xyz, "cifras_significativas_cuaternion_max": sig_q}


def ejecutar(fk_res):
    pres = presupuesto()
    offline = [fk_res["FK-N1-S0"], fk_res["FK-N2-S0"], fk_res["FK-N3-S0"], *fk_res["FK-L"]]
    obs_p = max(c["e_p_m"] for c in offline)
    obs_R = max(c["e_R_atan2_rad"] for c in offline)
    pres["observado_max_e_p_m"], pres["observado_max_e_R_atan2_rad"] = obs_p, obs_R
    pres["cumple_p"], pres["cumple_R"] = bool(obs_p <= pres["tau_p_m"]), bool(obs_R <= pres["tau_R_rad"])
    pres["sensibilidad_K"] = [{"K": k, "tau_p_m": k * M.EPS * L_REF * N_OPS, "tau_R_rad": k * M.EPS * N_OPS} for k in (1, 4, 10, 100)]
    irc5 = incertidumbres_irc5(fk_res, fk_res["FUERA"])
    util.escribir_csv(rutas.RESULTADOS / "tolerancias_presupuesto.csv", ["K", "N_ops", "L_ref_m", "tau_p_m", "tau_R_rad", "obs_max_e_p_m", "obs_max_e_R_atan2_rad", "estado"],
                      [[s["K"], N_OPS, L_REF, s["tau_p_m"], s["tau_R_rad"], obs_p, obs_R, "pendiente de aprobación"] for s in pres["sensibilidad_K"]])
    util.escribir_csv(rutas.RESULTADOS / "tolerancias_incertidumbres_irc5.csv", ["fuente", "valor", "cota_e_p_m", "cota_e_R_rad", "origen", "estado"],
                      [[f["fuente"], f["valor"], f.get("efecto_e_p_m", ""), f.get("efecto_e_R_rad", ""), f["origen"], f["estado"]] for f in irc5["filas"]])
    return {"presupuesto": pres, "irc5": irc5}
