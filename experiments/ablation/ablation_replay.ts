// ABLATION REPLAY DRIVER (27.10.2026, Codex R14-01/03): identical decision logic to the frozen ablation.ts (hash 883d602a);
// only the probe source, the per-set summary and these comments differ. Final C5 uses source-OR-model applicability, a hard
// BIN-presence check, a graded share of positive unit prices matching source numeric values to 0.01 without item alignment,
// fail-closed handling and a criterion floor; it was revised after held-out-1 results were available and frozen before
// holdout2 was generated and evaluated. Original header of the frozen file follows.
// ABLATION STAGE 2 (27.10.2026): replay five governance configurations on the SAME frozen LLM outputs (freeze_contracts.ts).
// No LLM calls. Configurations are cumulative:
//   C1 LLM only — every output accepted (provisional).
//   C2 + structural check — required fields present with the right type (JSON-schema-like, no semantic rules).
//   C3 + hard veto — BIN of 12 digits, at least one item (production hard criteria).
//   C4 + weighted criteria and escalation — production operator jrdCriteria + gate, tau_S = 0.9 (frozen commit 1114a138).
//   C5 + full operator — (a) applicability decided from the SOURCE text, not from the model output (addendum, third party);
//        criteria that do not apply are left out of S instead of scoring 1; (b) evidence: BIN and every price must occur in the
//        source text; (c) fail-closed: an extraction error, missing output or undefined S is escalated; (d) criterion floor:
//        any applicable soft criterion with s < 0.5 escalates regardless of S (added on the DEV set 27.10 after the first
//        replay showed dilution: an added satisfied criterion lifted S of third-party contracts from 0.889 to 0.900 ≥ tau_S).
// [historical, superseded by the header above] C5 was written before the held-out outputs were inspected; its rules use only document-type keywords and value presence.
// usage: tsx ablation.ts <frozen.json> <out.json>
import { readFileSync, writeFileSync } from "node:fs";
import { jrdCriteria } from "./apex_jrd_frozen";

type Crit = { code: string; s: number; q?: number; hard?: boolean; w?: number };
const clamp01 = (x: unknown) => { const n = Number(x); return Number.isFinite(n) ? Math.max(0, Math.min(1, n)) : 0; };

/** Gate identical to the production gate (artifact_make/src/decision-ledger.ts), plus an option to fail closed on undefined S. */
function gate(cr: Crit[], minScore: number, failClosed = false, floor: number | null = null) {
  const hardFail = cr.filter((c) => c.hard && clamp01(c.s) < 1).map((c) => c.code);
  const soft = cr.filter((c) => !c.hard);
  let num = 0, den = 0;
  for (const c of soft) { const w = c.w ?? 1, q = c.q == null ? 1 : clamp01(c.q); num += w * q * clamp01(c.s); den += w * q; }
  const S = den > 0 ? num / den : null;
  const lowSoft = soft.filter((c) => clamp01(c.s) < 1).map((c) => c.code);
  if (hardFail.length) return { state: "vetoed", S, codes: [...hardFail, ...lowSoft] };
  if (S == null && failClosed) return { state: "escalated", S, codes: ["no_score"] };
  // criterion floor (C5): one applicable criterion far below 1 escalates by itself — a weighted mean must not dilute it
  if (floor != null && soft.some((c) => clamp01(c.s) < floor)) return { state: "escalated", S, codes: lowSoft };
  if (S != null && S < minScore) return { state: "escalated", S, codes: lowSoft };
  return { state: "provisional", S, codes: lowSoft };
}

const digits = (s: string) => s.replace(/\D/g, "");
/** Structural check of the RAW model JSON: presence and type only. */
function structural(raw: any): string[] {
  const f: string[] = [];
  const str = (v: unknown) => typeof v === "string" && v.trim() !== "";
  if (!raw || typeof raw !== "object") return ["schema:root"];
  if (!raw.supplier || typeof raw.supplier !== "object") f.push("schema:supplier");
  else { if (!str(raw.supplier.name)) f.push("schema:supplier.name"); if (!str(String(raw.supplier.bin ?? ""))) f.push("schema:supplier.bin"); }
  if (!raw.contract || typeof raw.contract !== "object") f.push("schema:contract");
  if (!Array.isArray(raw.items) || raw.items.length === 0) f.push("schema:items");
  else raw.items.forEach((it: any, i: number) => {
    if (!str(it?.name)) f.push(`schema:items[${i}].name`);
    if (typeof it?.unit_price_with_vat !== "number" && !(str(it?.unit_price_with_vat) && /\d/.test(it.unit_price_with_vat))) f.push(`schema:items[${i}].price`);
  });
  return f;
}

