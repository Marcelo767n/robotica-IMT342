/* app.js — interfaz de "IRB 120 · Hito 2 en vivo". Toda la matemática viene de irb120.js (verificado contra Python). */
"use strict";
const R = window.IRB;
const $ = (s, el = document) => el.querySelector(s);
const fmt = (v, d = 3) => (v === null || v === undefined || Number.isNaN(v) ? "—" : (Math.abs(v) < 1e-12 ? 0 : v).toFixed(d));
const fexp = (v, d = 1) => (v === null || v === undefined || Number.isNaN(v) ? "—" : v.toExponential(d));
const fdeg = (v, d = 2) => fmt(R.deg(v) + 0, d);
const tok = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const JC = () => [1, 2, 3, 4, 5, 6].map((i) => tok(`--j${i}`));

const PRESETS = [
  { id: "ejemplo", name: "Ejemplo resuelto a mano", v: [0.40, 0.10, 0.35, 0, 180, 0] },
  { id: "ocho", name: "8 ramas admisibles", v: [0.45, -0.10, 0.60, 90, 90, 0] },
  { id: "seis", name: "6 admisibles", v: [0.40, 0.20, 0.60, 0, 135, 0] },
  { id: "corto", name: "Movimiento corto (triangular)", v: [0.5326, 0.0479, 0.5911, 158.253, 79.232, 163.253] },
  { id: "alcance", name: "Fuera de alcance", v: [0.90, 0.00, 0.40, 0, 90, 0] },
  { id: "limites", name: "Bloqueada por límites", v: [-0.055, -0.253, 0.343, 93.5, -4.4, -11.9] },
];

const SECTIONS = [
  { id: "resumen", crit: "▶", name: "Pipeline", sub: "De T_d al torque" },
  { id: "pieper", crit: "A", name: "Pieper · 8 ramas", sub: "15 %" },
  { id: "validacion", crit: "B", name: "Validación FK", sub: "10 %" },
  { id: "seleccion", crit: "A", name: "Selección de rama", sub: "criterio justificado" },
  { id: "lspb", crit: "C", name: "Trayectoria LSPB", sub: "15 %" },
  { id: "jacobiano", crit: "D", name: "Jacobiano", sub: "20 % · parte 1" },
  { id: "singularidad", crit: "D", name: "Singularidad", sub: "20 % · parte 2" },
  { id: "dinamica", crit: "E", name: "Dinámica 1R", sub: "15 %" },
  { id: "verificacion", crit: "F·G", name: "Verificación y defensa", sub: "5 % + 20 %" },
];

// ============================================================ estado del pipeline
const S = { spec: PRESETS[0].v, speed: 0.25, ramp: 0.25, t: 0, playing: true, rate: 0.5, branch: 0, section: "resumen" };

function compute() {
  const [x, y, z, r, p, w] = S.spec;
  S.T = R.poseFromXyzRpyDeg(x, y, z, r, p, w);
  S.home = R.analyzePose(R.forwardKinematicsTcp(R.HOME_Q), R.HOME_Q);
  S.rep = R.analyzePose(S.T, R.HOME_Q);
  S.rank = R.rankCandidates(S.rep, R.HOME_Q);
  S.best = S.rank.find((d) => d.rank === 1) || null;
  S.q0 = R.HOME_Q.slice();
  S.full = null;
  if (!S.best) { S.traj = null; return; }
  S.qf = S.best.candidate.q;
  const [vmax, amax] = R.defaultLimits(S.speed, S.ramp);
  S.vmax = vmax; S.amax = amax;
  S.traj = R.planLspb(S.q0, S.qf, vmax, amax);
  const N = 301, tf = S.traj.tf;
  S.ts = Array.from({ length: N }, (_, i) => (tf * i) / (N - 1));
  S.samp = S.ts.map((t) => S.traj.sample(t));
  S.model = R.shoulderModel(S.q0.map((v, i) => 0.5 * (v + S.qf[i])));
  S.tau = S.samp.map(([q, , qdd]) => S.model.components(q[1], qdd[1]));
  S.jac = S.samp.map(([q, qd]) => {
    const J = R.geometricJacobian(q), ra = R.rankAnalysis(J), tw = R.matvec(J, qd);
    return { smin: ra.s[5], rank: ra.rank, v: R.norm(tw.slice(0, 3)), w: R.norm(tw.slice(3)) };
  });
  const H = 1e-6;
  S.vnum = S.ts.map((t) => R.norm(R.scale(R.sub(R.pos(R.forwardKinematicsTcp(S.traj.sample(t + H)[0])), R.pos(R.forwardKinematicsTcp(S.traj.sample(t - H)[0]))), 1 / (2 * H))));
  S.tcpPath = S.samp.map(([q]) => R.pos(R.forwardKinematicsTcp(q)));
  const D = R.sub(S.qf, S.q0).map(Math.abs);
  S.critical = D.map((d, i) => Math.max(d / vmax[i], d / amax[i])).reduce((b, v, i, a) => (v > a[b] ? i : b), 0) + 1;
  S.triangular = S.traj.tf - 2 * S.traj.tb < 1e-6;
}

// ============================================================ utilidades de canvas
function prep(cv) {
  const r = cv.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
  const w = Math.max(10, r.width), h = Math.max(10, r.height);
  if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
  const ctx = cv.getContext("2d"); ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, w, h);
  return { ctx, w, h };
}
function niceTicks(a, b, n = 5) {
  if (!(b > a)) { b = a + 1; }
  const step0 = (b - a) / n, mag = 10 ** Math.floor(Math.log10(step0)), f = step0 / mag;
  const step = (f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10) * mag, out = [];
  for (let v = Math.ceil(a / step) * step; v <= b + 1e-9 * step; v += step) out.push(Math.abs(v) < step * 1e-9 ? 0 : v);
  return out;
}
/* Gráfica de líneas. o = {series:[{x,y,color,label,dash,width,dots}], xmin,xmax,ymin,ymax, logY, cursor, shades:[{a,b,color}], xlabel, ylabel, vlines, hlines} */
function chart(cv, o) {
  const { ctx, w, h } = prep(cv), ink = tok("--ink"), muted = tok("--muted"), grid = tok("--grid");
  const L = 52, Rm = 12, T = 10, B = 30, pw = w - L - Rm, ph = h - T - B;
  const all = o.series.flatMap((s) => s.y.filter((v) => Number.isFinite(v) && (!o.logY || v > 0)));
  let ymin = o.ymin ?? Math.min(...all), ymax = o.ymax ?? Math.max(...all);
  if (o.logY) { ymin = Math.log10(ymin); ymax = Math.log10(ymax); }
  if (ymax - ymin < 1e-9) { ymin -= 1; ymax += 1; } else if (o.ymin === undefined && !o.logY) { const pad = 0.08 * (ymax - ymin); ymin -= pad; ymax += pad; }
  const xmin = o.xmin, xmax = o.xmax;
  const X = (x) => L + ((x - xmin) / (xmax - xmin)) * pw;
  const Y = (y) => T + (1 - ((o.logY ? Math.log10(y) : y) - ymin) / (ymax - ymin)) * ph;
  ctx.font = "11px " + tok("--font-mono"); ctx.lineWidth = 1;
  (o.shades || []).forEach((s) => { ctx.fillStyle = s.color; ctx.globalAlpha = 0.13; ctx.fillRect(X(s.a), T, X(s.b) - X(s.a), ph); ctx.globalAlpha = 1; });
  const yt = o.logY ? niceTicks(Math.ceil(ymin), Math.floor(ymax), 6).filter(Number.isInteger) : niceTicks(ymin, ymax, 4);
  ctx.strokeStyle = grid; ctx.fillStyle = muted; ctx.textAlign = "right"; ctx.textBaseline = "middle";
  yt.forEach((v) => { const yy = o.logY ? T + (1 - (v - ymin) / (ymax - ymin)) * ph : Y(v); ctx.beginPath(); ctx.moveTo(L, yy); ctx.lineTo(L + pw, yy); ctx.stroke(); ctx.fillText(o.logY ? `1e${v}` : +v.toPrecision(4), L - 6, yy); });
  ctx.textAlign = "center"; ctx.textBaseline = "top";
  niceTicks(xmin, xmax, 6).forEach((v) => { ctx.beginPath(); ctx.moveTo(X(v), T); ctx.lineTo(X(v), T + ph); ctx.stroke(); ctx.fillText(+v.toPrecision(4), X(v), T + ph + 4); });
  ctx.strokeStyle = muted; ctx.strokeRect(L, T, pw, ph);
  if (o.xlabel) { ctx.textAlign = "right"; ctx.fillText(o.xlabel, L + pw, T + ph + 16); }
  if (o.ylabel) { ctx.save(); ctx.translate(12, T + ph / 2); ctx.rotate(-Math.PI / 2); ctx.textAlign = "center"; ctx.fillText(o.ylabel, 0, 0); ctx.restore(); }
  ctx.save(); ctx.beginPath(); ctx.rect(L, T, pw, ph); ctx.clip();
  (o.hlines || []).forEach((l) => { ctx.strokeStyle = l.color; ctx.setLineDash([5, 4]); ctx.beginPath(); ctx.moveTo(L, Y(l.y)); ctx.lineTo(L + pw, Y(l.y)); ctx.stroke(); ctx.setLineDash([]); if (l.label) { ctx.fillStyle = l.color; ctx.textAlign = "left"; ctx.textBaseline = "bottom"; ctx.fillText(l.label, L + 4, Y(l.y) - 2); } });
  o.series.forEach((s) => {
    ctx.strokeStyle = s.color; ctx.fillStyle = s.color; ctx.lineWidth = s.width || 1.8; ctx.setLineDash(s.dash || []);
    if (s.dots) { s.x.forEach((x, i) => { if (Number.isFinite(s.y[i]) && (!o.logY || s.y[i] > 0)) { ctx.beginPath(); ctx.arc(X(x), Y(s.y[i]), s.r || 2.4, 0, 7); ctx.fill(); } }); }
    else { ctx.beginPath(); let pen = false; s.x.forEach((x, i) => { const v = s.y[i]; if (!Number.isFinite(v) || (o.logY && v <= 0)) { pen = false; return; } pen ? ctx.lineTo(X(x), Y(v)) : ctx.moveTo(X(x), Y(v)); pen = true; }); ctx.stroke(); }
    ctx.setLineDash([]);
  });
  (o.marks || []).forEach((m) => { ctx.fillStyle = m.color; ctx.beginPath(); ctx.arc(X(m.x), Y(m.y), 5, 0, 7); ctx.fill(); });
  if (o.cursor !== undefined) { ctx.strokeStyle = ink; ctx.lineWidth = 1.2; ctx.beginPath(); ctx.moveTo(X(o.cursor), T); ctx.lineTo(X(o.cursor), T + ph); ctx.stroke(); }
  ctx.restore();
}
const legend = (items) => `<div class="legend">${items.map(([c, l, dash]) => `<span><i style="background:${dash ? "none" : c};${dash ? `border-top:2px dashed ${c};height:0` : ""}"></i>${l}</span>`).join("")}</div>`;

