// ABLATION STAGE 1 (27.10.2026, Bykov's review): ONE LLM call per synthetic document, outputs FROZEN to a file.
// Every ablation configuration (C1–C5, ablation.ts) is later computed from these same frozen outputs, so the effect of the
// rules is never mixed with generation variability. Extraction code = the paper's frozen copy (artifact_make/src/jrd-extract.ts,
// commit 1114a138) placed as apex_jrd_frozen.ts with one line added: normalizeDraft stores its raw input (the model's JSON).
// Dev set = 36 docs of run.ts; held-out set = 43 docs of run_holdout.ts (same generators, unchanged). OUT env = result file.
// Model is pinned by GEMINI_CASCADE_ANSWER. Synthetic data only.
import { extractJrd } from "./apex_jrd_frozen";
import { writeFileSync } from "node:fs";

type Rec = { set: "dev" | "holdout"; id: string; defects: string[]; text: string; truth?: { bin: string; total: number; items: number } };

// ---- dev generator (verbatim from run.ts) ----
const goodsA = [["Бумага для офисной техники А4", "пачка", 50, 2450], ["Ручка шариковая синяя", "штука", 200, 120], ["Папка-регистратор 75 мм", "штука", 40, 1350],
  ["Картридж для принтера HP 85A", "штука", 6, 18900], ["Степлер настольный", "штука", 10, 2900], ["Маркер для доски", "штука", 60, 450]];
const namesA = ["ТОО «Альфа Офис Синтетик»", "ТОО «Бета Снаб Тест»", "ИП «Гамма Синтез»", "ТОО «Дельта Канц Демо»", "ТОО «Эпсилон Трейд Модель»", "ИП «Зета Поставка Пример»"];
const binA = (i: number) => String(990000000000 + i * 7919).slice(0, 12);
function devDoc(i: number, defect: string): Rec {
  const n = namesA[i % namesA.length]; const b = binA(i + 1);
  let rows = goodsA.slice(i % 3, (i % 3) + 3).map((g) => [...g]);
  let binLine = `БИН: ${b}`; let vatLine = "Цены указаны с учётом НДС 16%"; let extra = ""; let truthBin = b;
  if (defect === "bin_short") { binLine = `БИН: ${b.slice(0, 11)}`; truthBin = b.slice(0, 11); }
  if (defect === "bin_missing") { binLine = ""; truthBin = ""; }
  if (defect === "no_items") { rows = []; }
  if (defect === "no_price") { rows[1][3] = ""; }
  if (defect === "vat_no_rate") { vatLine = "Цены указаны с учётом НДС"; }
  if (defect === "third_party") { extra = "Третья сторона (физическое лицо): Синтетиков Тест Тестович, ИИН 990101000000, роль: пострадавшая сторона"; }
  if (defect === "addendum_nobase") { extra = "ДОПОЛНИТЕЛЬНОЕ СОГЛАШЕНИЕ № 1 к договору о закупках (номер и дата основного договора не указаны)"; }
  const table = ["№;Наименование;Ед. изм.;Количество;Цена за ед. с НДС, тг", ...rows.map((r, k) => `${k + 1};${r[0]};${r[1]};${r[2]};${r[3]}`)].join("\n");
  const text = [`Коммерческое предложение (СИНТЕТИЧЕСКИЕ ДАННЫЕ ДЛЯ ИССЛЕДОВАНИЯ)`, `Поставщик: ${n}`, binLine, `E-mail: sales${i}@example.kz`, `Директор: Тестов Т.Т.`, vatLine, extra, "", table].filter((l) => l !== "").join("\n");
  const total = rows.reduce((s, r) => s + Number(r[2]) * (Number(r[3]) || 0), 0);
  return { set: "dev", id: `${defect}-${i}`, defects: defect === "clean" ? [] : [defect], text, truth: { bin: truthBin, total, items: rows.length } };
}
const devDefects = ["clean", "bin_short", "bin_missing", "no_items", "no_price", "vat_no_rate", "third_party", "addendum_nobase"];
const recs: Rec[] = []; let k = 0;
for (const d of devDefects) for (let j = 0; j < (d === "clean" ? 8 : 4); j++) recs.push(devDoc(k++, d));

// ---- held-out generator (verbatim from run_holdout.ts) ----
type D = "bin_short" | "bin_missing" | "bin_long" | "no_items" | "no_price" | "vat_no_rate" | "third_party" | "addendum_nobase";
const goodsB = [["Тонер-картридж Canon 725", 8, "шт.", 21500], ["Флеш-накопитель 64 ГБ", 30, "шт.", 4900], ["Бумага А3 80 г/м²", 12, "пачка", 5600],
  ["Клавиатура проводная USB", 15, "шт.", 7300], ["Мышь оптическая", 15, "шт.", 3900], ["Удлинитель сетевой 5 м", 10, "шт.", 4200], ["Скотч упаковочный 48 мм", 40, "рулон", 650]];
const namesB = ["ТОО «Омега Ресурс Пример»", "ИП «Каппа Трейд Синтетик»", "ТОО «Сигма Снабжение Демо»", "ИП «Тау Офис Модель»", "ТОО «Лямбда Поставка Тест»"];
const money = (v: number) => v.toLocaleString("ru-RU").replace(/ /g, " ") + " тг";
function hDoc(i: number, defects: D[]): Rec {
  const name = namesB[i % namesB.length]; const b = String(870000000000 + i * 104729).slice(0, 12);
  let rows = goodsB.slice(i % 4, (i % 4) + 3).map((g) => [...g]) as any[];
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
  return { set: "holdout", id: `${defects.join("+") || "clean"}-h${i}`, defects, text };
}
const plan: D[][] = [];
for (let n = 0; n < 10; n++) plan.push([]);
for (const d of ["bin_short", "bin_missing", "bin_long", "no_items", "no_price", "vat_no_rate", "third_party", "addendum_nobase"] as D[]) for (let n = 0; n < 3; n++) plan.push([d]);
for (const c of [["bin_missing", "no_price"], ["vat_no_rate", "third_party"], ["no_price", "addendum_nobase"]] as D[][]) for (let n = 0; n < 3; n++) plan.push(c);
let h = 0; for (const defects of plan) recs.push(hDoc(100 + h++, defects));

async function main() {
  const model = process.env.GEMINI_CASCADE_ANSWER ?? "default";
  const out: any[] = [];
  for (const r of recs) {
    const t0 = Date.now(); (globalThis as any).__lastRaw = undefined;
    try {
      const draft = await extractJrd(Buffer.from(r.text, "utf8"), "spec.csv", "text/csv");
      out.push({ ...r, model, raw: (globalThis as any).__lastRaw ?? null, draft, error: null, ms: Date.now() - t0 });
    } catch (e) {
      out.push({ ...r, model, raw: (globalThis as any).__lastRaw ?? null, draft: null, error: String((e as Error).message).slice(0, 300), ms: Date.now() - t0 });
    }
    const last = out[out.length - 1];
    console.log(JSON.stringify({ id: last.id, set: last.set, ok: !last.error, ms: last.ms }));
  }
  writeFileSync(process.env.OUT!, JSON.stringify(out, null, 1));
}
main().catch((e) => { console.error(e); process.exit(1); });
