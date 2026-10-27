// OPERATION APEX — controlled planted-defect evaluation of contract extraction + criteria operator (synthetic data only).
import { extractJrd, jrdCriteria, jrdFlat } from "@/apps/legal/lib/jrd-extract";
import { gate } from "@/lib/decision-ledger";
import { writeFileSync } from "node:fs";

type Case = { id: string; defect: string; expectVeto: string | null; expectLow: string | null; csv: string; truth: { bin: string; total: number; items: number } };
const goods = [["Бумага для офисной техники А4", "пачка", 50, 2450], ["Ручка шариковая синяя", "штука", 200, 120], ["Папка-регистратор 75 мм", "штука", 40, 1350],
  ["Картридж для принтера HP 85A", "штука", 6, 18900], ["Степлер настольный", "штука", 10, 2900], ["Маркер для доски", "штука", 60, 450]];
const names = ["ТОО «Альфа Офис Синтетик»", "ТОО «Бета Снаб Тест»", "ИП «Гамма Синтез»", "ТОО «Дельта Канц Демо»", "ТОО «Эпсилон Трейд Модель»", "ИП «Зета Поставка Пример»"];
const bin = (i: number) => String(990000000000 + i * 7919).slice(0, 12);
function doc(i: number, defect: string): Case {
  const n = names[i % names.length]; const b = bin(i + 1);
  let rows = goods.slice(i % 3, (i % 3) + 3).map((g) => [...g]);
  let binLine = `БИН: ${b}`; let vatLine = "Цены указаны с учётом НДС 16%"; let extra = ""; let expectVeto: string | null = null; let expectLow: string | null = null; let truthBin = b;
  if (defect === "bin_short") { binLine = `БИН: ${b.slice(0, 11)}`; expectVeto = "bin"; truthBin = b.slice(0, 11); }
  if (defect === "bin_missing") { binLine = ""; expectVeto = "bin"; truthBin = ""; }
  if (defect === "no_items") { rows = []; expectVeto = "items"; }
  if (defect === "no_price") { rows[1][3] = ""; expectLow = "prices"; }
  if (defect === "vat_no_rate") { vatLine = "Цены указаны с учётом НДС"; expectLow = "vat_explicit"; }
  if (defect === "third_party") { extra = "Третья сторона (физическое лицо): Синтетиков Тест Тестович, ИИН 990101000000, роль: пострадавшая сторона"; expectLow = "third_party_email"; }
  if (defect === "addendum_nobase") { extra = "ДОПОЛНИТЕЛЬНОЕ СОГЛАШЕНИЕ № 1 к договору о закупках (номер и дата основного договора не указаны)"; expectLow = "addendum_base"; }
  const table = ["№;Наименование;Ед. изм.;Количество;Цена за ед. с НДС, тг", ...rows.map((r, k) => `${k + 1};${r[0]};${r[1]};${r[2]};${r[3]}`)].join("\n");
  const csv = [`Коммерческое предложение (СИНТЕТИЧЕСКИЕ ДАННЫЕ ДЛЯ ИССЛЕДОВАНИЯ)`, `Поставщик: ${n}`, binLine, `E-mail: sales${i}@example.kz`, `Директор: Тестов Т.Т.`, vatLine, extra, "", table].filter((l) => l !== "").join("\n");
  const total = rows.reduce((s, r) => s + Number(r[2]) * (Number(r[3]) || 0), 0);
  return { id: `${defect}-${i}`, defect, expectVeto, expectLow, csv, truth: { bin: truthBin, total, items: rows.length } };
}
const defects = ["clean", "bin_short", "bin_missing", "no_items", "no_price", "vat_no_rate", "third_party", "addendum_nobase"];
const cases: Case[] = []; let k = 0;
for (const d of defects) for (let j = 0; j < (d === "clean" ? 8 : 4); j++) cases.push(doc(k++, d));
const out: any[] = [];
async function main() {
for (const c of cases) {
  const t0 = Date.now();
  try {
    const draft = await extractJrd(Buffer.from(c.csv, "utf8"), "spec.csv", "text/csv");
    const crit = jrdCriteria(draft); const g = gate(crit); const flat = jrdFlat(draft);
    const low = crit.filter((x) => !x.hard && x.s < 1).map((x) => x.code);
    out.push({ id: c.id, defect: c.defect, expectVeto: c.expectVeto, expectLow: c.expectLow, veto: g.veto, vetoReason: g.vetoReason, state: g.state, sTotal: g.sTotal, low,
      binOk: flat.bin === c.truth.bin, itemsOk: Number(flat.items) === c.truth.items, totalOk: Math.abs(Number(flat.total || 0) - c.truth.total) < 1, ms: Date.now() - t0, warnings: draft.warnings.length });
  } catch (e) { out.push({ id: c.id, defect: c.defect, error: String((e as Error).message).slice(0, 200), ms: Date.now() - t0 }); }
  console.log(JSON.stringify(out[out.length - 1]));
}
writeFileSync("/tmp/apex/results.json", JSON.stringify(out, null, 1));
}
main().catch((e) => { console.error(e); process.exit(1); });