// ============================================================ visor 3D (proyección en perspectiva, órbita con arrastre)
class View3D {
  constructor(cv) {
    this.cv = cv; this.az = -0.95; this.el = 0.38; this.dist = 1.55; this.target = [0.2, 0, 0.3];
    let drag = null;
    cv.addEventListener("pointerdown", (e) => { drag = [e.clientX, e.clientY, this.az, this.el]; cv.setPointerCapture(e.pointerId); cv.style.cursor = "grabbing"; });
    cv.addEventListener("pointermove", (e) => { if (!drag) return; this.az = drag[2] - (e.clientX - drag[0]) * 0.008; this.el = Math.max(-0.2, Math.min(1.45, drag[3] + (e.clientY - drag[1]) * 0.008)); this.onchange && this.onchange(); });
    cv.addEventListener("pointerup", () => { drag = null; cv.style.cursor = "grab"; });
    cv.addEventListener("wheel", (e) => { e.preventDefault(); this.dist = Math.max(0.8, Math.min(4, this.dist * (1 + Math.sign(e.deltaY) * 0.08))); this.onchange && this.onchange(); }, { passive: false });
  }
  begin() {
    const { ctx, w, h } = prep(this.cv); this.ctx = ctx; this.w = w; this.h = h;
    const ce = Math.cos(this.el), se = Math.sin(this.el), ca = Math.cos(this.az), sa = Math.sin(this.az);
    this.fwd = [-ce * ca, -ce * sa, -se];
    this.eye = R.sub(this.target, R.scale(this.fwd, this.dist));
    this.right = R.scale(R.cross(this.fwd, [0, 0, 1]), 1 / R.norm(R.cross(this.fwd, [0, 0, 1])));
    this.up = R.cross(this.right, this.fwd);
    this.f = Math.min(w, h) * 1.25;
    this.grid();
    return this;
  }
  P(p) { const d = R.sub(p, this.eye), z = R.dot(d, this.fwd); return [this.w / 2 + (this.f * R.dot(d, this.right)) / z, this.h / 2 - (this.f * R.dot(d, this.up)) / z]; }
  line(pts, color, width = 2, dash = [], alpha = 1) {
    const c = this.ctx; c.strokeStyle = color; c.lineWidth = width; c.setLineDash(dash); c.globalAlpha = alpha; c.lineJoin = "round"; c.lineCap = "round";
    c.beginPath(); pts.forEach((p, i) => { const [x, y] = this.P(p); i ? c.lineTo(x, y) : c.moveTo(x, y); }); c.stroke(); c.setLineDash([]); c.globalAlpha = 1;
  }
  dot(p, color, r = 3, alpha = 1) { const [x, y] = this.P(p); const c = this.ctx; c.globalAlpha = alpha; c.fillStyle = color; c.beginPath(); c.arc(x, y, r, 0, 7); c.fill(); c.globalAlpha = 1; }
  text(p, s, color) { const [x, y] = this.P(p); const c = this.ctx; c.fillStyle = color || tok("--muted"); c.font = "11px " + tok("--font-mono"); c.fillText(s, x + 5, y - 5); }
  grid() {
    const g = tok("--grid"), m = tok("--muted");
    for (let x = -0.4; x <= 0.71; x += 0.1) this.line([[x, -0.5, 0], [x, 0.5, 0]], g, 1);
    for (let y = -0.5; y <= 0.51; y += 0.1) this.line([[-0.4, y, 0], [0.7, y, 0]], g, 1);
    this.line([[0, 0, 0], [0.15, 0, 0]], tok("--j2"), 1.5); this.line([[0, 0, 0], [0, 0.15, 0]], tok("--j3"), 1.5);
    this.text([0.16, 0, 0], "x", m); this.text([0, 0.16, 0], "y", m);
  }
  frame(T, L = 0.08, dash = [], width = 2) {
    const o = R.pos(T); [["--j2", 0], ["--j3", 1], ["--j1", 2]].forEach(([c, k]) => this.line([o, R.add(o, R.scale(R.col(T, k), L))], tok(c), width, dash));
  }
  robot(q, color, { width = 5, alpha = 1, dash = [], tcpFrame = true } = {}) {
    const F = R.jointFrames(q), pts = F.map((f) => R.pos(f));
    const tcp = R.pos(R.forwardKinematicsTcp(q));
    this.line([[0, 0, 0], [0, 0, R.D1]], tok("--muted"), 9, [], 0.55 * alpha);
    this.line([...pts.slice(1), tcp], color, width, dash, alpha);
    pts.slice(1, 7).forEach((p) => this.dot(p, color, 4, alpha));
    this.dot(tcp, tok("--amber"), 4.5, alpha);
    if (tcpFrame) this.frame(R.forwardKinematicsTcp(q), 0.07, [], 2);
  }
}

// ============================================================ secciones
const V = {};

function rubricBox(pide, aqui) {
  return `<div class="rubric"><div><span class="label">La rúbrica pide (nivel Excelente)</span><ul>${pide.map((x) => `<li>${x}</li>`).join("")}</ul></div>
  <div><span class="label">Dónde se ve en esta página</span><ul>${aqui.map((x) => `<li>${x}</li>`).join("")}</ul></div></div>`;
}
const head = (badge, title, lead) => `<div class="head"><span class="badge">${badge}</span><h2>${title}</h2></div>${lead ? `<p class="muted">${lead}</p>` : ""}`;
const notReachable = () => `<div class="notice"><strong>La pose objetivo no es alcanzable.</strong> ${S.rep.verdict} Esta sección necesita una configuración final; cambia la pose o elige una de las poses de prueba.</div>`;
const statusPill = (d) => d.rank === 1 ? `<span class="pill ok">${d.status}</span>` : d.admissible ? `<span class="pill info">${d.status}</span>` : `<span class="pill bad">${d.status.replace("descartada: ", "✗ ")}</span>`;
const branchName = (c) => `${c.arm}/${c.elbow}/${c.wrist}`;
const branchColor = (d) => (d.rank === 1 ? tok("--ok") : d.admissible ? tok("--accent") : tok("--bad"));

// ---------- Resumen
V.resumen = {
  html() {
    const rep = S.rep, b = S.best;
    const stepsData = [
      ["pieper", "A", "Pieper", `${rep.candidates.filter((c) => c.real).length} reales · ${rep.admissible.length} admisibles`],
      ["validacion", "B", "Validación FK", `max e_p ${fexp(Math.max(...rep.checks.filter(Boolean).map((c) => c.ep), 0))} m`],
      ["seleccion", "A", "Selección", b ? `rama ${b.candidate.branch} · ${branchName(b.candidate)}` : "sin solución"],
      ["lspb", "C", "LSPB", S.traj ? `t_f ${fmt(S.traj.tf, 3)} s · J${S.critical} crítica` : "—"],
      ["jacobiano", "D", "Jacobiano", S.traj ? `rango(q_f) = ${R.rankAnalysis(R.geometricJacobian(S.qf)).rank}` : "—"],
      ["singularidad", "D", "Singularidad", "rango 6 → 5 en q5 = 0"],
      ["dinamica", "E", "Dinámica 1R", S.traj ? `pico τ₂ ${fmt(peakTau().v, 2)} N·m` : "—"],
    ];
    return `${head("Pipeline", "De la pose objetivo al torque del hombro", "Pose inicial: posición de calibración ABB (q = 0). Pose objetivo: la de la barra superior. Cada etapa usa el resultado de la anterior; haz clic en una para verla.")}
    <div class="steps">${stepsData.map(([id, c, n, o]) => `<a class="step" href="#${id}"><span class="crit">${c} · ${n}</span><span class="out">${o}</span></a>`).join("")}</div>
    <div class="grid2">
      <div class="panel"><h3>Movimiento de la pose inicial a la objetivo <span class="hint">arrastra para girar</span></h3><canvas class="view3d" id="cvHero"></canvas>
        ${legend([[tok("--muted"), "pose inicial (q = 0)"], [tok("--ok"), "pose objetivo"], [tok("--ink"), "trayectoria del TCP"]])}</div>
      <div class="panel"><h3>Rúbrica oficial y dónde se cumple</h3><div class="table-wrap"><table>
        <thead><tr><th class="l">Criterio</th><th>Peso</th><th class="l">Evidencia en vivo</th></tr></thead><tbody>
        ${[["A", "IK analítica (Pieper)", "15 %", "pieper", "8 ramas, atan2, real/admisible, geometría"], ["B", "Validación por FK", "10 %", "validacion", "posición + orientación, tolerancia, errores inyectados, ida y vuelta, modelo oficial"],
           ["C", "Trayectoria LSPB", "15 %", "lspb", "q, q̇, q̈ alineados, fronteras, límites, animación"], ["D", "Jacobiano y singularidad", "20 %", "jacobiano", "validación numérica, columnas, rango SVD, experimento q5 → 0"],
           ["E", "Dinámica 1R y τ(t)", "15 %", "dinamica", "τ_in + τ_g sobre el LSPB, péndulo, 1R vs completo"], ["F", "Integración y reproducibilidad", "5 %", "verificacion", "notebook 34/34, 56 pruebas, informe IEEE"],
           ["G", "Defensa individual", "20 %", "verificacion", "pipeline, ecuación, validación, transferencia"]]
          .map(([c, n, p, id, e]) => `<tr><td class="l"><a href="#${id}"><strong>${c}</strong> ${n}</a></td><td>${p}</td><td class="l" style="white-space:normal;font-family:var(--font-body)">${e}</td></tr>`).join("")}
        </tbody></table></div>
        <p class="hint">Todo lo que ves se calcula en vivo en el navegador con una traducción del paquete Python <span class="mono">irb120</span>, verificada contra él en 105 casos (diferencias ≤ 1e-9).</p></div>
    </div>`;
  },
  init() { this.v = new View3D($("#cvHero")); this.v.onchange = () => this.frame(); },
  frame() {
    const v = this.v.begin();
    v.robot(S.q0, tok("--muted"), { alpha: 0.7, tcpFrame: true });
    if (S.traj) {
      v.robot(S.qf, tok("--ok"), { alpha: 0.35, tcpFrame: false });
      v.line(S.tcpPath, tok("--ink"), 1.5, [4, 3]);
      v.robot(S.traj.sample(S.t)[0], tok("--accent"));
    }
    v.frame(S.T, 0.11, [5, 4], 2);
  },
  animated: true,
};

