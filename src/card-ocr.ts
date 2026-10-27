// QS · распознавание визитки: фото → поля контакта (заведующий кафедрой 28.09 со слов Дузбаева Н.Т.: «сканирование и распознавание
// визиток для внесения контактов; чего нет в визитке — внести вручную»). Фото НЕ сохраняется (чужие персональные данные).
import { geminiVisionJson } from "@/lib/gemini";
import { normalizeCountry } from "@/apps/kafedra/lib/qs/countries";
import type { Criterion } from "@/lib/decision-ledger";

export type CardFields = { title: string; first_name: string; last_name: string; job_title: string; department: string; organization: string; country: string; email: string; phone: string };
export type CardResult = { fields: CardFields; confidence: number; notes: string; inferred: string[] };

/** Справочник Title из QS (0389) — значение вне списка не подставляем. */
export const CARD_TITLES = ["Mr", "Ms", "Mrs", "Miss", "Dr", "Prof", "Professor", "Associate Professor", "Assistant Professor", "Other"];

const str = (v: unknown, max = 200) => String(v ?? "").replace(/\s+/g, " ").trim().slice(0, max);

/** Чистая нормализация ответа модели: только то, что похоже на правду; пустое остаётся пустым. */
export function normalizeCard(raw: Record<string, unknown> | null | undefined): CardFields {
  const r = raw ?? {};
  const email = (String(r.email ?? "").match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i)?.[0] ?? "").toLowerCase();
  const phoneRaw = String(r.phone ?? "").match(/\+?[\d][\d\s().-]{5,}\d/)?.[0] ?? "";
  const phone = phoneRaw.replace(/\s+/g, " ").trim();
  const digits = phone.replace(/\D/g, "").length;
  const titleKey = str(r.title, 40).replace(/\./g, "").toLowerCase();
  const title = CARD_TITLES.find((t) => t.toLowerCase() === titleKey) ?? "";
  const countryRaw = str(r.country, 60);
  // 02.10.2026 (#91): страна — по общему списку формы (lib/qs/countries.ts); неизвестное остаётся как распознано
  const country = normalizeCountry(countryRaw).value;
  return {
    title, first_name: str(r.first_name, 80), last_name: str(r.last_name, 80), job_title: str(r.job_title), department: str(r.department),
    organization: str(r.organization), country, email, phone: digits >= 7 && digits <= 15 ? phone : "",
  };
}

const SCHEMA = { type: "object", properties: {
  title: { type: "string" }, first_name: { type: "string" }, last_name: { type: "string" }, job_title: { type: "string" }, department: { type: "string" },
  organization: { type: "string" }, country: { type: "string" }, email: { type: "string" }, phone: { type: "string" }, confidence: { type: "number" }, notes: { type: "string" },
  inferred: { type: "array", items: { type: "string" } },
}, required: ["first_name", "last_name", "email", "organization", "confidence"] };

const PROMPT = `You read a photo of ONE business card. Extract ONLY what is printed on the card; never guess or invent a missing field — leave it as an empty string.
If the card has several languages, prefer the Latin-script (English) version. Put the person's given name in first_name and family name in last_name (no titles in names).
title: one of Mr, Ms, Mrs, Miss, Dr, Prof, Professor, Associate Professor, Assistant Professor — only if printed, else "".
job_title: the position; department: faculty/department if printed; organization: university or company name; country: country name in English if printed or clearly implied by the address, else "".
email: the work e-mail printed on the card; phone: the main phone with country code if printed.
Return JSON { title, first_name, last_name, job_title, department, organization, country, email, phone, confidence (0..1: how sure you are the extraction is correct), notes (short remark, e.g. "blurry photo", else ""),
inferred (list of field names whose value is NOT printed on the card as such but deduced from something else, e.g. a name taken from the e-mail address or a country taken from a phone code or city; [] if every value is printed) }.`;

/** Критерии решения по визитке (журнал решений ИИ 0740, lib/decision-ledger): жёсткие — без них контакт не создать
 *  (createAcademic/createEmployer требуют e-mail, имя, фамилию, организацию); мягкие — то, за что проверяющий QS возвращает
 *  контакт «на доработку» (страна, должность, кафедра — причины needs_fix в qs_audit), плюс формат телефона и Title из списка. */
/** Поля, которые модель вывела, а не прочитала (только известные ключи). */
export function inferredFields(v: unknown): string[] {
  const keys = ["title", "first_name", "last_name", "job_title", "department", "organization", "country", "email", "phone"];
  return Array.isArray(v) ? Array.from(new Set(v.map((x) => String(x ?? "").trim()).filter((x) => keys.includes(x)))) : [];
}

/** 26.10 (эксперимент с синтетическими визитками): без имени на визитке модель восстанавливала его из e-mail (0 из 4 пойманы),
 *  страну — из города/кода телефона. Происхождение значения (p_i модели): имя, которого нет на визитке, — вето; выведенная страна — мягко. */
export function cardCriteria(f: CardFields, inferred: string[] = []): Criterion[] {
  const has = (v: string) => (v.trim() ? 1 : 0);
  const nameInferred = inferred.includes("first_name") || inferred.includes("last_name");
  return [
    { code: "email", s: /^[^@\s]+@[^@\s]+\.[a-z]{2,}$/i.test(f.email) ? 1 : 0, hard: true },
    { code: "name", s: f.first_name.trim() && f.last_name.trim() && !nameInferred ? 1 : 0, hard: true },
    { code: "provenance", s: inferred.length ? 0 : 1, w: 1 },
    { code: "organization", s: has(f.organization) && !inferred.includes("organization") ? 1 : 0, hard: true },   // итерация 3: организация из домена e-mail — вето
    { code: "country", s: has(f.country), w: 2 },
    { code: "job_title", s: has(f.job_title), w: 2 },
    { code: "department", s: has(f.department), w: 1 },
    { code: "phone", s: has(f.phone), w: 0.5 },
    { code: "title", s: has(f.title), w: 0.5 },
  ];
}

export async function readBusinessCard(bytes: Buffer, mime: string, caller = "qs.card"): Promise<CardResult> {
  const r = await geminiVisionJson<Record<string, unknown>>(PROMPT, bytes.toString("base64"), mime, SCHEMA, 1024, undefined, caller);
  return { fields: normalizeCard(r), confidence: Math.max(0, Math.min(1, Number(r?.confidence ?? 0))), notes: str(r?.notes, 160), inferred: inferredFields(r?.inferred) };
}
