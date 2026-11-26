"""Plantillas P1-P5 del documento W14-S02 como CSV y fragmentos LaTeX (booktabs) para el informe."""

import numpy as np

from . import datos_irc5 as D, metricas as M, rutas, util
from . import fk as FK
from .util import mat, num, tex, vectex
from irb120.dh import TCP_Z_M, forward_kinematics, tcp_transform  # noqa: E402

GRUPO = "IMT-342 Andrade-Ayala-Navarro"


def _q(v):
    return vectex(v, 4)


def _q_partido(v):
    """q en dos líneas de tres ejes (cabe en una columna estrecha de la tabla P1a)."""
    partes = vectex(v, 4).split(r",\,")
    if len(partes) != 6:
        return vectex(v, 4)
    return r",\,".join(partes[:3]) + r",$\newline$" + r",\,".join(partes[3:])


def _ruta_partida(texto):
    """Nombre de archivo en monoespaciado que puede cortar línea tras «_» y «/»."""
    t = tex(texto)
    return r"\texttt{" + t.replace(r"\_", r"\_\allowbreak{}").replace("/", r"/\allowbreak{}") + "}"


def _fmt_p(v):
    return vectex(v, 6)


def p1(res, meta, ctx):
    fk = res["fk"]
    cm = f"dh.py@{ctx['git']['commit'][:7]}"
    filas = []

    def fila(cid, q, fecha, bt, ref, p_own, p_ref, q_own, q_ref, ep, eR, tol, evid):
        filas.append({"ID": cid, "Grp": GRUPO, "Mod/Commit": cm, "q_rad": q, "Fecha/t": fecha, "Base->TCP": bt, "Ref/Src": ref, "p_own_m": p_own, "p_ref_m": p_ref,
                      "R_own_quat_wxyz": q_own, "R_ref_quat_wxyz": q_ref, "e_p_m": ep, "e_R_rad": eR, "Tol": tol, "Decision": (meta.get(cid) or meta["FK-L"])["estado"], "Evidencia": evid})
    tol_irc5 = "estricto proyecto 1e-6 m/1e-6 rad (no aprobado)"
    tol_off = f"τp={res['tol']['presupuesto']['tau_p_m']:.1e} m; τR={res['tol']['presupuesto']['tau_R_rad']:.1e} rad (pendiente)"
    for n in ("N1", "N2"):
        r = fk[f"FK-{n}"]
        fila(f"FK-{n}", r["q_rad"], f"{r['t_representativa_utc']} (n={r['n_muestras']})", "base_link=Base -> tool0", "IRC5 RWS (S1)", r["p_own_m"], r["p_ref_m"],
             r["quat_own_wxyz"], M.R_a_cuaternion_wxyz(r["R_ref"]), r["e_p_m_rep"], r["e_R_rad_rep"], tol_irc5, meta[f"FK-{n}"]["evidencia"].split(";")[0])
        s0 = fk[f"FK-{n}-S0"]
        fila(f"FK-{n}-S0", s0["q_rad"], "offline", "base_link -> tool0", "rosi_model (S0)", s0["p_own_m"], s0["p_ref_m"], M.R_a_cuaternion_wxyz(s0["R_own"]), M.R_a_cuaternion_wxyz(s0["R_ref"]),
             s0["e_p_m"], s0["e_R_atan2_rad"], tol_off, "fk_offline_propia_vs_rosi.csv")
    g = fk["FK-N3"]
    fila("FK-N3", np.deg2rad(g["q_deg"]), "2026-10-29 (foto FlexPendant)", "base_link=Base -> tool0", "FlexPendant (S1 limitado)", g["p_own_m"], g["p_ref_m"], M.R_a_cuaternion_wxyz(g["R_own"]),
         M.R_a_cuaternion_wxyz(g["R_ref"]), g["e_p_m"], g["e_R_rad"], "resolución de pantalla 0.01 mm", g["archivo"].split("/")[-1])
    for c in fk["FK-L"]:
        fila(c["caso"].split(" ")[0], c["q_rad"], "offline: " + c["caso"].split("(")[1].rstrip(")"), "base_link -> tool0", "rosi_model (S0)", c["p_own_m"], c["p_ref_m"], M.R_a_cuaternion_wxyz(c["R_own"]),
             M.R_a_cuaternion_wxyz(c["R_ref"]), c["e_p_m"], c["e_R_atan2_rad"], tol_off, "fk_offline_propia_vs_rosi.csv")
    # FK-D-TCP: muestra representativa de N1
    r1 = fk["FK-N1"]
    T_tcp = forward_kinematics(r1["q_rad"]) @ tcp_transform(TCP_Z_M)
    e = M.error_pose(T_tcp, np.block([[r1["R_ref"], r1["p_ref_m"][:, None]], [np.zeros((1, 3)), np.ones((1, 1))]]))
    fila("FK-D-TCP", r1["q_rad"], "N1 (datos S1) + TCP simulado", "base_link -> TCP 0.150 m (propio) vs tool0 (IRC5)", "IRC5 RWS (S1), discrepancia intencional", T_tcp[:3, 3], r1["p_ref_m"],
         M.R_a_cuaternion_wxyz(T_tcp[:3, :3]), M.R_a_cuaternion_wxyz(r1["R_ref"]), e["e_p_m"], e["e_R_atan2_rad"], "esperado e_p = 0.150 m", "fk_d_tcp.csv")
    r2 = fk["FK-N2"]
    perm = FK.PERMUTACIONES["intercambio q4<->q6"]
    T_perm = forward_kinematics(np.array(r2["q_rad"])[perm])
    e2 = M.error_pose(T_perm, np.block([[r2["R_ref"], r2["p_ref_m"][:, None]], [np.zeros((1, 3)), np.ones((1, 1))]]))
    fila("FK-D-ORD", np.array(r2["q_rad"])[perm], "N2 (datos S1) + permutación q4<->q6", "base_link -> tool0", "IRC5 RWS (S1), orden articular erróneo intencional", T_perm[:3, 3], r2["p_ref_m"],
         M.R_a_cuaternion_wxyz(T_perm[:3, :3]), M.R_a_cuaternion_wxyz(r2["R_ref"]), e2["e_p_m"], e2["e_R_atan2_rad"], "esperado error grande; corregible", "fk_d_ord.csv")
    cols = list(filas[0].keys())
    util.escribir_csv(rutas.RESULTADOS / "P1_fk.csv", cols, [[f[c] if not isinstance(f[c], np.ndarray) else list(f[c]) for c in cols] for f in filas])
    # LaTeX: P1a (identificación) y P1b (poses)
    ha = ["ID", "Mod/Commit", r"$\mathbf{q}$ [rad]", "Fecha/$t$", "Base$\\to$TCP", "Ref/Src", "Tol.", "Decisión", "Evidencia"]
    fa = [[tex(f["ID"]), tex(f["Mod/Commit"]), _q_partido(f["q_rad"]), tex(f["Fecha/t"]), tex(f["Base->TCP"]), tex(f["Ref/Src"]), tex(f["Tol"]), tex(f["Decision"]), _ruta_partida(f["Evidencia"])] for f in filas]
    # Columnas de ancho fijo con salto de línea (legible en apaisado) en lugar de encoger la tabla entera.
    col = lambda cm: r">{\raggedright\arraybackslash}p{%.1fcm}" % cm
    spec_p1a = "".join(col(c) for c in (1.6, 2.0, 3.8, 3.0, 2.2, 3.4, 2.8, 1.6, 4.2))
    util.escribir_tex("P1a_fk_identificacion.tex", util.tabla_latex(ha, fa, spec_p1a, caption="P1a. Casos de FK: identificación, procedencia y decisión. Cuaternión y rotación declaradas en orden $(w,x,y,z)$.", label="tab:P1a", largo=True,
                                                                  nota="Fecha/$t$: instante de la muestra representativa (modo de la postura). Grp: " + tex(GRUPO)))
    hb = ["ID", r"$p_{own}$ [m]", r"$p_{ref}$ [m]", r"$R_{own}$ ($w,x,y,z$)", r"$R_{ref}$ ($w,x,y,z$)", r"$e_p$ [m]", r"$e_R$ [rad]"]
    fb = [[tex(f["ID"]), _fmt_p(f["p_own_m"]), _fmt_p(f["p_ref_m"]), vectex(f["R_own_quat_wxyz"], 7), vectex(f["R_ref_quat_wxyz"], 7), num(f["e_p_m"]), num(f["e_R_rad"])] for f in filas]
    util.escribir_tex("P1b_fk_poses_errores.tex", util.tabla_latex(hb, fb, "lllllrr", caption="P1b. Poses y errores de FK (SI). $e_R$ por \\texttt{arccos} en los casos reales S1 de la tabla de estadística; aquí por atan2 en los S0.", label="tab:P1b", ajustar=True))
    # estadística de los casos reales
    he = ["Caso", "$n$", r"$e_p$ mediana", r"$e_p$ p95", r"$e_p$ máx.", r"$e_R$ med. (arccos)", r"$e_R$ máx. (arccos)", "cota cuant. $e_p$", "cota cuant. $e_R$", "dentro crit. estricto"]
    fe = []
    for n in ("N1", "N2"):
        r = fk[f"FK-{n}"]
        fe.append([f"FK-{n}", r["n_muestras"], num(r["estadistica_e_p_m"]["mediana"]), num(r["estadistica_e_p_m"]["p95"]), num(r["estadistica_e_p_m"]["max"]), num(r["estadistica_e_R_rad"]["mediana"]),
                   num(r["estadistica_e_R_rad"]["max"]), num(r["cuantizacion"]["cota_e_p_m"]), num(r["cuantizacion"]["cota_e_R_rad"]), f"{r['n_dentro_criterio_estricto_proyecto']}/{r['n_muestras']}"])
    util.escribir_tex("P1c_fk_estadistica_real.tex", util.tabla_latex(he, fe, "lrrrrrrrrr", caption="P1c. FK real S1: estadística sobre todas las lecturas estacionarias de cada postura. Criterio estricto del proyecto: $1\\times10^{-6}$ m y $1\\times10^{-6}$ rad (propuesto, no aprobado).", label="tab:P1c", ajustar=True))
    return cols