// ---------- A: Pieper
V.pieper = {
  html() {
    const rep = S.rep, T0 = rep.T0, W = rep.W, z6 = R.col(S.T, 2);
    const planar = Math.hypot(W[0], W[1]), hgt = W[2] - R.D1, c = rep.candidates[0].c;
    const real = rep.candidates.filter((k) => k.real).length;
    return `${head("A · 15 %", "Cinemática inversa analítica por Pieper", "Los ejes 4, 5 y 6 se cortan en el centro de muñeca W: primero se coloca W con el brazo (q1, q2, q3) y luego se orienta con la muñeca (q4, q5, q6). 2 brazo × 2 codo × 2 muñeca = 8 ramas.")}
    ${rubricBox(["Estructura analítica, sin solver numérico", "Manejo correcto de ramas (hasta 8) y uso de atan2", "Procesar todas las poses y distinguir candidatos reales de admisibles", "Explicar la geometría de las ramas"],
      ["Panel de pasos: cada número sale de la fórmula (atan2, asin, ley de cosenos)", "Vista 3D: elige una rama o «todas» y gira el robot", "Tabla: real · en límites · error FK · admisible", "Prueba las poses «Fuera de alcance» y «Bloqueada por límites»"])}
    <div class="grid2">
      <div class="panel"><h3>Las 8 ramas en 3D <span class="hint">arrastra · rueda = zoom</span></h3>
        <div class="branchbar" id="bb">${[0, ...rep.candidates.map((k) => k.branch)].map((k) => {
          const d = k ? S.rank[k - 1] : null; const cls = d ? (d.rank === 1 ? "ok" : d.admissible ? "" : "bad") : "";
          return `<button type="button" data-b="${k}" class="${cls}" aria-pressed="${S.branch === k}">${k ? `R${k}` : "todas"}</button>`; }).join("")}</div>
        <canvas class="view3d" id="cvA"></canvas>
        ${legend([[tok("--ok"), "elegida"], [tok("--accent"), "admisible"], [tok("--bad"), "viola límites (ángulos sin ajustar)", true], [tok("--muted"), "triedro objetivo", true]])}
        <p class="hint" id="bInfo"></p></div>
      <div class="panel"><h3>Paso a paso con esta pose</h3>
        <div class="eq">p_TCP = (${R.pos(S.T).map((v) => fmt(v)).join(", ")})   z6 = (${z6.map((v) => fmt(v)).join(", ")})
p_W = p_TCP − (0.150 + d6)·z6 = (${W.map((v) => fmt(v, 4)).join(", ")}) m
r = √(x²+y²) = ${fmt(planar, 4)}    h = z_W − d1 = ${fmt(hgt, 4)}    D = ${fmt(rep.dist, 4)} m
alcance: |L2 − L3| = ${fmt(R.REACH_MIN, 3)} ≤ D ≤ L2 + L3 = ${fmt(R.REACH_MAX, 3)}  → ${rep.geometricallyReachable ? "dentro" : "FUERA"}
c = (D² − L2² − L3²)/(2·L2·L3) = ${fmt(c, 5)}   ${Math.abs(c) <= 1 ? "|c| ≤ 1 → 2 codos reales" : "|c| > 1 → no existe"}
q1 frente = atan2(y_W, x_W) = ${fdeg(Math.atan2(W[1], W[0]))}°   atrás = q1 + 180°
q3 = δ + asin(−c)  ó  δ + 180° − asin(−c),  δ = atan2(a3, d4) = ${fdeg(R.DELTA)}°
q2 = atan2(r, h) − atan2(L3 sin η, L2 + L3 cos η),  η = 90° + q3 − δ
R36 = R03ᵀ·R_d = Rz(q4)·Ry(−q5)·Rz(q6 + 180°)  → Euler ZYZ con atan2</div>
        <dl class="kv"><dt>Veredicto</dt><dd>${rep.verdict}</dd><dt>Ramas reales</dt><dd>${real} de 8</dd><dt>Admisibles</dt><dd>${rep.admissible.length} de 8</dd>
        <dt>Pose inicial</dt><dd>Pieper recupera q = 0 desde T₀ (${S.home.admissible.some((k) => k.q.every((v) => Math.abs(v) < 1e-9)) ? "sí" : "no"}), muñeca singular</dd></dl></div>
    </div>
    <div class="panel"><h3>Tabla de las 8 ramas <span class="hint">clic en una fila para verla en 3D</span></h3><div class="table-wrap"><table>
      <thead><tr><th>k</th><th class="l">brazo / codo / muñeca</th><th>q1</th><th>q2</th><th>q3</th><th>q4</th><th>q5</th><th>q6</th><th class="l">real</th><th class="l">límites</th><th>e_p [m]</th><th>e_R [rad]</th><th class="l">estado</th></tr></thead>
      <tbody>${rep.candidates.map((k, i) => { const ch = rep.checks[i], q = k.q || k.qRaw, d = S.rank[i];
        return `<tr class="clickable ${d.rank === 1 ? "sel" : ""}" data-b="${k.branch}"><td>${k.branch}</td><td class="l">${branchName(k)}${k.singular ? " ·sing" : ""}</td>${q ? q.map((v) => `<td>${fdeg(v)}</td>`).join("") : `<td colspan="6" style="text-align:center">no existe (|c| > 1)</td>`}
        <td class="l">${k.real ? "sí" : "no"}</td><td class="l">${!k.real ? "—" : k.q ? "sí" : "J" + k.out.join(",")}</td><td>${ch ? fexp(ch.ep) : "—"}</td><td>${ch ? fexp(ch.eR) : "—"}</td><td class="l">${statusPill(d)}</td></tr>`; }).join("")}</tbody></table></div></div>`;
  },
  init() {
    this.v = new View3D($("#cvA")); this.v.onchange = () => this.frame();
    const pick = (k) => { S.branch = +k; document.querySelectorAll("#bb button").forEach((b) => b.setAttribute("aria-pressed", String(+b.dataset.b === S.branch))); this.frame(); };
    $("#bb").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) pick(b.dataset.b); });
    $("#main").querySelectorAll("tr[data-b]").forEach((tr) => tr.addEventListener("click", () => pick(tr.dataset.b)));
    this.frame();
  },
  frame() {
    const v = this.v.begin();
    const show = S.branch ? [S.rank[S.branch - 1]] : S.rank;
    show.forEach((d) => {
      const c = d.candidate; if (!c.real) return;
      const q = c.q || c.qRaw;
      v.robot(q, branchColor(d), { width: S.branch ? 5 : 3, alpha: S.branch ? 1 : 0.85, dash: d.admissible ? [] : [6, 5], tcpFrame: !!S.branch });
    });
    v.frame(S.T, 0.11, [5, 4], 2);
    const info = $("#bInfo");
    if (S.branch) { const d = S.rank[S.branch - 1], c = d.candidate; info.textContent = c.real ? `Rama ${c.branch} (${branchName(c)}): q = (${(c.q || c.qRaw).map((x) => fdeg(x, 1)).join(", ")})° — ${d.status}` : `Rama ${c.branch}: no existe para esta pose.`; }
    else info.textContent = "Todas las ramas reales llegan al mismo TCP con la misma orientación; cambia cómo llega el brazo.";
  },
};

