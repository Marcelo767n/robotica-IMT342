/* irb120.js — traducción a JavaScript del paquete Python hito2/irb120 (mismas fórmulas, mismos nombres).
 * Se verifica contra Python con presentacion/verificar_port.mjs (vectores generados por generar_vectores.py).
 * Funciona en el navegador (global IRB) y en Node (module.exports).
 */
(function (root) {
  "use strict";
  const PI = Math.PI;

  // ------------------------------------------------------------------ álgebra mínima
  const eye = (n) => Array.from({ length: n }, (_, i) => Array.from({ length: n }, (_, j) => (i === j ? 1 : 0)));
  const matmul = (A, B) => A.map((row) => B[0].map((_, j) => row.reduce((s, a, k) => s + a * B[k][j], 0)));
  const transpose = (A) => A[0].map((_, j) => A.map((row) => row[j]));
  const matvec = (A, v) => A.map((row) => row.reduce((s, a, k) => s + a * v[k], 0));
  const dot = (a, b) => a.reduce((s, x, i) => s + x * b[i], 0);
  const norm = (a) => Math.sqrt(dot(a, a));
  const sub = (a, b) => a.map((x, i) => x - b[i]);
  const add = (a, b) => a.map((x, i) => x + b[i]);
  const scale = (a, s) => a.map((x) => x * s);
  const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const rot = (T) => T.slice(0, 3).map((r) => r.slice(0, 3));
  const pos = (T) => [T[0][3], T[1][3], T[2][3]];
  const col = (T, k) => [T[0][k], T[1][k], T[2][k]];
  const mod = (x, m) => ((x % m) + m) % m;
  const wrapPi = (a) => mod(a + PI, 2 * PI) - PI; // igual que Python: (a + pi) % (2 pi) - pi
  const deg = (r) => (r * 180) / PI;
  const rad = (d) => (d * PI) / 180;

  // ------------------------------------------------------------------ dh.py
  const DH = [
    { d: 0.29, a: 0.0, alpha: -PI / 2, off: 0 },
    { d: 0.0, a: 0.27, alpha: 0.0, off: -PI / 2 },
    { d: 0.0, a: 0.07, alpha: -PI / 2, off: 0 },
    { d: 0.302, a: 0.0, alpha: PI / 2, off: 0 },
    { d: 0.0, a: 0.0, alpha: -PI / 2, off: 0 },
    { d: 0.072, a: 0.0, alpha: 0.0, off: PI },
  ];
  const TCP_Z_M = 0.15;
  const LIMITS_DEG = [[-165, 165], [-110, 110], [-110, 70], [-160, 160], [-120, 120], [-400, 400]];
  const LIMITS = LIMITS_DEG.map(([a, b]) => [rad(a), rad(b)]);
  const MAX_SPEED_DEG = [250, 250, 250, 320, 320, 420];
  const MAX_SPEED = MAX_SPEED_DEG.map(rad);
  const HOME_Q = [0, 0, 0, 0, 0, 0];

  function dhTransform(theta, p) {
    const t = theta + p.off, ct = Math.cos(t), st = Math.sin(t), ca = Math.cos(p.alpha), sa = Math.sin(p.alpha);
    return [
      [ct, -st * ca, st * sa, p.a * ct],
      [st, ct * ca, -ct * sa, p.a * st],
      [0, sa, ca, p.d],
      [0, 0, 0, 1],
    ];
  }
  function jointFrames(q) {
    const F = [eye(4)];
    for (let i = 0; i < 6; i++) F.push(matmul(F[i], dhTransform(q[i], DH[i])));
    return F;
  }
  const forwardKinematics = (q) => jointFrames(q)[6];
  function tcpTransform() { const T = eye(4); T[2][3] = TCP_Z_M; return T; }
  const forwardKinematicsTcp = (q) => matmul(forwardKinematics(q), tcpTransform());
  const positionError = (A, B) => norm(sub(pos(A), pos(B)));
  function rotationError(A, B) {
    const R = matmul(transpose(rot(A)), rot(B));
    const c = (R[0][0] + R[1][1] + R[2][2] - 1) / 2;
    const s = norm([R[2][1] - R[1][2], R[0][2] - R[2][0], R[1][0] - R[0][1]]) / 2;
    return Math.atan2(s, Math.max(-1, Math.min(1, c)));
  }

  // ------------------------------------------------------------------ transforms.py
  function rpyToMatrix(r, p, y) {
    const cr = Math.cos(r), sr = Math.sin(r), cp = Math.cos(p), sp = Math.sin(p), cy = Math.cos(y), sy = Math.sin(y);
    const Rx = [[1, 0, 0], [0, cr, -sr], [0, sr, cr]];
    const Ry = [[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]];
    const Rz = [[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]];
    return matmul(matmul(Rz, Ry), Rx);
  }
  function poseFromXyzRpyDeg(x, y, z, r, p, yaw) {
    const R = rpyToMatrix(rad(r), rad(p), rad(yaw));
    return [[...R[0], x], [...R[1], y], [...R[2], z], [0, 0, 0, 1]];
  }
  function assertRigid(T, tol = 1e-6) {
    if (!Array.isArray(T) || T.length !== 4 || T.some((r) => r.length !== 4)) throw new Error("La pose debe ser una matriz 4x4.");
    if (T.flat().some((v) => !Number.isFinite(v))) throw new Error("La pose contiene valores no finitos.");
    if ([0, 0, 0, 1].some((v, i) => Math.abs(T[3][i] - v) > tol)) throw new Error("La última fila debe ser [0, 0, 0, 1].");
    const R = rot(T), RtR = matmul(transpose(R), R);
    const orth = Math.max(...RtR.flatMap((r, i) => r.map((v, j) => Math.abs(v - (i === j ? 1 : 0)))));
    if (orth > tol) throw new Error(`R no es ortonormal (max|RᵀR − I| = ${orth.toExponential(2)}).`);
    const det = det3(R);
    if (Math.abs(det - 1) > tol) throw new Error(`det(R) = ${det.toFixed(6)}; una rotación propia exige +1.`);
    return T;
  }
  const det3 = (R) =>
    R[0][0] * (R[1][1] * R[2][2] - R[1][2] * R[2][1]) - R[0][1] * (R[1][0] * R[2][2] - R[1][2] * R[2][0]) +
    R[0][2] * (R[1][0] * R[2][1] - R[1][1] * R[2][0]);

  // ------------------------------------------------------------------ validation.py
  const TOL_P = 1e-6, TOL_R = 1e-6;
  function fkCheck(target, q, tcp = true) {
    const T = tcp ? forwardKinematicsTcp(q) : forwardKinematics(q);
    const ep = positionError(target, T), eR = rotationError(target, T);
    const eF = Math.sqrt(T.flat().reduce((s, v, i) => s + (v - target.flat()[i]) ** 2, 0));
    return { ep, eR, eF, accepted: ep < TOL_P && eR < TOL_R };
  }

  // ------------------------------------------------------------------ pieper.py
  const D1 = DH[0].d, L2 = DH[1].a, A3 = DH[2].a, D4 = DH[3].d, D6 = DH[5].d;
  const L3 = Math.hypot(D4, A3), DELTA = Math.atan2(A3, D4);
  const REACH_MIN = Math.abs(L2 - L3), REACH_MAX = L2 + L3;

  function fitToLimits(angle, lo, hi, ref) {
    let best = null;
    for (let k = -3; k <= 3; k++) {
      const c = angle + 2 * PI * k;
      if (c >= lo - 1e-9 && c <= hi + 1e-9 && (best === null || Math.abs(c - ref) < Math.abs(best - ref))) best = c;
    }
    return best;
  }
  function wristCenter(T) { const z = col(T, 2); return sub(pos(T), scale(z, D6)); }
  function armBranches(W) {
    const [x, y, z] = W, planar = Math.hypot(x, y), height = z - D1, out = [];
    for (const [arm, q1, radial] of [["frente", Math.atan2(y, x), planar], ["atras", Math.atan2(y, x) + PI, -planar]]) {
      const c = (radial * radial + height * height - L2 * L2 - L3 * L3) / (2 * L2 * L3);
      if (Math.abs(c) > 1 + 1e-12) {
        for (const elbow of ["arriba", "abajo"]) out.push({ arm, elbow, real: false, c, q: [NaN, NaN, NaN] });
        continue;
      }
      const base = Math.asin(-Math.max(-1, Math.min(1, c))), alpha = Math.atan2(radial, height);
      for (const [elbow, q3md] of [["arriba", base], ["abajo", PI - base]]) {
        const q3 = wrapPi(q3md + DELTA), eta = PI / 2 + q3 - DELTA;
        const q2 = wrapPi(alpha - Math.atan2(L3 * Math.sin(eta), L2 + L3 * Math.cos(eta)));
        out.push({ arm, elbow, real: true, c, q: [wrapPi(q1), q2, q3] });
      }
    }
    return out;
  }
  function rotation03(q1, q2, q3) {
    let T = eye(4);
    [q1, q2, q3].forEach((a, i) => { T = matmul(T, dhTransform(a, DH[i])); });
    return rot(T);
  }
  function wristSolutions(R, q4ref) {
    const sb = Math.hypot(R[0][2], R[1][2]);
    if (sb < 1e-9) {
      if (R[2][2] < 0) {
        const diff = Math.atan2(-R[1][0], -R[0][0]), q6 = wrapPi(q4ref - diff - PI);
        return [["q5+", q4ref, -PI, q6, true], ["q5-", q4ref, -PI, q6, true]];
      }
      const total = Math.atan2(R[1][0], R[0][0]);
      return [["q5+", q4ref, 0, wrapPi(total - q4ref - PI), true], ["q5-", wrapPi(q4ref + PI), 0, wrapPi(total - q4ref - 2 * PI), true]];
    }
    const cb = R[2][2], out = [];
    for (const [wrist, s] of [["q5+", -1], ["q5-", 1]]) {
      const beta = Math.atan2(s * sb, cb), alpha = Math.atan2(s * R[1][2], s * R[0][2]);
      const gamma = Math.atan2(s * R[2][1], -s * R[2][0]);
      out.push([wrist, alpha, -beta, wrapPi(gamma - PI), false]);
    }
    return out;
  }
  function tool0FromTcp(Ttcp) { const Tinv = eye(4); Tinv[2][3] = -TCP_Z_M; return matmul(Ttcp, Tinv); }
  function enumerateCandidates(Ttool0, ref = HOME_Q) {
    const T = assertRigid(Ttool0), R = rot(T), cands = [];
    for (const b of armBranches(wristCenter(T))) {
      if (!b.real) {
        for (const wrist of ["q5+", "q5-"]) cands.push({ branch: cands.length + 1, arm: b.arm, elbow: b.elbow, wrist, real: false, qRaw: null, q: null, out: [], singular: false, c: b.c });
        continue;
      }
      const R36 = matmul(transpose(rotation03(...b.q)), R);
      for (const [wrist, q4, q5, q6, singular] of wristSolutions(R36, ref[3])) {
        const raw = [...b.q, q4, q5, q6];
        const fitted = raw.map((a, i) => fitToLimits(a, LIMITS[i][0], LIMITS[i][1], ref[i]));
        const out = fitted.map((v, i) => (v === null ? i + 1 : 0)).filter(Boolean);
        cands.push({ branch: cands.length + 1, arm: b.arm, elbow: b.elbow, wrist, real: true, qRaw: raw, q: out.length ? null : fitted, out, singular, c: b.c });
      }
    }
    return cands;
  }
  function analyzePose(Ttcp, ref = HOME_Q) {
    assertRigid(Ttcp);
    const T0 = tool0FromTcp(Ttcp), cands = enumerateCandidates(T0, ref);
    const checks = cands.map((c) => (c.real ? fkCheck(Ttcp, c.q || c.qRaw) : null));
    const W = wristCenter(T0), dist = Math.hypot(Math.hypot(W[0], W[1]), W[2] - D1);
    const accepted = (c) => c.real && c.q !== null && checks[c.branch - 1] && checks[c.branch - 1].accepted;
    const admissible = cands.filter(accepted);
    let verdict;
    if (admissible.length) verdict = `ALCANZABLE: ${admissible.length} de 8 ramas son admisibles.`;
    else if (!cands.some((c) => c.real)) verdict = `NO ALCANZABLE: la distancia hombro–muñeca ${dist.toFixed(4)} m está fuera de [${REACH_MIN.toFixed(3)}, ${REACH_MAX.toFixed(3)}] m.`;
    else {
      const blocked = [...new Set(cands.filter((c) => c.real).flatMap((c) => c.out))].sort((a, b) => a - b);
      verdict = `NO ALCANZABLE: existe geométricamente, pero todas las ramas violan límites articulares (juntas ${blocked.join(", ")}).`;
    }
    return { Ttcp, T0, W, dist, candidates: cands, checks, accepted, admissible, reachable: admissible.length > 0, geometricallyReachable: cands.some((c) => c.real), verdict };
  }
  const limitMarginDeg = (q) => deg(Math.min(...q.map((v, i) => Math.min(v - LIMITS[i][0], LIMITS[i][1] - v))));
  const WEIGHTS = [1, 1, 1, 0.5, 0.5, 0.5];
  function rankCandidates(report, ref = HOME_Q, minSigma = 1e-2, minMargin = 5) {
    const [vmax, amax] = defaultLimits();
    const rows = report.candidates.map((c) => {
      if (!report.accepted(c)) {
        const reason = !c.real ? "descartada: no existe (|c| > 1)" : c.q === null ? "descartada: fuera de límites J" + c.out.join(",") : "descartada: no pasa la FK";
        return { candidate: c, admissible: false, sigmaMin: NaN, margin: NaN, cost: NaN, tf: NaN, status: reason, rank: null };
      }
      return {
        candidate: c, admissible: true, sigmaMin: svd(geometricJacobian(c.q)).s[5], margin: limitMarginDeg(c.q),
        cost: norm(c.q.map((v, i) => WEIGHTS[i] * (v - ref[i]))), tf: planLspb(ref, c.q, vmax, amax).tf, status: "", rank: null,
      };
    });
    const adm = rows.filter((r) => r.admissible);
    let pool = [], note = "";
    for (const [rm, rs, n] of [[false, false, ""], [true, false, " (margen relajado)"], [true, true, " (margen y σ relajados)"]]) {
      pool = adm.filter((r) => (rs || r.sigmaMin >= minSigma) && (rm || r.margin >= minMargin));
      note = n;
      if (pool.length || !adm.length) break;
    }
    for (const r of adm) if (!pool.includes(r)) r.status = r.sigmaMin < minSigma ? `descartada: cerca de singularidad (σmin < ${minSigma})` : `descartada: a menos de ${minMargin}° de un límite`;
    pool.sort((a, b) => a.cost - b.cost || b.sigmaMin - a.sigmaMin);
    pool.forEach((r, i) => { r.rank = i + 1; r.status = i === 0 ? "ELEGIDA" + note : `apta (puesto ${i + 1})`; });
    return rows;
  }

  // ------------------------------------------------------------------ lspb.py
  function defaultLimits(speedScale = 0.25, ramp = 0.25) {
    const vmax = MAX_SPEED.map((v) => v * speedScale);
    return [vmax, vmax.map((v) => v / ramp)];
  }
  function lspb(q0, qf, tf, tb) {
    const D = sub(qf, q0), V = D.map((d) => d / (tf - tb)), A = V.map((v) => v / tb);
    const zero = q0.map(() => 0);
    function sample(t) {
      if (t < 0) return [q0.slice(), zero.slice(), zero.slice()];
      if (t > tf) return [qf.slice(), zero.slice(), zero.slice()];
      if (t < tb) return [q0.map((q, i) => q + 0.5 * A[i] * t * t), A.map((a) => a * t), A.slice()];
      if (t <= tf - tb) return [q0.map((q, i) => q + V[i] * (t - 0.5 * tb)), V.slice(), zero.slice()];
      const r = tf - t;
      return [qf.map((q, i) => q - 0.5 * A[i] * r * r), A.map((a) => a * r), A.map((a) => -a)];
    }
    const phase = (t) => (t < 0 || t > tf ? "reposo" : t < tb ? "acelera" : t <= tf - tb ? "crucero" : "frena");
    return { q0, qf, tf, tb, V, A, sample, phase };
  }
  function planLspb(q0, qf, vmax, amax) {
    const dist = sub(qf, q0).map(Math.abs);
    if (Math.max(...dist) === 0) return lspb(q0, qf, 1, 0.5);
    const K = Math.max(...dist.map((d, i) => d / amax[i])), Dv = Math.max(...dist.map((d, i) => d / vmax[i]));
    const blend = (tf) => 0.5 * (tf - Math.sqrt(tf * tf - 4 * K));
    const feasible = (tf) => tf * tf >= 4 * K && blend(tf) <= tf - Dv + 1e-12;
    let low = Math.max(2 * Math.sqrt(K), Dv), high = 2 * low + 1;
    while (!feasible(high)) high *= 2;
    if (feasible(low)) high = low;
    else for (let i = 0; i < 100; i++) { const m = 0.5 * (low + high); if (feasible(m)) high = m; else low = m; }
    return lspb(q0, qf, high, blend(high));
  }

  // ------------------------------------------------------------------ jacobian.py
  function geometricJacobian(q, reference = "tcp") {
    const F = jointFrames(q);
    let p;
    if (reference === "tcp") p = matvec(F[6], [0, 0, TCP_Z_M, 1]).slice(0, 3);
    else if (reference === "tool0") p = pos(F[6]);
    else p = pos(F[4]);
    const J = Array.from({ length: 6 }, () => Array(6).fill(0));
    for (let i = 0; i < 6; i++) {
      const z = col(F[i], 2), v = cross(z, sub(p, pos(F[i])));
      for (let r = 0; r < 3; r++) { J[r][i] = v[r]; J[r + 3][i] = z[r]; }
    }
    return J;
  }
  function numericalJacobian(q, h = 1e-6) {
    const R = rot(forwardKinematicsTcp(q)), J = Array.from({ length: 6 }, () => Array(6).fill(0));
    for (let i = 0; i < 6; i++) {
      const qp = q.slice(), qm = q.slice(); qp[i] += h; qm[i] -= h;
      const P = forwardKinematicsTcp(qp), M = forwardKinematicsTcp(qm);
      const v = scale(sub(pos(P), pos(M)), 1 / (2 * h));
      const dR = rot(P).map((row, a) => row.map((x, b) => (x - rot(M)[a][b]) / (2 * h)));
      const S = matmul(dR, transpose(R));
      const w = [S[2][1], S[0][2], S[1][0]];
      for (let r = 0; r < 3; r++) { J[r][i] = v[r]; J[r + 3][i] = w[r]; }
    }
    return J;
  }
  // SVD por Jacobi de un lado (Hestenes): A V = U S. Devuelve s (desc), V (columnas) y U (columnas).
  function svd(Ain) {
    const m = Ain.length, n = Ain[0].length;
    const A = Ain.map((r) => r.slice()), V = eye(n);
    for (let sweep = 0; sweep < 80; sweep++) {
      let off = 0;
      for (let p = 0; p < n - 1; p++) for (let qq = p + 1; qq < n; qq++) {
        let alpha = 0, beta = 0, gamma = 0;
        for (let i = 0; i < m; i++) { alpha += A[i][p] ** 2; beta += A[i][qq] ** 2; gamma += A[i][p] * A[i][qq]; }
        if (Math.abs(gamma) <= 1e-300 || Math.abs(gamma) < 1e-15 * Math.sqrt(alpha * beta)) continue;
        off = Math.max(off, Math.abs(gamma) / Math.sqrt(alpha * beta));
        const zeta = (beta - alpha) / (2 * gamma), t = Math.sign(zeta || 1) / (Math.abs(zeta) + Math.sqrt(1 + zeta * zeta));
        const c = 1 / Math.sqrt(1 + t * t), s = c * t;
        for (let i = 0; i < m; i++) { const a = A[i][p], b = A[i][qq]; A[i][p] = c * a - s * b; A[i][qq] = s * a + c * b; }
        for (let i = 0; i < n; i++) { const a = V[i][p], b = V[i][qq]; V[i][p] = c * a - s * b; V[i][qq] = s * a + c * b; }
      }
      if (off < 1e-15) break;
    }
    const sv = Array.from({ length: n }, (_, j) => Math.sqrt(A.reduce((s, r) => s + r[j] ** 2, 0)));
    const order = sv.map((_, j) => j).sort((a, b) => sv[b] - sv[a]);
    const s = order.map((j) => sv[j]);
    const Vc = order.map((j) => V.map((r) => r[j])); // columnas de V
    const Uc = order.map((j) => (sv[j] > 1e-12 * (s[0] || 1) ? A.map((r) => r[j] / sv[j]) : null));
    // columnas de U faltantes (σ ≈ 0): completar con el complemento ortogonal (Gram-Schmidt)
    for (let k = 0; k < Uc.length; k++) if (!Uc[k]) {
      for (let e = 0; e < m && !Uc[k]; e++) {
        let u = Array.from({ length: m }, (_, i) => (i === e ? 1 : 0));
        for (const w of Uc) if (w) u = sub(u, scale(w, dot(u, w)));
        if (norm(u) > 1e-6) Uc[k] = scale(u, 1 / norm(u));
      }
    }
    return { s, V: Vc, U: Uc };
  }
  const RANK_TOL = 1e-6;
  function rankAnalysis(J, tol = RANK_TOL) {
    const d = svd(J), rank = d.s.filter((x) => x > tol).length;
    return { s: d.s, rank, lost: d.U.slice(rank), nullMotions: d.V.slice(rank), cond: d.s[5] === 0 ? Infinity : d.s[0] / d.s[5], U: d.U, V: d.V };
  }
  function solve(Ain, b) { // Gauss con pivoteo parcial
    const n = b.length, A = Ain.map((r, i) => [...r, b[i]]);
    for (let k = 0; k < n; k++) {
      let p = k; for (let i = k + 1; i < n; i++) if (Math.abs(A[i][k]) > Math.abs(A[p][k])) p = i;
      [A[k], A[p]] = [A[p], A[k]];
      for (let i = k + 1; i < n; i++) { const f = A[i][k] / A[k][k]; for (let j = k; j <= n; j++) A[i][j] -= f * A[k][j]; }
    }
    const x = Array(n).fill(0);
    for (let i = n - 1; i >= 0; i--) x[i] = (A[i][n] - A[i].slice(i + 1, n).reduce((s, a, j) => s + a * x[i + 1 + j], 0)) / A[i][i];
    return x;
  }
  const det = (M) => { // det por eliminación
    const n = M.length, A = M.map((r) => r.slice()); let d = 1;
    for (let k = 0; k < n; k++) {
      let p = k; for (let i = k + 1; i < n; i++) if (Math.abs(A[i][k]) > Math.abs(A[p][k])) p = i;
      if (A[p][k] === 0) return 0;
      if (p !== k) { [A[k], A[p]] = [A[p], A[k]]; d = -d; }
      d *= A[k][k];
      for (let i = k + 1; i < n; i++) { const f = A[i][k] / A[k][k]; for (let j = k; j < n; j++) A[i][j] -= f * A[k][j]; }
    }
    return d;
  };
  const armPositionDeterminant = (q) => det(geometricJacobian(q, "wrist").slice(0, 3).map((r) => r.slice(0, 3)));

  // ------------------------------------------------------------------ dynamics.py (datos CAD Truc & Lam 2020 + pinza SMC)
  const G = 9.81;
  const diag3 = (a, b, c, s) => [[a * s, 0, 0], [0, b * s, 0], [0, 0, c * s]];
  const PAPER_LINKS = [
    { m: 4.248, c: [0, 0.054, 0], I: diag3(19.699, 14.484, 19.952, 1e-3) },
    { m: 5.412, c: [-0.169, 0, 0], I: diag3(35.942, 83.522, 57.569, 1e-3) },
    { m: 4.077, c: [-0.012, 0, 0.023], I: [[17.562e-3, 0, -1.993e-3], [0, 23.14e-3, 0], [-1.993e-3, 0, 11.589e-3]] },
    { m: 1.832, c: [0, -0.007, 0], I: diag3(7.247, 3.919, 5.551, 1e-3) },
    { m: 0.755, c: [0, 0, 0], I: diag3(1.12, 1.227, 0.559, 1e-3) },
    { m: 0.019, c: [0, 0, -0.007], I: diag3(2.347, 2.347, 4.123, 1e-6) },
  ];
  const GRIPPER_MASS = 0.115, GRIPPER_COM = [0, 0, 0.04];
  const parallelAxis = (I, m, d) => I.map((r, i) => r.map((v, j) => v + m * ((i === j ? dot(d, d) : 0) - d[i] * d[j])));
  const LINKS = (() => {
    const w = PAPER_LINKS[5], m = w.m + GRIPPER_MASS;
    const c = add(scale(w.c, w.m), scale(GRIPPER_COM, GRIPPER_MASS)).map((v) => v / m);
    let I = parallelAxis(w.I, w.m, sub(w.c, c));
    I = parallelAxis(I, GRIPPER_MASS, sub(GRIPPER_COM, c));
    return [...PAPER_LINKS.slice(0, 5), { m, c, I }];
  })();
  function comJacobians(q) {
    const F = jointFrames(q);
    return LINKS.map((L, k) => {
      const T = F[k + 1], p = matvec(T, [...L.c, 1]).slice(0, 3);
      const Jv = [[], [], []], Jw = [[], [], []];
      for (let j = 0; j < 6; j++) {
        const z = col(F[j], 2), v = j <= k ? cross(z, sub(p, pos(F[j]))) : [0, 0, 0], w = j <= k ? z : [0, 0, 0];
        for (let r = 0; r < 3; r++) { Jv[r][j] = v[r]; Jw[r][j] = w[r]; }
      }
      return { Jv, Jw, R: rot(T) };
    });
  }
  function massMatrix(q) {
    let M = Array.from({ length: 6 }, () => Array(6).fill(0));
    comJacobians(q).forEach(({ Jv, Jw, R }, k) => {
      const Ib = matmul(matmul(R, LINKS[k].I), transpose(R));
      const A = matmul(transpose(Jv), Jv), B = matmul(matmul(transpose(Jw), Ib), Jw);
      M = M.map((r, i) => r.map((v, j) => v + LINKS[k].m * A[i][j] + B[i][j]));
    });
    return M.map((r, i) => r.map((v, j) => 0.5 * (v + M[j][i])));
  }
  function gravityVector(q) {
    const g = Array(6).fill(0);
    comJacobians(q).forEach(({ Jv }, k) => { for (let j = 0; j < 6; j++) g[j] += LINKS[k].m * G * Jv[2][j]; });
    return g;
  }
  function coriolisVector(q, qd, h = 1e-6) {
    const dM = [];
    for (let k = 0; k < 6; k++) {
      const qp = q.slice(), qm = q.slice(); qp[k] += h; qm[k] -= h;
      const P = massMatrix(qp), Mm = massMatrix(qm);
      dM.push(P.map((r, i) => r.map((v, j) => (v - Mm[i][j]) / (2 * h))));
    }
    const mdq = Array(6).fill(0);
    for (let k = 0; k < 6; k++) { const t = matvec(dM[k], qd); for (let i = 0; i < 6; i++) mdq[i] += qd[k] * t[i]; }
    const grad = dM.map((D) => dot(qd, matvec(D, qd)));
    return mdq.map((v, i) => v - 0.5 * grad[i]);
  }
  const inverseDynamics = (q, qd, qdd) => add(add(matvec(massMatrix(q), qdd), coriolisVector(q, qd)), gravityVector(q));

  // ------------------------------------------------------------------ dynamics_1r.py
  function shoulderModel(qRef) {
    const F = jointFrames(qRef), axis = col(F[1], 2), origin = pos(F[1]);
    let mass = 0, first = [0, 0, 0], Iaxis = 0;
    for (let n = 2; n <= 6; n++) {
      const L = LINKS[n - 1], T = F[n], c = matvec(T, [...L.c, 1]).slice(0, 3), R = rot(T), off = sub(c, origin);
      const Ib = matmul(matmul(R, L.I), transpose(R));
      Iaxis += dot(axis, matvec(Ib, axis)) + L.m * (dot(off, off) - dot(off, axis) ** 2);
      mass += L.m; first = add(first, scale(off, L.m));
    }
    const r = scale(first, 1 / mass), rp = sub(r, scale(axis, dot(r, axis))), lc = norm(rp);
    const DOWN = [0, 0, -1], theta = Math.atan2(dot(axis, cross(DOWN, rp)), dot(DOWN, rp));
    const Ic = Iaxis - mass * lc * lc, J = Ic + mass * lc * lc, phi0 = theta - qRef[1];
    const components = (q2, q2dd) => { const ti = J * q2dd, tg = mass * G * lc * Math.sin(q2 + phi0); return [ti, tg, ti + tg]; };
    return { mass, lc, Ic, J, phi0, qRef, mglc: mass * G * lc, components, theta: (q2) => q2 + phi0 };
  }

  // ------------------------------------------------------------------ rosi_model.py (verificación independiente)
  const ROSI = [[[0, 0, 0], [0, 0, 1]], [[0, 0, 0.29], [0, 1, 0]], [[0, 0, 0.27], [0, 1, 0]], [[0, 0, 0.07], [1, 0, 0]], [[0.302, 0, 0], [0, 1, 0]], [[0.072, 0, 0], [1, 0, 0]]];
  function axisRot(a, t) {
    const [x, y, z] = a, K = [[0, -z, y], [z, 0, -x], [-y, x, 0]], K2 = matmul(K, K);
    return eye(3).map((r, i) => r.map((v, j) => v + Math.sin(t) * K[i][j] + (1 - Math.cos(t)) * K2[i][j]));
  }
  function rosiForwardKinematics(q) {
    let T = eye(4);
    ROSI.forEach(([xyz, ax], i) => { const R = axisRot(ax, q[i]); T = matmul(T, [[...R[0], xyz[0]], [...R[1], xyz[1]], [...R[2], xyz[2]], [0, 0, 0, 1]]); });
    const R = axisRot([0, 1, 0], PI / 2);
    return matmul(T, [[...R[0], 0], [...R[1], 0], [...R[2], 0], [0, 0, 0, 1]]);
  }

  const API = {
    PI, deg, rad, wrapPi, matmul, transpose, matvec, dot, norm, sub, add, scale, cross, rot, pos, col, eye, solve, det,
    DH, TCP_Z_M, LIMITS, LIMITS_DEG, MAX_SPEED, MAX_SPEED_DEG, HOME_Q, D1, L2, L3, DELTA, REACH_MIN, REACH_MAX,
    dhTransform, jointFrames, forwardKinematics, forwardKinematicsTcp, positionError, rotationError,
    rpyToMatrix, poseFromXyzRpyDeg, assertRigid, fkCheck, TOL_P, TOL_R,
    wristCenter, armBranches, wristSolutions, enumerateCandidates, analyzePose, rankCandidates, limitMarginDeg, WEIGHTS,
    defaultLimits, planLspb, lspb, geometricJacobian, numericalJacobian, svd, rankAnalysis, RANK_TOL, armPositionDeterminant,
    LINKS, massMatrix, gravityVector, coriolisVector, inverseDynamics, shoulderModel, rosiForwardKinematics,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = API;
  else root.IRB = API;
})(typeof window !== "undefined" ? window : globalThis);
