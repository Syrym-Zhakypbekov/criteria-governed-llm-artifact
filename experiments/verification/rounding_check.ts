// R2.7 (MAKE revision, November 2026): can the 4-decimal rounding of the aggregate in production (src/decision-ledger.ts,
// Math.round(S * 10000) / 10000) change any C4 decision relative to the unrounded aggregate of the offline replay
// (experiments/ablation/ablation_replay.ts)? A decision can differ only if 0.89995 <= S < 0.9 (tau_S = 0.9).
// For every frozen model output (development, held-out 1, held-out 2; both models) this recomputes S with the frozen
// production criteria, applies both gates, and reports any disagreement and the closest distance of S to tau_S.
// Usage (from the repository root): npx tsx experiments/verification/rounding_check.ts   (exit 0 = no decision differs)
import { readFileSync } from "node:fs";
import { jrdCriteria } from "../ablation/apex_jrd_frozen";

const TAU = 0.9;
const clamp01 = (v: number) => Math.max(0, Math.min(1, Number.isFinite(v) ? v : 0));
const files = [
  "frozen_gemini-3.8-flash.json", "frozen_gemini-3.1-flash-lite.json",
  "frozen_h2_gemini-3.8-flash.json", "frozen_h2_gemini-3.1-flash-lite.json",
];
let n = 0, differ = 0, minGap = Infinity, closest = "";
for (const f of files) {
  const recs: any[] = JSON.parse(readFileSync(`experiments/ablation/${f}`, "utf8"));
  for (const r of recs) {
    if (r.error || !r.draft) continue;
    const crit: any[] = jrdCriteria(r.draft) as any[];
    if (crit.some((c) => c.hard && clamp01(c.s) < 1)) { n++; continue; } // vetoed: S does not matter
    let num = 0, den = 0;
    for (const c of crit.filter((c) => !c.hard)) { const w = c.w ?? 1; num += w * clamp01(c.s); den += w; }
    if (den === 0) { n++; continue; }
    const S = num / den, Sr = Math.round(S * 10000) / 10000;
    const replayEsc = S < TAU, prodEsc = Sr < TAU;
    if (replayEsc !== prodEsc) { differ++; console.log(`DIFFERS ${f} ${r.id}: S=${S} rounded=${Sr}`); }
    const gap = Math.abs(S - TAU);
    if (gap < minGap && gap > 0) { minGap = gap; closest = `${f} ${r.id} S=${S.toFixed(6)}`; }
    n++;
  }
}
console.log(`records checked: ${n}; decisions that differ between rounded and unrounded S: ${differ}`);
console.log(`closest non-equal S to tau_S=${TAU}: gap ${minGap.toFixed(6)} (${closest})`);
process.exit(differ ? 1 : 0);