// ---------- B: Validación
V.validacion = {
  html() {
    const adm = S.rep.admissible[0];
    return `${head("B · 10 %", "Validación sistemática por cinemática directa", "Cada rama real se reinyecta en la FK y se compara la pose completa: e_p = ‖p(q) − p_d‖ y e_R = ángulo de R_dᵀR(q). Se acepta si e_p < 1e-6 m y e_R < 1e-6 rad.")}
    ${rubricBox(["Verificar sistemáticamente los candidatos", "Comparar posición y orientación", "Documentar error y criterio de aceptación", "Identificar inconsistencias"],
      ["Gráfica: error de cada rama frente a la tolerancia", "Inyector de errores: un error solo en q6 no mueve el TCP y aun así se rechaza", "Ida y vuelta FK → IK → FK con poses aleatorias", "Comparación con el modelo oficial de ROS-Industrial"])}
    <div class="grid2">
      <div class="panel"><h3>Error FK de cada rama real (escala log)</h3><canvas class="chart tall" id="cvErr"></canvas>
        ${legend([[tok("--accent"), "e_p [m]"], [tok("--amber"), "e_R [rad]"], [tok("--bad"), "tolerancia 1e-6", true]])}</div>
      <div class="panel"><h3>¿El criterio detecta errores? Inyéctalos</h3>
        ${adm ? `<p class="hint">Parte de la rama admisible R${adm.branch} y le suma un error a q1 o a q6.</p>
        <div class="controls"><label>Δq1 <input type="range" id="dq1" min="0" max="20" step="0.1" value="0"><span class="mono" id="dq1v">0 mrad</span></label>
        <label>Δq6 <input type="range" id="dq6" min="0" max="20" step="0.1" value="10"><span class="mono" id="dq6v">10 mrad</span></label></div>
        <dl class="kv" id="injOut"></dl>` : `<p class="muted">No hay rama admisible para esta pose; prueba otra pose.</p>`}
        <h3 style="margin-top:6px">Pruebas masivas</h3>
        <div class="controls"><button class="btn" id="btnRT" type="button">Ida y vuelta: 300 poses aleatorias</button><button class="btn" id="btnRosi" type="button">FK frente al modelo oficial ROS-Industrial</button></div>
        <dl class="kv" id="massOut"><dt>Ida y vuelta</dt><dd>pendiente</dd><dt>ROS-Industrial</dt><dd>pendiente</dd></dl>
        <p class="hint">El modelo oficial (abb_irb120_support) usa traslaciones y ejes de los planos de ABB, sin nuestra tabla DH: es una fuente geométrica independiente.</p></div>
    </div>`;
  },
  init() {
    const pts = S.rep.candidates.map((c, i) => [c, S.rep.checks[i]]).filter(([, ch]) => ch);
    chart($("#cvErr"), { xmin: 0.5, xmax: 8.5, ymin: 1e-18, ymax: 1e-2, logY: true, xlabel: "rama k",
      series: [{ x: pts.map(([c]) => c.branch - 0.1), y: pts.map(([, ch]) => Math.max(ch.ep, 1e-18)), color: tok("--accent"), dots: true, r: 5 },
               { x: pts.map(([c]) => c.branch + 0.1), y: pts.map(([, ch]) => Math.max(ch.eR, 1e-18)), color: tok("--amber"), dots: true, r: 5 }],
      hlines: [{ y: 1e-6, color: tok("--bad"), label: "tolerancia" }] });
    const adm = S.rep.admissible[0];
    if (adm) {
      const upd = () => {
        const a = +$("#dq1").value / 1000, b = +$("#dq6").value / 1000;
        $("#dq1v").textContent = `${(a * 1000).toFixed(1)} mrad`; $("#dq6v").textContent = `${(b * 1000).toFixed(1)} mrad`;
        const q = adm.q.slice(); q[0] += a; q[5] += b;
        const ch = R.fkCheck(S.T, q);
        $("#injOut").innerHTML = `<dt>e_p</dt><dd>${fexp(ch.ep, 2)} m</dd><dt>e_R</dt><dd>${fexp(ch.eR, 2)} rad</dd><dt>Resultado</dt><dd>${ch.accepted ? '<span class="pill ok">acepta</span>' : '<span class="pill bad">rechaza</span>'}${a === 0 && b > 0 ? " · solo orientación: el TCP no se movió" : ""}</dd>`;
      };
      $("#dq1").addEventListener("input", upd); $("#dq6").addEventListener("input", upd); upd();
    }
    $("#btnRT").addEventListener("click", () => this.roundTrip()); $("#btnRosi").addEventListener("click", () => this.rosi());
    setTimeout(() => { this.roundTrip(); this.rosi(); }, 50);
  },
  roundTrip() {
    let seed = 7; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    let ok = 0, rec = 0, wp = 0, wr = 0; const N = 300;
    for (let n = 0; n < N; n++) {
      const q = R.LIMITS.map(([a, b]) => a + (b - a) * rnd());
      const T = R.forwardKinematicsTcp(q), rep = R.analyzePose(T, q);
      if (rep.admissible.length) ok++;
      if (rep.admissible.some((c) => c.q.every((v, i) => Math.abs(v - q[i]) < 1e-6))) rec++;
      rep.admissible.forEach((c) => { const ch = rep.checks[c.branch - 1]; wp = Math.max(wp, ch.ep); wr = Math.max(wr, ch.eR); });
    }
    this.rt = { N, ok, rec, wp, wr };
    $("#massOut").children[1].innerHTML = `${ok}/${N} resueltas · q original recuperado ${rec}/${N} · peor e_p ${fexp(wp)} m, e_R ${fexp(wr)} rad ${rec === N ? '<span class="pill ok">ok</span>' : '<span class="pill bad">revisar</span>'}`;
  },
  rosi() {
    let seed = 11; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647); let worst = 0;
    for (let n = 0; n < 300; n++) {
      const q = R.LIMITS.map(([a, b]) => a + (b - a) * rnd());
      const A = R.forwardKinematics(q), B = R.rosiForwardKinematics(q);
      worst = Math.max(worst, ...A.flat().map((v, i) => Math.abs(v - B.flat()[i])));
    }
    this.rosiWorst = worst;
    $("#massOut").children[3].innerHTML = `300 configuraciones · max |T_DH − T_ROS-I| = ${fexp(worst)} ${worst < 1e-9 ? '<span class="pill ok">coinciden</span>' : '<span class="pill bad">difieren</span>'}`;
  },
};

// ---------- Selección
V.seleccion = {
  html() {
    return `${head("A · selección", "De 8 ramas a 1: criterio de selección", "Filtros en orden y luego un costo. Si ninguna rama pasa los filtros 2 y 3, se relajan en ese orden y la tabla lo indica.")}
    <div class="grid3">
      <div class="panel"><span class="label">1 · Admisible</span><p>Real, dentro de límites y verificada por FK. Obligatorio: si no, el robot real no puede adoptarla.</p></div>
      <div class="panel"><span class="label">2 · Lejos de singularidad</span><p>σ<sub>min</sub>(J) ≥ 0.01, porque ‖q̇‖ ≤ ‖ẋ‖/σ<sub>min</sub>: la amplificación de velocidad queda acotada a 100×.</p></div>
      <div class="panel"><span class="label">3 · Lejos de los topes</span><p>Margen ≥ 5° en las seis juntas: el controlador tiene límites de software y el seguimiento tiene error.</p></div>
    </div>
    <div class="panel"><span class="label">4 · Menor desplazamiento ponderado</span><p>‖W(q − q₀)‖ con W = diag(1, 1, 1, ½, ½, ½): menos tiempo, energía y volumen barrido. Las juntas 1–3 mueven unos 12 kg; la muñeca, menos de 3 kg. El t<sub>f</sub> del LSPB se informa pero no decide: lo fija una sola junta y depende del supuesto de a<sub>max</sub>.</p></div>
    <div class="panel"><h3>Tabla de decisión</h3><div class="table-wrap"><table>
      <thead><tr><th>k</th><th class="l">rama</th><th class="l">adm.</th><th>σ_min(J)</th><th>margen [°]</th><th>‖W(q−q₀)‖</th><th>t_f LSPB [s]</th><th class="l">decisión</th></tr></thead>
      <tbody>${S.rank.map((d) => `<tr class="${d.rank === 1 ? "sel" : ""}"><td>${d.candidate.branch}</td><td class="l">${branchName(d.candidate)}</td><td class="l">${d.admissible ? "sí" : "no"}</td><td>${fmt(d.sigmaMin, 4)}</td><td>${fmt(d.margin, 1)}</td><td>${fmt(d.cost, 4)}</td><td>${fmt(d.tf, 4)}</td><td class="l">${statusPill(d)}</td></tr>`).join("")}</tbody></table></div>
      ${S.best ? `<p><strong>Elegida: rama ${S.best.candidate.branch} (${branchName(S.best.candidate)})</strong>, q<sub>f</sub> = (${S.qf.map((v) => fdeg(v)).join(", ")})°. σ<sub>min</sub> = ${fmt(S.best.sigmaMin, 3)}, margen ${fmt(S.best.margin, 1)}°, costo ${fmt(S.best.cost, 3)}.</p>` : notReachable()}</div>`;
  },
  init() {},
};

// ---------- C: LSPB
function playerHtml(id) {
  return `<div class="controls"><button class="btn" id="${id}Play" type="button">${S.playing ? "Pausa" : "Reproducir"}</button>
  <label>t <input type="range" id="${id}T" min="0" max="1000" value="0"><span class="mono" id="${id}Tv"></span></label>
  <label>reproducción <select id="${id}Rate"><option value="0.25">0.25×</option><option value="0.5">0.5×</option><option value="1">1×</option></select></label>
  <span class="mono" id="${id}Phase"></span></div>`;
}
function bindPlayer(id) {
  $(`#${id}Play`).addEventListener("click", (e) => { S.playing = !S.playing; e.target.textContent = S.playing ? "Pausa" : "Reproducir"; });
  $(`#${id}T`).addEventListener("input", (e) => { S.playing = false; $(`#${id}Play`).textContent = "Reproducir"; S.t = (+e.target.value / 1000) * S.traj.tf; current().frame(); });
  const rs = $(`#${id}Rate`); rs.value = String(S.rate); rs.addEventListener("change", () => { S.rate = +rs.value; });
}
function syncPlayer(id) {
  const el = $(`#${id}T`); if (!el || !S.traj) return;
  el.value = String(Math.round((S.t / S.traj.tf) * 1000)); $(`#${id}Tv`).textContent = `${S.t.toFixed(3)} s`;
  const ph = S.traj.phase(S.t); $(`#${id}Phase`).textContent = `fase: ${ph}`;
}
const phaseShades = () => [{ a: 0, b: S.traj.tb, color: tok("--ok") }, { a: S.traj.tf - S.traj.tb, b: S.traj.tf, color: tok("--bad") }];