def p2(res, meta, ctx):
    ik = res["ik"]
    cm = f"Pieper@{ctx['git']['commit'][:7]}"
    filas, tex_filas, tex_meta = [], [], []
    for pid, p in ik["poses"].items():
        rd = p["resumen_dls"]
        d = ik["dls"]
        ref = f"DLS(rosi) λ={d['lambda']}, tol={d['tol_p_m']:.0e}, it≤{d['max_iter']}, t≤{d['timeout_s']}s"
        sem = f"{rd['n_intentos']} semillas (rng={d['rng_seed']})"
        tex_meta.append([tex(pid), tex(p["fuente"]), tex(cm), tex(ref), tex(sem), f"{rd['n_convergidos']}/{rd['n_intentos']}", f"{rd['ramas_reales_halladas_por_DLS']}/{rd['ramas_propias_reales']}", f"{rd['n_sin_rama_propia']}"])
        for b in p["ramas"]:
            lim = "sí" if b["dentro_limites"] else ("n/a" if not b["real"] else "no: " + ",".join(f"J{j}" for j in b["fuera_de_limites"]))
            filas.append([pid, p["fuente"], cm, ref, sem, b["rama"], f"{b['brazo']}/{b['codo']}/{b['muneca']}", b["q_rad"] if b["q_rad"] is not None else "", b["e_p_propia_m"], b["e_R_propia_rad"], b["e_p_ref_m"], b["e_R_ref_rad"],
                          lim + " | dh.py (hoja ABB)", b["estado"], "ik_ramas.csv"])
            if b["real"]:
                qs = _q(b["q_rad"]) if b["q_rad"] is not None else "n/d"
                res_own = f"{num(b['e_p_propia_m'], 2)} / {num(b['e_R_propia_rad'], 2)}"
                res_ref = f"{num(b['e_p_ref_m'], 2)} / {num(b['e_R_ref_rad'], 2)}"
            else:
                qs, res_own, res_ref = "n/d", "n/d", "n/d"
            tex_filas.append([tex(pid), b["rama"], tex(f"{b['brazo'][:3]}/{b['codo'][:3]}/{b['muneca']}"), qs, res_own, res_ref, tex(lim), "sí" if b["encontrada_por_DLS"] else "no", tex(b["estado"])])
    util.escribir_csv(rutas.RESULTADOS / "P2_ik.csv", ["ID_pose", "Td_fuente", "metodo_propio", "metodo_ref", "semilla", "rama", "config", "q_rad", "e_p_propia_m", "e_R_propia_rad", "e_p_ref_m", "e_R_ref_rad", "limites_fuente", "estado_solucion", "evidencia"], filas)
    util.escribir_tex("P2a_ik_poses.tex", util.tabla_latex(["ID pose", r"$T_d$ / fuente", "Método propio", "Método ref.", "Semilla", "DLS conv.", "Ramas halladas", "DLS sin rama"], tex_meta, "llllllll",
                                                           caption="P2a. Poses objetivo de IK y métodos (propio: Pieper por \\texttt{atan2}; referencia: DLS numérico sobre la FK de ROS-Industrial).", label="tab:P2a", ajustar=True))
    util.escribir_tex("P2b_ik_ramas.tex", util.tabla_latex(["ID pose", "Rama $k$", "Config.", r"$\mathbf{q}^{(k)}$ [rad]", r"$e_p/e_R$ FK propia [m/rad]", r"$e_p/e_R$ FK ref. [m/rad]", "Límites", "DLS", "Estado de la solución"], tex_filas,
                                                           "lcllllllp{5.2cm}", caption="P2b. Las 8 ramas de Pieper por pose: residuos por FK propia y por FK independiente, límites y clasificación.", label="tab:P2b", largo=True,
                                                           nota="Límites: de la hoja ABB (\\texttt{dh.py}); xacro y URDF difieren hasta $3.3\\times10^{-6}$ rad. Cribado exploratorio: $e_p\\le10^{-6}$ m, $e_R\\le10^{-5}$ rad (pendiente de aprobación)."))


