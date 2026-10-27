// HOLD-OUT 2 (27.10.2026, after Codex R13-02): a NEW confirmatory set, generated only AFTER the final C5 code was frozen
// (ablation_freeze.sha256, entry 883d602a). Same defect families as before, but new suppliers, a pipe-separated table with
// prices in tenge with tiyn decimals and NBSP thousands separators, new wording for every defect ("трехсторонний" without ё,
// "ИИН/БИН", VAT without a rate phrased differently, addendum named "Дополнительное соглашение № 5 к договору поставки")
// and new compound defects. ONE LLM call per document; outputs frozen like freeze_contracts.ts. Synthetic data only.
import { extractJrd } from "./apex_jrd_frozen";
import { writeFileSync } from "node:fs";

type D = "bin_short" | "bin_missing" | "bin_long" | "no_items" | "no_price" | "vat_no_rate" | "third_party" | "addendum_nobase";
const goods: [string, number, string, number][] = [["Перчатки нитриловые (уп. 100 шт.)", 20, "упаковка", 3490.5], ["Антисептик для рук 1 л", 35, "флакон", 1875.25],
  ["Батарейки AA (уп. 4 шт.)", 50, "упаковка", 1290.0], ["Лампа светодиодная E27 12 Вт", 60, "штука", 845.75], ["Кабель HDMI 3 м", 12, "штука", 2760.4],
  ["Папка-скоросшиватель пластиковая", 150, "штука", 185.9], ["Скрепки 28 мм (уп. 100 шт.)", 80, "упаковка", 210.0]];
const names = ["ТОО «Нова Ресурс Синтез»", "ИП «Орион Поставка Тест»", "ТОО «Вега Снаб Пример»", "ИП «Лира Офис Модель»", "ТОО «Альтаир Трейд Демо»"];
// decimal POINT (a decimal comma would be split into two cells by the CSV reader before the model sees it)
const money = (v: number) => { const [a, c] = v.toFixed(2).split("."); return a.replace(/\B(?=(\d{3})+(?!\d))/g, " ") + "." + c; };
function doc(i: number, defects: D[]) {
  const name = names[i % names.length]; const b = String(910000000000 + i * 65537).slice(0, 12);
  let rows = goods.slice(i % 5, (i % 5) + 3).map((g) => [...g]) as any[];
  let bin = `ИИН/БИН: ${b}`; let vat = "НДС 16% включен в стоимость."; const extra: string[] = [];
  for (const d of defects) {
    if (d === "bin_short") bin = `ИИН/БИН: ${b.slice(0, 11)}`;
    if (d === "bin_missing") bin = "";
    if (d === "bin_long") bin = `ИИН/БИН: ${b}4`;
    if (d === "no_items") rows = [];
    if (d === "no_price" && rows.length) rows[0][3] = null;
    if (d === "vat_no_rate") vat = "Стоимость указана с учетом налога на добавленную стоимость.";
    if (d === "third_party") extra.push("Договор является трехсторонним: Сторона 3 — физическое лицо Синтезов Модель Тестович, ИИН 870303000000.");
    if (d === "addendum_nobase") extra.push("Дополнительное соглашение № 5 к договору поставки (номер и дата основного договора будут указаны позднее).");
  }
  const table = ["№ | Наименование | Количество | Ед. изм. | Цена за ед., тенге с НДС", ...rows.map((r, k) => `${k + 1} | ${r[0]} | ${r[1]} | ${r[2]} | ${r[3] == null ? "—" : money(r[3])}`)].join("\n");
  const text = ["ЗАЯВКА НА ПОСТАВКУ (синтетические данные для исследования)", `Наименование поставщика: ${name}`, bin, `Эл. почта для подписи договора: sign${i}@example.net`,
    "Директор: Синтезов С.С.", vat, ...extra, "", table].filter((l) => l !== "").join("\n");
  return { set: "holdout2", id: `${defects.join("+") || "clean"}-q${i}`, defects, text };
}
const plan: D[][] = [];
for (let n = 0; n < 10; n++) plan.push([]);
for (const d of ["bin_short", "bin_missing", "bin_long", "no_items", "no_price", "vat_no_rate", "third_party", "addendum_nobase"] as D[]) for (let n = 0; n < 3; n++) plan.push([d]);
for (const c of [["bin_long", "third_party"], ["no_price", "vat_no_rate"], ["addendum_nobase", "third_party"]] as D[][]) for (let n = 0; n < 3; n++) plan.push(c);
const recs = plan.map((defects, k) => doc(200 + k, defects));

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
    console.log(JSON.stringify({ id: last.id, ok: !last.error, ms: last.ms }));
  }
  writeFileSync(process.env.OUT!, JSON.stringify(out, null, 1));
}
main().catch((e) => { console.error(e); process.exit(1); });