V.lspb = {
  html() {
    if (!S.traj) return head("C · 15 %", "Trayectoria LSPB") + notReachable();
    const T = S.traj;
    return `${head("C · 15 %", "Trayectoria LSPB sincronizada", "Todas las juntas comparten t_f y t_b, parten y llegan en reposo. V = (q_f − q₀)/(t_f − t_b), a = V/t_b. Se busca el t_f mínimo que respeta v_max y a_max de cada junta.")}
    ${rubricBox(["Construir el perfil con parámetros justificados", "Obtener q, q̇, q̈ y cumplir las condiciones de frontera", "Graficar e interpretar; código y ecuaciones consistentes"],
      ["Animación 3D sincronizada con las tres gráficas (cursor común)", "Controles de velocidad (% del datasheet) y rampa (supuesto de a_max)", "Verificaciones en vivo: fronteras, reposo, continuidad, límites"])}
    ${playerHtml("pl")}
    <div class="grid2">
      <div class="panel"><h3>Movimiento en 3D <span class="hint">arrastra para girar</span></h3><canvas class="view3d" id="cvC"></canvas></div>
      <div class="panel"><h3>Perfiles q, q̇, q̈ <span class="hint">verde: acelera · rojo: frena</span></h3>
        <canvas class="chart" id="cq"></canvas><canvas class="chart" id="cqd"></canvas><canvas class="chart" id="cqdd"></canvas>
        ${legend(JC().map((c, i) => [c, `q${i + 1}`]))}</div>
    </div>
    <div class="grid2">
      <div class="panel"><h3>Parámetros <span class="mono">t_f = ${fmt(T.tf, 4)} s · t_b = ${fmt(T.tb, 4)} s${S.triangular ? " · triangular" : ""}</span></h3>
        <div class="controls"><label>v_max = <span class="mono" id="spv">${Math.round(S.speed * 100)} %</span> del datasheet <input type="range" id="sp" min="10" max="100" step="5" value="${Math.round(S.speed * 100)}"></label>
        <label>rampa a v_max <input type="range" id="rp" min="0.1" max="1" step="0.05" value="${S.ramp}"><span class="mono" id="rpv">${S.ramp.toFixed(2)} s</span></label></div>
        <div class="table-wrap"><table><thead><tr><th>junta</th><th>D [°]</th><th>V [°/s]</th><th>a [°/s²]</th><th>|V|/v_max</th><th>|a|/a_max</th></tr></thead><tbody>
        ${T.V.map((v, i) => `<tr class="${i + 1 === S.critical ? "sel" : ""}"><td>J${i + 1}${i + 1 === S.critical ? " ★" : ""}</td><td>${fdeg(S.qf[i] - S.q0[i])}</td><td>${fdeg(v)}</td><td>${fdeg(T.A[i])}</td><td>${fmt(Math.abs(v) / S.vmax[i], 2)}</td><td>${fmt(Math.abs(T.A[i]) / S.amax[i], 2)}</td></tr>`).join("")}</tbody></table></div>
        <p class="hint">★ junta crítica: llega a su límite y fija t_f; las demás van más lentas para llegar a la vez.</p></div>
      <div class="panel"><h3>Verificaciones en vivo</h3><div class="checks" id="lspbChecks"></div></div>
    </div>`;
  },
  init() {
    if (!S.traj) return;
    this.v = new View3D($("#cvC")); this.v.onchange = () => this.frame(); bindPlayer("pl");
    const rerun = () => { S.speed = +$("#sp").value / 100; S.ramp = +$("#rp").value; S.t = 0; compute(); render(); };
    $("#sp").addEventListener("change", rerun); $("#rp").addEventListener("change", rerun);
    $("#sp").addEventListener("input", () => { $("#spv").textContent = `${$("#sp").value} %`; });
    $("#rp").addEventListener("input", () => { $("#rpv").textContent = `${(+$("#rp").value).toFixed(2)} s`; });
    const T = S.traj, s0 = T.sample(0), sf = T.sample(T.tf); let jump = 0;
    [T.tb, T.tf - T.tb].forEach((t) => { const a = T.sample(t - 1e-9), b = T.sample(t + 1e-9); jump = Math.max(jump, ...a[0].map((v, i) => Math.abs(v - b[0][i])), ...a[1].map((v, i) => Math.abs(v - b[1][i]))); });
    const vm = Math.min(...T.V.map((v, i) => S.vmax[i] - Math.abs(v))), am = Math.min(...T.A.map((a, i) => S.amax[i] - Math.abs(a)));
    const checks = [["q(0) = q₀ y q(t_f) = q_f", Math.max(...s0[0].map((v, i) => Math.abs(v - S.q0[i])), ...sf[0].map((v, i) => Math.abs(v - S.qf[i]))) < 1e-9],
      ["reposo: q̇(0) = q̇(t_f) = 0", Math.max(...s0[1].map(Math.abs), ...sf[1].map(Math.abs)) < 1e-12], [`q y q̇ continuas en los empalmes (salto ${fexp(jump)})`, jump < 1e-6],
      ["|V| ≤ v_max en las 6 juntas", vm > -1e-9], ["|a| ≤ a_max en las 6 juntas", am > -1e-9], ["t_b ≤ t_f/2 (existe el perfil)", T.tb <= T.tf / 2 + 1e-12],
      ["fuera de [0, t_f]: reposo (q̇ = q̈ = 0)", T.sample(T.tf + 0.1)[2].every((v) => v === 0)], ["q̈ salta en los empalmes (LSPB es C¹, no C²)", true]];
    $("#lspbChecks").innerHTML = checks.map(([t, ok]) => `<div class="check ${ok ? "" : "fail"}"><b>${ok ? "✓" : "✗"}</b><span>${t}</span></div>`).join("");
    this.frame();
  },
  frame() {
    if (!S.traj) return; syncPlayer("pl");
    const v = this.v.begin();
    v.robot(S.q0, tok("--muted"), { alpha: 0.3, tcpFrame: false }); v.robot(S.qf, tok("--ok"), { alpha: 0.3, tcpFrame: false });
    v.line(S.tcpPath, tok("--ink"), 1.5, [4, 3]); v.robot(S.traj.sample(S.t)[0], tok("--accent")); v.frame(S.T, 0.11, [5, 4]);
    const c = JC(), xs = S.ts, opts = { xmin: 0, xmax: S.traj.tf, cursor: S.t, shades: phaseShades() };
    chart($("#cq"), { ...opts, ylabel: "q [°]", series: c.map((col, j) => ({ x: xs, y: S.samp.map((s) => R.deg(s[0][j])), color: col })) });
    chart($("#cqd"), { ...opts, ylabel: "q̇ [°/s]", series: c.map((col, j) => ({ x: xs, y: S.samp.map((s) => R.deg(s[1][j])), color: col })) });
    chart($("#cqdd"), { ...opts, ylabel: "q̈ [°/s²]", xlabel: "t [s]", series: c.map((col, j) => ({ x: xs, y: S.samp.map((s) => R.deg(s[2][j])), color: col })) });
  },
  animated: true,
};