def p3(res, meta, ctx):
    jac = res["jac"]
    d = rutas.RESULTADOS / "jacobianos"
    d.mkdir(parents=True, exist_ok=True)
    filas, tf = [], []
    for c in jac["casos"]:
        nombre = f"{c['id']}_{c['punto']}"
        util.escribir_csv(d / f"{nombre}_propio.csv", [f"dq{i}" for i in range(1, 7)], c["J_own"].tolist())
        util.escribir_csv(d / f"{nombre}_ref_fd.csv", [f"dq{i}" for i in range(1, 7)], c["J_ref"].tolist())
        marco = f"{{B}}; punto {'TCP z=0.150 m' if c['punto'] == 'tcp' else 'tool0'}; twist [v;ω] (v arriba)"
        filas.append([c["id"] + "-" + c["punto"], util.vec(c["q_rad"]), marco, f"jacobianos/{nombre}_propio.csv", f"jacobianos/{nombre}_ref_fd.csv", c["eJv_h"], c["eJw_h"], util.vec(jac["qd_test_rad_s"], 3),
                      util.vec(c["V_own"]), f"h*={jac['h_usado']:.0e}: ver jacobiano_fd_curva.csv", meta[c["id"]]["estado"], "jacobiano_errores.csv"])
        tf.append([tex(c["id"] + "-" + c["punto"]), _q(c["q_rad"]), tex(f"B; {'TCP' if c['punto'] == 'tcp' else 'tool0'}; [v;w]"), num(c["eJv_h"], 2), num(c["eJw_h"], 2), num(c["e_v_own_vs_fd_m_s"], 2) + " / " + num(c["e_w_own_vs_fd_rad_s"], 2),
                   vectex(c["V_own"], 3), tex(meta[c["id"]]["estado"])])
    util.escribir_csv(rutas.RESULTADOS / "P3_jacobiano.csv", ["ID", "q_rad", "frame_TCP_twist", "J_own_archivo", "J_ref_archivo", "eJv_m_rad", "eJw_rad_rad", "qdot_test_rad_s", "J_qdot_m_s_rad_s", "h_error_FD", "decision", "evidencia"], filas)
    util.escribir_tex("P3a_jacobiano.tex", util.tabla_latex(["ID", r"$\mathbf{q}$ [rad]", "Frame/TCP/Twist", r"$e_{J_v}$ [m/rad]", r"$e_{J_\omega}$ [rad/rad]", r"$\lVert J\dot q-\mathrm{FD}\rVert$ lin./ang.", r"$J\dot{\mathbf{q}}$ [m/s, rad/s]", "Decisión"], tf, "llllllll",
                                                           caption=f"P3a. Jacobiano propio frente a referencia independiente (FD central sobre la FK de ROS-Industrial, $h={jac['h_usado']:.0e}$ rad). $\\dot{{q}}_{{test}}={util.vec(jac['qd_test_rad_s'], 3)}$ rad/s. Errores de $J_v$ y $J_\\omega$ por separado.", label="tab:P3a", ajustar=True))
    # curva E_i(h)
    import csv
    with open(rutas.RESULTADOS / "jacobiano_fd_curva.csv", newline="", encoding="utf-8") as fh:
        curva = [r for r in csv.DictReader(fh) if r["fk_referencia"] == "rosi"]
    hf = [[num(float(r["h_rad"]), 1), num(float(r["E_v_fro_m_rad"]), 3), num(float(r["E_w_fro_rad_rad"]), 3), *[num(float(r[f"E_col{i}_m_rad"]), 2) for i in range(1, 7)]] for r in curva]
    cv = jac["curva"]
    util.escribir_tex("P3b_jacobiano_fd_curva.tex", util.tabla_latex(["$h$ [rad]", r"$E_{J_v}$ [m/rad]", r"$E_{J_\omega}$ [rad/rad]", *[f"$E_{i}$" for i in range(1, 7)]], hf, "lrrrrrrrr",
                                                                     caption=f"P3b. Curva $h\\to E_i(h)$ en la postura de FK-N2 (TCP). Mínimo estable observado $h^*={cv['h_min']:.0e}$ rad; pendientes log-log {cv['pendiente_truncamiento']:.2f} (truncamiento) y {cv['pendiente_redondeo']:.2f} (redondeo).", label="tab:P3b", ajustar=True))


