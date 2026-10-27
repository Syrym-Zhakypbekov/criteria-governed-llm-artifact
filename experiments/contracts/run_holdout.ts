// HELD-OUT evaluation of the FROZEN contract operator (production code at commit 1114a138, tau_S = 0.9), written 27.10.2026
// AFTER all design iterations: new supplier names, different document layout (tab table, reordered columns, prices with
// spaces and currency), a new defect type (13-digit BIN) and compound defects. Synthetic data only. OUT env = result file.
import { extractJrd, jrdCriteria } from "@/apps/legal/lib/jrd-extract";
import { gate } from "@/lib/decision-ledger";
import { writeFileSync } from "node:fs";

type D = "bin_short" | "bin_missing" | "bin_long" | "no_items" | "no_price" | "vat_no_rate" | "third_party" | "addendum_nobase";
const VETO: D[] = ["bin_short", "bin_missing", "bin_long", "no_items"];
const LOW: Record<string, string> = { no_price: "prices", vat_no_rate: "vat_explicit", third_party: "third_party_email", addendum_nobase: "addendum_base" };
const goods = [["Тонер-картридж Canon 725", 8, "шт.", 21500], ["Флеш-накопитель 64 ГБ", 30, "шт.", 4900], ["Бумага А3 80 г/м²", 12, "пачка", 5600],
  ["Клавиатура проводная USB", 15, "шт.", 7300], ["Мышь оптическая", 15, "шт.", 3900], ["Удлинитель сетевой 5 м", 10, "шт.", 4200], ["Скотч упаковочный 48 мм", 40, "рулон", 650]];
const names = ["ТОО «Омега Ресурс Пример»", "ИП «Каппа Трейд Синтетик»", "ТОО «Сигма Снабжение Демо»", "ИП «Тау Офис Модель»", "ТОО «Лямбда Поставка Тест»"];
const money = (v: number) => v.toLocaleString("ru-RU").replace(/ /g, " ") + " тг";
function doc(i: number, defects: D[]) {
  const name = names[i % names.length]; const b = String(870000000000 + i * 104729).slice(0, 12);
  let rows = goods.slice(i % 4, (i % 4) + 3).map((g) => [...g]) as any[];
  let bin = `БИН/ИИН поставщика: ${b}`; let vat = "Все цены включают НДС 16%."; const extra: string[] = [];
  for (const d of defects) {
    if (d === "bin_short") bin = `БИН/ИИН поставщика: ${b.slice(0, 11)}`;
    if (d === "bin_missing") bin = "";
    if (d === "bin_long") bin = `БИН/ИИН поставщика: ${b}7`;
    if (d === "no_items") rows = [];
    if (d === "no_price" && rows.length) rows[rows.length - 1][3] = "";
    if (d === "vat_no_rate") vat = "Цены указаны с НДС.";
    if (d === "third_party") extra.push("Договор трёхсторонний. Третья сторона — физическое лицо: Примеров Пример Примерович, ИИН 880202000000, получатель поставки.");
    if (d === "addendum_nobase") extra.push("Документ оформляется как ДОПОЛНИТЕЛЬНОЕ СОГЛАШЕНИЕ к ранее заключённому договору (реквизиты основного договора будут сообщены позже).");
  }
  const table = ["Наименование\tКол-во\tЕд.\tЦена с НДС", ...rows.map((r) => `${r[0]}\t${r[1]}\t${r[2]}\t${r[3] === "" ? "" : money(r[3])}`)].join("\n");
  const text = ["СПЕЦИФИКАЦИЯ К ЗАКУПКЕ (синтетический документ для исследования)", `Поставщик: ${name}`, bin, `Контакт для подписания: director${i}@example.org`,
    "Руководитель: Примеров П.П.", vat, ...extra, "", table].filter((l) => l !== "").join("\n");
  return { id: `${defects.join("+") || "clean"}-h${i}`, defects, text };
}
const plan: D[][] = [];
for (let k = 0; k < 10; k++) plan.push([]);
for (const d of ["bin_short", "bin_missing", "bin_long", "no_items", "no_price", "vat_no_rate", "third_party", "addendum_nobase"] as D[]) for (let k = 0; k < 3; k++) plan.push([d]);
for (const c of [["bin_missing", "no_price"], ["vat_no_rate", "third_party"], ["no_price", "addendum_nobase"]] as D[][]) for (let k = 0; k < 3; k++) plan.push(c);
const out: any[] = [];
async function main() {
  let i = 0;
  for (const defects of plan) {
    const c = doc(100 + i++, defects); const t0 = Date.now();
    try {
      const draft = await extractJrd(Buffer.from(c.text, "utf8"), "spec.csv", "text/csv");
      const crit = jrdCriteria(draft); const g = gate(crit, { minScore: 0.9 });
      const low = crit.filter((x) => !x.hard && x.s < 1).map((x) => x.code);
      const expectVeto = defects.some((d) => VETO.includes(d)); const expectLow = defects.filter((d) => LOW[d]).map((d) => LOW[d]);
      const routed = g.state !== "provisional";
      const criterionHit = expectVeto ? g.veto : expectLow.every((x) => low.includes(x));
      out.push({ id: c.id, defects, expectVeto, expectLow, veto: g.veto, vetoReason: g.vetoReason, state: g.state, sTotal: g.sTotal, low, routed, criterionHit, ms: Date.now() - t0 });
    } catch (e) { out.push({ id: c.id, defects, error: String((e as Error).message).slice(0, 200), ms: Date.now() - t0 }); }
    console.log(JSON.stringify(out[out.length - 1]));
  }
  writeFileSync(process.env.OUT!, JSON.stringify(out, null, 1));
}
main().catch((e) => { console.error(e); process.exit(1); });