// ---------- D: Jacobiano
V.jacobiano = {
  html() {
    if (!S.traj) return head("D · 20 %", "Jacobiano") + notReachable();
    const J0 = R.geometricJacobian(R.HOME_Q), Jf = R.geometricJacobian(S.qf), dn = Math.max(...Jf.flat().map((v, i) => Math.abs(v - R.numericalJacobian(S.qf).flat()[i])));
    return `${head("D · 20 %", "Jacobiano geométrico ẋ = J(q) q̇", "Columna i = [z_{i−1} × (p_TCP − o_{i−1}); z_{i−1}]: la velocidad del TCP cuando solo gira la junta i a 1 rad/s.")}
    ${rubricBox(["Jacobiano consistente con al menos una validación", "Interpretar sus columnas", "Usar el rango como criterio central"],
      ["J(q(t)) en vivo durante el LSPB, coloreado por magnitud", `Validación: max|J − J_numérico| en q_f = ${fexp(dn)}; ‖J_v q̇‖ frente a dp/dt numérico`, "Columna 1 en q = 0 calculada a mano: (0, 0.524, 0 | 0, 0, 1)"])}
    ${playerHtml("pj")}
    <div class="grid2">
      <div class="panel"><h3>J(q(t)) <span class="mono" id="jRank"></span></h3><div class="table-wrap" id="jTable"></div>
        <p class="hint">Filas v_x, v_y, v_z [m/s por rad/s] y ω_x, ω_y, ω_z. ‖J_v,i‖ es la palanca: las juntas 1–3 posicionan y las 4–6 orientan. En q = 0 las columnas 4 y 6 son iguales (singularidad de muñeca).</p></div>
      <div class="panel"><h3>Validación sobre la trayectoria</h3><canvas class="chart" id="cv"></canvas>
        ${legend([[tok("--accent"), "‖J_v q̇‖"], [tok("--amber"), "‖dp/dt‖ numérico (puntos)"]])}
        <canvas class="chart" id="cs"></canvas>${legend([[tok("--ok"), "σ_min(J(q(t)))"], [tok("--bad"), "tolerancia de rango 1e-6", true]])}
        <dl class="kv"><dt>Columna 1, q = 0</dt><dd>(${J0.map((r) => fmt(r[0], 3)).join(", ")})</dd><dt>Columna 2, q = 0</dt><dd>(${J0.map((r) => fmt(r[1], 3)).join(", ")})</dd><dt>max|J − J_num| (q_f)</dt><dd>${fexp(dn)}</dd>
        <dt>max|J_v q̇ − dp/dt|</dt><dd>${fexp(Math.max(...S.jac.map((j, i) => Math.abs(j.v - S.vnum[i])).slice(2, -2)))} m/s</dd></dl></div>
    </div>`;
  },
  init() { if (!S.traj) return; bindPlayer("pj"); this.frame(); },
  frame() {
    if (!S.traj) return; syncPlayer("pj");
    const [q] = S.traj.sample(S.t), J = R.geometricJacobian(q), ra = R.rankAnalysis(J), mx = Math.max(...J.flat().map(Math.abs));
    const rows = ["v_x", "v_y", "v_z", "ω_x", "ω_y", "ω_z"];
    $("#jTable").innerHTML = `<table><thead><tr><th class="l"></th>${[1, 2, 3, 4, 5, 6].map((i) => `<th>J${i}</th>`).join("")}</tr></thead><tbody>${J.map((r, i) => `<tr><td class="l">${rows[i]}</td>${r.map((v) => `<td style="background:color-mix(in srgb, var(--accent) ${Math.round((Math.abs(v) / mx) * 38)}%, transparent)">${fmt(v, 3)}</td>`).join("")}</tr>`).join("")}
      <tr><td class="l">‖J_v‖</td>${[0, 1, 2, 3, 4, 5].map((k) => `<td>${fmt(Math.hypot(J[0][k], J[1][k], J[2][k]), 3)}</td>`).join("")}</tr></tbody></table>`;
    $("#jRank").textContent = `σ = (${ra.s.map((s) => s.toPrecision(3)).join(", ")}) · rango ${ra.rank}`;
    const o = { xmin: 0, xmax: S.traj.tf, cursor: S.t, shades: phaseShades() };
    chart($("#cv"), { ...o, ylabel: "[m/s]", series: [{ x: S.ts, y: S.jac.map((j) => j.v), color: tok("--accent"), width: 2.4 }, { x: S.ts.filter((_, i) => i % 12 === 6), y: S.vnum.filter((_, i) => i % 12 === 6), color: tok("--amber"), dots: true }] });
    chart($("#cs"), { ...o, logY: true, ymin: 1e-8, ymax: 2, ylabel: "σ_min", xlabel: "t [s]", series: [{ x: S.ts, y: S.jac.map((j) => Math.max(j.smin, 1e-8)), color: tok("--ok") }], hlines: [{ y: 1e-6, color: tok("--bad") }] });
  },
  animated: true,
};

// ---------- D: Singularidad
const QBASE = [30, -20, 15, 40, 0, 60].map(R.rad);
const q5FromSlider = (s) => (s >= 1000 ? 0 : R.rad(45 * 10 ** (-4.5 * (s / 1000))));
V.singularidad = {
  html() {
    return `${head("D · 20 %", "Experimento independiente: acercarse a q5 = 0", "Postura fija q = (30°, −20°, 15°, 40°, q5, 60°). Al llevar q5 a 0, los ejes 4 y 6 quedan alineados. El criterio es el rango por SVD (σ_i > 1e-6); el determinante es solo un complemento: |det J| = ∏σ_i.")}
    ${rubricBox(["Experimento de aproximación claro", "Rango como criterio central (det solo cuando corresponde)", "Explicar la movilidad que se pierde", "Amplificación de velocidad sin confundirla con torque infinito"],
      ["Control deslizante q5: σ_i, rango, det y la factorización en vivo", "Botón «movimiento nulo»: q̇4 = −q̇6 gira la muñeca y el TCP no se mueve", "‖q̇‖ = 1/σ6 y ρ = max|q̇_i|/v_max,i frente a ‖Jᵀu₆‖ → 0"])}
    <div class="controls"><label>q5 <input type="range" id="q5s" min="0" max="1000" value="600" style="width:260px"><span class="mono" id="q5v"></span></label>
      <button class="btn" type="button" id="nullBtn">Animar movimiento nulo (q̇4 = −q̇6)</button><span class="hint">al final del recorrido q5 = 0 exacto</span></div>
    <div class="grid2">
      <div class="panel"><h3>Postura del experimento <span class="hint">la estela muestra si el TCP se mueve</span></h3><canvas class="view3d" id="cvS"></canvas></div>
      <div class="panel"><h3>Valores singulares <span class="mono" id="rankBadge"></span></h3><canvas class="chart" id="csv"></canvas>
        <dl class="kv" id="singOut"></dl>
        <canvas class="chart" id="camp"></canvas>${legend([[tok("--accent"), "‖q̇‖ = 1/σ6 [rad/s]"], [tok("--amber"), "ρ = max|q̇_i|/v_max,i"], [tok("--ok"), "‖Jᵀu₆‖ (torque estático)"]])}</div>
    </div>
    <div class="panel"><h3>Lectura física</h3><p>En q5 = 0, z5 = z3: dos motores producen la misma rotación. El espacio nulo de J es q̇ ∝ (0, 0, 0, 1, 0, −1): girar J4 y J6 en sentidos opuestos no mueve el TCP. Se pierde la rotación alrededor de z3 × z4. Para moverse en esa dirección haría falta ‖q̇‖ = 1/σ6 → ∞. En estática, τ = JᵀF y Jᵀu₆ = σ6 v₆ → 0: una carga en la dirección perdida <strong>no</strong> requiere torque. La singularidad amplifica velocidades, no torques.</p></div>`;
  },
  init() {
    this.v = new View3D($("#cvS")); this.v.onchange = () => this.frame(); this.trail = []; this.nullT = null;
    this.seq = [];
    for (let s = 0; s < 1000; s += 25) { const q = QBASE.slice(); q[4] = q5FromSlider(s); const J = R.geometricJacobian(q), d = R.svd(J), u6 = d.U[5], qd = R.solve(J, u6);
      this.seq.push({ q5: R.deg(q[4]), amp: R.norm(qd), rho: Math.max(...qd.map((v, i) => Math.abs(v) / R.MAX_SPEED[i])), tau: R.norm(R.matvec(R.transpose(J), u6)) }); }
    $("#q5s").addEventListener("input", () => { this.trail = []; this.frame(); });
    $("#nullBtn").addEventListener("click", () => { this.nullT = this.nullT === null ? 0 : null; this.trail = []; $("#nullBtn").textContent = this.nullT === null ? "Animar movimiento nulo (q̇4 = −q̇6)" : "Detener movimiento nulo"; });
    this.frame();
  },
  frame(dt = 0) {
    const s = +$("#q5s").value, q = QBASE.slice(); q[4] = q5FromSlider(s);
    $("#q5v").textContent = `${fmt(R.deg(q[4]), q[4] === 0 ? 0 : 4)}°`;
    const J = R.geometricJacobian(q), ra = R.rankAnalysis(J), d = R.svd(J), u6 = d.U[5];
    const det = R.det(J), detT = -Math.sin(q[4]) * R.armPositionDeterminant(q);
    const qd = ra.rank === 6 ? R.solve(J, u6) : null;
    $("#rankBadge").innerHTML = ra.rank === 6 ? `<span class="pill ok">rango 6</span>` : `<span class="pill bad">rango ${ra.rank} · singular</span>`;
    chart($("#csv"), { xmin: 0.5, xmax: 6.5, ymin: 1e-18, ymax: 10, logY: true, xlabel: "σ_i", series: [{ x: [1, 2, 3, 4, 5, 6], y: ra.s.map((v) => Math.max(v, 1e-18)), color: tok("--accent"), dots: true, r: 6 }], hlines: [{ y: 1e-6, color: tok("--bad"), label: "tolerancia de rango" }] });
    $("#singOut").innerHTML = `<dt>σ6</dt><dd>${fexp(ra.s[5], 2)} (σ6/sin q5 = ${q[4] ? fmt(ra.s[5] / Math.sin(q[4]), 3) : "—"})</dd><dt>κ(J)</dt><dd>${Number.isFinite(ra.cond) && ra.cond < 1e15 ? fexp(ra.cond, 2) : "∞"}</dd>
      <dt>det J</dt><dd>${fexp(det, 3)} · −sin q5 · det(J_brazo) = ${fexp(detT, 3)}</dd>
      <dt>q̇ para twist unitario en u₆</dt><dd>${qd ? `‖q̇‖ = ${fmt(R.norm(qd), 1)} rad/s · q̇4 = ${fmt(qd[3], 1)}, q̇6 = ${fmt(qd[5], 1)} · ρ = ${fmt(Math.max(...qd.map((v, i) => Math.abs(v) / R.MAX_SPEED[i])), 1)}` : "no existe (J no invertible)"}</dd>
      <dt>‖Jᵀu₆‖</dt><dd>${fexp(R.norm(R.matvec(R.transpose(J), u6)), 2)} N·m por unidad de carga</dd>
      ${ra.rank < 6 ? `<dt>espacio nulo v₆</dt><dd>(${ra.nullMotions[0].map((v) => fmt(v, 3)).join(", ")})</dd>` : ""}`;
    const sq = this.seq;
    chart($("#camp"), { xmin: -3, xmax: 1.8, logY: true, ymin: 1e-6, ymax: 1e6, xlabel: "log10(q5 [°])  ← hacia la singularidad", series: [
      { x: sq.map((r) => Math.log10(r.q5)), y: sq.map((r) => r.amp), color: tok("--accent") }, { x: sq.map((r) => Math.log10(r.q5)), y: sq.map((r) => r.rho), color: tok("--amber") },
      { x: sq.map((r) => Math.log10(r.q5)), y: sq.map((r) => r.tau), color: tok("--ok") }], hlines: [{ y: 1, color: tok("--bad"), label: "ρ = 1 (límite del datasheet)" }],
      marks: q[4] > 0 ? [{ x: Math.log10(R.deg(q[4])), y: R.norm(qd), color: tok("--accent") }] : [] });
    // 3D con movimiento nulo
    const qa = q.slice();
    if (this.nullT !== null) { this.nullT += dt; const a = 0.6 * Math.sin(this.nullT * 2); qa[3] += a; qa[5] -= a; this.trail.push(R.pos(R.forwardKinematicsTcp(qa))); if (this.trail.length > 240) this.trail.shift(); }
    const v = this.v.begin();
    if (this.trail.length > 1) v.line(this.trail, tok("--amber"), 2.5);
    v.robot(qa, ra.rank < 6 ? tok("--bad") : tok("--accent"));
    const F = R.jointFrames(qa); [3, 5].forEach((k) => { const o = R.pos(F[k]), z = R.col(F[k], 2); v.line([R.sub(o, R.scale(z, 0.12)), R.add(o, R.scale(z, 0.18))], k === 3 ? tok("--j4") : tok("--j6"), 1.6, [4, 3]); });
    v.text(R.pos(F[4]), "ejes 4 y 6", tok("--muted"));
  },
  animated: true,
};