/** C5 criteria: production criteria with applicability from the source and evidence checks. */
function fullCriteria(d: any, text: string): Crit[] {
  const base: Crit[] = jrdCriteria(d);
  const low = text.toLowerCase();
  // 27.10 fix (found by the Codex review): JS \w does not match Cyrillic, so the first version never detected addenda
  const isAddendum = /дополнительн[а-яё]*\s+соглашени/i.test(low);
  const isTriple = /тр[её]хсторонн|третья сторона/.test(low);
  // applicability = UNION: a criterion applies when the source OR the model output indicates the document type (Codex R13-01)
  const srcDigits = text.match(/\d[\d  ]*\d|\d/g)?.map(digits) ?? [];   // thousands separators only (space, NBSP), never tabs
  const out: Crit[] = [];
  for (const c of base) {
    if (c.code === "addendum_base") {
      if (!isAddendum && !d.contract?.addendum) continue;                 // not applicable: left out of S
      const ok = d.contract?.addendum && d.contract.addendum.baseNumber && d.contract.addendum.baseDate;
      out.push({ ...c, s: ok ? 1 : 0 }); continue;
    }
    if (c.code === "third_party_email") {
      if (!isTriple && !d.thirdParty) continue;
      out.push({ ...c, s: d.thirdParty && d.thirdParty.email ? 1 : 0 }); continue;
    }
    out.push(c);
  }
  const bin = digits(String(d.supplier?.bin ?? ""));
  out.push({ code: "bin_evidence", s: bin.length === 12 && srcDigits.includes(bin) ? 1 : 0, hard: true });
  // v4 (Codex R13-03): exact monetary value to 0.01 (decimal comma or dot, space/NBSP thousands), not integer-rounded;
  // a price counts as evidenced when that exact value occurs among the source numbers (item alignment not checked)
  // separators written as escapes (space, NBSP U+00A0, narrow NBSP U+202F): a typed NBSP silently became a plain space (27.10)
  const srcNums = (text.match(/\d[\d   ]*(?:[.,]\d{1,2})?/g) ?? []).map((t) => Number(t.replace(/[   ]/g, "").replace(",", ".")));
  const prices = (d.items ?? []).map((it: any) => Number(it.unitPriceWithVat) || 0).filter((p: number) => p > 0);
  const evid = prices.length ? prices.filter((p: number) => srcNums.some((n) => Math.abs(n - p) < 0.005)).length / prices.length : 0;
  out.push({ code: "price_evidence", s: d.items?.length ? evid : 1, w: 3 });
  return out;
}

const EXPECT: Record<string, string[]> = {
  bin_short: ["bin", "bin_evidence", "schema:supplier.bin"], bin_missing: ["bin", "bin_evidence", "schema:supplier.bin"], bin_long: ["bin", "bin_evidence"],
  no_items: ["items", "schema:items"], no_price: ["prices", "price_evidence", "schema:items[0].price", "schema:items[1].price", "schema:items[2].price"],
  vat_no_rate: ["vat_explicit"], third_party: ["third_party_email"], addendum_nobase: ["addendum_base"],
};