def p4(res, meta, ctx):
    sing = res["sing"]
    filas, tf = [], []
    for c in sing["casos"]:
        filas.append([c["id"], "twist completo 6D del TCP", f"J_s=[Jv/L;Jω], L={c['L']:.2f} m", 6, c["ratio_sigma"], f"{c['tau_num_Js']:.3e} (=max(m,n)·eps·σmax)", util.vec(c["q_rad"]), util.vec(c["dir_perdida_fisica"], 4),
                      f"1/σmin={c['amplificacion_qdot_dir_min']:.3g} rad/s por unidad de twist; vmax={c['twist_max_dir_min_escalado']:.2e}", "sí (‖JᵀF‖=%.3g N·m vs ‖τ_act‖=%.3g N·m)" % (c["norma_tau_ext_peso"], c["norma_tau_act"]), "singularidad_svd.csv"])
        tf.append([tex(c["id"]), tex("6D TCP"), f"$L={c['L']:.2f}$ m", f"{c['rango_Js']}/6", num(c["ratio_sigma"], 2), num(c["tau_num_Js"], 2), _q(c["q_rad"]), vectex(c["dir_perdida_fisica"], 2),
                   num(c["amplificacion_qdot_dir_min"], 2), num(c["norma_tau_ext_peso"], 3) + " / " + num(c["norma_tau_act"], 3), num(c["kappa_Js"], 2)])
    util.escribir_csv(rutas.RESULTADOS / "P4_singularidad.csv", ["ID", "subespacio", "matriz_escala_L", "r_max", "sigma_min_sobre_max", "umbral_tau_num", "q_rad", "dir_perdida_[vx,vy,vz,wx,wy,wz]", "efecto_velocidad", "separacion_torque", "evidencia"], filas)
    util.escribir_tex("P4_singularidad.tex", util.tabla_latex(["ID", "Subespacio", "Escala", r"rango/$r_{\max}$", r"$\sigma_{\min}/\sigma_{\max}$", r"$\tau_{num}$", r"$\mathbf{q}$ [rad]", r"Dir. perdida $[v;\omega]$ (unit.)", r"$1/\sigma_{\min}$", r"$\lVert J^TF\rVert/\lVert\tau_{act}\rVert$ [N m]", r"$\kappa(J_s)$"], tf,
                                                          "llllllllllr", caption="P4. Análisis de singularidad (SVD de $J_s$). $\\tau_{num}=\\max(m,n)\\,\\epsilon\\,\\sigma_{\\max}$; $F$ = 10 N hacia abajo en el TCP; $\\tau_{act}=M\\ddot q+C\\dot q+g$ con $\\dot q,\\ddot q$ declarados. El $\\kappa$ de $J$ sin escalar mezcla unidades y no se interpreta.", label="tab:P4", ajustar=True))


