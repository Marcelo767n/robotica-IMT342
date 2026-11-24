"""validation_cases.csv (esquema EXACTO del protocolo W12-S01), estados P5 / nivel de evidencia y manifiestos por experimento."""

import datetime
import platform

import numpy as np

from . import datos_irc5 as D, rutas, util
from . import metricas as M

COLUMNAS_PROTOCOLO = ["case_id", "case_type", "q_rad_vector", "base_frame", "tcp_frame", "model_version", "reference_version", "position_error_m",
                      "orientation_error_rad", "jacobian_error_fro", "rank_threshold", "rank_observed", "acceptance_result", "evidence_link", "notes"]
ESTADOS_P5 = ("verificado", "parcial", "fallido", "no ejecutado", "bloqueado por acceso")
EQUIPO = "Dayana Andrade, Mirko Ayala, Marcelo Navarro (IMT-342, UCB, 2-2026)"
OPERADOR = "por completar por el equipo"

ARCH_MODELO = ["hito2/irb120/dh.py", "hito2/irb120/pieper.py", "hito2/irb120/jacobian.py", "hito2/irb120/dynamics.py", "hito2/irb120/urdf_chain.py"]
ARCH_REF = ["hito2/irb120/rosi_model.py"]


def contexto():
    git = rutas.commit_git()
    import matplotlib, scipy
    sha = {a: rutas.sha256_archivo(rutas.RAIZ / a) for a in ARCH_MODELO + ARCH_REF}
    sha["hito2/datos/irb120.urdf"] = rutas.sha256_archivo(rutas.URDF)
    return {"git": git, "sha": sha, "py": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__, "matplotlib": matplotlib.__version__,
            "so": platform.platform(), "generado_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "proc": D.cargar_procedencia()}


def _ver_modelo(c):
    return f"hito2/irb120/dh.py sha256:{c['sha']['hito2/irb120/dh.py'][:12]} @ {c['git']['commit'][:10]}{'+hito3 sin versionar' if c['git']['hito3_sin_versionar'] else ''}"


def _ver_rosi(c):
    return f"hito2/irb120/rosi_model.py sha256:{c['sha']['hito2/irb120/rosi_model.py'][:12]} (ROS-Industrial abb_irb120_support kinetic-devel)"


def _ver_irc5(c, ses):
    a = c["proc"]["archivos"][ses]
    return f"IRC5 RWS http://192.168.125.1 (tool0/Base/wobj0) {a['archivo'].split('/')[-1]} sha256:{a['sha256'][:12]}"


def construir(res, ctx):
    """Devuelve (filas validation_cases, meta por caso). `meta` lleva nivel, estado, justificación y manifiesto."""
    fk, ik, jac, sing, tol, sint = res["fk"], res["ik"], res["jac"], res["sing"], res["tol"], res["sint"]
    filas, meta = [], {}
    commit = ctx["git"]["commit"][:10]

    def add(cid, tipo, q, base, tcp, mv, rv, ep, eR, eJ, rthr, robs, estado, evid, notas, nivel, just, extra=None):
        assert estado in ESTADOS_P5
        filas.append([cid, tipo, util.vec(q) if q is not None else "", base, tcp, mv, rv,
                      "" if ep is None else f"{ep:.6e}", "" if eR is None else f"{eR:.6e}", "" if eJ is None else f"{eJ:.6e}",
                      "" if rthr is None else f"{rthr:.6e}", "" if robs is None else robs, estado, evid, notas])
        meta[cid] = {"tipo": tipo, "nivel": nivel, "estado": estado, "justificacion": just, "q": q, "evidencia": evid, **(extra or {})}

    base_m, base_r = "base_link (modelo propio)", "Base del IRC5"
    # ---- FK reales (S1)
    for n, ses in (("N1", "S1"), ("N2", "S2")):
        r = fk[f"FK-{n}"]
        ses_k = ses
        add(f"FK-{n}", "FK nominal (real)", r["q_rad"], f"{base_m} = {base_r}", "tool0 (brida); sin TCP",
            _ver_modelo(ctx), _ver_irc5(ctx, ses_k), r["estadistica_e_p_m"]["max"], r["estadistica_e_R_rad"]["max"], None, None, None, "parcial",
            f"hito3/datos/fk_real_{n}_estacionarias.csv; hito3/resultados/fk_real_errores_por_muestra.csv; hito3/resultados/figuras/fk_real_errores_N1_N2.png",
            (f"n={r['n_muestras']} lecturas estacionarias (Δq<=1e-3°) de UNA postura; e_p mediana={r['estadistica_e_p_m']['mediana']:.2e} m, p95={r['estadistica_e_p_m']['p95']:.2e}, max={r['estadistica_e_p_m']['max']:.2e} (columna = max); "
             f"e_R(arccos) mediana={r['estadistica_e_R_rad']['mediana']:.2e} rad, max={r['estadistica_e_R_rad']['max']:.2e}; {r['n_dentro_criterio_estricto_proyecto']}/{r['n_muestras']} dentro del criterio estricto del proyecto (1e-6 m, 1e-6 rad; NO aprobado); "
             f"cota de cuantización de los datos e_p<={r['cuantizacion']['cota_e_p_m']:.1e} m, e_R<={r['cuantizacion']['cota_e_R_rad']:.1e} rad; "
             f"R^T R max={max(r['ortogonalidad_max_R_own'], r['ortogonalidad_max_R_ref']):.1e}, |det-1| max={max(r['det_dev_max_R_own'], r['det_dev_max_R_ref']):.1e}; cuaternión del IRC5 en orden (w,x,y,z)"),
            "S1", "Observación del controlador por RWS con unidad, fuente y marca temporal (S1). No es S2 (no trazada por ROS) ni S3. Parcial: umbral no aprobado; una sola postura por caso; J6 casi constante en ambas posturas; "
                  "TCP físico no medido (se usa la brida); %d lecturas FUERA sin causa demostrada." % res["fk"]["FUERA"]["n_fuera"])
        add(f"FK-{n}-S0", "FK nominal (offline, ref. independiente)", r["q_rad"], base_m, "tool0 (brida)", _ver_modelo(ctx), _ver_rosi(ctx),
            fk[f"FK-{n}-S0"]["e_p_m"], fk[f"FK-{n}-S0"]["e_R_atan2_rad"], None, None, None, "verificado",
            "hito3/resultados/fk_offline_propia_vs_rosi.csv",
            f"misma q de FK-{n}; e_R por atan2 (arccos da {fk[f'FK-{n}-S0']['e_R_rad']:.1e}, piso ~2.1e-8); FK de URDF del repositorio vs propia: e_p={fk[f'FK-{n}-S0']['e_p_urdf_m']:.1e} m (NO independiente: el URDF se generó de la tabla DH); verificación procedimental, umbral exploratorio pendiente",
            "S0", "Modelo vs modelo. rosi_model es independiente de la TABLA DH y del código propio, no de la geometría nominal ABB: no demuestra exactitud física.")
    g = fk["FK-N3"]
    add("FK-N3", "FK nominal (real, complementario 29/10)", np.deg2rad(g["q_deg"]), f"{base_m} = {base_r}", "tool0 (brida)", _ver_modelo(ctx),
        "FlexPendant Jogging Linear, Base/tool0/wobj0, foto transcrita (evidencia G2)", g["e_p_m"], g["e_R_rad"], None, None, None, "parcial",
        g["archivo"], f"una postura; resolución de pantalla 0.01 mm / 5 decimales; sin marca temporal simultánea q-pose; e_p={g['e_p_m']:.2e} m es del orden de la resolución de la pantalla ({g['cota_cuantizacion_e_p_m']:.1e} m); orden de cuaternión (w,x,y,z)",
        "S1", "Lectura de pantalla del controlador (S1 limitado): sin tiempo simultáneo ni registro automático; solo apoyo complementario.")
    lmax_p = max(c["e_p_m"] for c in fk["FK-L"]); lmax_R = max(c["e_R_atan2_rad"] for c in fk["FK-L"])
    add("FK-L", "FK cerca de límites (offline)", fk["FK-L"][0]["q_rad"], base_m, "tool0 (brida)", _ver_modelo(ctx), _ver_rosi(ctx), lmax_p, lmax_R, None, None, None, "verificado",
        "hito3/resultados/fk_offline_propia_vs_rosi.csv",
        f"4 posturas (1° dentro de límites superior/inferior/alternados y exactamente en el límite superior); límites ABB de dh.py vs xacro vs URDF difieren hasta {fk['limites']['max_dif_dh_rosi_rad']:.1e} rad; q_rad_vector = FK-L1",
        "S0", "Offline contra rosi_model; los límites son los documentados de la hoja ABB (dh.py), no leídos del controlador.")
    add("FK-L-REAL", "FK cerca de límites (real)", None, "-", "tool0", "-", "IRC5", None, None, None, None, None, "bloqueado por acceso", "-",
        "Requiere mover el robot cerca de límites con supervisor autorizado y límites de software del IRC5 leídos; NO-GO físico en W14-S02. Plan alternativo: FK-L offline.",
        "S1 (pendiente)", "Depende de permiso/hardware no disponibles.")
    t = fk["FK-D-TCP"]
    add("FK-D-TCP", "FK diagnóstico TCP", fk["FK-N1"]["q_rad"], base_m, "TCP z=0.150 m (propio) vs tool0 (IRC5): discrepancia INTENCIONAL", _ver_modelo(ctx), _ver_irc5(ctx, "S1"),
        t["estadistica_e_p_m"]["max"], t["estadistica_e_R_atan2_rad"]["max"], None, None, None, "verificado",
        "hito3/resultados/fk_d_tcp.csv; hito3/resultados/figuras/fk_d_tcp_d_ord.png",
        f"e_p mediana={t['estadistica_e_p_m']['mediana']:.6f} m ≈ d=0.150 m sobre el eje z6 (cos={t['barrido'][-2]['cos_angulo_con_z6']:.12f}); e_R sin cambio (traslación pura); con la misma herramienta en ambos lados e_p vuelve a {t['estadistica_e_p_corregido_m']['mediana']:.1e} m (mediana)",
        "S1", "Datos reales S1 + perturbación offline declarada: demuestra la sensibilidad a la herramienta y la regla de no comparar brida con TCP.")
    o = fk["FK-D-ORD"]["permutaciones"]
    add("FK-D-ORD", "FK diagnóstico orden articular", fk["FK-N2"]["q_rad"], base_m, "tool0 (brida)", _ver_modelo(ctx), _ver_irc5(ctx, "S2"),
        max(p["e_p_max_m"] for p in o), max(p["e_R_max_rad"] for p in o), None, None, None, "verificado", "hito3/resultados/fk_d_ord.csv; hito3/resultados/figuras/fk_d_tcp_d_ord.png",
        "; ".join(f"{p['permutacion']}: e_p mediana={p['e_p_mediana_m']:.3g} m" for p in o) + f"; corrección (permutación inversa): e_p max={max(p['e_p_corregido_max_m'] for p in o):.1e} m; grados leídos como rad: e_p mediana={fk['FK-D-ORD']['error_unidades_grados_como_rad_e_p_mediana_m']:.3g} m",
        "S1", "Datos reales S1 con permutación offline intencional; el error emerge y desaparece al invertir la permutación.")
    f = fk["FUERA"]
    add("FK-FUERA", "FK diagnóstico de muestras FUERA", None, base_m, "tool0 (brida)", _ver_modelo(ctx), "IRC5 RWS (S1), sesiones 1 y 2", f["estadistica_e_p_m"]["max"], f["estadistica_e_R_rad"]["max"], None, None, None, "parcial",
        "hito3/datos/fk_real_fuera.csv; hito3/resultados/fk_fuera_diagnostico.csv; hito3/resultados/figuras/fk_fuera_diagnostico.png",
        f"{f['n_fuera']} muestras FUERA (todas con Δq=0 y ventana<={f['estadistica_ventana_ms']['max']:.0f} ms): " + "; ".join(f"{k[:1]}={v}" for k, v in f["categorias"].items())
        + f"; fallan e_R>1e-6 rad: {f['n_falla_orientacion']}, e_p>1e-6 m: {f['n_falla_posicion']}. La pose del IRC5 fluctúa a q constante (Δq equivalente mediana {f['estadistica_dq_equivalente_deg']['mediana']:.1e}° ≫ semi-ulp float32): causa no determinable con estos datos.",
        "S1", "Clasificadas con el árbol del Bloque C; causa raíz indeterminada por datos (falta registro simultáneo y repetición controlada).")
    add("FK-INV", "FK diagnóstico lecturas inválidas", None, "-", "-", "-", "IRC5 RWS (S1), sesión 2", None, None, None, None, None, "parcial", "hito3/datos/fk_real_procedencia.json",
        f"{f['lecturas_invalidas_total']} lecturas LECTURA_INVALIDA, todas en la sesión 2 tras 2026-11-04T23:05:49Z (ConnectTimeout, ConnectionError, ReadTimeout): pérdida de enlace HTTP con el controlador; sin dato de q ni pose ⇒ no entran en ninguna métrica; causa de la pérdida de enlace no diagnosticada",
        "S1", "Sin datos que comparar; clasificadas por tipo de excepción.")
    add("FK-TCP-REAL", "FK con TCP físico", None, "-", "TCP real del IRC5", "-", "IRC5 (tooldata)", None, None, None, None, None, "bloqueado por acceso", "-",
        "El tooldata activo del IRC5 no se ha leído (tcp_verified_on_robot: false); el TCP de 0.150 m es convención del modelo. Requiere sesión con el robot (lectura RWS de solo lectura). Plan alternativo: FK-D-TCP offline.", "S1 (pendiente)", "Depende de acceso al controlador.")
    # ---- IK
    for pid, p in ik["poses"].items():
        validas = [b for b in p["ramas"] if b["estado"] == "válida en modelo"]
        reales = [b for b in p["ramas"] if b["real"]]
        wep = max([max(b["e_p_propia_m"], b["e_p_ref_m"]) for b in validas], default=None)
        weR = max([max(b["e_R_propia_rad"], b["e_R_ref_rad"]) for b in validas], default=None)
        rd = p["resumen_dls"]
        estado = "verificado"
        if p["tipo"] == "singular":
            estado = "parcial"
        cont = {k: sum(1 for b in p["ramas"] if b["estado"].startswith(k)) for k in ("válida", "no válida", "indeterminada", "numéricamente", "sin solución")}
        add(pid, f"IK ({p['tipo']})", p["q_doc_rad"], base_m, "tool0 (brida)", _ver_modelo(ctx) + " (pieper.py)", _ver_rosi(ctx) + " + DLS numérico",
            wep, weR, None, None, None, estado, "hito3/resultados/ik_ramas.csv; hito3/resultados/ik_dls_intentos.csv; hito3/resultados/figuras/ik_ramas_residuos.png",
            f"{p['fuente']}; 8 ramas: {cont['válida']} válidas, {cont['no válida']} no válidas, {cont['indeterminada']} indeterminadas por datos, {cont['numéricamente']} numéricamente singulares, {cont['sin solución']} inexistentes; "
            f"residuo = peor de FK propia y rosi sobre las válidas; DLS: {rd['n_convergidos']}/{rd['n_intentos']} convergidos, {rd['n_soluciones_distintas']} soluciones distintas, {rd['ramas_reales_halladas_por_DLS']}/{rd['ramas_propias_reales']} ramas reales halladas, {rd['n_sin_rama_propia']} sin rama propia"
            + (f"; ninguna convergió (mejor residuo {rd['mejor_residuo_sin_convergencia']:.3f} m): 'no encontrada' numérica, 'inexistente' por |cos θ3|>1" if p['tipo'] == "inalcanzable" else "")
            + ("; q4 y q6 solo determinados en suma (familia continua): DLS halló %d (q4,q6) distintos con la misma suma" % rd["n_familia_singular_q4_distintos"] if p["tipo"] == "singular" else ""),
            "S0", "IK propia vs FK propia/independiente y DLS independiente; offline.", {"pose": pid})
    add("IK-REAL", "IK con movimiento físico", None, "-", "-", "-", "IRC5", None, None, None, None, None, "bloqueado por acceso", "-",
        "Ejecutar una solución IK en el robot (cadena ROS→IRC5→movimiento, nivel S3) requiere GO firmado y supervisor; no verificado.", "S3 (no alcanzado)", "NO-GO físico; plan alternativo: IK offline (IK-1..IK-5).")
    add("S3-MOV", "Movimiento ROS→IRC5 (Gate 3)", None, "-", "-", "-", "IRC5", None, None, None, None, None, "parcial", "hito3/docs/evidencia_gate3_movimiento.md",
        "Sesiones 16–19/11: 265 órdenes PC→IRC5 (RWS + LabJointRws) registradas, 264 con aceptación (código 2) y q de llegada leída del "
        "controlador (error máx. 0,186°). Falta para 'verificado': autorización GO firmada en archivo y registro independiente del "
        "movimiento observado (video/operador); la orden 59 del 18/11 no tiene resultado.",
        "S3 técnico (registrado); S3 autorizado no acreditado",
        "Ver hito3/docs/evidencia_gate3_movimiento.md y gate3_ordenes.csv; firmar checklist_seguridad.md en la próxima sesión.")
    # ---- Jacobiano
    por_pose = {}
    for c in jac["casos"]:
        por_pose.setdefault(c["id"], {})[c["punto"]] = c
    for pid, d in por_pose.items():
        c, c0 = d["tcp"], d["tool0"]
        rn = M.rango_numerico(c["J_own"])
        add(pid, "Jacobiano (offline, ref. independiente)", c["q_rad"], base_m, "TCP z=0.150 m (y tool0 en notes)", _ver_modelo(ctx) + " (jacobian.py)", _ver_rosi(ctx) + " + FD central",
            None, None, c["eJv_h"], rn["tau_num"], rn["rango"], "verificado", "hito3/resultados/jacobiano_errores.csv; hito3/resultados/figuras/jacobiano_errores_separados.png",
            f"jacobian_error_fro = eJv [m/rad] (TCP) con h={jac['h_usado']:.0e}; eJω={c['eJw_h']:.2e} rad/rad; tool0: eJv={c0['eJv_h']:.2e}, eJω={c0['eJw_h']:.2e}; con h=1e-6: eJv={c['eJv_1e6']:.2e}, eJω={c['eJw_1e6']:.2e}; "
            f"q̇ declarado {util.vec(jac['qd_test_rad_s'], 3)} rad/s: ‖Jq̇−FD‖ lineal={c['e_v_own_vs_fd_m_s']:.1e} m/s, angular={c['e_w_own_vs_fd_rad_s']:.1e} rad/s; métricas Jv y Jω separadas (sin norma mezclada)",
            "S0", "J propio vs diferenciación numérica de la FK independiente; dominado por el error de FD, no por el J.")
    cv = jac["curva"]
    add("J-FD", "Jacobiano curva h→E(h)", cv["q_rad"], base_m, "TCP z=0.150 m", _ver_modelo(ctx), _ver_rosi(ctx) + " + FD central", None, None, cv["E_min"], None, None, "verificado",
        "hito3/resultados/jacobiano_fd_curva.csv; hito3/resultados/figuras/jacobiano_fd_curva_visual4.png",
        f"h=1e-1..1e-10; mínimo estable h*={cv['h_min']:.0e} (E_min={cv['E_min']:.1e} m/rad; h teórico ∛ε={cv['h_teorico_cbrt_eps']:.1e}); pendiente de truncamiento {cv['pendiente_truncamiento']:.2f} (≈2), de redondeo {cv['pendiente_redondeo']:.2f} (≈−1)",
        "S0", "Caracterización numérica de la referencia por FD (autoconvergencia).")
    add("J-REAL", "Jacobiano vs controlador", None, "-", "-", "-", "IRC5", None, None, None, None, None, "bloqueado por acceso", "-",
        "El IRC5 no entrega J; validarlo exigiría velocidades cartesianas medidas con movimiento autorizado. Plan alternativo: referencia FD sobre FK que sí coincide con el IRC5 (FK-N1/N2).", "S1/S3 (no alcanzado)", "Depende de hardware y GO.")
    # ---- Singularidad
    for c in sing["casos"]:
        add(c["id"], f"Singularidad ({c['tipo']})", c["q_rad"], base_m, "TCP z=0.150 m", _ver_modelo(ctx) + " (jacobian.py)", "SVD sobre J_s=[Jv/L;Jω], L=%.2f m" % c["L"],
            None, None, None, c["tau_num_Js"], c["rango_Js"], "verificado", "hito3/resultados/singularidad_svd.csv; hito3/resultados/singularidad_sigma.csv; hito3/resultados/figuras/singularidad_svd_tau.png",
            f"{c['descripcion']}; rank_num(J)={c['rango_J']}, rank_num(J_s)={c['rango_Js']}; κ(J_s)={c['kappa_Js']:.3g}, σmin/σmax={c['ratio_sigma']:.2e}, σmin(J_s)={c['sigma_min_Js']:.2e}; κ(J mixto, no interpretable)={c['kappa_J_mixto']:.2g}; "
            f"dirección perdida dominante {c['dir_perdida_dominante']} (cos con predicción geométrica={c['cos_dir_perdida_vs_analitica']}); 1/σmin={c['amplificacion_qdot_dir_min']:.3g}; ‖Jᵀ F‖ (10 N)={c['norma_tau_ext_peso']:.2f} N·m vs ‖τ_act‖={c['norma_tau_act']:.2f} N·m",
            "S0", "Análisis algebraico del modelo; sin datos físicos.")
    add("F-TAU", "Esfuerzo estático vs dinámica", None, base_m, "TCP z=0.150 m", _ver_modelo(ctx) + " (dynamics.py)", "definición J^T F vs M q̈ + C q̇ + g", None, None, None, None, None, "verificado",
        "hito3/resultados/singularidad_svd.csv; hito3/resultados/singularidad_barrido_q5.csv",
        "τ_ext=Jᵀ F es finito en todas las posturas (incl. rango 5 y 4) y distinto de τ_act dinámico; el wrench en la dirección perdida da ‖Jᵀ F‖≈σmin‖F‖≈0 (lo soporta la estructura); inercias del modelo son datos del artículo (no medidas en este robot)",
        "S0", "Demostración algebraica sobre el modelo propio.")
    # ---- métricas, tolerancias
    add("MET-SINT", "Verificación del código de métricas", None, "-", "-", "hito3/validacion/metricas.py", "ejemplos 1-3 del documento W14-S02", None, None, None, None, None, "verificado" if sint["todas_ok"] else "fallido",
        "hito3/resultados/verificacion_metricas_sinteticas.csv", f"{sint['n']} comprobaciones (2R, e_R=π/18, rango 1, clip, log, cuaternión)", "S0", "Valores esperados del documento.")
    p = tol["presupuesto"]
    add("TOL-OFF", "Presupuesto de tolerancia offline", None, "-", "-", _ver_modelo(ctx), _ver_rosi(ctx), p["observado_max_e_p_m"], p["observado_max_e_R_atan2_rad"], None, None, None, "parcial",
        "hito3/resultados/tolerancias_presupuesto.csv",
        f"τ_p=K ε L N_ops={p['tau_p_m']:.2e} m, τ_R={p['tau_R_rad']:.2e} rad (K={p['K']:.0f}, N_ops={p['N_ops']}, L={p['L_ref_m']:.3f} m declarados; el error observado es menor); cribado exploratorio sintético del documento 1e-6 m / 1e-5 rad; ESTADO: pendiente de aprobación docente",
        "S0", "Presupuesto numérico declarado, sin aprobación; K y N_ops son estimaciones.")
    add("TOL-IRC5", "Incertidumbres FK vs IRC5", None, "-", "-", "-", "IRC5 RWS (S1)", None, None, None, None, None, "parcial", "hito3/resultados/tolerancias_incertidumbres_irc5.csv",
        "Se listan y acotan resolución de xyz, cuaternión y q, ventana temporal y fluctuación observada; TCP y calibración de base sin medir. Sin umbral aprobado: pendiente y bloqueada por datos.", "S1", "No se inventa ninguna tolerancia física.")
    return filas, meta


def escribir(filas, meta):
    util.escribir_csv(rutas.RESULTADOS / "validation_cases.csv", COLUMNAS_PROTOCOLO, filas)
    util.escribir_csv(rutas.RESULTADOS / "casos_estado_evidencia.csv", ["case_id", "tipo", "nivel_evidencia", "estado_P5", "justificacion"],
                      [[k, v["tipo"], v["nivel"], v["estado"], v["justificacion"]] for k, v in meta.items()])


# ------------------------------------------------------------------------------------------------ manifiestos
def manifiesto(cid, m, fila, ctx):
    proc = ctx["proc"]
    es_real = m["nivel"].startswith("S1") and cid.startswith(("FK-N1", "FK-N2", "FK-N3", "FK-D", "FK-F", "FK-I")) and not cid.endswith("S0")
    ses = "S2" if cid in ("FK-N2", "FK-D-ORD") else "S1"
    datos = {"origen": "archivo offline del repositorio (sin acceso al robot en esta ejecución)", "endpoint_variable": None, "archivos": []}
    if es_real and cid in ("FK-N1", "FK-N2", "FK-D-TCP", "FK-D-ORD"):
        n = "N2" if cid in ("FK-N2", "FK-D-ORD") else "N1"
        a = proc["archivos"][ses]
        datos = {"origen": "IRC5 vía RWS (HTTP), capturado el 2026-11-04 por el nodo validacion_fk; solo lectura",
                 "endpoint_variable": "RWS rapid/robtarget y jointtarget (tool0, wobj0, Base) vía http://192.168.125.1",
                 "archivos": [{"subconjunto": f"hito3/datos/fk_real_{n}_estacionarias.csv", "sha256": rutas.sha256_archivo(rutas.DATOS / f"fk_real_{n}_estacionarias.csv"),
                               "filas": proc[f"n_filas_{n}"], "crudo": a["archivo"], "crudo_sha256": a["sha256"], "crudo_lineas": a["lineas"], "crudo_en": "checkout principal (solo lectura)"}]}
    elif cid in ("FK-FUERA", "FK-INV"):
        datos = {"origen": "IRC5 vía RWS (HTTP), sesiones 1 y 2 del 2026-11-04", "endpoint_variable": "igual que FK-N1",
                 "archivos": [{"subconjunto": "hito3/datos/fk_real_fuera.csv", "sha256": rutas.sha256_archivo(rutas.DATOS / "fk_real_fuera.csv"), "filas": proc["n_fuera_total"]},
                              {"resumen": "hito3/datos/fk_real_procedencia.json", "sha256": rutas.sha256_archivo(rutas.DATOS / "fk_real_procedencia.json")}]}
    elif cid == "FK-N3":
        datos = {"origen": "FlexPendant (pantalla Jogging, Linear) transcrita de foto; q por RWS", "endpoint_variable": None,
                 "archivos": [{"archivo": "docs/conexion_abb/evidencias/g2_fk_vs_controlador_pose1_2026-10-29.json", "sha256": rutas.sha256_archivo(rutas.EVIDENCIAS / "g2_fk_vs_controlador_pose1_2026-10-29.json")}]}
    tiempo = {"reloj": "PC de adquisición (UTC) + 'stamp' ROS; el IRC5 no entrega marca propia", "timestamp_q": "q_before y q_after (RWS), dos lecturas consecutivas",
              "timestamp_pose": "received_at_utc de cada muestra (pose entre las dos lecturas de q)", "latencia": "window_ms 11-54 ms (ver FK-N1/N2)",
              "estado_robot": "estacionario (Δq <= 1e-3 °)"} if es_real else {"reloj": "no aplica (offline)", "timestamp_q": None, "timestamp_pose": None, "latencia": None, "estado_robot": "no aplica"}
    nivel = m["nivel"]
    man = {
        "id_prueba": cid, "equipo": EQUIPO, "operador": OPERADOR, "generado_utc": ctx["generado_utc"], "tipo": m["tipo"],
        "codigo_modelo": {"repositorio": "robotica-IMT342 (rama claude/proyecto-hito3-4-objetivos-9709f0)", "commit": ctx["git"]["commit"],
                          "hito3_sin_versionar": ctx["git"]["hito3_sin_versionar"],
                          "modelo_propio": {"archivos": {a: ctx["sha"][a] for a in ARCH_MODELO}, "parametros_DH": "hito2/irb120/dh.py (Bahani et al. 2023, tabla I): d=[0.290,0,0,0.302,0,0.072] a=[0,0.270,0.070,0,0,0] alpha=[-90,0,-90,90,-90,0]°, offsets θ2=-90°, θ6=+180°",
                                            "tcp_z_m": 0.150},
                          "referencia_codigo": {a: ctx["sha"][a] for a in ARCH_REF},
                          "urdf": {"archivo": "hito2/datos/irb120.urdf", "sha256": ctx["sha"]["hito2/datos/irb120.urdf"], "uso": "solo comprobación de implementación (no independiente: generado de la tabla DH)"},
                          "software": {"python": ctx["py"], "numpy": ctx["numpy"], "scipy": ctx["scipy"], "matplotlib": ctx["matplotlib"], "so": ctx["so"]}},
        "juntas": {"nombres": [f"joint_{i}" for i in range(1, 7)], "joint_order": [f"joint_{i}" for i in range(1, 7)], "tipos": ["revolute"] * 6,
                   "q_rad": (m["q"].tolist() if m["q"] is not None and hasattr(m["q"], "tolist") else None),
                   "signos": "positivos según ABB (eje 1..6); coincidencia empírica con el IRC5 en las posturas de FK-N1/N2",
                   "offsets": "los de dh.py (θ2 −90°, θ6 +180°) internos al modelo; cero mecánico ABB = q=0", "cero_mecanico": "calibración de fábrica del robot no consultada"},
        "unidades": {"angulos": "rad (los datos del IRC5 llegan en grados y se convierten)", "longitudes": "m (los datos del IRC5 llegan en mm)", "velocidad": "rad/s", "cuaternion": "(w, x, y, z)"},
        "frames": {"base_propia": "base_link", "base_referencia": "Base del IRC5 (coordinate=Base)" if es_real else "base_link de rosi_model", "world": "no usado (wobj0)",
                   "flange": "tool0", "tool": "tool0" if "TCP" not in fila[4] else fila[4], "tcp": fila[4]},
        "herramienta": {"activo_en_irc5": "tool0 (brida), wobj0" if es_real else "no aplica", "pose_relativa": "identidad (tool0) / Tz(0.150) solo en FK-D-TCP y Jacobiano-TCP",
                        "fuente": "IRC5 (tool0 por definición) / convención del modelo (0.150 m); tooldata real NO leído"},
        "datos": datos, "tiempo": tiempo,
        "referencia": {"descripcion": fila[6], "independencia": ("IRC5 físico: independiente del modelo" if es_real else "rosi_model/DLS/FD: independiente de la tabla DH y del código propio; comparte geometría nominal ABB"),
                       "limitaciones": "ver notes de validation_cases.csv"},
        "seguridad": {"condicion": "offline; sin movimiento del robot; lectura RWS pasiva en los datos S1", "go_firmado": None, "nivel_alcanzado": nivel,
                      "nota": "NO-GO físico en W14-S02; S3 (movimiento ROS→IRC5) no verificado"},
        "tolerancias": {"version_criterio": "W14-S02 (propuesta normativa)", "umbral_propuesto": "estricto del proyecto 1e-6 m / 1e-6 rad (IRC5) y cribado sintético 1e-6 m / 1e-5 rad (offline)",
                        "umbral_aprobado": None, "incertidumbre": "ver tolerancias_incertidumbres_irc5.csv", "estado": "pendiente de aprobación"},
        "nivel_evidencia": nivel, "estado_P5": m["estado"], "justificacion_estado": m["justificacion"],
        "validation_cases_row": dict(zip(COLUMNAS_PROTOCOLO, fila)),
    }
    return man


def escribir_manifiestos(filas, meta, ctx):
    rutas.MANIFIESTOS.mkdir(parents=True, exist_ok=True)
    for f in rutas.MANIFIESTOS.glob("*.yaml"):
        f.unlink()
    for fila in filas:
        cid = fila[0]
        man = manifiesto(cid, meta[cid], fila, ctx)
        (rutas.MANIFIESTOS / f"{cid}.yaml").write_text("# Manifiesto por experimento (Bloque B, W14-S02). Generado por hito3.validacion.\n" + util.a_yaml(man) + "\n", encoding="utf-8")
    return len(filas)