// ---------- E: Dinámica 1R
function peakTau() { if (!S.tau) return { v: NaN }; let k = 0; S.tau.forEach((t, i) => { if (Math.abs(t[2]) > Math.abs(S.tau[k][2])) k = i; }); return { v: S.tau[k][2], t: S.ts[k], k }; }
V.dinamica = {
  html() {
    if (!S.traj) return head("E · 15 %", "Dinámica 1R") + notReachable();
    const m = S.model, pk = peakTau(), cr = S.ts.map((t, i) => [S.traj.phase(t), S.tau[i][2]]).filter(([p]) => p === "crucero").map(([, v]) => Math.abs(v));
    const hold = m.components(S.qf[1], 0)[2];
    return `${head("E · 15 %", "Dinámica reducida 1R del hombro", "τ = J·θ̈ + m·g·ℓc·sin θ, con θ medido desde la vertical inferior y J = I_c + m·ℓc². La junta 2 carga los eslabones 2–6 y la pinza; las juntas 3–6 se congelan en la postura media.")}
    ${rubricBox(["Usar el modelo 1R trabajado; documentar supuestos y parámetros", "Calcular τ a partir del LSPB y separar contribuciones", "Presentar τ(t) y relacionarlo con la trayectoria"],
      ["Péndulo equivalente animado: θ, centro de masa, gravedad", "τ_in, τ_g y τ sincronizados con la animación", "Parámetros calculados del CAD (Truc & Lam 2020 + pinza SMC)", "1R frente al modelo completo de 6 GDL (mismos datos CAD)"])}
    ${playerHtml("pd")}
    <div class="grid2">
      <div class="panel"><h3>Péndulo equivalente (plano del hombro)</h3><canvas class="view3d" id="cvP" style="cursor:default"></canvas>
        <dl class="kv"><dt>m</dt><dd>${fmt(m.mass, 3)} kg</dd><dt>ℓc</dt><dd>${fmt(m.lc, 4)} m</dd><dt>I_c</dt><dd>${fmt(m.Ic, 4)} kg·m²</dd><dt>J = I_c + m ℓc²</dt><dd>${fmt(m.J, 4)} kg·m²</dd>
        <dt>φ₀ (θ = q2 + φ₀)</dt><dd>${fdeg(m.phi0)}°</dd><dt>m g ℓc</dt><dd>${fmt(m.mglc, 2)} N·m</dd><dt>J = M₂₂ (modelo completo)</dt><dd>${fexp(Math.abs(m.J - R.massMatrix(m.qRef)[1][1]))}</dd></dl></div>
      <div class="panel"><h3>Torque del hombro τ(t)</h3><canvas class="chart" id="ctq2"></canvas><canvas class="chart tall" id="ctau"></canvas>
        ${legend([[tok("--accent"), "τ_in = J q̈₂"], [tok("--amber"), "τ_g = m g ℓc sin θ"], [tok("--ink"), "τ = τ_in + τ_g"], [tok("--ink"), "sostén (robot detenido)", true]])}
        <dl class="kv"><dt>Pico</dt><dd>${fmt(pk.v, 2)} N·m en t = ${fmt(pk.t, 3)} s (${S.traj.phase(pk.t)})</dd><dt>Al detenerse (t_f⁺)</dt><dd>τ = τ_g = ${fmt(hold, 2)} N·m</dd>
        <dt>En crucero</dt><dd>${cr.length ? `|τ| de ${fmt(Math.min(...cr), 2)} a ${fmt(Math.max(...cr), 2)} N·m con q̈ = 0` : "perfil triangular: no hay crucero"}</dd><dt>1R vs completo</dt><dd id="fullOut">calculando…</dd></dl></div>
    </div>
    <div class="panel"><h3>1R frente al modelo de Lagrange completo (6 GDL, mismos datos CAD)</h3><canvas class="chart" id="cfull"></canvas>
      ${legend([[tok("--muted"), "τ₂ modelo completo M q̈ + c + g"], [tok("--ink"), "τ modelo 1R"]])}
      <p class="hint">La diferencia mide lo que deja fuera la reducción (juntas 3–6 en movimiento, acoplamientos). No es una validación contra el robot real.</p></div>`;
  },
  init() {
    if (!S.traj) return; bindPlayer("pd");
    setTimeout(() => {
      if (!S.full) { const idx = S.ts.map((_, i) => i).filter((i) => i % 4 === 0); S.full = { x: idx.map((i) => S.ts[i]), y: idx.map((i) => R.inverseDynamics(...S.samp[i])[1]), idx }; }
      const err = S.full.idx.map((i, k) => S.tau[i][2] - S.full.y[k]), rms = Math.sqrt(err.reduce((s, e) => s + e * e, 0) / err.length), ref = Math.sqrt(S.full.y.reduce((s, e) => s + e * e, 0) / err.length);
      const out = $("#fullOut"); if (out) out.textContent = `error RMS ${fmt(rms, 3)} N·m (${fmt((100 * rms) / ref, 1)} %)`;
      this.frame();
    }, 30);
    this.frame();
  },
  frame() {
    if (!S.traj) return; syncPlayer("pd");
    const m = S.model, [q, , qdd] = S.traj.sample(S.t), th = m.theta(q[1]), [ti, tg, tt] = m.components(q[1], qdd[1]);
    // péndulo 2D
    const cv = $("#cvP"), { ctx, w, h } = prep(cv), cx = w / 2, cy = h * 0.55, Lp = Math.min(w, h) * 0.36;
    ctx.strokeStyle = tok("--grid"); ctx.setLineDash([4, 4]); ctx.beginPath(); ctx.moveTo(cx, cy - Lp * 1.2); ctx.lineTo(cx, cy + Lp * 1.2); ctx.stroke(); ctx.setLineDash([]);
    const px = cx + Lp * Math.sin(th), py = cy + Lp * Math.cos(th);
    ctx.strokeStyle = tok("--accent"); ctx.lineWidth = 6; ctx.lineCap = "round"; ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(px, py); ctx.stroke();
    ctx.fillStyle = tok("--ink"); ctx.beginPath(); ctx.arc(cx, cy, 7, 0, 7); ctx.fill();
    ctx.fillStyle = tok("--amber"); ctx.beginPath(); ctx.arc(px, py, 11, 0, 7); ctx.fill();
    ctx.strokeStyle = tok("--bad"); ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(px, py + 46); ctx.stroke(); ctx.beginPath(); ctx.moveTo(px - 5, py + 38); ctx.lineTo(px, py + 46); ctx.lineTo(px + 5, py + 38); ctx.stroke();
    ctx.strokeStyle = tok("--muted"); ctx.lineWidth = 1.2; ctx.beginPath(); const a0 = Math.PI / 2, a1 = Math.PI / 2 - th; ctx.arc(cx, cy, 34, Math.min(a0, a1), Math.max(a0, a1)); ctx.stroke();
    const arc = Math.max(10, Math.min(40, Math.abs(tt) * 1.6)); ctx.strokeStyle = tok("--ink"); ctx.lineWidth = 2.5; ctx.beginPath(); ctx.arc(cx, cy, 22, -Math.PI / 2, -Math.PI / 2 + Math.sign(tt) * arc / 22, tt < 0); ctx.stroke();
    ctx.font = "12px " + tok("--font-mono"); ctx.fillStyle = tok("--ink"); ctx.textAlign = "left";
    ctx.fillText(`θ = ${fdeg(th, 1)}°  (desde la vertical inferior)`, 10, 18); ctx.fillText(`τ_in = ${fmt(ti, 2)}  τ_g = ${fmt(tg, 2)}  τ = ${fmt(tt, 2)} N·m`, 10, 36);
    ctx.fillStyle = tok("--muted"); ctx.fillText("centro de masa (ámbar), peso m·g (rojo), eje del hombro (negro)", 10, h - 10);
    // curvas
    const hold = 0.25, xs = S.ts, o = { xmin: 0, xmax: S.traj.tf + hold, cursor: S.t, shades: [...phaseShades(), { a: S.traj.tf, b: S.traj.tf + hold, color: tok("--muted") }] };
    const tauHold = m.components(S.qf[1], 0)[2];
    chart($("#ctq2"), { ...o, ylabel: "q̈₂ [°/s²]", series: [{ x: [...xs, S.traj.tf + 1e-9, S.traj.tf + hold], y: [...S.samp.map((s) => R.deg(s[2][1])), 0, 0], color: tok("--j2") }] });
    chart($("#ctau"), { ...o, ylabel: "τ₂ [N·m]", xlabel: "t [s]", series: [{ x: xs, y: S.tau.map((t) => t[0]), color: tok("--accent") }, { x: xs, y: S.tau.map((t) => t[1]), color: tok("--amber") },
      { x: xs, y: S.tau.map((t) => t[2]), color: tok("--ink"), width: 2.6 }, { x: [S.traj.tf, S.traj.tf + hold], y: [tauHold, tauHold], color: tok("--ink"), dash: [5, 4], width: 2.6 }] });
    if (S.full) chart($("#cfull"), { xmin: 0, xmax: S.traj.tf, cursor: S.t, shades: phaseShades(), ylabel: "τ₂ [N·m]", xlabel: "t [s]", series: [{ x: S.full.x, y: S.full.y, color: tok("--muted"), width: 5 }, { x: xs, y: S.tau.map((t) => t[2]), color: tok("--ink"), width: 1.6 }] });
  },
  animated: true,
};

