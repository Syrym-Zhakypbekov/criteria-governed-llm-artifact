import { readBusinessCard, cardCriteria } from "@/apps/kafedra/lib/qs/card-ocr";
import { gate } from "@/lib/decision-ledger";
import { readFileSync, writeFileSync } from "node:fs";
const cases = JSON.parse(readFileSync("/tmp/apex/cards/truth.json", "utf8")) as Array<{ file: string; defect: string; truth: Record<string, string> }>;
const norm = (s: string) => String(s ?? "").trim().toLowerCase();
async function main() {
  const out: any[] = [];
  for (const c of cases) {
    const f = "/tmp/apex/cards/" + c.file.split("/").pop();
    const t0 = Date.now();
    try {
      const r = await readBusinessCard(readFileSync(f), "image/png", "research.synthetic");
      const crit = cardCriteria(r.fields, r.inferred ?? []); const g = gate(crit, { confidence: r.confidence });
      const fieldOk: Record<string, boolean> = {};
      for (const k of Object.keys(c.truth)) fieldOk[k] = norm((r.fields as any)[k]) === norm(c.truth[k]) || (k === "country" && norm(c.truth[k]) === "united states" && /united states|usa/.test(norm((r.fields as any)[k])));
      const low = crit.filter((x) => !x.hard && x.s < 1).map((x) => x.code);
      out.push({ id: f.split("/").pop(), defect: c.defect, veto: g.veto, vetoReason: g.vetoReason, state: g.state, sTotal: g.sTotal, low, confidence: r.confidence, fieldOk, inferred: r.inferred, got: r.fields, ms: Date.now() - t0 });
    } catch (e) { out.push({ id: c.file, defect: c.defect, error: String((e as Error).message).slice(0, 200) }); }
    console.log(JSON.stringify(out[out.length - 1]).slice(0, 400));
  }
  writeFileSync("/tmp/apex/cards_results.json", JSON.stringify(out, null, 1));
}
main().catch((e) => { console.error(e); process.exit(1); });
