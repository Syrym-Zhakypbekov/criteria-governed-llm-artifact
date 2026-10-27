// HELD-OUT business-card evaluation of the FROZEN operator (production card-ocr + cardCriteria + gate, 27.10.2026).
// Expected: no_email / no_org / no_name -> hard veto; no_job -> job_title flagged; no_country -> country or provenance flagged.
// DIR = folder with h*.png + truth.json, OUT = result file.
import { readBusinessCard, cardCriteria } from "@/apps/kafedra/lib/qs/card-ocr";
import { gate } from "@/lib/decision-ledger";
import { readFileSync, writeFileSync } from "node:fs";
const DIR = process.env.DIR!, OUT = process.env.OUT!;
const cases = JSON.parse(readFileSync(DIR + "/truth.json", "utf8")) as Array<{ file: string; defects: string[] }>;
const VETO = ["no_email", "no_org", "no_name"];
async function main() {
  const out: any[] = [];
  for (const c of cases) {
    const t0 = Date.now();
    try {
      const r = await readBusinessCard(readFileSync(DIR + "/" + c.file), "image/png", "research.synthetic");
      const crit = cardCriteria(r.fields, r.inferred ?? []); const g = gate(crit, { confidence: r.confidence });
      const low = crit.filter((x) => !x.hard && x.s < 1).map((x) => x.code);
      const per = c.defects.map((d) => ({ d, hit: VETO.includes(d) ? g.veto && String(g.vetoReason ?? "").length > 0
        : d === "no_job" ? low.includes("job_title") : low.includes("country") || low.includes("provenance") }));
      out.push({ id: c.file, defects: c.defects, veto: g.veto, vetoReason: g.vetoReason, state: g.state, sTotal: g.sTotal, low, inferred: r.inferred, per,
        flagged: g.state !== "provisional" || low.length > 0, routed: g.state === "vetoed" || g.state === "escalated", got: r.fields, ms: Date.now() - t0 });
    } catch (e) { out.push({ id: c.file, defects: c.defects, error: String((e as Error).message).slice(0, 200) }); }
    console.log(JSON.stringify(out[out.length - 1]).slice(0, 300));
  }
  writeFileSync(OUT, JSON.stringify(out, null, 1));
}
main().catch((e) => { console.error(e); process.exit(1); });