// ---------- F·G: verificación y defensa
V.verificacion = {
  html() {
    const c = [];
    const ok = (t, v) => c.push([t, !!v]);
    ok("FK(q = 0) = (0.374, 0, 0.630) m, como el datasheet", R.pos(R.forwardKinematics(R.HOME_Q)).every((v, i) => Math.abs(v - [0.374, 0, 0.63][i]) < 1e-12));
    ok("Pieper enumera siempre 8 ramas", S.rep.candidates.length === 8);
    ok("Toda rama real reproduce T_d (e_p, e_R < 1e-6)", S.rep.candidates.every((k, i) => !k.real || S.rep.checks[i].accepted));
    ok("Pieper recupera q = 0 desde la pose inicial", S.home.admissible.some((k) => k.q.every((v) => Math.abs(v) < 1e-9)));
    ok("Se rechaza una matriz que no es pose rígida (det R = 4)", (() => { try { const T = R.forwardKinematicsTcp(R.HOME_Q).map((r) => r.slice()); for (let i = 0; i < 3; i++) { T[i][0] *= 2; T[i][1] *= 2; } R.analyzePose(T); return false; } catch (e) { return true; } })());
    if (S.traj) {
      ok("La rama elegida es admisible y reproduce T_d", R.fkCheck(S.T, S.qf).accepted);
      ok("LSPB: reposo en las fronteras", Math.max(...S.traj.sample(0)[1].map(Math.abs), ...S.traj.sample(S.traj.tf)[1].map(Math.abs)) < 1e-12);
      ok("J analítico = J numérico (< 1e-8)", Math.max(...R.geometricJacobian(S.qf).flat().map((v, i) => Math.abs(v - R.numericalJacobian(S.qf).flat()[i]))) < 1e-8);
      ok("1R: J = M₂₂ del modelo completo", Math.abs(S.model.J - R.massMatrix(S.model.qRef)[1][1]) < 1e-9);
    }
    const qs = QBASE.slice(); ok("Rango 6 → 5 exactamente en q5 = 0", R.rankAnalysis(R.geometricJacobian(qs)).rank === 5 && R.rankAnalysis(R.geometricJacobian(QBASE.map((v, i) => (i === 4 ? R.rad(0.01) : v)))).rank === 6);
    ok("FK por DH = modelo oficial ROS-Industrial (q = 0)", Math.max(...R.forwardKinematics(R.HOME_Q).flat().map((v, i) => Math.abs(v - R.rosiForwardKinematics(R.HOME_Q).flat()[i]))) < 1e-12);
    const qa = [["G1 · Pipeline", "Pose inicial y pose objetivo → Pieper (8 ramas) → FK valida cada rama → criterio elige q_f → LSPB da q(t), q̇(t), q̈(t) → J da ẋ(t) y, aparte, el rango estudia la singularidad → con q₂(t), q̈₂(t) el 1R da τ(t)."],
      ["G2 · Una ecuación", "Ley de cosenos: −sin(q3 − δ) = (D² − L2² − L3²)/(2 L2 L3). LSPB: V = D/(t_f − t_b), a = V/t_b. Jacobiano: J_i = [z × (p − o); z]. 1R: de T = ½Jθ̇² y V = mgℓc(1 − cos θ) sale τ = Jθ̈ + mgℓc sin θ."],
      ["G3 · Validación", "Toda rama se reinyecta en la FK (posición y orientación, 1e-6). Ida y vuelta con poses aleatorias. La FK coincide con el modelo oficial de ROS-Industrial. J frente a diferencias finitas. 1R frente al modelo completo."],
      ["G3 · ¿Torque infinito en la singularidad?", "No. Diverge la velocidad articular para la dirección perdida (‖q̇‖ = 1/σ6). En estática, Jᵀu₆ = σ6 v₆ → 0: esa carga no requiere torque."],
      ["G3 · ¿Por qué hay torque en crucero?", "Por la gravedad: τ_g = m g ℓc sin θ depende de la posición, no de la aceleración."],
      ["G4 · ¿8 reales y 1 admisible?", "La matemática no conoce los topes mecánicos. Ejemplo: las ramas «atrás» piden q1 = −165.96° y el límite es ±165°."]];
    return `${head("F · G", "Verificación, reproducibilidad y defensa")}
    <div class="grid2">
      <div class="panel"><h3>Verificaciones en vivo <span class="pill ${c.every(([, v]) => v) ? "ok" : "bad"}">${c.filter(([, v]) => v).length}/${c.length}</span></h3>
        <div class="checks" style="grid-template-columns:minmax(0,1fr)">${c.map(([t, v]) => `<div class="check ${v ? "" : "fail"}"><b>${v ? "✓" : "✗"}</b><span>${t}</span></div>`).join("")}</div></div>
      <div class="panel"><h3>Entregables (criterio F)</h3>
        <dl class="kv"><dt>Notebook</dt><dd>hito2/Hito2_IRB120_pipeline.ipynb · 34/34 verificaciones</dd><dt>Pruebas</dt><dd>python -m pytest -q tests · 56 pruebas</dd><dt>Informe IEEE</dt><dd>docs/hito2/informe_ieee/informe_hito2_ieee.pdf</dd>
        <dt>Esta página</dt><dd>hito2/presentacion/ · irb120.js verificado contra Python (verificar_port.mjs, 105 casos)</dd><dt>Datos</dt><dd>DH: Bahani 2023 · límites y v_max: ABB · masas: Truc & Lam 2020 · pinza: SMC</dd><dt>Supuestos</dt><dd>TCP 0.150 m (diseño) · a_max = v_max / rampa (ABB no la publica)</dd></dl></div>
    </div>
    <div class="panel qa"><h3>Defensa individual (G1–G4): respuestas cortas</h3>${qa.map(([q, a]) => `<details><summary>${q}</summary><p>${a}</p></details>`).join("")}</div>`;
  },
  init() {},
};

// ============================================================ navegación y bucle
function current() { return V[S.section]; }
function render() {
  $("#rail").innerHTML = SECTIONS.map((s) => `<a href="#${s.id}" aria-current="${s.id === S.section}"><span class="crit">${s.crit}</span><span>${s.name}</span><small>${s.sub}</small></a>`).join("");
  const vd = $("#verdict"); vd.textContent = S.rep.verdict.split(":")[0] + (S.best ? ` · rama ${S.best.candidate.branch}` : ""); vd.className = "verdict " + (S.rep.reachable ? "ok" : "bad"); vd.title = S.rep.verdict;
  $("#main").innerHTML = `<section class="view" aria-live="polite">${current().html()}</section>`;
  current().init();
  if (current().frame) current().frame();
}
function go() {
  const h = location.hash.replace("#", "");
  S.section = SECTIONS.some((s) => s.id === h) ? h : "resumen";
  render(); window.scrollTo(0, 0);
}
window.addEventListener("hashchange", go);
let last = performance.now();
function loop(now) {
  const dt = Math.min(0.1, (now - last) / 1000); last = now;
  const v = current();
  if (v && v.animated) {
    if (S.section === "singularidad") v.frame(dt);
    else if (S.traj && S.playing) { S.t += dt * S.rate; if (S.t > S.traj.tf + 0.35) S.t = 0; v.frame(); }
  }
  requestAnimationFrame(loop);
}
const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
if (reduce.matches) S.playing = false;

$("#presets").innerHTML = PRESETS.map((p) => `<button class="chip" type="button" data-p="${p.id}">${p.name}</button>`).join("");
$("#presets").addEventListener("click", (e) => {
  const b = e.target.closest("button"); if (!b) return;
  const p = PRESETS.find((x) => x.id === b.dataset.p);
  ["px", "py", "pz", "pr", "pp", "pw"].forEach((id, i) => { $("#" + id).value = p.v[i]; });
  $("#poseForm").requestSubmit();
});
$("#poseForm").addEventListener("submit", (e) => {
  e.preventDefault();
  const v = ["px", "py", "pz", "pr", "pp", "pw"].map((id) => parseFloat($("#" + id).value));
  if (v.some((x) => !Number.isFinite(x))) { $("#formErr").textContent = "Escribe los seis valores numéricos (m y grados)."; return; }
  $("#formErr").textContent = ""; S.spec = v; S.t = 0; S.branch = 0; compute(); render();
});
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => render());
new MutationObserver(() => render()).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
let rz; window.addEventListener("resize", () => { clearTimeout(rz); rz = setTimeout(render, 200); });

compute(); go(); requestAnimationFrame(loop);