def p5_y_otros(res, meta, ctx, filas_casos):
    nombres = {"verificado": 0, "parcial": 0, "fallido": 0, "no ejecutado": 0, "bloqueado por acceso": 0}
    tf = []
    for cid, m in meta.items():
        nombres[m["estado"]] += 1
        tf.append([tex(cid), tex(m["nivel"]), tex(m["estado"]), tex(m["justificacion"][:150] + ("…" if len(m["justificacion"]) > 150 else ""))])
    util.escribir_tex("P5_estados_por_caso.tex", util.tabla_latex(["Caso", "Nivel", "Estado P5", "Justificación (resumen)"], tf, "lllp{9cm}", caption="P5. Estado formal de decisión y nivel de evidencia por caso. «Verificado» = verificación procedimental (umbrales pendientes de aprobación docente).", label="tab:P5", largo=True))
    # FUERA
    f = res["fk"]["FUERA"]
    ff = [[tex(k), v] for k, v in f["categorias"].items()]
    ff.append([tex("Lecturas inválidas (ConnectTimeout/ConnectionError/ReadTimeout; sin datos q-pose)"), f["lecturas_invalidas_total"]])
    util.escribir_tex("FK_diagnostico_fuera.tex", util.tabla_latex(["Clasificación (árbol del Bloque C)", "Muestras"], ff, "p{11cm}r", caption=f"Diagnóstico de las {f['n_fuera']} muestras FUERA de las dos sesiones. Todas con $\\Delta q=0$ y ventana $\\le{f['estadistica_ventana_ms']['max']:.0f}$ ms. Mediana de $e_p$: {f['estadistica_e_p_m']['mediana']:.2e} m; máx. $e_R$: {f['estadistica_e_R_rad']['max']:.2e} rad.", label="tab:fuera"))
    # presupuesto e incertidumbres
    p = res["tol"]["presupuesto"]
    fp = [[num(s["K"], 2), num(s["tau_p_m"], 3), num(s["tau_R_rad"], 3)] for s in p["sensibilidad_K"]]
    util.escribir_tex("G_presupuesto_tolerancia.tex", util.tabla_latex(["$K$", r"$\tau_p=K\epsilon L N_{ops}$ [m]", r"$\tau_R=K\epsilon N_{ops}$ [rad]"], fp, "lrr",
                                                                       caption=f"Presupuesto numérico offline ($\\epsilon={p['eps_mach']:.3e}$, $N_{{ops}}={p['N_ops']}$, $L={p['L_ref_m']:.3f}$ m; $K=10$ declarado). Error máximo observado FK propia vs ROS-Industrial: $e_p={p['observado_max_e_p_m']:.2e}$ m, $e_R={p['observado_max_e_R_atan2_rad']:.2e}$ rad (atan2). Estado: pendiente de aprobación.", label="tab:G"))
    fi = [[tex(x["fuente"]), tex(x["valor"]), tex(x["origen"]), tex(x["estado"])] for x in res["tol"]["irc5"]["filas"]]
    util.escribir_tex("H_incertidumbres_irc5.tex", util.tabla_latex(["Fuente de incertidumbre", "Valor / cota", "Origen", "Estado"], fi, "p{3.6cm}p{6.2cm}p{3cm}p{2.6cm}",
                                                                    caption="Incertidumbres de la comparación FK propia vs IRC5. No existe umbral numérico aprobado: estado pendiente y bloqueado por datos.", label="tab:H", largo=True))
    # resumen de resultados
    return nombres
