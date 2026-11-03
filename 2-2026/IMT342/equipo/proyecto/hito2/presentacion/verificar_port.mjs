// Compara irb120.js con los casos de Python (vectores.json). Uso: node presentacion/verificar_port.mjs
import { createRequire } from "module";
import { readFileSync } from "fs";
const require = createRequire(import.meta.url);
const IRB = require("./irb120.js");
const cases = JSON.parse(readFileSync(new URL("./vectores.json", import.meta.url)));
let worst = { q: 0, rank: 0, sv: 0, J: 0, lspb: 0, model: 0, tau: 0 }, fails = 0;
const upd = (k, v) => { if (!(v <= worst[k])) worst[k] = v; };
const maxdiff = (a, b) => Math.max(...a.flat(3).map((v, i) => Math.abs(v - b.flat(3)[i])));
for (const [n, c] of cases.entries()) {
  const rep = IRB.analyzePose(c.T, IRB.HOME_Q);
  if (rep.reachable !== c.verdict_reachable || rep.geometricallyReachable !== c.geo) { fails++; console.log("veredicto", n); }
  rep.candidates.forEach((k, i) => {
    const p = c.cands[i];
    if (k.real !== p.real || k.wrist !== p.wrist || k.singular !== p.singular || JSON.stringify(k.out) !== JSON.stringify(p.out)) { fails++; console.log("rama", n, i + 1, k, p); }
    if (p.qraw) upd("q", maxdiff(k.qRaw, p.qraw));
    if (p.q) upd("q", maxdiff(k.q, p.q));
  });
  const rk = IRB.rankCandidates(rep, IRB.HOME_Q);
  rk.forEach((r, i) => {
    const p = c.rank[i];
    if (r.rank !== p.rank) { fails++; console.log("rank", n, i + 1, r.rank, p.rank); }
    if (p.sigma !== null) upd("rank", Math.max(Math.abs(r.sigmaMin - p.sigma), Math.abs(r.margin - p.margin), Math.abs(r.cost - p.cost), Math.abs(r.tf - p.tf)));
  });
  if (c.qf) {
    const tr = IRB.planLspb(IRB.HOME_Q, c.qf, ...IRB.defaultLimits());
    upd("lspb", Math.max(Math.abs(tr.tf - c.tf), Math.abs(tr.tb - c.tb)));
    c.ts.forEach((t, i) => upd("lspb", maxdiff(tr.sample(t), c.samples[i])));
    upd("J", maxdiff(IRB.geometricJacobian(c.qf), c.J));
    upd("sv", maxdiff(IRB.svd(IRB.geometricJacobian(c.qf)).s, c.sv));
    const m = IRB.shoulderModel(c.qf.map((v) => v / 2));
    upd("model", maxdiff([m.mass, m.lc, m.Ic, m.J, m.phi0], c.model));
    upd("tau", maxdiff(IRB.inverseDynamics(...c.tau_full_q), c.tau_full));
  }
}
console.log(`${cases.length} casos; discrepancias discretas: ${fails}`);
console.log("peores diferencias:", Object.fromEntries(Object.entries(worst).map(([k, v]) => [k, v.toExponential(1)])));
process.exit(fails === 0 && Math.max(...Object.values(worst)) < 1e-6 ? 0 : 1);
