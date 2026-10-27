// ═══ /contracts/jrd шаг 5b: файл юриста → список предметов договора (20.10.2026) ═══
// юрист загружает то, что у него уже есть: Excel со спецификацией, протокол итогов закупки (PDF/Word),
// коммерческое предложение или фото таблицы. Gemini раскладывает по полям, человек проверяет таблицу
// на странице, потом Astra создаёт черновик в Salem из браузера пользователя (lib/salem-session/browser.ts).
// Excel/Word → текст (xlsx / mammoth) → geminiJson; PDF/фото → geminiVisionJson. Числа нормализуем кодом.
import * as XLSX from "xlsx";
import mammoth from "mammoth";
import { geminiText, geminiVisionJson } from "@/lib/gemini";
import { addendumBasis } from "@/apps/legal/lib/salem-jrd-flow";
import type { Criterion } from "@/lib/decision-ledger";

/** Мягкий разбор JSON модели: снимает ```-обёртки и текст вокруг, хвостовые запятые, //-комментарии.
 *  20.10 (юрист, договор услуг 1-337/26 «OSPANOV»): JSON.parse падал «Expected double-quoted property name». */
export function parseLooseJson(raw: string): any {
  let s = raw.replace(/^```(?:json)?\s*/i, "").replace(/```\s*$/, "").trim();
  const a = s.indexOf("{"), b = s.lastIndexOf("}");
  if (a >= 0 && b > a) s = s.slice(a, b + 1);
  try { return JSON.parse(s); } catch { /* чиним ниже */ }
  const fixed = s
    .replace(/\/\/[^\n"]*$/gm, "")             // комментарии до конца строки (вне строк с кавычками)
    .replace(/,\s*([}\]])/g, "$1")             // хвостовые запятые
    .replace(/([{,]\s*)([A-Za-z_]\w*)\s*:/g, '$1"$2":'); // ключи без кавычек
  return JSON.parse(fixed);
}

/** JSON от модели для разбора договора: большой лимит ответа (договор услуг с длинными описаниями не влезал
 *  в 2048 токенов общего geminiJson), мягкий разбор, при неудаче — одна просьба «верни исправленный JSON». */
async function askJson(prompt: string): Promise<any> {
  // 21.10 (юрист, 38 строк): «думанье» модели (~4.7 тыс. токенов) съедало лимит 8192, JSON обрывался → повторный вызов
  // «исправь JSON» → 46 + 57 с, а прокси МУИТ рвёт запрос на 60 с (504). Думать коротко, лимит с запасом.
  const raw = await geminiText(prompt, { tier: "answer", json: true, maxTokens: 16384, fastThinking: true, caller: "jrd-extract" });
  try { return parseLooseJson(raw); }
  catch (e) {
    const again = await geminiText(`Исправь синтаксис JSON (ничего не меняя по смыслу) и верни ТОЛЬКО JSON. Ошибка разбора: ${(e as Error).message}\n\n${raw.slice(0, 20_000)}`, { tier: "answer", json: true, maxTokens: 8192, caller: "jrd-extract" });
    return parseLooseJson(again);
  }
}

/** ktruHints — родовые названия «как в справочнике КТРУ» (20.10, юрист: «Перкуссия/Дабыл/Шаңқобыз» буквально не ищутся,
 *  а в КТРУ это «Инструмент музыкальный (ударный/язычковый)»). */
export type JrdItem = { name: string; description: string; qty: number; unit: string; unitPriceWithVat: number; ktruHints: string[] };
/** Реквизиты поставщика из договора/протокола — для карточки нового поставщика в Salem (lib/salem-org-body.ts). */
export type JrdSupplier = { name: string; bin: string; address: string; phone: string; email: string; iban: string; bank: string; bik: string; director: string };
export type JrdKind = "goods" | "services" | "works";
export type JrdAddendum = { baseNumber: string; baseDate: string };
/** Третья сторона — физлицо (трёхсторонний: «шлагбаум», юрист 20.10): ФИО, ИИН, контакты, роль в договоре. */
export type JrdPerson = { fio: string; iin: string; email: string; phone: string; role: string };
export type JrdDraft = {
  supplier: JrdSupplier;
  /** null — договор двусторонний. */
  thirdParty: JrdPerson | null;
  /** kind: что закупаем — товары/услуги/работы (20.10: договор услуг юриста 1-337/26 «OSPANOV»). */
  /** from/until — срок действия договора ГГГГ-ММ-ДД из текста («действует до 31.12.2027»), "" — не указан. */
  contract: { number: string; date: string; basis: string; vatRate: number; withVat: boolean; kind: JrdKind; from: string; until: string;
    /** Документ — доп. соглашение (23.10, юрист: ДС №1 к бумажному договору 1-317/26): номер и дата ОСНОВНОГО договора. null — обычный договор. */
    addendum: JrdAddendum | null };
  items: JrdItem[];
  warnings: string[];
};

const PROMPT = `Ты помощник юриста университета. Из документа (спецификация, протокол итогов закупки, коммерческое предложение)
извлеки данные для договора о закупке. Верни ТОЛЬКО JSON без пояснений:
{"supplier":{"name":"","bin":"","address":"","phone":"","email":"","iban":"","bank":"","bik":"","director":""},
 "contract":{"number":"","date":"ДД.ММ.ГГГГ","basis":"","vat_rate":16,"with_vat":true,"kind":"goods","from":"","until":"","addendum":null},
 "items":[{"name":"","description":"","qty":1,"unit":"Штука","unit_price_with_vat":0,"ktru_hints":["",""]}],
 "third_party":null}
Правила:
- third_party — ТОЛЬКО если в договоре кроме университета и поставщика/исполнителя есть ещё сторона-ФИЗЛИЦО
  («Сторона-2», «Пострадавшая сторона», «Получатель»): {"fio":"Фамилия Имя Отчество","iin":"12 цифр","email":"","phone":"","role":"Пострадавшая сторона"}.
  Двусторонний договор — third_party: null. Физлицо НЕ поставщик: supplier — организация/ИП, которая выполняет работы/поставляет.
- supplier.bin — 12 цифр БИН/ИИН поставщика (не университета 090440001325), иначе "".
- supplier.name — полное наименование с формой («Индивидуальный предприниматель «INSERVICE»», «ТОО «…»»).
- supplier.address/phone/email/iban/bank/bik/director — из реквизитов ПОСТАВЩИКА (не университета: не Манаса 34/1, не KZ… МУИТ).
  iban — счёт KZ… (20 знаков), bik — БИК банка, director — ФИО руководителя/ИП.
- kind — что закупается: "goods" (товары, «о закупках товаров»), "services" (услуги, «о закупках услуг», Исполнитель/Орындаушы),
  "works" (работы, «о закупках работ», Подрядчик).
- from/until — срок действия договора из текста («вступает в силу с … и действует до 31.12.2027») в формате ДД.ММ.ГГГГ;
  нет срока действия, но есть «срок выполнения работ / поставки / оказания услуг до 31 октября 2026» — until = эта дата; нет ничего — "".
- basis — основание, например «протокол об итогах закупок № 342/26 от 14.10.2026», иначе "".
- addendum — ТОЛЬКО если документ сам является дополнительным соглашением («Дополнительное соглашение №… к Договору…»,
  «…Шартқа №… Қосымша келісім»): {"base_number":"1-317/26","base_date":"05.10.2026"} — номер и дата ОСНОВНОГО договора,
  который соглашение меняет. Обычный договор — addendum: null. Тогда kind — по виду основного договора (товары/услуги/работы).
  Если это доп. соглашение, но номер или дата основного договора в документе НЕ указаны — всё равно верни addendum с пустыми строками
  {"base_number":"","base_date":""} (не null): юрист должен увидеть, что основание надо вписать.
- items — каждая строка таблицы товаров/работ/услуг. name — короткое общее название (как в справочнике: «Портрет», «Бумага для офисного оборудования», «Ручка канцелярская»),
  description — полное описание из документа (размеры, модель, цвет).
- ktru_hints — 1–3 РОДОВЫХ названия по-русски, как в госсправочнике КТРУ: что это по сути, без брендов, местных и казахских названий
  («Шаңқобыз» → «Инструмент музыкальный (язычковый)»; «Дабыл» → «Инструмент музыкальный (ударный)», «Барабан»;
  «ведущий мероприятия» → «Услуги по организации мероприятий»; «Dell P2725H» → «Монитор»).
- unit — единица измерения словом («Штука», «Упаковка», «Комплект», «Услуга», «Килограмм»…).
- unit_price_with_vat — цена за единицу С НДС числом. Если в документе цена без НДС, умножь на (1 + vat_rate/100).
- Если НДС нет («без НДС», «не является плательщиком НДС») — with_vat=false, vat_rate=0, цену бери как есть.
- vat_rate — ТОЛЬКО если ставка прямо написана цифрой («НДС 16%», «12%»); написано лишь «включая НДС» — vat_rate=0, with_vat=true.
  Не угадывай ставку по памяти (20.10: «включая НДС» без цифры модель превратила в 12%).
- Если цены в документе без НДС, а НДС начисляется сверху без цифры ставки — пересчитай по 16% (ставка РК с 2026).
- Не выдумывай: чего нет в документе — пустая строка или 0.`;

const num = (v: unknown): number => {
  if (typeof v === "number") return Number.isFinite(v) ? v : 0;
  const s = String(v ?? "").replace(/\s| /g, "").replace(",", ".").replace(/[^\d.]/g, "");
  const n = parseFloat(s);
  return Number.isFinite(n) ? n : 0;
};

const str = (v: unknown) => String(v ?? "").trim();

/** Ответ модели → строгая форма + предупреждения человеку. Чистая функция (тестируется без сети). */
/** «31.12.2027» / «2027-12-31» → «2027-12-31»; мусор и даты вне 2020–2040 → "". */
export function isoDate(v: unknown): string {
  const t = String(v ?? "").trim();
  const m = t.match(/^(\d{1,2})\.(\d{1,2})\.(\d{4})$/) ?? null;
  const [y, mo, d] = m ? [+m[3], +m[2], +m[1]] : (t.match(/^(\d{4})-(\d{2})-(\d{2})$/)?.slice(1).map(Number) ?? [0, 0, 0]);
  if (y < 2020 || y > 2040 || mo < 1 || mo > 12 || d < 1 || d > 31) return "";
  return `${y}-${String(mo).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}

export function normalizeDraft(raw: any): JrdDraft {
  const warnings: string[] = [];
  const bin = String(raw?.supplier?.bin ?? "").replace(/\D/g, "");
  if (bin && bin.length !== 12) warnings.push(`БИН/ИИН поставщика «${bin}» не из 12 цифр — проверьте.`);
  if (!bin) warnings.push("В файле не нашёлся БИН/ИИН поставщика — впишите его вручную.");
  const withVat = raw?.contract?.with_vat !== false;
  const rawRate = num(raw?.contract?.vat_rate);
  const vatRate = withVat ? (rawRate || 16) : 0;
  if (withVat && !rawRate) warnings.push("Ставка НДС в файле не указана цифрой — поставлено 16%. Проверьте поле «НДС».");
  const items: JrdItem[] = (Array.isArray(raw?.items) ? raw.items : [])
    .map((it: any) => ({
      name: String(it?.name ?? "").trim(),
      description: String(it?.description ?? it?.name ?? "").trim(),
      qty: num(it?.qty) || 1,
      unit: String(it?.unit ?? "Штука").trim() || "Штука",
      unitPriceWithVat: Math.round(num(it?.unit_price_with_vat) * 100) / 100,
      ktruHints: (Array.isArray(it?.ktru_hints) ? it.ktru_hints : []).map((h: unknown) => String(h ?? "").trim()).filter(Boolean).slice(0, 3),
    }))
    .filter((it: JrdItem) => it.name);
  const k = String(raw?.contract?.kind ?? "").toLowerCase();
  const kind: JrdKind = k.startsWith("serv") ? "services" : k.startsWith("work") ? "works" : "goods";
  if (!items.length) warnings.push("Не нашлось ни одной строки товара — добавьте строки вручную.");
  items.forEach((it, i) => { if (!it.unitPriceWithVat) warnings.push(`Строка ${i + 1} «${it.name}»: нет цены.`); });
  const tp = raw?.third_party;
  const thirdParty: JrdPerson | null = tp && str(tp.fio) ? {
    fio: str(tp.fio), iin: str(tp.iin).replace(/\D/g, "").slice(0, 12), email: str(tp.email), phone: str(tp.phone), role: str(tp.role) || "Пострадавшая сторона",
  } : null;
  if (thirdParty) warnings.push(`Договор трёхсторонний: третья сторона — физлицо ${thirdParty.fio}. Укажите его e-mail для подписи ЭЦП.`);
  const ad = raw?.contract?.addendum;
  // 26.10 (контролируемый эксперимент с подсаженными дефектами): ДС без номера и даты основного договора терялось — addendum был null,
  // и критерий «данные основания ДС» не срабатывал (0 из 4). Теперь объект addendum сохраняется и с пустыми полями.
  const addendum: JrdAddendum | null = ad && typeof ad === "object"
    ? { baseNumber: str(ad.base_number).replace(/^№\s*/, ""), baseDate: str(ad.base_date) } : null;
  let basis = String(raw?.contract?.basis ?? "").trim();
  if (addendum) {
    if (addendum.baseNumber || addendum.baseDate) basis = addendumBasis(addendum);   // в шаблоне ДС «Документальное основание» = основной договор
    if (!addendum.baseNumber || !addendum.baseDate) warnings.push("Доп. соглашение: не нашлись номер или дата основного договора — впишите в «Основание», например «№ 1-317/26 (05.10.2026)».");
  }
  return {
    thirdParty,
    supplier: {
      name: str(raw?.supplier?.name), bin,
      address: str(raw?.supplier?.address), phone: str(raw?.supplier?.phone), email: str(raw?.supplier?.email),
      iban: str(raw?.supplier?.iban).replace(/\s/g, "").toUpperCase(), bank: str(raw?.supplier?.bank),
      bik: str(raw?.supplier?.bik).replace(/\s/g, "").toUpperCase(), director: str(raw?.supplier?.director),
    },
    contract: { number: String(raw?.contract?.number ?? "").trim(), date: String(raw?.contract?.date ?? "").trim(), basis, vatRate, withVat, kind,
      from: isoDate(raw?.contract?.from), until: isoDate(raw?.contract?.until), addendum },
    items,
    warnings,
  };
}

/** Плоский вид договора для журнала решений ИИ (0740): ответ ИИ и то, что юрист отправил в Salem, сравниваются по этим полям. */
export function jrdFlat(d: { supplier: { bin: string; name: string; email: string; director: string }; contract: { number: string; basis: string; vatRate: number; withVat: boolean; kind: JrdKind; from: string; until: string };
  items: Array<{ qty: number; unitPriceWithVat: number }> }): Record<string, string> {
  const total = d.items.reduce((s, it) => s + (Number(it.qty) || 0) * (Number(it.unitPriceWithVat) || 0), 0);
  return {
    bin: d.supplier.bin, supplier: d.supplier.name, email: d.supplier.email, director: d.supplier.director,
    number: d.contract.number, basis: d.contract.basis, vat: d.contract.withVat ? String(d.contract.vatRate) : "0", kind: d.contract.kind,
    from: d.contract.from, until: d.contract.until, items: String(d.items.length), total: total ? total.toFixed(2) : "",
  };
}

/** Критерии решения по договору (журнал решений ИИ 0740): жёсткие — без них договор в Salem не создать (БИН из 12 цифр,
 *  хотя бы одна строка); мягкие — то, о чём normalizeDraft предупреждает юриста (цены, НДС, данные ДС, e-mail подписанта). */
export function jrdCriteria(d: JrdDraft): Criterion[] {
  const priced = d.items.length ? d.items.filter((it) => it.unitPriceWithVat > 0).length / d.items.length : 0;
  return [
    { code: "bin", s: /^\d{12}$/.test(d.supplier.bin) ? 1 : 0, hard: true },
    { code: "items", s: d.items.length ? 1 : 0, hard: true },
    { code: "prices", s: priced, w: 3 },
    { code: "vat_explicit", s: d.warnings.some((w) => w.startsWith("Ставка НДС")) ? 0 : 1, w: 1 },
    { code: "supplier_name", s: d.supplier.name ? 1 : 0, w: 1 },
    { code: "signer_email", s: d.supplier.email ? 1 : 0, w: 1 },
    { code: "addendum_base", s: d.contract.addendum && !(d.contract.addendum.baseNumber && d.contract.addendum.baseDate) ? 0 : 1, w: 2 },
    { code: "third_party_email", s: d.thirdParty && !d.thirdParty.email ? 0 : 1, w: 1 },
  ];
}

/** HTML от mammoth → таблицы текстом: строка таблицы = строка, ячейки через « | » как есть (равные соседние
 *  НЕ схлопывать: «цена 152 000 | сумма 152 000» при кол-ве 1). Чистая функция — тест в jrd-extract.test.ts. */
export function wordTables(html: string): string[] {
  const clean = (s: string) => s.replace(/<[^>]+>/g, " ").replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/&quot;/g, "\"").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/\s+/g, " ").trim();
  return [...html.matchAll(/<table[\s\S]*?<\/table>/g)].map(([t]) =>
    [...t.matchAll(/<tr[\s\S]*?<\/tr>/g)].map(([tr]) => {
      const cells = [...tr.matchAll(/<t[dh][^>]*>([\s\S]*?)<\/t[dh]>/g)].map((m) => clean(m[1]));
      return cells.some(Boolean) ? cells.join(" | ") : "";
    }).filter(Boolean).join("\n"),
  ).filter(Boolean);
}

/** Строки таблицы спецификации (из wordTables) → предметы кодом, без модели. 21.10 (юрист, подписка «Евразия пресс»,
 *  38 изданий на 3 690 000 ₸): модель возвращала одну первую строку. Шапка: наименование + цена; строка — первая ячейка
 *  номер. Остальные колонки («Срок подписки в месяцах: 12») — в описание. Цена «как в таблице»; если ИТОГО = сумма × (1+НДС),
 *  то в таблице цены без НДС — добавляем. null — таблица не похожа на спецификацию. Чистая функция. */
export function specItems(table: string, vatRate = 16): JrdItem[] | null {
  const lines = table.split("\n").map((l) => l.split(" | ").map((c) => c.trim()));
  const hi = lines.findIndex((c) => c.some((x) => /наименовани|атауы/i.test(x)) && c.some((x) => /цена|бағасы|стоимост/i.test(x)));
  if (hi < 0) return null;
  const head = lines[hi];
  const col = (re: RegExp, not?: RegExp) => head.findIndex((x) => re.test(x) && !(not && not.test(x)));
  const iName = col(/наименовани|атауы/i);
  const iQty = col(/кол-?во|количеств|саны/i);
  const iUnit = col(/ед\.? ?изм|өлшем/i);
  const iPrice = col(/цена за|за ед|бірлік бағасы|бағасы/i, /общ|жалпы|сумм/i);
  const iTotal = col(/общая|сумма|жалпы|итого/i);
  const used = new Set([0, iName, iQty, iUnit, iPrice, iTotal]);
  // Двухэтажная шапка (23.10, ДС Абиловой 1-317/26: «Стоимость материала: цена | сумма», «Стоимость работы: цена | сумма»,
  // «Всего тг без НДС»): строки данных длиннее шапки → колонки съезжают. Тогда итог строки = последняя ячейка
  // (шапка кончается «Всего/Итого/Сумма»), цена за ед. = итог / кол-во; подшапку и строку «1 | 2 | 3 …» пропускаем.
  const lastIsTotal = /всего|итого|сумма|жиыны|барлығы/i.test(head[head.length - 1] ?? "");
  const items: JrdItem[] = [];
  let sum = 0;
  for (const c of lines.slice(hi + 1)) {
    if (c.length > 2 && c.every((x, j) => x === String(j + 1))) continue;          // строка номеров колонок
    // накладные / транспортные / непредвиденные расходы — отдельные строки, без них ВСЕГО не сходится
    const label = c.find(Boolean) ?? "";
    if (/накладн|транспортн|непредвиден|үстеме|көлік|күтпеген/i.test(label)) {
      const v = num(c[c.length - 1]);
      if (v > 0) { items.push({ name: label, description: label, qty: 1, unit: "Услуга", unitPriceWithVat: v, ktruHints: [] }); sum += v; }
      continue;
    }
    if (!/^\d+\.?$/.test(c[0] ?? "") || !c[iName] || /^\d+$/.test(c[iName])) continue;
    const wide = c.length > head.length && lastIsTotal;
    const qty = (iQty >= 0 ? num(c[iQty]) : 0) || 1;
    const total = wide ? num(c[c.length - 1]) : iTotal >= 0 ? num(c[iTotal]) : 0;
    const price = wide ? (total ? total / qty : 0) : (iPrice >= 0 ? num(c[iPrice]) : 0) || (total ? total / qty : 0);
    const extra = wide ? [] : head.map((h, j) => (used.has(j) || !c[j] ? "" : `${h.replace(/^.*\/\s*/, "").trim()}: ${c[j]}`)).filter(Boolean);
    items.push({ name: c[iName], description: [c[iName], ...extra].join(", "), qty, unit: iUnit >= 0 && c[iUnit] ? c[iUnit] : "Штука", unitPriceWithVat: price, ktruHints: [] });
    sum += total || price * qty;
  }
  if (!items.length) return null;
  const itogo = lines.filter((c) => /итого|жиыны|всего/i.test(c.join(" "))).map((c) => Math.max(...c.map(num))).find((v) => v > 0) ?? 0;
  if (vatRate && itogo && Math.abs(itogo - sum * (1 + vatRate / 100)) < 1 && Math.abs(itogo - sum) >= 1)
    items.forEach((it) => { it.unitPriceWithVat = Math.round(it.unitPriceWithVat * (1 + vatRate / 100) * 100) / 100; });
  items.forEach((it) => { it.unitPriceWithVat = Math.round(it.unitPriceWithVat * 100) / 100; });
  return items;
}

/** Модель и код разошлись по строкам → берём строки кода (их больше), подсказки КТРУ — модели: по имени строки,
 *  иначе общие для всех (у подписки все строки «Периодическое печатное издание»). */
export function mergeSpecItems(draft: JrdDraft, rows: JrdItem[] | null): JrdDraft {
  if (!rows || rows.length <= draft.items.length) return draft;
  const byName = new Map(draft.items.map((it) => [it.name.toLowerCase(), it.ktruHints]));
  // модель видела только первые строки: если у них одинаковая родовая подсказка — она общая для всех
  const firsts = new Set(draft.items.map((it) => it.ktruHints[0] ?? ""));
  const common = draft.items.length && firsts.size === 1 && !firsts.has("") ? draft.items[0].ktruHints : [];
  const items = rows.map((r) => ({ ...r, ktruHints: byName.get(r.name.toLowerCase()) ?? common }));
  const warnings = draft.warnings.filter((w) => !/ни одной строки|нет цены/.test(w));
  items.forEach((it, i) => { if (!it.unitPriceWithVat) warnings.push(`Строка ${i + 1} «${it.name}»: нет цены.`); });
  return { ...draft, items, warnings };
}

/** Тип файла по имени/MIME. */
export function kindOf(name: string, mime: string): "excel" | "word" | "pdf" | "image" | null {
  const n = name.toLowerCase();
  if (/\.(xlsx|xls|csv)$/.test(n) || /spreadsheet|excel|csv/.test(mime)) return "excel";
  if (/\.docx$/.test(n) || /wordprocessingml/.test(mime)) return "word";
  if (/\.pdf$/.test(n) || mime === "application/pdf") return "pdf";
  if (/\.(png|jpe?g|webp)$/.test(n) || mime.startsWith("image/")) return "image";
  return null;
}

export async function extractJrd(buf: Buffer, name: string, mime: string): Promise<JrdDraft> {
  const kind = kindOf(name, mime);
  if (!kind) throw new Error("Поддерживаются Excel (.xlsx, .xls, .csv), Word (.docx), PDF и фото таблицы.");
  if (kind === "excel") {
    const wb = XLSX.read(buf, { type: "buffer" });
    const text = wb.SheetNames.slice(0, 5).map((s) => `## Лист «${s}»\n` + XLSX.utils.sheet_to_csv(wb.Sheets[s], { blankrows: false })).join("\n\n").slice(0, 60_000);
    return normalizeDraft(await askJson(`${PROMPT}\n\nДОКУМЕНТ (Excel, CSV по листам):\n${text}`));
  }
  if (kind === "word") {
    // 20.10 (юрист, «Договор ИП Arcad.docx»): extractRawText сплющивает таблицу спецификации в россыпь строк
    // среди 36 тыс. знаков двуязычного текста → строки терялись. Теперь таблицы — построчно «ячейка | ячейка»,
    // таблица спецификации и реквизиты идут ПЕРВЫМИ, текст договора — после.
    const { value: html } = await mammoth.convertToHtml({ buffer: buf });
    const { value: text } = await mammoth.extractRawText({ buffer: buf });
    const tables = wordTables(html);
    // У юристов МУИТ весь текст договора — тоже таблица (две колонки KZ|RU), поэтому огромные таблицы не берём в «спецификацию»
    const spec = tables.filter((t) => t.length < 8000 && /наименовани|атауы|ед\.? ?изм|количеств|саны|цена за|бағасы|реквизит|деректеме/i.test(t));
    const body = [
      spec.length ? `ТАБЛИЦЫ СПЕЦИФИКАЦИИ И РЕКВИЗИТОВ (строка = строка таблицы, ячейки через « | »):\n${spec.join("\n\n")}` : "",
      `ТЕКСТ ДОГОВОРА:\n${text}`,
    ].filter(Boolean).join("\n\n").slice(0, 60_000);
    // Строки спецификации уже прочитаны кодом → модель не переписывает их назад (длинный ответ = 504 на прокси):
    // просим реквизиты + до 3 строк для подсказок КТРУ. Ставку НДС берём из ответа модели, цены — пересчитываем кодом.
    const pre = spec.map((t) => specItems(t, 0)).find((r) => r && r.length) ?? null;
    const note = pre && pre.length > 3
      ? `\n- Таблица спецификации (${pre.length} строк) уже прочитана программой: в items верни ТОЛЬКО первые 3 строки (для ktru_hints), остальные не переписывай.`
      : "";
    const draft = normalizeDraft(await askJson(`${PROMPT}\n- В Word-договоре строки товаров бери из таблицы спецификации (Приложение №1), реквизиты поставщика — из таблицы реквизитов.${note}\n\nДОКУМЕНТ (Word):\n${body}`));
    const rows = spec.map((t) => specItems(t, draft.contract.withVat ? draft.contract.vatRate : 0)).find((r) => r && r.length) ?? null;
    return mergeSpecItems(draft, rows);
  }
  const raw = await geminiVisionJson(PROMPT, buf.toString("base64"), kind === "pdf" ? "application/pdf" : (mime || "image/jpeg"), undefined, 4096, undefined, "jrd-extract");
  return normalizeDraft(raw);
}