const [, , inFile, outFile] = process.argv;
const recs: any[] = JSON.parse(readFileSync(inFile, "utf8"));
const rows: any[] = [];
for (const r of recs) {
  const res: Record<string, any> = {};
  const ok = !r.error && r.draft;
  // C1
  res.C1 = { state: ok ? "provisional" : "error", codes: [] };
  // C2
  const sf = ok ? structural(r.raw) : [];
  res.C2 = !ok ? { state: "error", codes: [] } : sf.length ? { state: "escalated", codes: sf } : { state: "provisional", codes: [] };
  // C3 = C2 + hard veto
  const crit = ok ? (jrdCriteria(r.draft) as Crit[]) : [];
  const hard = crit.filter((c) => c.hard && c.s < 1).map((c) => c.code);
  res.C3 = !ok ? { state: "error", codes: [] } : hard.length ? { state: "vetoed", codes: [...hard, ...sf] } : res.C2;
  // C4 = C3 + weighted criteria and escalation (production gate, tau_S = 0.9)
  if (!ok) res.C4 = { state: "error", codes: [] };
  else { const g = gate(crit, 0.9); res.C4 = g.state === "provisional" && sf.length ? { state: "escalated", codes: sf } : { state: g.state, codes: [...g.codes, ...sf] }; }
  // C5 = full operator, fail-closed
  if (!ok) res.C5 = { state: "escalated", codes: ["fail_closed"] };
  else { const g = gate(fullCriteria(r.draft, r.text), 0.9, true, 0.5); res.C5 = g.state === "provisional" && sf.length ? { state: "escalated", codes: sf } : { state: g.state, codes: [...g.codes, ...sf] }; }
  // production operator alone (sanity: must reproduce the paper's held-out numbers)
  res.PROD = ok ? (() => { const g = gate(crit, 0.9); return { state: g.state, codes: g.codes }; })() : { state: "error", codes: [] };
  const defective = r.defects.length > 0;
  for (const [k, v] of Object.entries(res)) {
    v.routed = v.state === "vetoed" || v.state === "escalated";
    v.traced = defective && v.routed ? r.defects.every((d: string) => (EXPECT[d] ?? []).some((code) => v.codes.includes(code))) : null;
  }
  rows.push({ set: r.set, id: r.id, model: r.model, defects: r.defects, defective, error: r.error, ...res });
}
writeFileSync(outFile, JSON.stringify(rows, null, 1));
// PROBES: does each C5 safeguard fire when the model omits what the source says? (counterfactual drafts, no LLM)
{
  const base = recs.find((r) => !r.defects.length && r.draft);
  if (!base) throw new Error("No clean draft available for counterfactual probes");
  const mk = (patch: (d: any) => void, extra: string) => { const d = JSON.parse(JSON.stringify(base.draft)); patch(d); return { d, text: base.text + "\n" + extra }; };
  const probes: Array<[string, { d: any; text: string }]> = [
    ["addendum in source, model omits addendum", mk((d) => { d.contract.addendum = null; }, "ДОПОЛНИТЕЛЬНОЕ СОГЛАШЕНИЕ № 2 к договору (номер и дата основного договора не указаны)")],
    ["three-party in source, model omits third party", mk((d) => { d.thirdParty = null; }, "Договор трёхсторонний. Третья сторона — физическое лицо.")],
    ["BIN padded by the model", mk((d) => { d.supplier.bin = "0" + d.supplier.bin.slice(0, 11); }, "")],
    ["price altered by 0.25 by the model", mk((d) => { d.items[0].unitPriceWithVat = d.items[0].unitPriceWithVat + 0.25; }, "")],
  ];
  for (const [name, p] of probes) {
    const c4 = gate(jrdCriteria(p.d), 0.9), c5 = gate(fullCriteria(p.d, p.text), 0.9, true, 0.5);
    console.log(`PROBE ${name}: C4 ${c4.state} · C5 ${c5.state} (${c5.codes.join(",")})`);
  }
}
const cfgs = ["PROD", "C1", "C2", "C3", "C4", "C5"];
for (const set of [...new Set(rows.map((r) => r.set))]) {
  const R = rows.filter((x) => x.set === set); const D = R.filter((x) => x.defective), C = R.filter((x) => !x.defective);
  console.log(`${set}: ${R.length} docs (${D.length} defective, ${C.length} clean), errors ${R.filter((x) => x.error).length}`);
  for (const c of cfgs) console.log(`  ${c}: routed defective ${D.filter((x) => x[c].routed).length}/${D.length} · traced ${D.filter((x) => x[c].traced).length}/${D.length} · false alarms ${C.filter((x) => x[c].routed).length}/${C.length}`);
}
